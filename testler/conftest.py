import os

os.environ["VERITABANI_SIFRELEME_ANAHTARI"] = "test_anahtari_32_karakter_uzunlugunda_minimum"
os.environ["JWT_GIZLI_ANAHTARI"] = "test_jwt_anahtari_32_karakter_uzunlugunda"
os.environ["VARSAYILAN_YONETICI_SIFRESI"] = "test_sifresi_12_karakter_minimum"

import numpy as np
import pytest

import uygulama.cekirdek.konfigurasyon as konfigurasyon_modulu


@pytest.fixture
def mock_vektor_servisi():
    class MockVektorServisi:
        model_adi = "test_model"
        vektor_boyutu = 384

        def metni_vektore_donustur(self, metin: str) -> np.ndarray:
            vektor = np.ones(self.vektor_boyutu, dtype=np.float32)
            return vektor / np.linalg.norm(vektor)

        def metinleri_vektore_donustur(self, metinler: list[str]) -> np.ndarray:
            return np.vstack(
                [self.metni_vektore_donustur(metin) for metin in metinler]
            )

        def vektoru_bloba_donustur(self, vektor: np.ndarray) -> bytes:
            dizi = np.asarray(vektor, dtype="<f4")
            if dizi.shape != (self.vektor_boyutu,):
                raise ValueError("Vektor boyutu gecersiz")
            return np.ascontiguousarray(dizi).tobytes(order="C")

        def blobu_vektore_donustur(self, blob: bytes) -> np.ndarray:
            if len(blob) != self.vektor_boyutu * 4:
                raise ValueError("Vektor BLOB boyutu gecersiz")
            return np.frombuffer(blob, dtype="<f4").astype(np.float32)

    return MockVektorServisi()


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
    from uygulama.modeller.veritabani_modelleri import tablolari_olustur

    tablolari_olustur()
    yield veritabani_yolu
