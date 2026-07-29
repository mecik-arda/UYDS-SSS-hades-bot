import hashlib
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from uygulama.modeller.semalar import AramaAdayi
from uygulama.servisler import yeniden_siralayici as yeniden_siralayici_modulu
from uygulama.servisler.yeniden_siralayici import (
    CrossEncoderYenidenSiralayici,
    YENIDEN_SIRALAMA_MANIFESTI,
    YENIDEN_SIRALAMA_MODEL_DOSYALARI,
    YenidenSiralamaHatasi,
    yeniden_siralama_manifestini_olustur,
    yerel_yeniden_siralama_modelini_dogrula,
)


class _SahteCrossEncoder:
    def __init__(self, skorlar):
        self._skorlar = skorlar
        self.ciftler = None

    def predict(self, ciftler, **ayarlar):
        self.ciftler = ciftler
        assert ayarlar["batch_size"] == 2
        assert ayarlar["show_progress_bar"] is False
        assert ayarlar["convert_to_numpy"] is True
        return np.asarray(self._skorlar)


def _aday(kimlik, metin, rrf_skoru):
    return AramaAdayi(
        sss_id=kimlik,
        parca_id=kimlik,
        aday_metni=metin,
        kaynak_dokuman=None,
        kaynak_sayfa=None,
        kaynak_satir=None,
        fts_sirasi=None,
        vektor_sirasi=None,
        rrf_skoru=rrf_skoru,
        vektor_benzerlik_skoru=None,
        yeniden_siralama_skoru=None,
    )


def _gecerli_model_dizini_olustur(gecici_yol):
    model_yolu = gecici_yol / "model"
    model_yolu.mkdir()
    yapilandirma = {
        "architectures": ["XLMRobertaForSequenceClassification"],
        "model_type": "xlm-roberta",
        "hidden_size": 384,
        "id2label": {"0": "LABEL_0"},
    }
    tokenizer_yapilandirmasi = {
        "tokenizer_class": "XLMRobertaTokenizer",
    }
    for dosya_adi in YENIDEN_SIRALAMA_MODEL_DOSYALARI:
        icerik = dosya_adi.encode("utf-8")
        if dosya_adi == "config.json":
            icerik = json.dumps(yapilandirma).encode("utf-8")
        if dosya_adi == "tokenizer_config.json":
            icerik = json.dumps(tokenizer_yapilandirmasi).encode("utf-8")
        (model_yolu / dosya_adi).write_bytes(icerik)
    manifest = yeniden_siralama_manifestini_olustur(model_yolu)
    (model_yolu / YENIDEN_SIRALAMA_MANIFESTI).write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    return model_yolu


def test_cross_encoder_ilk_adaylari_skorlayip_siralar():
    model = _SahteCrossEncoder([0.2, 0.9])
    servis = CrossEncoderYenidenSiralayici(
        model_yolu="kullanilmaz",
        aday_sayisi=2,
        toplu_islem_boyutu=2,
        maksimum_token=512,
        model=model,
    )
    adaylar = [
        _aday(1, "birinci", 0.4),
        _aday(2, "ikinci", 0.3),
        _aday(3, "ucuncu", 0.2),
    ]
    sonuc = servis.yeniden_sirala("soru", adaylar)
    assert [aday.sss_id for aday in sonuc] == [2, 1, 3]
    assert sonuc[0].yeniden_siralama_skoru == pytest.approx(0.9)
    assert sonuc[1].yeniden_siralama_skoru == pytest.approx(0.2)
    assert sonuc[2] == adaylar[2]
    assert model.ciftler == [("soru", "birinci"), ("soru", "ikinci")]


def test_cross_encoder_gecersiz_skoru_reddeder():
    servis = CrossEncoderYenidenSiralayici(
        model_yolu="kullanilmaz",
        aday_sayisi=2,
        toplu_islem_boyutu=2,
        maksimum_token=512,
        model=_SahteCrossEncoder([np.nan, 0.4]),
    )
    with pytest.raises(YenidenSiralamaHatasi):
        servis.yeniden_sirala("soru", [_aday(1, "bir", 0.2), _aday(2, "iki", 0.1)])


