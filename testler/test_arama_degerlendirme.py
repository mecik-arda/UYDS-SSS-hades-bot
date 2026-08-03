from testler.karsilastirma.degerlendirme import (
    davranis_basarili_mi,
    kabul_durumunu_hesapla,
    metrikleri_hesapla,
)


def _sonuc(
    kimlik: str,
    beklenen: str,
    kaynaklar: list[int],
    beklenen_kaynaklar: list[int],
    cevaplandi: bool,
    yeterli_guven: bool,
    gecikme: float,
) -> dict:
    return {
        "senaryo_id": kimlik,
        "test_gecerli": True,
        "beklenen_davranis": beklenen,
        "kaynak_idleri": kaynaklar,
        "beklenen_kaynak_idleri": beklenen_kaynaklar,
        "cevaplandi": cevaplandi,
        "yeterli_guven": yeterli_guven,
        "gecen_sure_ms": gecikme,
    }


def test_arama_ve_gecikme_metrikleri_hesaplanir():
    sonuclar = [
        _sonuc("T-1", "BASARILI_CEVAP", [7, 8, 9], [7], True, True, 10),
        _sonuc("T-2", "BASARILI_CEVAP", [8, 7, 9], [7], True, True, 20),
        _sonuc("T-3", "BASARILI_CEVAP", [8, 9, 7], [7], True, True, 30),
        _sonuc("T-4", "BASARILI_CEVAP", [8, 9, 10], [7], True, True, 40),
        _sonuc("T-5", "GUVEN_ESIK_ALTI", [], [], False, False, 50),
    ]

    metrikler = metrikleri_hesapla(sonuclar)

    assert metrikler["top_1_dogruluk"] == 25.0
    assert metrikler["top_3_dogruluk"] == 75.0
    assert metrikler["mrr_10"] == 0.4583
    assert metrikler["ndcg_10"] == 0.5327
    assert metrikler["p50_gecikme_ms"] == 30.0
    assert metrikler["p95_gecikme_ms"] == 48.0
    assert metrikler["cevap_vermeme_basarisi"] == 100.0
    assert metrikler["kaynak_gosterme_orani"] == 100.0


def test_etiketsiz_veri_arama_kabulunu_gecemez():
    sonuclar = [
        _sonuc("T-1", "BASARILI_CEVAP", [7], [], True, True, 10),
        _sonuc("T-2", "GUVEN_ESIK_ALTI", [], [], False, False, 20),
    ]

    metrikler = metrikleri_hesapla(sonuclar)
    kabul = kabul_durumunu_hesapla(metrikler)

    assert metrikler["etiketli_senaryo"] == 0
    assert metrikler["top_1_dogruluk"] is None
    assert metrikler["top_3_dogruluk"] is None
    assert kabul["basarili"] is False
    assert kabul["kontroller"]["asgari_etiketli_senaryo"] is False


def test_dusuk_guven_sonucunda_kaynak_sizdirilmasi_basarisizdir():
    sonuc = _sonuc(
        "T-1",
        "GUVEN_ESIK_ALTI",
        [7],
        [],
        False,
        False,
        10,
    )

    assert davranis_basarili_mi(sonuc) is False
