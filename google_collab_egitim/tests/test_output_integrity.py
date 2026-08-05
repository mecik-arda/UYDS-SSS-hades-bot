# ============================================================
# Test: Çıktı bütünlüğü ve sonuç tutarlılığı
# ============================================================
"""Doğrulanan/şüpheli maskesi, _kayit_no benzersizliği, eksik kayıt kontrolü."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.checkpoint import butunluk_kontrolu, eksik_kayitlari_bul


class TestDogrulananMaskesi:
    """doğrulanan = dogru + guven >= esik + ~_islem_hatasi"""

    def test_dogrulanan_maskesi(self):
        df = pd.DataFrame({
            "_karar": ["dogru", "dogru", "dogru", "kismen_dogru", "kanit_yetersiz"],
            "_guven": [0.95, 0.80, 0.90, 0.70, 0.0],
            "_islem_hatasi": [False, False, True, False, False],
            "_kaynak_idleri": ["[0,1]", "[2]", "[3]", "[]", "[]"],
        })

        dogrulanan_mask = (
            (df["_karar"] == "dogru")
            & (df["_guven"] >= 0.85)
            & (~df["_islem_hatasi"])
            & (df["_kaynak_idleri"] != "[]")
        )
        # dogru + güven>=0.85 + hatasız + kaynak var → sadece indeks 0
        assert list(df[dogrulanan_mask].index) == [0]

    def test_supheli_diger_tum_kayitlar(self):
        df = pd.DataFrame({
            "_karar": ["dogru", "dogru", "kismen_dogru", "yanlis", "cevap_bos"],
            "_guven": [0.95, 0.80, 0.70, 0.0, 1.0],
            "_islem_hatasi": [False, False, False, False, False],
            "_kaynak_idleri": ["[1,2]", "[]", "[]", "[]", "[]"],
        })
        GUVEN_ESIK = 0.85

        dogrulanan_mask = (
            (df["_karar"] == "dogru")
            & (df["_guven"] >= GUVEN_ESIK)
            & (~df["_islem_hatasi"])
            & (df["_kaynak_idleri"] != "[]")
        )
        dogrulanan = df[dogrulanan_mask]
        supheli = df[~dogrulanan_mask]

        assert len(dogrulanan) == 1
        assert len(supheli) == 4


class TestKayitNoBenzersizlik:
    """_kayit_no tekrarı kontrolü."""

    def test_benzersiz_kayit_nolari(self):
        sonuclar = [
            {"_kayit_no": 0, "karar": "dogru"},
            {"_kayit_no": 1, "karar": "kanit_yetersiz"},
            {"_kayit_no": 2, "karar": "dogru"},
        ]
        nolar = [s["_kayit_no"] for s in sonuclar]
        assert len(nolar) == len(set(nolar))

    def test_mukerer_son_gecerli(self):
        """Aynı _kayit_no iki kez varsa son geçerli olan kullanılır."""
        sonuclar = [
            {"_kayit_no": 1, "karar": "yanlis", "guven": 0.3},
            {"_kayit_no": 1, "karar": "dogru", "guven": 0.9},
        ]
        harita = {}
        for s in sonuclar:
            harita[s["_kayit_no"]] = s
        # Son eklenen geçerli
        assert harita[1]["karar"] == "dogru"
        assert harita[1]["guven"] == 0.9


class TestEksikKayitFinal:
    """Final bütünlük kontrolü."""

    def test_eksik_yok(self):
        harita = {i: {} for i in range(100)}
        eksik = butunluk_kontrolu(harita, 100)
        assert eksik == []

    def test_eksik_var(self):
        harita = {0: {}, 2: {}, 5: {}}
        eksik = butunluk_kontrolu(harita, 6)
        assert 1 in eksik
        assert 3 in eksik
        assert 4 in eksik

    def test_islem_hatasi_eksik_sayilir(self):
        harita = {
            0: {"karar": "dogru", "_islem_hatasi": False},
            1: {"karar": "error", "_islem_hatasi": True},
            2: {"karar": "kanit_yetersiz", "_islem_hatasi": False},
        }
        tamamlanan, hatali, _ = eksik_kayitlari_bul(harita, 3)
        assert 0 in tamamlanan
        assert 2 in tamamlanan
        assert 1 in hatali


class TestSmokeTestEsikleri:
    """Smoke test başarısızlık kuralları."""

    def test_islem_hatasi_orani_yuksek(self):
        benchmark_sonuc = [
            {"_islem_hatasi": False} for _ in range(10)
        ] + [
            {"_islem_hatasi": True} for _ in range(5)
        ]  # 5/15 = 33% hata
        hata_orani = sum(1 for s in benchmark_sonuc if s["_islem_hatasi"]) / len(benchmark_sonuc)
        assert hata_orani > 0.05  # Smoke test durdurulmalı

    def test_ortalama_kaynak_dusuk(self):
        rag_sonuc_kaynaklar = [0, 1, 0, 2, 0, 1, 0, 0, 1, 0]  # ort = 0.5
        ortalama = np.mean(rag_sonuc_kaynaklar)
        assert ortalama < 1.0  # Smoke test durdurulmalı

    def test_kanit_yetersiz_orani_yuksek(self):
        kararlar = (["kanit_yetersiz"] * 85) + (["dogru"] * 10) + (["kismen_dogru"] * 5)
        ky_oran = kararlar.count("kanit_yetersiz") / len(kararlar)
        assert ky_oran > 0.80  # Uyarı verilmeli