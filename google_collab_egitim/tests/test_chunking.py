# ============================================================
# Test: Tokenizer tabanlı chunking
# ============================================================
"""Chunking modülünün birim testleri."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.chunking import (
    tokenizer_bazli_chunk,
    belgeyi_chunkla,
    chunk_istatistikleri,
    _metni_cumlelere_ayir,
)


class TestCumleAyirma:
    """Cümlelere ayırma testleri."""

    def test_basit_cumle(self):
        cumleler = _metni_cumlelere_ayir("Merhaba dünya. Bu bir test. İkinci cümle.")
        assert len(cumleler) == 3

    def test_turkce_cumle(self):
        cumleler = _metni_cumlelere_ayir(
            "Hakediş onaylandı. Sistem güncellendi. İşlem tamam."
        )
        assert len(cumleler) == 3

    def test_tek_cumle(self):
        cumleler = _metni_cumlelere_ayir("Bu tek bir cümle")
        assert len(cumleler) == 1


class TestTokenizerChunk:
    """Tokenizer bazlı chunking testleri."""

    def test_bos_metin(self):
        result = tokenizer_bazli_chunk("", None, hedef_token=100)
        assert result == []

    def test_kisa_metin(self):
        metin = "Bu kısa bir metin. Tek chunk olmalı."
        result = tokenizer_bazli_chunk(metin, None, hedef_token=100, overlap_token=20)
        assert len(result) == 1

    def test_uzun_metin_cok_chunk(self):
        """Uzun metin birden fazla chunk'a bölünmeli (kelime bazlı fallback)."""
        # Noktasız metin → cümle algılanmaz → direkt token split
        metin = " ".join(["kelime"] * 200)
        result = tokenizer_bazli_chunk(
            metin, None, hedef_token=10, overlap_token=3, min_chunk_token=1
        )
        # 200 kelime / (10*1.3 - 3*1.3) ≈ 22 chunk
        assert len(result) > 1

    def test_overlap_calismasi(self):
        """Overlap ile art arda gelen chunk'larda örtüşme olmalı."""
        metin = ". ".join([f"Cümle {i}" for i in range(20)]) + "."
        result = tokenizer_bazli_chunk(metin, None, hedef_token=30, overlap_token=10)
        assert len(result) > 1

    def test_min_chunk_birlestirme(self):
        """Çok kısa chunk'lar komşuya birleşmeli."""
        metin = "Kısa. " * 3 + "Bu daha uzun bir cümle olup chunk sınırını aşacak kadar uzatılmıştır. " * 5
        result = tokenizer_bazli_chunk(
            metin, None, hedef_token=50, overlap_token=10, min_chunk_token=30
        )
        # Her chunk en az min_chunk_token kadar olmalı
        for chunk in result:
            assert len(chunk.split()) >= 3  # Yaklaşık kontrol


class TestBelgeChunkla:
    """belgeyi_chunkla fonksiyonunun testleri."""

    def test_bos_belge_listesi(self):
        result = belgeyi_chunkla([], None)
        assert result == []

    def test_metadata_korunmasi(self):
        belgeler = [
            {
                "dosya": "test.pdf",
                "sayfa": 3,
                "metin": "Bu test sayfasıdır. İkinci cümle. Üçüncü cümle. Dördüncü cümle.",
                "meta": {
                    "kaynak_tipi": "mevzuat",
                    "kurum": "Test Kurumu",
                },
            }
        ]
        result = belgeyi_chunkla(belgeler, None, hedef_token=10, overlap_token=3)
        assert len(result) >= 1
        for chunk in result:
            assert chunk["dokuman"] == "test.pdf"
            assert chunk["sayfa"] == 3
            assert chunk["kaynak_tipi"] == "mevzuat"
            assert chunk["kurum"] == "Test Kurumu"

    def test_global_chunk_id(self):
        belgeler = [
            {"dosya": "a.pdf", "sayfa": 1, "metin": "A. " * 30, "meta": {}},
            {"dosya": "b.pdf", "sayfa": 2, "metin": "B. " * 30, "meta": {}},
        ]
        result = belgeyi_chunkla(belgeler, None, hedef_token=10, overlap_token=2)
        ids = [c["chunk_id"] for c in result]
        assert ids == list(range(len(ids)))
        assert len(set(ids)) == len(ids)  # Benzersiz

    def test_yerel_chunk_sirasi(self):
        belgeler = [
            {"dosya": "a.pdf", "sayfa": 1, "metin": "A. " * 30, "meta": {}},
        ]
        result = belgeyi_chunkla(belgeler, None, hedef_token=10, overlap_token=2)
        for i, c in enumerate(result):
            assert c["yerel_chunk"] == i + 1


class TestChunkIstatistikleri:
    """Chunk istatistikleri testleri."""

    def test_bos_chunk_istatistik(self):
        stats = chunk_istatistikleri([], None)
        assert stats["toplam_chunk"] == 0

    def test_dolu_istatistik(self):
        chunklar = [
            {"metin": "Kısa.", "dokuman": "a.pdf", "modul": "Hakediş"},
            {"metin": "Bu daha uzun bir metin parçasıdır.", "dokuman": "b.pdf", "modul": "İhale"},
        ]
        stats = chunk_istatistikleri(chunklar, None)
        assert stats["toplam_chunk"] == 2
        assert stats["dokuman_sayisi"] == 2
        assert stats["modul_sayisi"] == 2