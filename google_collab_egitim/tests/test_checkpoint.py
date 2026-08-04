# ============================================================
# Test: Checkpoint yönetimi
# ============================================================
"""Checkpoint modülü — kaydetme, yükleme, eksik kayıt tespiti."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.checkpoint import (
    checkpoint_yukle,
    checkpoint_kaydet,
    eksik_kayitlari_bul,
    butunluk_kontrolu,
    sonuc_ekle,
)


class TestCheckpointKaydetYukle:
    """Checkpoint kaydetme/yükleme testleri."""

    def test_yukle_bos_dosya(self, temp_dir):
        sonuc_dosyasi = os.path.join(temp_dir, "sonuclar.jsonl")
        meta_dosyasi = os.path.join(temp_dir, "meta.json")
        harita, gecerli = checkpoint_yukle(
            sonuc_dosyasi, meta_dosyasi, {"excel_hash": "abc123"}
        )
        assert harita == {}
        assert not gecerli

    def test_kaydet_ve_yukle(self, temp_dir):
        sonuc_dosyasi = os.path.join(temp_dir, "sonuclar.jsonl")
        meta_dosyasi = os.path.join(temp_dir, "meta.json")
        beklenen_meta = {"excel_hash": "abc123", "model": "qwen"}

        # Önce meta kaydet
        checkpoint_kaydet(meta_dosyasi, beklenen_meta)
        # Bir sonuç ekle
        sonuc_ekle(sonuc_dosyasi, {
            "_kayit_no": 0, "karar": "dogru", "guven": 0.9,
            "_islem_hatasi": False, "_veri_indeksi": 0,
        })

        # Yükle
        harita, gecerli = checkpoint_yukle(sonuc_dosyasi, meta_dosyasi, beklenen_meta)
        assert gecerli
        assert 0 in harita
        assert harita[0]["karar"] == "dogru"

    def test_meta_uyusmazligi(self, temp_dir):
        sonuc_dosyasi = os.path.join(temp_dir, "sonuclar.jsonl")
        meta_dosyasi = os.path.join(temp_dir, "meta.json")

        checkpoint_kaydet(meta_dosyasi, {"excel_hash": "abc123", "model": "qwen"})
        sonuc_ekle(sonuc_dosyasi, {
            "_kayit_no": 0, "karar": "dogru", "guven": 0.9,
            "_islem_hatasi": False, "_veri_indeksi": 0,
        })

        # Farklı meta ile yüklemeye çalış
        harita, gecerli = checkpoint_yukle(
            sonuc_dosyasi, meta_dosyasi,
            {"excel_hash": "xyz789", "model": "qwen"}  # hash farklı
        )
        assert not gecerli


class TestEksikKayit:
    """Eksik kayıt tespit testleri."""

    def test_tum_kayitlar_tamam(self):
        harita = {
            0: {"karar": "dogru", "_islem_hatasi": False},
            1: {"karar": "kanit_yetersiz", "_islem_hatasi": False},
            2: {"karar": "dogru", "_islem_hatasi": False},
        }
        tamamlanan, hatali, eksik = eksik_kayitlari_bul(harita, 3)
        assert len(tamamlanan) == 3
        assert len(hatali) == 0
        assert len(eksik) == 0

    def test_islem_hatasi_tekrar(self):
        harita = {
            0: {"karar": "dogru", "_islem_hatasi": False},
            1: {"karar": "error", "_islem_hatasi": True},
            2: {"karar": "dogru", "_islem_hatasi": False},
        }
        tamamlanan, hatali, eksik = eksik_kayitlari_bul(harita, 3)
        assert 1 in hatali
        # Hatalı haritadan silinmeli
        assert 1 not in harita

    def test_eksik_kayit(self):
        harita = {
            0: {"karar": "dogru", "_islem_hatasi": False},
        }
        tamamlanan, hatali, eksik = eksik_kayitlari_bul(harita, 5)
        assert len(eksik) == 4
        assert 1 in eksik
        assert 4 in eksik


class TestButunluk:
    """Sonuç bütünlüğü testleri."""

    def test_tam_butunluk(self):
        harita = {i: {} for i in range(10)}
        eksik = butunluk_kontrolu(harita, 10)
        assert eksik == []

    def test_eksik_butunluk(self):
        harita = {0: {}, 1: {}, 3: {}, 5: {}}
        eksik = butunluk_kontrolu(harita, 6)
        assert 2 in eksik
        assert 4 in eksik