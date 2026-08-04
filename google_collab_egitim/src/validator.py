# ============================================================
# v4.1 Validator — LLM çıktı doğrulama ve düzeltme
# ============================================================
"""
Model JSON çıktılarını doğrular, hatalı alanları düzeltir,
tutarsızlıkları giderir.

Doğrulama kuralları:
  - JSON parse edilebiliyor mu?
  - karar izin verilen değerlerden biri mi?
  - guven 0-1 aralığında mı?
  - kaynak_idleri sunulan ID'ler arasında mı?
  - "dogru" kararı boş kaynak listesiyle verilmiş mi? → kanit_yetersiz
  - "dogru" kararında düzeltilmiş cevap boş mu?
"""

import re
from typing import Any, Dict, List, Optional, Set

from .utils import json_guvenli_yukle


# ============================================================
# Sabitler
# ============================================================
GECERLI_KARARLAR: Set[str] = {
    "dogru",
    "kismen_dogru",
    "yanlis",
    "kanit_yetersiz",
    "soru_belirsiz",
    "error",
    "cevap_bos",
}


# ============================================================
# Çıktı Parse Etme
# ============================================================
def vllm_cikti_parse(cikti) -> Optional[str]:
    """
    vLLM çıktı nesnesinden ham metni güvenli şekilde çıkarır.
    NoneType / eksik outputs durumlarını yakalar.

    Returns:
        Ham metin veya None
    """
    if cikti is None:
        return None
    if not hasattr(cikti, "outputs") or not cikti.outputs:
        return None
    try:
        return cikti.outputs[0].text.strip()
    except (AttributeError, IndexError, TypeError):
        return None


def ham_metinden_json_cikar(
    ham_metin: str,
    sunulan_idler: Optional[Set[int]] = None,
) -> Dict[str, Any]:
    """
    Ham model metninden JSON parse eder ve doğrular.

    Args:
        ham_metin: Modelin ürettiği ham metin
        sunulan_idler: Prompt'ta sunulan chunk_id'lerin kümesi

    Returns:
        Doğrulanmış sonuç sözlüğü. Hata durumunda _islem_hatasi=True içerir.
    """
    sonuc = _varsayilan_hata_sonuc("JSON parse edilemedi")

    if not ham_metin:
        return sonuc

    # Markdown temizleme
    metin = ham_metin.strip()
    metin = re.sub(r"```(?:json)?\s*", "", metin).replace("```", "").strip()

    # JSON bloğu bul
    basla = metin.find("{")
    bitir = metin.rfind("}")
    if basla >= 0 and bitir > basla:
        metin = metin[basla : bitir + 1]

    try:
        import json
        ham = json.loads(metin)
    except json.JSONDecodeError as e:
        return {
            "karar": "error",
            "guven": 0.0,
            "kaynak_idleri": [],
            "dayanak": f"JSON parse hatası: {str(e)[:200]}",
            "eksik_veya_hata": "",
            "duzeltilmis_cevap": "",
            "_islem_hatasi": True,
        }

    return sonuc_dogrula(ham, sunulan_idler or set())


def sonuc_dogrula(
    ham_sonuc: Dict[str, Any],
    sunulan_idler: Set[int],
) -> Dict[str, Any]:
    """
    Ham JSON sözlüğünü doğrular ve düzeltir.

    Kurallar:
      1. karar geçersizse → soru_belirsiz
      2. guven 0-1 dışındaysa → sınırlandır
      3. kaynak_idleri sunulanlar dışındaysa → filtrele
      4. "dogru" + boş kaynak → kanit_yetersiz
      5. "dogru" + dolu düzeltilmiş cevap → boşalt
    """
    sonuc = dict(ham_sonuc)
    sonuc["_islem_hatasi"] = False

    # 1. Karar doğrulama
    karar = str(sonuc.get("karar", "")).lower().strip()
    if karar not in GECERLI_KARARLAR:
        sonuc["karar"] = "soru_belirsiz"
    else:
        sonuc["karar"] = karar

    # 2. Güven doğrulama
    try:
        guven = float(sonuc.get("guven", 0))
        sonuc["guven"] = max(0.0, min(1.0, guven))
    except (ValueError, TypeError):
        sonuc["guven"] = 0.0

    # 3. Kaynak ID doğrulama
    try:
        ham_idler = sonuc.get("kaynak_idleri", [])
        if not isinstance(ham_idler, list):
            ham_idler = []
        if sunulan_idler:
            sonuc["kaynak_idleri"] = [
                int(x) for x in ham_idler if int(x) in sunulan_idler
            ]
        else:
            sonuc["kaynak_idleri"] = [int(x) for x in ham_idler]
    except (ValueError, TypeError):
        sonuc["kaynak_idleri"] = []

    # 4. String alanları düzelt
    for alan in ["dayanak", "eksik_veya_hata", "duzeltilmis_cevap"]:
        if not isinstance(sonuc.get(alan), str):
            sonuc[alan] = str(sonuc.get(alan, ""))

    # 5. dogru + boş kaynak → kanit_yetersiz
    if sonuc["karar"] == "dogru" and not sonuc["kaynak_idleri"]:
        sonuc["karar"] = "kanit_yetersiz"
        sonuc["guven"] = 0.0
        sonuc["dayanak"] = "Geçerli bir kaynak parçasına dayanılmadı."

    # 6. dogru → düzeltilmiş cevap boş olmalı
    if sonuc["karar"] == "dogru":
        sonuc["duzeltilmis_cevap"] = ""

    return sonuc


def _varsayilan_hata_sonuc(mesaj: str = "") -> Dict[str, Any]:
    """Varsayılan hata sonucu."""
    return {
        "karar": "error",
        "guven": 0.0,
        "kaynak_idleri": [],
        "dayanak": mesaj,
        "eksik_veya_hata": "",
        "duzeltilmis_cevap": "",
        "_islem_hatasi": True,
    }


# ============================================================
# Toplu Çıktı Doğrulama
# ============================================================
def batch_ciktilari_dogrula(
    ciktilar: List[Any],
    kayit_bilgileri: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Batch model çıktılarını sırayla doğrular.
    Her kayıt için kayit_bilgileri içindeki sunulan_idler kullanılır.

    Args:
        ciktilar: vLLM çıktı nesneleri listesi
        kayit_bilgileri: Her kayıt için {"sunulan_idler": set(), "bos_mu": bool, ...}

    Returns:
        Doğrulanmış sonuç listesi
    """
    sonuclar = []
    cikti_idx = 0

    for bilgi in kayit_bilgileri:
        if bilgi.get("bos_mu"):
            # Cevap boş veya kaynaksız → model çağrılmadı
            if bilgi.get("cevap_bos"):
                from .prompt_builder import cevap_bos_yanit
                sonuc = cevap_bos_yanit()
            else:
                from .prompt_builder import kanit_yetersiz_yanit
                sonuc = kanit_yetersiz_yanit()
        else:
            cikti = ciktilar[cikti_idx] if cikti_idx < len(ciktilar) else None
            cikti_idx += 1

            ham_metin = vllm_cikti_parse(cikti)
            if ham_metin is None:
                from .prompt_builder import islem_hatasi_yanit
                sonuc = islem_hatasi_yanit("NoneType / eksik outputs")
            else:
                sunulan_idler = bilgi.get("sunulan_idler", set())
                sonuc = ham_metinden_json_cikar(ham_metin, sunulan_idler)

        sonuclar.append(sonuc)

    return sonuclar