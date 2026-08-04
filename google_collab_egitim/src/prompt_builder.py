# ============================================================
# v4.1 Prompt Builder — Token kontrollü prompt oluşturucu
# ============================================================
"""
Qwen3-32B-AWQ için chat template tabanlı token hesaplama ve
token limitine uyan prompt oluşturma.

Özellikler:
  - Chat template ile gerçek token sayımı
  - Token limiti aşılırsa kaynakları sondan çıkarır
  - Kaynaklar tamamen çıkarılır (ortadan kesilmez)
  - "sunulan_kaynak_idleri" yalnızca prompt'ta kalanları içerir
  - Cevap ve soru son çare olarak kısaltılır
"""

import textwrap
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Sistem Promptu
# ============================================================
SISTEM_PROMPT = textwrap.dedent("""\
Sen UYDS mevzuat ve teknik süreç doğrulama uzmanısın.

YALNIZCA verilen kaynak metinlere dayan.
Kaynaklarda açıkça bulunmayan bilgiyi kendi genel bilginle tamamlama.
Kaynak yetersizse "kanit_yetersiz" kararı ver.
Soru anlaşılmıyorsa "soru_belirsiz" kararı ver.
Kaynaklar cevabın bir kısmını destekliyorsa ancak önemli eksik varsa "kismen_dogru" kararı ver.
Kaynaklarla çelişiyorsa "yanlis" kararı ver.
Cevap tam olarak destekleniyorsa "dogru" kararı ver.

"dogru" kararında "duzeltilmis_cevap" boş string olmalıdır.
Yalnızca "kismen_dogru" veya "yanlis" kararında düzeltilmiş cevap üret.
Sadece sunulan kaynak ID'lerini kullan.
Yalnızca geçerli JSON üret.""")


# ============================================================
# Değerlendirme Promptu
# ============================================================
DOGRULAMA_PROMPT_SABLON = textwrap.dedent("""\
Sana bir soru, bir cevap ve ilgili kaynak metin parçaları veriyorum. Görevin:

1. SADECE verilen KAYNAK metinlere dayanarak cevabın doğruluğunu değerlendir.
2. Kendi bilgine başvurma. Kaynaklarda kanıt yoksa "kanit_yetersiz" de.
3. Soru anlaşılamıyorsa "soru_belirsiz" de.

Karar seçenekleri:
- "dogru": Cevap kaynaklarla birebir örtüşüyor, hiçbir hata veya eksik yok.
- "kismen_dogru": Cevap genel olarak doğru ama küçük bir eksik veya belirsizlik var.
- "yanlis": Cevap kaynaklarla açıkça çelişiyor veya yanlış bilgi içeriyor.
- "kanit_yetersiz": Kaynaklar bu soruyu cevaplamak için yeterli bilgi içermiyor.
- "soru_belirsiz": Soru net değil, anlaşılmıyor veya cevaplanamaz formatta.

Önemli kurallar:
- "guven" 0.0-1.0 arası. Kaynak açıkça destekliyorsa 0.90+, kısmen destekliyorsa 0.70-0.89.
- "kaynak_idleri": Dayandığın kaynak parçalarının chunk_id'lerini yaz.
- "dayanak": Kararını destekleyen kanıtı 2-3 cümleyle açıkla.
- "eksik_veya_hata": Cevapta neyin eksik/yanlış olduğunu belirt (sorun yoksa boş).
- 🔴 "duzeltilmis_cevap": Karar "dogru" ise BOŞ STRING yaz. Sadece "kismen_dogru" veya "yanlis" ise düzeltilmiş cevap üret.

--- SORU ---
{soru}

--- MEVCUT CEVAP ---
{cevap}

--- KAYNAK METİNLER ---
{kaynaklar}

Yalnızca JSON çıktısı üret, başka metin ekleme.""")


