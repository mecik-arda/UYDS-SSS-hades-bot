# ============================================================
# v4.1 Retrieval — Dense/Bibrit RAG kaynak getirici
# ============================================================
"""
Dense cosine similarity ile kaynak parçaları arar.
İleri sürümde BM25 + Reciprocal Rank Fusion eklenecek.

Şu anki mimari:
  Dense retrieval → top_k → min_skor filtreleme → en uygun son_k
"""

import numpy as np
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Sürüm Sabiti
# ============================================================
RETRIEVAL_ALGORITMA_SURUMU = "1.0"


# ============================================================
# Dense Retrieval
# ============================================================
def dense_kaynak_ara(
    soru_vektor: np.ndarray,
    kaynak_vektorler: np.ndarray,
    tum_parcalar: List[Dict[str, Any]],
    top_k: int = 10,
    son_k: int = 3,
    min_skor: float = 0.3,
    ilk_havuz_filtresi: Optional[str] = None,
    ikinci_havuz_min_skor: Optional[float] = None,
    dogrudan_boost: float = 0.0,
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Cosine similarity (nokta çarpım) ile en uygun kaynakları bulur.

    Args:
        soru_vektor: (embedding_dim,) sorgu vektörü
        kaynak_vektorler: (n_kaynak, embedding_dim) kaynak vektörleri
        tum_parcalar: kaynak parçalarının listesi
        top_k: kaç aday alınacağı
        son_k: en fazla kaç sonuç döneceği
        min_skor: minimum cosine benzerlik eşiği
        ilk_havuz_filtresi: "dogrudan_ilgili" → önce sadece bu havuzda ara
                            "dolayli_ilgili" → yalnızca dolaylı havuz
        ikinci_havuz_min_skor: İlk havuzda yeterli sonuç yoksa (maks skor < bu değer)
                               ikinci havuza fallback yap
        dogrudan_boost: Doğrudan ilgili chunk'lara uygulanacak skor bonusu (örn: 0.1)

    Returns:
        (secilen_parcalar, maks_skor): Seçilen chunk'lar ve en yüksek skor
    """
    if len(kaynak_vektorler) == 0:
        return [], 0.0

    # Havuz filtrelemesi: uyds_ilgililik alanına göre indeksleri ayır
    if ilk_havuz_filtresi:
        tum_indeksler = list(range(len(tum_parcalar)))
        ilk_havuz_indeksleri = [
            i for i in tum_indeksler
            if tum_parcalar[i].get("uyds_ilgililik") == ilk_havuz_filtresi
        ]
        ikinci_havuz_indeksleri = [
            i for i in tum_indeksler
            if tum_parcalar[i].get("uyds_ilgililik") != ilk_havuz_filtresi
        ]

        # Önce ilk havuzda ara
        ilk_sonuclar, ilk_maks = _havuzda_ara(
            soru_vektor, kaynak_vektorler, tum_parcalar,
            ilk_havuz_indeksleri, top_k, son_k, min_skor, dogrudan_boost,
        )

        # İlk havuzda yeterli skor bulundu mu?
        if ilk_sonuclar and (not ikinci_havuz_min_skor or ilk_maks >= ikinci_havuz_min_skor):
            return ilk_sonuclar, ilk_maks

        # Fallback: ikinci havuzda da ara
        ikinci_sonuclar, ikinci_maks = _havuzda_ara(
            soru_vektor, kaynak_vektorler, tum_parcalar,
            ikinci_havuz_indeksleri, top_k, son_k,
            min_skor * 0.8,  # İkinci havuzda eşik biraz daha düşük
            0.0,
        )

        # İki havuzu birleştir (ilk havuz öncelikli)
        if ilk_sonuclar or ikinci_sonuclar:
            birlestirilmis = ilk_sonuclar + ikinci_sonuclar
            # Skora göre sırala, en yüksek son_k'yi al
            birlestirilmis.sort(key=lambda x: x.get("birlesik_skor", 0), reverse=True)
            birlestirilmis = birlestirilmis[:son_k]
            maks_skor = max(ilk_maks, ikinci_maks)
            return birlestirilmis, maks_skor

        return [], 0.0

    # Havuz filtresi yoksa tüm havuzda ara (orijinal davranış)
    return _havuzda_ara(
        soru_vektor, kaynak_vektorler, tum_parcalar,
        list(range(len(tum_parcalar))), top_k, son_k, min_skor, dogrudan_boost,
    )


def _havuzda_ara(
    soru_vektor: np.ndarray,
    kaynak_vektorler: np.ndarray,
    tum_parcalar: List[Dict[str, Any]],
    havuz_indeksleri: List[int],
    top_k: int,
    son_k: int,
    min_skor: float,
    dogrudan_boost: float,
) -> Tuple[List[Dict[str, Any]], float]:
    """Belirli bir indeks havuzunda dense retrieval yapar."""
    if not havuz_indeksleri:
        return [], 0.0

    havuz_indeksleri = np.array(havuz_indeksleri, dtype=int)
    havuz_vektorler = kaynak_vektorler[havuz_indeksleri]

    # Cosine benzerlik
    skorlar = np.dot(havuz_vektorler, soru_vektor)

    # Doğrudan boost
    if dogrudan_boost > 0:
        for j, i in enumerate(havuz_indeksleri):
            if tum_parcalar[i].get("uyds_ilgililik") == "dogrudan_ilgili":
                skorlar[j] += dogrudan_boost

    # Top-k seçimi
    if len(skorlar) <= top_k:
        sirali = np.argsort(skorlar)[::-1]
    else:
        top_n = np.argpartition(skorlar, -top_k)[-top_k:]
        sirali = top_n[np.argsort(skorlar[top_n])[::-1]]

    # Son_k filtreleme
    secilenler = []
    maks_skor = 0.0
    gorulen_dokumanlar = set()
    ayni_dokuman_limiti = 2

    for j in sirali:
        if len(secilenler) >= son_k:
            break

        skor = float(skorlar[j])
        if skor < min_skor:
            continue

        if skor > maks_skor:
            maks_skor = skor

        gercek_indeks = int(havuz_indeksleri[j])
        parca = tum_parcalar[gercek_indeks].copy()
        dokuman = parca.get("dokuman", "")

        if dokuman:
            doc_count = sum(1 for p in secilenler if p.get("dokuman") == dokuman)
            if doc_count >= ayni_dokuman_limiti:
                continue

        parca["dense_skor"] = round(skor, 4)
        parca["birlesik_skor"] = round(skor, 4)
        secilenler.append(parca)

    return secilenler, maks_skor


def toplu_kaynak_ara(
    soru_vektorler: np.ndarray,
    kaynak_vektorler: np.ndarray,
    tum_parcalar: List[Dict[str, Any]],
    top_k: int = 10,
    son_k: int = 3,
    min_skor: float = 0.3,
) -> Tuple[List[List[Dict[str, Any]]], List[float]]:
    """
    Tüm sorular için toplu RAG retrieval yapar.

    Returns:
        (tum_parcalar_listesi, tum_maks_skorlar)
    """
    tum_parcalar_listesi = []
    tum_maks_skorlar = []

    for i in range(len(soru_vektorler)):
        if i % 500 == 0:
            print(f"   RAG: {i}/{len(soru_vektorler)}...")
        parcalar, maks_skor = dense_kaynak_ara(
            soru_vektorler[i],
            kaynak_vektorler,
            tum_parcalar,
            top_k=top_k,
            son_k=son_k,
            min_skor=min_skor,
        )
        tum_parcalar_listesi.append(parcalar)
        tum_maks_skorlar.append(maks_skor)

    return tum_parcalar_listesi, tum_maks_skorlar


# ============================================================
# RAG Sonuç İstatistikleri
# ============================================================
def rag_istatistikleri(
    tum_parcalar_listesi: List[List[Dict[str, Any]]],
    tum_maks_skorlar: List[float],
) -> Dict[str, Any]:
    """RAG sonuçlarından özet istatistik üretir."""
    kaynaksiz = sum(1 for p in tum_parcalar_listesi if not p)
    ortalama_parca = (
        sum(len(p) for p in tum_parcalar_listesi) / len(tum_parcalar_listesi)
        if tum_parcalar_listesi
        else 0
    )
    gecerli_skorlar = [s for s in tum_maks_skorlar if s > 0]
    ortalama_skor = np.mean(gecerli_skorlar) if gecerli_skorlar else 0.0

    return {
        "toplam_sorgu": len(tum_parcalar_listesi),
        "kaynaksiz_sorgu": kaynaksiz,
        "kaynaksiz_oran": kaynaksiz / len(tum_parcalar_listesi) if tum_parcalar_listesi else 0,
        "ortalama_parca_sayisi": round(ortalama_parca, 2),
        "ortalama_maks_skor": round(ortalama_skor, 4),
        "retrieval_algoritma_surumu": RETRIEVAL_ALGORITMA_SURUMU,
    }