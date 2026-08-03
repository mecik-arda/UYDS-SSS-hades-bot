import json
from pathlib import Path

import pytest

from uygulama.cekirdek import konfigurasyon as konfigurasyon_modulu
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.servisler.terim_haritasi import (
    AZAMI_TERIM_UZUNLUGU,
    TerimHaritasi,
    TerimHaritasiHatasi,
    terimi_normalize_et,
    sorguyu_normalize_et,
)

_GECERLI_HARITA = {
    "başvuru": ["müracaat", "talep"],
    "ödeme": ["ücret", "tahsilat"],
}


def _harita_dosyasi_olustur(dizin: Path, icerik: dict) -> Path:
    dosya = dizin / "test_harita.json"
    dosya.write_text(json.dumps(icerik, ensure_ascii=False), encoding="utf-8")
    return dosya


class TestTerimHaritasiYukleme:
    def test_gecerli_json_yuklenir(self, tmp_path, monkeypatch):
        _harita_dosyasi_olustur(tmp_path, _GECERLI_HARITA)
        harita = TerimHaritasi(dosya_yolu=tmp_path / "test_harita.json")
        sonuc = harita.yukle()
        assert "başvuru" in sonuc
        assert "müracaat" in sonuc["başvuru"]

    def test_dosya_bulunamazsa_file_not_found_error_firlatilir(self):
        harita = TerimHaritasi(dosya_yolu=Path("/var/yok/dizin/harita_yok.json"))
        with pytest.raises(FileNotFoundError):
            harita.yukle()

    def test_bos_nesne_reddedilir(self, tmp_path):
        _harita_dosyasi_olustur(tmp_path, {})
        harita = TerimHaritasi(dosya_yolu=tmp_path / "test_harita.json")
        with pytest.raises(TerimHaritasiHatasi, match="bos olmayan"):
            harita.yukle()

    def test_liste_olmayan_es_anlamlilar_reddedilir(self, tmp_path):
        _harita_dosyasi_olustur(tmp_path, {"anahtar": "liste_degil"})
        harita = TerimHaritasi(dosya_yolu=tmp_path / "test_harita.json")
        with pytest.raises(TerimHaritasiHatasi):
            harita.yukle()

    def test_bos_es_anlamli_listesi_reddedilir(self, tmp_path):
        _harita_dosyasi_olustur(tmp_path, {"anahtar": []})
        harita = TerimHaritasi(dosya_yolu=tmp_path / "test_harita.json")
        with pytest.raises(TerimHaritasiHatasi):
            harita.yukle()

    def test_json_yinelenen_anahtar_son_degeri_alir(self, tmp_path):
        dosya = tmp_path / "test_harita.json"
        dosya.write_text(
            '{"aynı_terim": ["a"], "aynı_terim": ["b"]}',
            encoding="utf-8",
        )
        harita = TerimHaritasi(dosya_yolu=dosya)
        sonuc = harita.yukle()
        assert sonuc["aynı_terim"] == ("b",)

    def test_gecersiz_json_dosyasi_reddedilir(self, tmp_path):
        dosya = tmp_path / "test_harita.json"
        dosya.write_text("{bozuk json,,,", encoding="utf-8")
        harita = TerimHaritasi(dosya_yolu=dosya)
        with pytest.raises(TerimHaritasiHatasi, match="okunamadi"):
            harita.yukle()

    def test_boyut_sinirini_asan_dosya_reddedilir(self, tmp_path, monkeypatch):
        dosya = tmp_path / "buyuk_harita.json"
        dosya.write_bytes(b"x" * (1024 * 1024 + 1))
        harita = TerimHaritasi(dosya_yolu=dosya)
        with pytest.raises(TerimHaritasiHatasi, match="boyutu"):
            harita.yukle()

    def test_capraz_grup_terim_catismasi_reddedilir(self, tmp_path):
        _harita_dosyasi_olustur(
            tmp_path,
            {"grup_a": ["ortak"], "grup_b": ["ortak"]},
        )
        harita = TerimHaritasi(dosya_yolu=tmp_path / "test_harita.json")
        with pytest.raises(TerimHaritasiHatasi, match="birden fazla"):
            harita.yukle()


class TestTerimHaritasiSorgulama:
    def test_es_anlamlilari_getirir(self, tmp_path):
        _harita_dosyasi_olustur(tmp_path, _GECERLI_HARITA)
        harita = TerimHaritasi(dosya_yolu=tmp_path / "test_harita.json")
        sonuc = harita.es_anlamlilari_al("müracaat")
        assert "başvuru" in sonuc
        assert "talep" in sonuc

    def test_bilinmeyen_terim_bos_doner(self, tmp_path):
        _harita_dosyasi_olustur(tmp_path, _GECERLI_HARITA)
        harita = TerimHaritasi(dosya_yolu=tmp_path / "test_harita.json")
        assert harita.es_anlamlilari_al("bilinmeyen_xyz") == ()

    def test_ana_terim_kendisini_icermez(self, tmp_path):
        _harita_dosyasi_olustur(tmp_path, _GECERLI_HARITA)
        harita = TerimHaritasi(dosya_yolu=tmp_path / "test_harita.json")
        sonuc = harita.es_anlamlilari_al("başvuru")
        assert "başvuru" not in sonuc


class TestNormalizasyon:
    def test_turkce_buyuk_i_kucuk_isiz_olur(self):
        sonuc = terimi_normalize_et("İSTANBUL")
        assert "istanbul" in sonuc

    def test_buyuk_i_noktasiz_olur(self):
        sonuc = terimi_normalize_et("IŞIK")
        assert "ışık" in sonuc

    def test_bos_metin_reddedilir(self):
        with pytest.raises(TerimHaritasiHatasi, match="bos"):
            terimi_normalize_et("   ")

    def test_kontrol_karakteri_reddedilir(self):
        with pytest.raises(TerimHaritasiHatasi, match="kontrol"):
            terimi_normalize_et("merhaba\x00")

    def test_azami_terim_uzunlugu_asilamaz(self):
        with pytest.raises(TerimHaritasiHatasi, match="karakteri asamaz"):
            terimi_normalize_et("a" * (AZAMI_TERIM_UZUNLUGU + 1))

    def test_sorgu_normalizasyonu_bosluklari_tekler(self):
        sonuc = sorguyu_normalize_et("  çok   fazla   boşluk  ")
        assert sonuc == "çok fazla boşluk"

    def test_unicode_nfc_normalizasyonu_uygulanir(self):
        a_umlaut = "\u0061\u0308"
        a_umlaut_nfc = "\u00e4"
        assert terimi_normalize_et(a_umlaut) == terimi_normalize_et(a_umlaut_nfc)

    def test_es_anlamli_kendi_kendine_normalize_edilince_atlanir(self, tmp_path):
        ham = {"anahtar": ["anahtar", "gerçek_es"]}
        _harita_dosyasi_olustur(tmp_path, ham)
        harita = TerimHaritasi(dosya_yolu=tmp_path / "test_harita.json")
        harita.yukle()
        sonuc = harita.es_anlamlilari_al("anahtar")
        assert "anahtar" not in sonuc
        assert "gerçek_es" in sonuc