# ============================================================
# JSON Çıktı Şeması (vLLM Structured Outputs)
# ============================================================
CEVAP_SEMASI = {
    "type": "object",
    "properties": {
        "karar": {
            "type": "string",
            "enum": [
                "dogru",
                "kismen_dogru",
                "yanlis",
                "kanit_yetersiz",
                "soru_belirsiz",
            ],
        },
        "guven": {"type": "number", "minimum": 0, "maximum": 1},
        "kaynak_idleri": {"type": "array", "items": {"type": "integer"}},
        "dayanak": {"type": "string", "description": "Kaynak kanıt (2-3 cümle)"},
        "eksik_veya_hata": {
            "type": "string",
            "description": "Eksik/yanlış (yoksa boş)",
        },
        "duzeltilmis_cevap": {
            "type": "string",
            "description": "Karar 'dogru' ise BOŞ",
        },
    },
    "required": [
        "karar",
        "guven",
        "kaynak_idleri",
        "dayanak",
        "eksik_veya_hata",
        "duzeltilmis_cevap",
    ],
    "additionalProperties": False,
}


# ============================================================
# Kaynak Formatlama
# ============================================================
def kaynak_formatla(parcalar: List[Dict[str, Any]]) -> str:
    """Kaynak parçalarını LLM girdi formatına dönüştürür."""
    if not parcalar:
        return "(Kaynak bulunamadı — kanit_yetersiz kararı vermelisin)"

    metin = ""
    for p in parcalar:
        cid = p.get("chunk_id", "?")
        dok = p.get("dokuman", "?")
        say = p.get("sayfa", "?")
        skor = p.get("dense_skor", p.get("skor", 0))
        metin += (
            f"\n[Kaynak ID:{cid} | {dok} | s.{say} | skor:{skor:.3f}]\n"
            f"{p.get('metin', '')}\n"
        )
    return metin


# ============================================================
# Prompt Oluşturma
# ============================================================
def prompt_olustur(
    soru: str,
    cevap: str,
    parcalar: List[Dict[str, Any]],
) -> str:
    """Değerlendirme promptunu oluşturur."""
    kaynak_metni = kaynak_formatla(parcalar) if parcalar else "(Kaynak bulunamadı)"
    return DOGRULAMA_PROMPT_SABLON.format(
        soru=soru,
        cevap=cevap,
        kaynaklar=kaynak_metni,
    )