def test_cross_encoder_bos_sorguda_modeli_cagirmaz():
    model = _SahteCrossEncoder([0.8])
    servis = CrossEncoderYenidenSiralayici(
        model_yolu="kullanilmaz",
        aday_sayisi=1,
        toplu_islem_boyutu=2,
        maksimum_token=512,
        model=model,
    )
    adaylar = [_aday(1, "bir", 0.2)]
    assert servis.yeniden_sirala("   ", adaylar) == adaylar
    assert model.ciftler is None


def test_cross_encoder_guvenli_cevrimdisi_parametrelerle_yuklenir(
    tmp_path,
    monkeypatch,
):
    yakalanan = {}
    sahte_model = _SahteCrossEncoder([0.7])

    def sahte_cross_encoder(model_yolu, **ayarlar):
        yakalanan["model_yolu"] = model_yolu
        yakalanan["ayarlar"] = ayarlar
        return sahte_model

    monkeypatch.setattr(
        yeniden_siralayici_modulu,
        "yerel_yeniden_siralama_modelini_dogrula",
        lambda model_yolu: None,
    )
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(CrossEncoder=sahte_cross_encoder),
    )
    servis = CrossEncoderYenidenSiralayici(
        model_yolu=tmp_path,
        aday_sayisi=1,
        toplu_islem_boyutu=2,
        maksimum_token=512,
    )
    sonuc = servis.yeniden_sirala("soru", [_aday(1, "aday", 0.2)])
    assert sonuc[0].yeniden_siralama_skoru == pytest.approx(0.7)
    assert yakalanan["model_yolu"] == str(tmp_path.resolve())
    assert yakalanan["ayarlar"] == {
        "max_length": 512,
        "local_files_only": True,
        "trust_remote_code": False,
        "model_kwargs": {"use_safetensors": True},
        "processor_kwargs": {"use_fast": True},
    }


def test_yerel_model_manifesti_ve_resmi_ozeti_dogrulanir(
    tmp_path,
    monkeypatch,
):
    model_yolu = _gecerli_model_dizini_olustur(tmp_path)
    model_ozeti = hashlib.sha256(
        (model_yolu / "model.safetensors").read_bytes()
    ).hexdigest()
    monkeypatch.setattr(
        yeniden_siralayici_modulu,
        "YENIDEN_SIRALAMA_MODEL_OZETI",
        model_ozeti,
    )
    yerel_yeniden_siralama_modelini_dogrula(model_yolu)


def test_yerel_model_beklenmeyen_dosyayi_reddeder(tmp_path, monkeypatch):
    model_yolu = _gecerli_model_dizini_olustur(tmp_path)
    model_ozeti = hashlib.sha256(
        (model_yolu / "model.safetensors").read_bytes()
    ).hexdigest()
    monkeypatch.setattr(
        yeniden_siralayici_modulu,
        "YENIDEN_SIRALAMA_MODEL_OZETI",
        model_ozeti,
    )
    (model_yolu / "pytorch_model.bin").write_bytes(b"guvensiz")
    with pytest.raises(YenidenSiralamaHatasi):
        yerel_yeniden_siralama_modelini_dogrula(model_yolu)


def test_yerel_model_degistirilmis_dosyayi_reddeder(tmp_path, monkeypatch):
    model_yolu = _gecerli_model_dizini_olustur(tmp_path)
    model_ozeti = hashlib.sha256(
        (model_yolu / "model.safetensors").read_bytes()
    ).hexdigest()
    monkeypatch.setattr(
        yeniden_siralayici_modulu,
        "YENIDEN_SIRALAMA_MODEL_OZETI",
        model_ozeti,
    )
    tokenizer_yolu = model_yolu / "tokenizer.json"
    tokenizer_yolu.write_bytes(tokenizer_yolu.read_bytes() + b"degisiklik")
    with pytest.raises(YenidenSiralamaHatasi):
        yerel_yeniden_siralama_modelini_dogrula(model_yolu)
