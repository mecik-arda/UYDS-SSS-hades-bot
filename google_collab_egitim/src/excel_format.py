# ============================================================
# excel_format.py — Excel başlık algılama ve format tespiti
# ============================================================
"""
UYDS ve standart Excel formatlarını tespit eder.

UYDS formatı (5 zorunlu alan):
  Modül, Konu, Açıklama, Yapılacak, Yapılan İşlem

Standart format (2 zorunlu alan):
  Soru, Cevap  (Kategori opsiyonel)

Hem veri_ayiklama_v4.1.ipynb hem test/excel_format testleri aynı
mantığı kullansın diye burada toplanır.
"""

from typing import Dict, Iterable, List, Optional, Tuple

from src.utils import adi_normalize_et

BILINEN_BASLIKLAR = {
    "modul", "musteri", "konu", "aciklama",
    "yapilacak", "yapilan islem", "kategori",
}

UYDS_HEDEF: Dict[str, List[str]] = {
    "modul": ["modul"],
    "konu": ["konu"],
    "aciklama": ["aciklama"],
    "yapilacak": ["yapilacak"],
    "yapilan_islem": ["yapilan islem", "yapilan_islem"],
}

STANDART_HEDEF: Dict[str, List[str]] = {
    "soru": ["soru"],
    "cevap": ["cevap"],
    "kategori": ["kategori"],
}

GEREKLI_UYDS = {"modul", "konu", "aciklama", "yapilacak", "yapilan_islem"}


def alan_eslestir(
    sutun_adlari: Iterable[str],
    hedef_adlar: Dict[str, List[str]],
) -> Dict[str, str]:
    """
    Normalize edilmiş sütun adlarını hedef alan adlarıyla eşleştirir.

    Dönüş: {hedef_anahtar: gerçek_sütun_adı}
    """
    normalize_harita = {adi_normalize_et(k): k for k in sutun_adlari}
    eslesme: Dict[str, str] = {}
    for anahtar, adaylar in hedef_adlar.items():
        for aday in adaylar:
            norm = adi_normalize_et(aday)
            if norm in normalize_harita:
                eslesme[anahtar] = normalize_harita[norm]
                break
    return eslesme


def baslik_satiri_bul(
        ham_df,
        bilinen: Optional[set] = None,
        pencere: int = 20,
        esik: int = 3,
) -> Optional[int]:
    """Ham DataFrame'de başlık satırı indeksini döndürür, yoksa None."""
    bilinen = bilinen if bilinen is not None else BILINEN_BASLIKLAR
    for _, satir in ham_df.head(pencere).iterrows():
        hucre_kumesi = {adi_normalize_et(str(d)) for d in satir.tolist()}
        if len(hucre_kumesi & bilinen) >= esik:
            return int(satir.name)
    return None


def excel_formatini_tespit_et(
    sutun_adlari: Iterable[str],
) -> Tuple[str, Dict[str, str]]:
    """
    Sütun adlarından Excel formatını tespit eder.

    Dönüş: (format, eslesme)
      format: "uyds" veya "standart"
      eslesme: ilgili hedef → gerçek sütun adı haritası

    Fırlatır:
        ValueError: desteklenmeyen format
    """
    sutun_listesi = list(sutun_adlari)

    uyds_eslesme = alan_eslestir(sutun_listesi, UYDS_HEDEF)
    if GEREKLI_UYDS.issubset(uyds_eslesme):
        return "uyds", uyds_eslesme

    standart_eslesme = alan_eslestir(sutun_listesi, STANDART_HEDEF)
    if {"soru", "cevap"}.issubset(standart_eslesme):
        return "standart", standart_eslesme

    raise ValueError(
        f"Desteklenmeyen Excel formatı. Bulunan sütunlar: {sutun_listesi}"
    )