def mesaj_olustur(
    soru: str,
    cevap: str,
    parcalar: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Chat template için mesaj listesi oluşturur."""
    prompt = prompt_olustur(soru, cevap, parcalar)
    return [
        {"role": "system", "content": SISTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


# ============================================================
# Token Kontrollü Prompt Kısaltma
# ============================================================
def token_say(
    messages: List[Dict[str, str]],
    tokenizer,
    enable_thinking: bool = False,
) -> int:
    """
    Chat template ile gerçek token sayısını hesaplar.
    Tokenizer yoksa karakter/4 fallback kullanır.
    """
    if tokenizer is not None:
        try:
            chat_kwargs = {}
            if hasattr(tokenizer, "chat_template") and "enable_thinking" in str(
                tokenizer.chat_template or ""
            ):
                chat_kwargs["enable_thinking"] = enable_thinking
            templated = tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                **chat_kwargs,
            )
            return len(templated)
        except Exception:
            pass

    # Fallback: yaklaşık karakter/4
    toplam_karakter = sum(
        len(m.get("content", "")) for m in messages if isinstance(m, dict)
    )
    return toplam_karakter // 4


def prompt_token_kisalt(
    soru: str,
    cevap: str,
    parcalar: List[Dict[str, Any]],
    tokenizer,
    token_limit: int,
    enable_thinking: bool = False,
) -> Tuple[str, str, str, List[Dict[str, Any]]]:
    """
    Token limitine uygun hale getirilmiş prompt bileşenlerini döndürür.

    Strateji (sırasıyla):
      1. Tüm kaynaklarla dene
      2. En düşük skorlu kaynağı tamamen çıkar
      3. Kaynak sayısını 3→2→1 düşür
      4. Cevabı kısalt (0.6, 0.3 oran)
      5. Soruyu kısalt (0.6, 0.3 oran)
      6. Son çare: agresif kısaltma

    Returns:
        (kisaltilmis_soru, kisaltilmis_cevap, kaynak_metni, kalan_parcalar)
        kalan_parcalar: Prompt'a gerçekten dahil edilen chunk'lar
    """
    if not parcalar:
        return soru, cevap, "(Kaynak bulunamadı)", []

    # RAG skoruna göre sırala (en yüksek önce)
    siralanan = sorted(
        parcalar,
        key=lambda p: p.get("dense_skor", p.get("skor", 0)),
        reverse=True,
    )

    # Deneme 1: Tüm kaynaklarla başla, sondan çıkar
    for k in range(len(siralanan), 0, -1):
        secili = siralanan[:k]
        kaynak_metni = kaynak_formatla(secili)
        messages = mesaj_olustur(soru, cevap, secili)
        # prompt_olustur içinde kaynak_formatla tekrar çağrılır, tutarlı olması için
        # mesaj_olustur içindeki prompt_olustur'u override edelim
        prompt_metni = DOGRULAMA_PROMPT_SABLON.format(
            soru=soru, cevap=cevap, kaynaklar=kaynak_metni
        )
        messages = [
            {"role": "system", "content": SISTEM_PROMPT},
            {"role": "user", "content": prompt_metni},
        ]
        if token_say(messages, tokenizer, enable_thinking) <= token_limit:
            return soru, cevap, kaynak_metni, secili

    # Deneme 2: Sadece 1 kaynak + cevap/soru kısalt
    secili = siralanan[:1]
    kaynak_metni = kaynak_formatla(secili)

    for cevap_oran in [1.0, 0.6, 0.3]:
        for soru_oran in [1.0, 0.6, 0.3]:
            k_cevap = (
                cevap
                if cevap_oran == 1.0
                else cevap[: max(100, int(len(cevap) * cevap_oran))] + "..."
            )
            k_soru = (
                soru
                if soru_oran == 1.0
                else soru[: max(150, int(len(soru) * soru_oran))] + "..."
            )
            prompt_metni = DOGRULAMA_PROMPT_SABLON.format(
                soru=k_soru, cevap=k_cevap, kaynaklar=kaynak_metni
            )
            messages = [
                {"role": "system", "content": SISTEM_PROMPT},
                {"role": "user", "content": prompt_metni},
            ]
            if token_say(messages, tokenizer, enable_thinking) <= token_limit:
                return k_soru, k_cevap, kaynak_metni, secili

    # Deneme 3: Son çare agresif kısaltma
    return soru[:200], cevap[:100], kaynak_metni[:500], secili


# ============================================================
# Kaynaksız Durumlar için Hazır Yanıtlar
# ============================================================
def kanit_yetersiz_yanit() -> Dict[str, Any]:
    """Kaynak bulunamadığında dönecek hazır yanıt."""
    return {
        "karar": "kanit_yetersiz",
        "guven": 0.0,
        "kaynak_idleri": [],
        "dayanak": "Kaynak metin bulunamadı.",
        "eksik_veya_hata": "Cevabı doğrulayacak kaynak metin bulunamadı.",
        "duzeltilmis_cevap": "",
        "_islem_hatasi": False,
    }


def cevap_bos_yanit() -> Dict[str, Any]:
    """Cevap boş olduğunda dönecek hazır yanıt."""
    return {
        "karar": "cevap_bos",
        "guven": 1.0,
        "kaynak_idleri": [],
        "dayanak": "Cevap alanı boş.",
        "eksik_veya_hata": "Yapılan İşlem alanı dolu değil.",
        "duzeltilmis_cevap": "",
        "_islem_hatasi": False,
    }


def islem_hatasi_yanit(hata_mesaji: str = "") -> Dict[str, Any]:
    """Model çağrısı başarısız olduğunda dönecek yanıt."""
    return {
        "karar": "error",
        "guven": 0.0,
        "kaynak_idleri": [],
        "dayanak": f"Model çıktısı alınamadı: {hata_mesaji[:200]}",
        "eksik_veya_hata": "vLLM çağrısı başarısız oldu.",
        "duzeltilmis_cevap": "",
        "_islem_hatasi": True,
    }