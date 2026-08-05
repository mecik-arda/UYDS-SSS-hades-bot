# ============================================================
# Test: Dense Retrieval
# ============================================================
"""Retrieval modülü — dense cosine similarity, min_skor, aynı doküman limiti."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval import dense_kaynak_ara, toplu_kaynak_ara, rag_istatistikleri


class TestDenseKaynakAra:
    """Dense retrieval testleri."""

    @pytest.fixture
    def ornek_vektor_parcalar(self):
        """3 parçalı örnek veri seti."""
        vektorler = np.array([
            [1.0, 0.0, 0.0],   # chunk 0
            [0.0, 1.0, 0.0],   # chunk 1
            [0.0, 0.0, 1.0],   # chunk 2
        ], dtype=np.float32)
        # Normalize
        vektorler = vektorler / np.linalg.norm(vektorler, axis=1, keepdims=True)

        parcalar = [
            {"chunk_id": 0, "dokuman": "a.pdf", "sayfa": 1, "metin": "Hakediş onayı."},
            {"chunk_id": 1, "dokuman": "a.pdf", "sayfa": 2, "metin": "Belge kontrolü."},
            {"chunk_id": 2, "dokuman": "b.pdf", "sayfa": 5, "metin": "İhale süreci."},
        ]
        return vektorler, parcalar

    def test_bos_kaynak(self):
        sonuc, skor = dense_kaynak_ara(
            np.array([1.0, 0.0, 0.0]),
            np.array([]).reshape(0, 3),
            [],
            top_k=10, son_k=3, min_skor=0.3,
        )
        assert sonuc == []
        assert skor == 0.0

    def test_tam_eslesme(self, ornek_vektor_parcalar):
        vektorler, parcalar = ornek_vektor_parcalar
        soru = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        soru = soru / np.linalg.norm(soru)

        sonuc, skor = dense_kaynak_ara(
            soru, vektorler, parcalar, top_k=10, son_k=3, min_skor=0.3,
        )
        assert len(sonuc) >= 1
        assert sonuc[0]["chunk_id"] == 0
        assert skor > 0.9

    def test_min_skor_filtre(self, ornek_vektor_parcalar):
        vektorler, parcalar = ornek_vektor_parcalar
        soru = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        soru = soru / np.linalg.norm(soru)

        sonuc, _ = dense_kaynak_ara(
            soru, vektorler, parcalar, top_k=10, son_k=3, min_skor=0.99,
        )
        assert len(sonuc) >= 1  # 1.0 cos sim → 1 chunk geçer

    def test_ayni_dokuman_limiti(self, ornek_vektor_parcalar):
        """Aynı dokümandan en fazla 2 chunk alınmalı."""
        vektorler, parcalar = ornek_vektor_parcalar
        vektorler = np.vstack([vektorler, vektorler])  # 6 vektör
        parcalar2 = parcalar + [
            {"chunk_id": i, "dokuman": p["dokuman"], "metin": p["metin"]}
            for i, p in enumerate(parcalar, 3)
        ]
        soru = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        soru = soru / np.linalg.norm(soru)

        sonuc, _ = dense_kaynak_ara(
            soru, vektorler, parcalar2, top_k=10, son_k=5, min_skor=0.0,
        )
        a_doc = [p for p in sonuc if p["dokuman"] == "a.pdf"]
        assert len(a_doc) <= 2

    def test_skor_siralamasi(self, ornek_vektor_parcalar):
        vektorler, parcalar = ornek_vektor_parcalar
        soru = np.array([0.7, 0.7, 0.0], dtype=np.float32)
        soru = soru / np.linalg.norm(soru)

        sonuc, _ = dense_kaynak_ara(
            soru, vektorler, parcalar, top_k=10, son_k=3, min_skor=0.0,
        )
        skorlar = [p["dense_skor"] for p in sonuc]
        assert skorlar == sorted(skorlar, reverse=True)


class TestTopluKaynakAra:
    """Toplu retrieval testleri."""

    def test_toplu_3_sorgu(self, ornek_vektor_parcalar):
        vektorler, parcalar = ornek_vektor_parcalar
        sorular = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ], dtype=np.float32)
        sorular = sorular / np.linalg.norm(sorular, axis=1, keepdims=True)

        tum_parcalar, tum_skorlar = toplu_kaynak_ara(
            sorular, vektorler, parcalar, top_k=10, son_k=3, min_skor=0.3,
        )
        assert len(tum_parcalar) == 3
        assert len(tum_skorlar) == 3
        for i, (p, s) in enumerate(zip(tum_parcalar, tum_skorlar)):
            assert len(p) >= 1
            assert s > 0.9


class TestRagIstatistikleri:
    """RAG istatistik testleri."""

    def test_istatistik_bos(self):
        stats = rag_istatistikleri([], [])
        assert stats["toplam_sorgu"] == 0
        assert stats["kaynaksiz_sorgu"] == 0

    def test_istatistik_dolu(self):
        parcalar_list = [[{"chunk_id": 0}], [], [{"chunk_id": 1}, {"chunk_id": 2}]]
        skorlar = [0.9, 0.0, 0.85]
        stats = rag_istatistikleri(parcalar_list, skorlar)
        assert stats["toplam_sorgu"] == 3
        assert stats["kaynaksiz_sorgu"] == 1
        assert stats["ortalama_parca_sayisi"] == 1.0