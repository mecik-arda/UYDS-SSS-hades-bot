# ============================================================
# Test: JSON çıktı doğrulama
# ============================================================
"""Validator modülü — JSON parse, karar doğrulama testleri."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.validator import (
    ham_metinden_json_cikar,
    sonuc_dogrula,
    GECERLI_KARARLAR,
)


class TestJSONParse:
    """JSON parse testleri."""

    def test_gecerli_json(self):
        sonuc = ham_metinden_json_cikar(
            '{"karar":"dogru","guven":0.95,"kaynak_idleri":[1,2],'
            '"dayanak":"Kaynak destekliyor.","eksik_veya_hata":"",'
            '"duzeltilmis_cevap":""}',
            sunulan_idler={1, 2},
        )
        assert sonuc["karar"] == "dogru"
        assert sonuc["guven"] == 0.95
        assert sonuc["kaynak_idleri"] == [1, 2]
        assert not sonuc["_islem_hatasi"]

    def test_markdown_kod_bloklu_json(self):
        sonuc = ham_metinden_json_cikar(
            '```json\n{"karar":"dogru","guven":0.9,"kaynak_idleri":[5],'
            '"dayanak":"Test","eksik_veya_hata":"","duzeltilmis_cevap":""}\n```',
            sunulan_idler={5},
        )
        assert sonuc["karar"] == "dogru"
        assert not sonuc["_islem_hatasi"]

    def test_bozuk_json(self):
        sonuc = ham_metinden_json_cikar("bu json değil", sunulan_idler=set())
        assert sonuc["_islem_hatasi"]

    def test_bos_metin(self):
        sonuc = ham_metinden_json_cikar("", sunulan_idler=set())
        assert sonuc["_islem_hatasi"]


class TestKararDogrulama:
    """Karar doğrulama kuralları testleri."""

    def test_gecersiz_karar_soru_belirsiz(self):
        sonuc = sonuc_dogrula(
            {"karar": "belirsiz_karar", "guven": 0.5, "kaynak_idleri": [1],
             "dayanak": "", "eksik_veya_hata": "", "duzeltilmis_cevap": ""},
            sunulan_idler={1},
        )
        assert sonuc["karar"] == "soru_belirsiz"

    def test_dogru_bos_kaynak(self):
        sonuc = sonuc_dogrula(
            {"karar": "dogru", "guven": 0.95, "kaynak_idleri": [],
             "dayanak": "Doğru", "eksik_veya_hata": "", "duzeltilmis_cevap": ""},
            sunulan_idler=set(),
        )
        assert sonuc["karar"] == "kanit_yetersiz"
        assert sonuc["guven"] == 0.0

    def test_dogru_duzeltilmis_cevap_bosalt(self):
        sonuc = sonuc_dogrula(
            {"karar": "dogru", "guven": 0.95, "kaynak_idleri": [1],
             "dayanak": "Doğru", "eksik_veya_hata": "", "duzeltilmis_cevap": "Gereksiz metin"},
            sunulan_idler={1},
        )
        assert sonuc["karar"] == "dogru"
        assert sonuc["duzeltilmis_cevap"] == ""

    def test_guven_sinir_disi(self):
        sonuc = sonuc_dogrula(
            {"karar": "dogru", "guven": 1.5, "kaynak_idleri": [1],
             "dayanak": "", "eksik_veya_hata": "", "duzeltilmis_cevap": ""},
            sunulan_idler={1},
        )
        assert 0.0 <= sonuc["guven"] <= 1.0

    def test_kaynak_id_filtreleme(self):
        sonuc = sonuc_dogrula(
            {"karar": "dogru", "guven": 0.9, "kaynak_idleri": [1, 99, 100],
             "dayanak": "", "eksik_veya_hata": "", "duzeltilmis_cevap": ""},
            sunulan_idler={1, 2, 3},
        )
        assert sonuc["kaynak_idleri"] == [1]

    def test_gecerli_kararlar(self):
        for karar in ["dogru", "kismen_dogru", "yanlis", "kanit_yetersiz", "soru_belirsiz"]:
            sonuc = sonuc_dogrula(
                {"karar": karar, "guven": 0.8, "kaynak_idleri": [1],
                 "dayanak": "Test", "eksik_veya_hata": "", "duzeltilmis_cevap": ""},
                sunulan_idler={1},
            )
            assert sonuc["karar"] == karar
            assert not sonuc["_islem_hatasi"]