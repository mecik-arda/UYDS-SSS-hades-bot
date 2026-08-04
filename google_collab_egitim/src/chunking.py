# ============================================================
# v4.1 Chunking — Tokenizer tabanlı belge bölümleme
# ============================================================
"""
Embedding modelinin tokenizer'ını kullanarak belge metinlerini
chunk'lara böler.

Özellikler:
  - Tokenizer tabanlı (kelime/karakter değil)
  - Cümle sınırında bölme (mümkünse cümleyi ikiye bölmez)
  - Overlap (örtüşme) desteği
  - Başlık/bölüm bilgisi korunur
  - Çok kısa parçalar komşuya birleştirilir
  - Tablo içerikleri satır anlamı korunarak dönüştürülür
  - Sürüm sabiti ile checkpoint uyumluluğu
"""

import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Sürüm Sabiti
# ============================================================
CHUNK_ALGORITMA_SURUMU = "1.0"


# ============================================================
# Cümle Algılama
# ============================================================
_CUMLE_BOLUCU = re.compile(
    r"(?<=[.!?…])\s+(?=[A-ZÂÂÊÎÔÛÜĞŞÇÖİ0-9])",
)


def _metni_cumlelere_ayir(metin: str) -> List[str]:
    """Metni noktalama işaretlerine göre cümlelere ayırır."""
    ham = _CUMLE_BOLUCU.split(metin)
    return [c.strip() for c in ham if c.strip()]


# ============================================================
# Tokenizer Bazlı Chunking
# ============================================================
def _metni_tokenlara_bol(metin: str, tokenizer) -> List[int]:
    """Metni token ID'lerine dönüştürür."""
    if tokenizer is None:
        return list(range(len(metin.split())))
    try:
        return tokenizer.encode(metin, add_special_tokens=False)
    except Exception:
        return list(range(len(metin.split())))


def _tokenlari_birlestir(
    token_idler: List[int],
    tokenizer,
    orijinal_metin: str = "",
) -> str:
    """Token ID'lerini metne çevirir. Tokenizer yoksa kelime dilimleme."""
    if not token_idler:
        return ""
    if tokenizer is not None:
        try:
            return tokenizer.decode(token_idler, skip_special_tokens=True)
        except Exception:
            pass
    # Fallback: kelime indeks dilimleme
    if orijinal_metin:
        kelimeler = orijinal_metin.split()
        start = token_idler[0] if token_idler else 0
        end = token_idler[-1] if token_idler else 0
        if start < len(kelimeler) and end < len(kelimeler):
            return " ".join(kelimeler[start : end + 1])
    return ""


def _duz_token_chunk(
    tokenler: List[int],
    orijinal_metin: str,
    tokenizer,
    hedef_token: int,
    overlap_token: int,
    fallback_metin: str = "",
) -> List[str]:
    """Token listesini düz parçalara böler."""
    if len(tokenler) <= hedef_token:
        return [orijinal_metin]

    fb = fallback_metin or orijinal_metin
    parcalar = []
    basla = 0
    while basla < len(tokenler):
        bitir = min(basla + hedef_token, len(tokenler))
        parca_tokens = tokenler[basla:bitir]
        parca_metin = _tokenlari_birlestir(parca_tokens, tokenizer, fb)
        if parca_metin.strip():
            parcalar.append(parca_metin.strip())
        if bitir >= len(tokenler):
            break
        basla = bitir - overlap_token
    return parcalar


