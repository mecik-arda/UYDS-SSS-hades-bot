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

    Returns:
        (secilen_parcalar, maks_skor): Seçilen chunk'lar ve en yüksek skor
    """
    if len(kaynak_vektorler) == 0:
        return [], 0.0

    # Cosine benzerlik (vektörler normalize olduğu için dot product)
    skorlar = np.dot(kaynak_vektorler, soru_vektor)

    # Top-k seçimi
    if len(skorlar) <= top_k:
        top_indeksler = np.argsort(skorlar)[::-1]
    else:
        top_indeksler = np.argpartition(skorlar, -top_k)[-top_k:]
        top_indeksler = top_indeksler[np.argsort(skorlar[top_indeksler])[::-1]]

    # Son_k filtreleme
    secilenler = []
    maks_skor = 0.0
    gorulen_dokumanlar = set()  # Aynı dokümandan çok chunk gelmesini önle
    ayni_dokuman_limiti = 2     # Aynı dokümandan en fazla 2 chunk

    for i in top_indeksler:
        if len(secilenler) >= son_k:
            break

        skor = float(skorlar[i])
        if skor < min_skor:
            continue

        if skor > maks_skor:
            maks_skor = skor

        parca = tum_parcalar[i].copy()
        dokuman = parca.get("dokuman", "")

        # Aynı dokümandan çok chunk gelmesin
        if dokuman:
            doc_count = sum(1 for p in secilenler if p.get("dokuman") == dokuman)
            if doc_count >= ayni_dokuman_limiti:
                continue

        parca["dense_skor"] = round(skor, 4)
        parca["birlesik_skor"] = round(skor, 4)  # BM25 yoksa dense = birleşik
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