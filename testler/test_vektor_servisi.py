import math

import numpy as np
import pytest

from uygulama.servisler.vektor_servisi import VektorModeliHatasi, VektorServisi

_VEKTOR_BOYUTU = 384


class MockSentenceTransformer:
    def __init__(self, vektor_boyutu: int = _VEKTOR_BOYUTU):
        self._vektor_boyutu = vektor_boyutu

    def get_embedding_dimension(self):
        return self._vektor_boyutu

    def encode(self, metinler, batch_size=None, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True):
        vektorler = np.ones((len(metinler), self._vektor_boyutu), dtype=np.float32)
        normlar = np.linalg.norm(vektorler, axis=1, keepdims=True)
        return vektorler / normlar


class TestVektorServisiOlusturma:
    def test_gecerli_parametrelerle_olusturulur(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            toplu_islem_boyutu=8,
            model=MockSentenceTransformer(384),
        )
        assert servis.model_adi == "test_model"
        assert servis.vektor_boyutu == 384

    def test_bos_model_adi_reddedilir(self):
        with pytest.raises(ValueError, match="bos olamaz"):
            VektorServisi(model_adi="   ", vektor_boyutu=384, model=MockSentenceTransformer(384))


class TestMetinleriVektoreDonustur:
    def test_tek_metin_384_boyutlu_vektor_uretir(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            model=MockSentenceTransformer(384),
        )
        vektor = servis.metni_vektore_donustur("merhaba dünya")
        assert vektor.shape == (384,)
        assert np.isfinite(vektor).all()

    def test_toplu_metin_matris_uretir(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            model=MockSentenceTransformer(384),
        )
        vektorler = servis.metinleri_vektore_donustur(["bir", "iki", "üç"])
        assert vektorler.shape == (3, 384)
        assert np.isfinite(vektorler).all()

    def test_birim_norm_vektor_uretir(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            model=MockSentenceTransformer(384),
        )
        vektor = servis.metni_vektore_donustur("test metni")
        norm = np.linalg.norm(vektor)
        assert math.isclose(norm, 1.0, rel_tol=1e-5)

    def test_bos_metin_listesi_bos_matris_dondurur(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            model=MockSentenceTransformer(384),
        )
        sonuc = servis.metinleri_vektore_donustur([])
        assert sonuc.shape == (0, 384)

    def test_bos_string_iceren_liste_reddedilir(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            model=MockSentenceTransformer(384),
        )
        with pytest.raises(ValueError, match="bos olamaz"):
            servis.metinleri_vektore_donustur(["gecerli", "   "])

    def test_model_boyutu_uyusmazligi_reddedilir(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=100,
            model=MockSentenceTransformer(384),
        )
        with pytest.raises(VektorModeliHatasi, match="boyut"):
            servis.metni_vektore_donustur("test")


class TestBLOBDonusum:
    def test_vektor_blob_gidis_donus(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            model=MockSentenceTransformer(384),
        )
        orijinal = servis.metni_vektore_donustur("test metni")
        blob = servis.vektoru_bloba_donustur(orijinal)
        assert len(blob) == 384 * 4
        geri_donen = servis.blobu_vektore_donustur(blob)
        assert np.allclose(orijinal, geri_donen, atol=1e-6)

    def test_yanlis_boyutlu_blob_reddedilir(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            model=MockSentenceTransformer(384),
        )
        with pytest.raises(ValueError, match="BLOB boyutu"):
            servis.blobu_vektore_donustur(b"x" * 100)

    def test_yanlis_boyutlu_vektor_bloba_donusturulemez(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            model=MockSentenceTransformer(384),
        )
        yanlis_boyutlu = np.ones(100, dtype=np.float32)
        with pytest.raises(ValueError, match="eslesmiyor"):
            servis.vektoru_bloba_donustur(yanlis_boyutlu)

    def test_nan_vektor_bloba_donusturulemez(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            model=MockSentenceTransformer(384),
        )
        nan_vektor = np.full(384, np.nan, dtype=np.float32)
        with pytest.raises(ValueError, match="sonlu"):
            servis.vektoru_bloba_donustur(nan_vektor)

    def test_inf_vektor_bloba_donusturulemez(self):
        servis = VektorServisi(
            model_adi="test_model",
            vektor_boyutu=384,
            model=MockSentenceTransformer(384),
        )
        inf_vektor = np.full(384, np.inf, dtype=np.float32)
        with pytest.raises(ValueError, match="sonlu"):
            servis.vektoru_bloba_donustur(inf_vektor)