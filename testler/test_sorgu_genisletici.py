import pytest

from uygulama.servisler.sorgu_genisletici import SorguGenisletici, SorguGenisletmeHatasi
from uygulama.servisler.terim_haritasi import TerimHaritasi


class _SahteTerimHaritasi(TerimHaritasi):
    def __init__(self, harita=None):
        self._harita_dict = harita or {}
        self._ters_harita_dict = {}
        if harita:
            for ana_terim, es_anlamlilar in harita.items():
                for terim in (ana_terim,) + es_anlamlilar:
                    self._ters_harita_dict[terim] = ana_terim

    def yukle(self):
        self._harita = dict(self._harita_dict)
        self._ters_harita = dict(self._ters_harita_dict)
        return dict(self._harita)

    def es_anlamlilari_al(self, terim):
        return ()


@pytest.fixture
def bos_harita():
    return _SahteTerimHaritasi({})


@pytest.fixture
def dolu_harita():
    return _SahteTerimHaritasi({
        "harcama belgesi": ("fatura", "dekont"),
        "iptal": ("geri alma", "fesih"),
    })


class TestSorguGenisleticiBosHarita:
    def test_bos_sorgu_reddedilir(self, bos_harita):
        genisletici = SorguGenisletici(bos_harita)
        with pytest.raises(SorguGenisletmeHatasi):
            genisletici.genislet("")

    def test_sadece_noktalama_reddedilir(self, bos_harita):
        genisletici = SorguGenisletici(bos_harita)
        with pytest.raises(SorguGenisletmeHatasi):
            genisletici.genislet("?!.,")

    def test_sadece_dolgu_kelimeleri_reddedilir(self, bos_harita):
        genisletici = SorguGenisletici(bos_harita)
        with pytest.raises(SorguGenisletmeHatasi):
            genisletici.genislet("nasil nedir ne kadar")

    def test_anlamli_kelime_fts_formatinda_doner(self, bos_harita):
        genisletici = SorguGenisletici(bos_harita)
        sonuc = genisletici.genislet("fatura iptal")
        assert '"' in sonuc.fts_sorgusu
        assert "fatura" in sonuc.fts_sorgusu
        assert "iptal" in sonuc.fts_sorgusu
        assert sonuc.genisletilen_terim_sayisi == 0
        assert sonuc.kullanilan_grup_sayisi == 0

    def test_ozel_karakterler_kacirilir(self, bos_harita):
        genisletici = SorguGenisletici(bos_harita)
        sonuc = genisletici.genislet("fatura-(iptal)")
        assert "(" not in sonuc.fts_sorgusu
        assert ")" not in sonuc.fts_sorgusu
        assert "-" not in sonuc.fts_sorgusu


class TestSorguGenisleticiDoluHarita:
    def test_grup_ici_or_gruplar_arasi_and(self, dolu_harita):
        genisletici = SorguGenisletici(dolu_harita)
        sonuc = genisletici.genislet("fatura iptal")
        assert "OR" in sonuc.fts_sorgusu
        assert "AND" in sonuc.fts_sorgusu
        assert sonuc.genisletilen_terim_sayisi > 0
        assert sonuc.kullanilan_grup_sayisi > 0

    def test_cok_kelimeli_terim_once_eslesir(self, dolu_harita):
        genisletici = SorguGenisletici(dolu_harita)
        sonuc = genisletici.genislet("harcama belgesi")
        assert "harcama belgesi" in sonuc.fts_sorgusu
        assert sonuc.genisletilen_terim_sayisi > 0

    def test_es_anlamli_genisletme_or_grubu_uretir(self, dolu_harita):
        genisletici = SorguGenisletici(dolu_harita)
        sonuc = genisletici.genislet("fatura")
        assert "fatura" in sonuc.fts_sorgusu
        assert "dekont" in sonuc.fts_sorgusu
        assert "OR" in sonuc.fts_sorgusu

    def test_dolgu_kelimeleri_zorunlu_and_yapilmaz(self, dolu_harita):
        genisletici = SorguGenisletici(dolu_harita)
        sonuc = genisletici.genislet("fatura nasil iptal edilir")
        assert "nasil" not in sonuc.fts_sorgusu
        assert "edilir" not in sonuc.fts_sorgusu

    def test_ayni_grup_yinelenince_grup_sayisi_dogru(self, dolu_harita):
        genisletici = SorguGenisletici(dolu_harita)
        sonuc = genisletici.genislet("fatura dekont")
        assert sonuc.kullanilan_grup_sayisi == 1
        assert sonuc.fts_sorgusu.count('"harcama belgesi"') == 1

    def test_kota_asiminda_orijinal_terimler_korunur(self):
        kota_asimli_harita = _SahteTerimHaritasi({
            "ana": tuple(f"es{indeks}" for indeks in range(15)),
        })
        genisletici = SorguGenisletici(kota_asimli_harita)
        sonuc = genisletici.genislet("ana korunacak")
        assert '"ana"' in sonuc.fts_sorgusu
        assert "korunacak" in sonuc.fts_sorgusu
        assert sonuc.genisletilen_terim_sayisi == 0
        assert sonuc.kullanilan_grup_sayisi == 0
