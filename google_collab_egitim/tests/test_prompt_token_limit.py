# ============================================================
# Test: Prompt token limiti ve kısaltma
# ============================================================
"""Prompt builder modülü — token sayımı, kısaltma stratejisi."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.prompt_builder import (
    token_say,
    prompt_token_kisalt,
    kaynak_formatla,
    mesaj_olustur,
    SISTEM_PROMPT,
    DOGRULAMA_PROMPT_SABLON,
    kanit_yetersiz_yanit,
    cevap_bos_yanit,
    islem_hatasi_yanit,
    CEVAP_SEMASI,
)


class TestTokenSay:
    """Token sayma testleri."""

    def test_tokenizer_yok_fallback(self):
        messages = [
            {"role": "system", "content": "Sen bir uzmansın."},
            {"role": "user", "content": "Soruyu değerlendir."},
        ]
        count = token_say(messages, None)
        assert count > 0
        # Karakter/4 ≈ 9-10 token
        assert 5 <= count <= 50

    def test_bos_mesaj(self):
        count = token_say([], None)
        assert count == 0


class TestHazirYanitlar:
    """Kaynaksız/boş cevap/hata yanıtları testleri."""

    def test_kanit_yetersiz(self):
        yanit = kanit_yetersiz_yanit()
        assert yanit["karar"] == "kanit_yetersiz"
        assert yanit["guven"] == 0.0
        assert yanit["kaynak_idleri"] == []
        assert not yanit["_islem_hatasi"]

    def test_cevap_bos(self):
        yanit = cevap_bos_yanit()
        assert yanit["karar"] == "cevap_bos"
        assert yanit["guven"] == 1.0

    def test_islem_hatasi(self):
        yanit = islem_hatasi_yanit("vLLM hatası")
        assert yanit["karar"] == "error"
        assert yanit["_islem_hatasi"]


class TestJSONSemasi:
    """Structured output JSON şeması testleri."""

    def test_zorunlu_alanlar(self):
        assert "karar" in CEVAP_SEMASI["required"]
        assert "guven" in CEVAP_SEMASI["required"]
        assert "kaynak_idleri" in CEVAP_SEMASI["required"]
        assert "dayanak" in CEVAP_SEMASI["required"]

    def test_karar_degerleri(self):
        enum = CEVAP_SEMASI["properties"]["karar"]["enum"]
        assert "dogru" in enum
        assert "kismen_dogru" in enum
        assert "yanlis" in enum
        assert "kanit_yetersiz" in enum
        assert "soru_belirsiz" in enum

    def test_additional_properties_false(self):
        assert CEVAP_SEMASI.get("additionalProperties") is False


class TestPromptTokenKisalt:
    """Prompt kısaltma stratejisi testleri."""

    @pytest.fixture
    def uzun_parcalar(self):
        """Uzun metinli 5 chunk."""
        uzun_metin = "Bu oldukça uzun bir referans metnidir ve birçok cümle içermektedir. " * 20
        return [
            {"chunk_id": i, "dokuman": f"doc{i}.pdf", "sayfa": i,
             "metin": uzun_metin, "skor": 0.9 - i * 0.1}
            for i in range(5)
        ]

    def test_kaynaksiz_durum(self):
        soru, cevap, kaynak_metni, kalan = prompt_token_kisalt(
            "Soru", "Cevap", [], None, token_limit=1000,
        )
        assert kalan == []
        assert "(Kaynak bulunamadı)" in kaynak_metni

    def test_tum_kaynaklar_sigiyor(self, uzun_parcalar):
        """Kısa metinli chunk'lar token limitine sığmalı."""
        kisa_parcalar = [
            {"chunk_id": 0, "dokuman": "a.pdf", "metin": "Kısa metin.", "skor": 0.9}
        ]
        soru, cevap, kaynak_metni, kalan = prompt_token_kisalt(
            "Soru?", "Cevap.", kisa_parcalar, None, token_limit=2000,
        )
        assert len(kalan) == 1

    def test_skor_siralamasi(self, uzun_parcalar):
        """En yüksek skorlu chunk'lar önce gelmeli."""
        _, _, _, kalan = prompt_token_kisalt(
            "Soru", "Cevap", uzun_parcalar, None, token_limit=50,
        )
        if kalan:
            assert kalan[0]["skor"] >= kalan[-1]["skor"]


class TestKaynakFormatla:
    """Kaynak formatlama testleri."""

    def test_bos_parca(self):
        metin = kaynak_formatla([])
        assert "kanit_yetersiz" in metin.lower()

    def test_formatli_cikti(self):
        parcalar = [
            {"chunk_id": 5, "dokuman": "test.pdf", "sayfa": 3,
             "metin": "Örnek metin.", "skor": 0.85},
        ]
        metin = kaynak_formatla(parcalar)
        assert "[Kaynak ID:5" in metin
        assert "test.pdf" in metin
        assert "Örnek metin" in metin


class TestMesajOlustur:
    """Chat mesajı oluşturma testleri."""

    def test_sistem_ve_kullanici_mesaji(self):
        parcalar = [
            {"chunk_id": 1, "dokuman": "a.pdf", "metin": "Test.", "skor": 0.9},
        ]
        mesaj = mesaj_olustur("Soru?", "Cevap!", parcalar)
        assert len(mesaj) == 2
        assert mesaj[0]["role"] == "system"
        assert mesaj[1]["role"] == "user"
        assert "Soru?" in mesaj[1]["content"]
        assert "Cevap!" in mesaj[1]["content"]