import os

os.environ["VERITABANI_SIFRELEME_ANAHTARI"] = "test_anahtari_32_karakter_uzunlugunda_minimum"
os.environ["JWT_GIZLI_ANAHTARI"] = "test_jwt_anahtari_32_karakter_uzunlugunda"
os.environ["VARSAYILAN_YONETICI_SIFRESI"] = "test_sifresi_12_karakter_minimum"

import pytest

import uygulama.cekirdek.konfigurasyon as konfigurasyon_modulu


@pytest.fixture
def gecici_veritabani(tmp_path, monkeypatch):
    veritabani_yolu = tmp_path / "test.db"
    monkeypatch.setenv("VERITABANI_YOLU", str(veritabani_yolu))
    monkeypatch.setenv("ES_ANLAMLILAR_YOLU", str(tmp_path / "es_anlamlilar.json"))
    test_konfigurasyon = konfigurasyon_modulu.Konfigurasyon(
        VERITABANI_YOLU=str(veritabani_yolu),
        ES_ANLAMLILAR_YOLU=str(tmp_path / "es_anlamlilar.json"),
        VERITABANI_SIFRELEME_ANAHTARI="test_anahtari_32_karakter_uzunlugunda_minimum",
        JWT_GIZLI_ANAHTARI="test_jwt_anahtari_32_karakter_uzunlugunda",
        VARSAYILAN_YONETICI_SIFRESI="test_sifresi_12_karakter_minimum",
    )
    monkeypatch.setattr(
        konfigurasyon_modulu,
        "konfigurasyon",
        test_konfigurasyon,
    )
    import uygulama.cekirdek.veritabani as veritabani_modulu

    monkeypatch.setattr(
        veritabani_modulu,
        "konfigurasyon",
        test_konfigurasyon,
    )
    yield veritabani_yolu
