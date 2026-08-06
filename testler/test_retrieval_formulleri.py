import math


def top_1_dogruluk(sonuclar: list[dict]) -> float:
    toplam = len(sonuclar)
    if toplam == 0:
        return 0.0
    top_1 = sum(1 for s in sonuclar if s.get("isabet_sirasi", 0) == 1)
    return round(top_1 / toplam * 100, 2)


def top_3_dogruluk(sonuclar: list[dict]) -> float:
    toplam = len(sonuclar)
    if toplam == 0:
        return 0.0
    top_3 = sum(1 for s in sonuclar if 0 < s.get("isabet_sirasi", 0) <= 3)
    return round(top_3 / toplam * 100, 2)


def mrr(sonuclar: list[dict]) -> float:
    ters_siralar = []
    for s in sonuclar:
        sira = s.get("isabet_sirasi", 0)
        ters_siralar.append(1.0 / sira if sira > 0 else 0.0)
    if not ters_siralar:
        return 0.0
    return round(sum(ters_siralar) / len(ters_siralar), 4)


def ndcg(sonuclar: list[dict]) -> float:
    ndcg_degerleri = []
    for s in sonuclar:
        sira = s.get("isabet_sirasi", 0)
        dcg = 1.0 / math.log2(sira + 1) if sira > 0 else 0.0
        ideal_dcg = 1.0
        ndcg_degerleri.append(dcg / ideal_dcg)
    if not ndcg_degerleri:
        return 0.0
    return round(sum(ndcg_degerleri) / len(ndcg_degerleri), 4)


def test_top_1_sifir_sonuc():
    assert top_1_dogruluk([]) == 0.0


def test_top_1_hepsi_birinci_sirada():
    sonuclar = [{"isabet_sirasi": 1}, {"isabet_sirasi": 1}, {"isabet_sirasi": 1}]
    assert top_1_dogruluk(sonuclar) == 100.0


def test_top_1_yarisi_birinci():
    sonuclar = [{"isabet_sirasi": 1}, {"isabet_sirasi": 2}, {"isabet_sirasi": 1}, {"isabet_sirasi": 3}]
    assert top_1_dogruluk(sonuclar) == 50.0


def test_top_1_hicbiri():
    sonuclar = [{"isabet_sirasi": 2}, {"isabet_sirasi": 0}, {"isabet_sirasi": 5}]
    assert top_1_dogruluk(sonuclar) == 0.0


def test_top_3_iki_uc_arasi():
    sonuclar = [{"isabet_sirasi": 1}, {"isabet_sirasi": 3}, {"isabet_sirasi": 4}, {"isabet_sirasi": 2}]
    assert top_3_dogruluk(sonuclar) == 75.0


def test_mrr_birinci_ve_ikinci():
    sonuclar = [{"isabet_sirasi": 1}, {"isabet_sirasi": 2}]
    beklenen = round((1.0 / 1 + 1.0 / 2) / 2, 4)
    assert mrr(sonuclar) == beklenen


def test_mrr_sifir_isabet():
    sonuclar = [{"isabet_sirasi": 0}, {"isabet_sirasi": 0}]
    assert mrr(sonuclar) == 0.0


def test_mrr_tek_birinci():
    sonuclar = [{"isabet_sirasi": 1}]
    assert mrr(sonuclar) == 1.0


def test_ndcg_birinci_sirada():
    sonuclar = [{"isabet_sirasi": 1}]
    dcg = 1.0 / math.log2(2)
    ideal = 1.0
    beklenen = round(dcg / ideal, 4)
    assert ndcg(sonuclar) == beklenen


def test_ndcg_ikinci_sirada():
    sonuclar = [{"isabet_sirasi": 2}]
    dcg = 1.0 / math.log2(3)
    ideal = 1.0
    beklenen = round(dcg / ideal, 4)
    assert ndcg(sonuclar) == beklenen


def test_ndcg_ucuncu_sirada():
    sonuclar = [{"isabet_sirasi": 3}]
    dcg = 1.0 / math.log2(4)
    ideal = 1.0
    beklenen = round(dcg / ideal, 4)
    assert ndcg(sonuclar) == beklenen


def test_ndcg_yoksa_sifir():
    sonuclar = [{"isabet_sirasi": 0}]
    assert ndcg(sonuclar) == 0.0
