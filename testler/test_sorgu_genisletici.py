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
    def test_kisa_sorgu_or_modu_kullanir(self, dolu_harita):
        genisletici = SorguGenisletici(dolu_harita)
        sonuc = genisletici.genislet("fatura iptal")
        assert "OR" in sonuc.fts_sorgusu
        assert sonuc.kullanilan_grup_sayisi == 2
        assert sonuc.genisletilen_terim_sayisi > 0

    def test_uzun_sorgu_and_modu_kullanir(self, dolu_harita):
        genisletici = SorguGenisletici(dolu_harita)
        sonuc = genisletici.genislet(
            "fatura iptali icin gerekli belgeleri nasil hazirlarim lutfen yardim edin acil"
        )
        assert "AND" in sonuc.fts_sorgusu
        assert sonuc.kullanilan_grup_sayisi >= 1

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

    @pytest.mark.parametrize("soru", ("İZİN", "IZIN"))
    def test_turkce_buyuk_i_es_anlamli_grubuyla_eslesir(self, soru):
        turkce_harita = _SahteTerimHaritasi({
            "izin": ("musaade",),
        })
        genisletici = SorguGenisletici(turkce_harita)
        sonuc = genisletici.genislet(soru)
        assert '"izin"' in sonuc.fts_sorgusu
        assert '"musaade"' in sonuc.fts_sorgusu
        assert sonuc.kullanilan_grup_sayisi == 1

    def test_turkce_tam_eslesme_yedek_eslesmeden_once_kullanilir(self):
        turkce_harita = _SahteTerimHaritasi({
            "izin": ("musaade",),
            "ızın": ("ozel terim",),
        })
        genisletici = SorguGenisletici(turkce_harita)
        sonuc = genisletici.genislet("IZIN")
        assert '"ozel terim"' in sonuc.fts_sorgusu
        assert '"musaade"' not in sonuc.fts_sorgusu

    def test_iki_yuz_bir_karakterlik_sorgu_kabul_edilir(self, bos_harita):
        genisletici = SorguGenisletici(bos_harita)
        soru = "a" * 201
        sonuc = genisletici.genislet(soru)
        assert soru in sonuc.fts_sorgusu

    def test_iki_bin_karakteri_asan_sorgu_reddedilir(self, bos_harita):
        genisletici = SorguGenisletici(bos_harita)
        with pytest.raises(SorguGenisletmeHatasi):
            genisletici.genislet("a" * 2001)