def _uzun_cumleyi_bol(
    cumle_metni: str,
    cumle_tokens: List[int],
    tokenizer,
    hedef_token: int,
) -> List[str]:
    """Tek bir uzun cümleyi hedef_token boyutunda parçalara böler."""
    if len(cumle_tokens) <= hedef_token:
        return [cumle_metni]

    # Virgül, noktalı virgül gibi yerlerden bölmeye çalış
    alt_bol = re.split(r"(?<=[,;:])\s+", cumle_metni)
    if len(alt_bol) > 1:
        parcalar = []
        mevcut = []
        mevcut_tok = 0
        for bol in alt_bol:
            bt = _metni_tokenlara_bol(bol, tokenizer)
            if mevcut_tok + len(bt) <= hedef_token:
                mevcut.append(bol)
                mevcut_tok += len(bt)
            else:
                if mevcut:
                    parcalar.append(" ".join(mevcut))
                mevcut = [bol]
                mevcut_tok = len(bt)
        if mevcut:
            parcalar.append(" ".join(mevcut))
        return parcalar

    # Virgül de yoksa token bazlı böl
    return _duz_token_chunk(
        cumle_tokens, cumle_metni, tokenizer,
        hedef_token, max(1, hedef_token // 4), cumle_metni,
    )


def _kelime_bazli_chunk(
    kelimeler: List[str],
    hedef_token: int,
    overlap_token: int,
) -> List[str]:
    """Tokenizer yoksa kelime bazlı fallback chunking."""
    kelime_hedef = int(hedef_token * 1.3)
    kelime_overlap = int(overlap_token * 1.3)

    parcalar = []
    basla = 0
    while basla < len(kelimeler):
        bitir = min(basla + kelime_hedef, len(kelimeler))
        parca_metin = " ".join(kelimeler[basla:bitir])
        parcalar.append(parca_metin)
        if bitir >= len(kelimeler):
            break
        basla = bitir - kelime_overlap
    return parcalar


def _kisa_chunklari_birlestir(
    chunklar: List[str],
    tokenizer,
    min_token: int = 20,
) -> List[str]:
    """Çok kısa chunk'ları komşularıyla birleştirir."""
    if len(chunklar) <= 1:
        return chunklar
    sonuc = []
    for chunk in chunklar:
        tokens = _metni_tokenlara_bol(chunk, tokenizer)
        if len(tokens) < min_token and sonuc:
            sonuc[-1] = sonuc[-1] + " " + chunk
        else:
            sonuc.append(chunk)
    return sonuc


def tokenizer_bazli_chunk(
    metin: str,
    tokenizer,
    hedef_token: int = 110,
    overlap_token: int = 25,
    min_chunk_token: int = 20,
) -> List[str]:
    """
    Tokenizer kullanarak metni token sayısına göre chunk'lara böler.

    Args:
        metin: Bölünecek metin
        tokenizer: HuggingFace tokenizer (None ise kelime tabanlı fallback)
        hedef_token: Hedef chunk token sayısı (varsayılan: 110)
        overlap_token: Chunk'lar arası örtüşme token sayısı (varsayılan: 25)
        min_chunk_token: Bundan kısa chunk'lar komşuya birleştirilir

    Returns:
        Chunk metinlerinin listesi
    """
    if not metin or not metin.strip():
        return []

    # Önce cümlelere ayır
    cumleler = _metni_cumlelere_ayir(metin)

    if not cumleler:
        # Cümle algılanamazsa doğrudan token bazlı böl
        tokenler = _metni_tokenlara_bol(metin, tokenizer)
        if tokenizer is not None:
            return _duz_token_chunk(tokenler, metin, tokenizer, hedef_token, overlap_token, metin)
        else:
            kelimeler = metin.split()
            return _kelime_bazli_chunk(kelimeler, hedef_token, overlap_token)

    # Her cümleyi tokenize et
    cumle_tokenler = []
    for cumle in cumleler:
        tokenler = _metni_tokenlara_bol(cumle, tokenizer)
        if tokenler:
            cumle_tokenler.append((cumle, tokenler))

    if not cumle_tokenler:
        return []

    # Cümleleri hedef token sayısına göre grupla
    chunklar = []
    mevcut_cumleler = []
    mevcut_token_sayisi = 0

    for cumle_metni, cumle_tokens in cumle_tokenler:
        c_len = len(cumle_tokens)

        if mevcut_token_sayisi + c_len <= hedef_token:
            mevcut_cumleler.append(cumle_metni)
            mevcut_token_sayisi += c_len
        else:
            if mevcut_cumleler:
                chunklar.append(" ".join(mevcut_cumleler))

                # Overlap
                if overlap_token > 0:
                    yeni_baslangic = []
                    yeni_token = 0
                    for cm in reversed(mevcut_cumleler):
                        ct = _metni_tokenlara_bol(cm, tokenizer)
                        if yeni_token + len(ct) <= overlap_token:
                            yeni_baslangic.insert(0, cm)
                            yeni_token += len(ct)
                        else:
                            break
                    mevcut_cumleler = yeni_baslangic
                    mevcut_token_sayisi = yeni_token + c_len
                else:
                    mevcut_cumleler = [cumle_metni]
                    mevcut_token_sayisi = c_len
            else:
                # Tek cümle hedef_token'ı aşıyor → zorla böl
                alt_chunklar = _uzun_cumleyi_bol(
                    cumle_metni, cumle_tokens, tokenizer, hedef_token
                )
                chunklar.extend(alt_chunklar)
                mevcut_cumleler = []
                mevcut_token_sayisi = 0
                continue

            mevcut_cumleler.append(cumle_metni)
            mevcut_token_sayisi += c_len

    if mevcut_cumleler:
        chunklar.append(" ".join(mevcut_cumleler))

    chunklar = _kisa_chunklari_birlestir(chunklar, tokenizer, min_chunk_token)
    return chunklar


# ============================================================
# Metadata Zengin Chunk Oluşturma
# ============================================================
def belgeyi_chunkla(
    belge_listesi: List[Dict[str, Any]],
    tokenizer,
    hedef_token: int = 110,
    overlap_token: int = 25,
) -> List[Dict[str, Any]]:
    """Belge listesini zengin metadata ile chunk'lara böler."""
    tum_chunklar = []
    global_chunk_id = 0

    for belge in belge_listesi:
        metin = belge.get("metin", "")
        if not metin.strip():
            continue

        ham_chunklar = tokenizer_bazli_chunk(
            metin, tokenizer, hedef_token=hedef_token, overlap_token=overlap_token
        )
        if not ham_chunklar:
            continue

        dosya_adi = belge.get("dosya", "bilinmeyen")
        sayfa_no = belge.get("sayfa")
        meta = belge.get("meta", {})

        for yerel_i, chunk_metni in enumerate(ham_chunklar):
            if not chunk_metni.strip():
                continue
            tum_chunklar.append({
                "chunk_id": global_chunk_id,
                "kaynak_id": meta.get("kaynak_id", ""),
                "kaynak_tipi": meta.get("kaynak_tipi", "bilinmeyen"),
                "dokuman": dosya_adi,
                "kurum": meta.get("kurum", ""),
                "modul": meta.get("modul", ""),
                "alt_konu": meta.get("alt_konu", ""),
                "sayfa": sayfa_no,
                "yerel_chunk": yerel_i + 1,
                "yayin_tarihi": meta.get("yayin_tarihi", ""),
                "surum": meta.get("surum", ""),
                "resmiyet_seviyesi": meta.get("resmiyet_seviyesi", "belirsiz"),
                "metin": chunk_metni.strip(),
            })
            global_chunk_id += 1

    return tum_chunklar


# ============================================================
# Chunk İstatistikleri
# ============================================================
def chunk_istatistikleri(
    chunklar: List[Dict[str, Any]], tokenizer
) -> Dict[str, Any]:
    """Chunk listesi için istatistik üretir."""
    if not chunklar:
        return {"toplam_chunk": 0}

    import statistics

    token_sayilari = [
        len(_metni_tokenlara_bol(ch["metin"], tokenizer))
        for ch in chunklar
    ]

    return {
        "toplam_chunk": len(chunklar),
        "dokuman_sayisi": len(set(ch["dokuman"] for ch in chunklar)),
        "modul_sayisi": len(set(ch["modul"] for ch in chunklar if ch["modul"])),
        "moduller": sorted(set(ch["modul"] for ch in chunklar if ch["modul"])),
        "ortalama_token": statistics.mean(token_sayilari) if token_sayilari else 0,
        "medyan_token": statistics.median(token_sayilari) if token_sayilari else 0,
        "min_token": min(token_sayilari) if token_sayilari else 0,
        "maks_token": max(token_sayilari) if token_sayilari else 0,
        "chunk_algoritma_surumu": CHUNK_ALGORITMA_SURUMU,
    }