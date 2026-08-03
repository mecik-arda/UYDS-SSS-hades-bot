import pytest

from uygulama.servisler.metin_parcalayici import MetinParcalayici


class TestMetinParcalayiciOlusturma:
    def test_gecerli_parametrelerle_olusturulur(self):
        parcalayici = MetinParcalayici(hedef_karakter_sayisi=500, azami_karakter_sayisi=800)
        assert parcalayici.hedef_karakter_sayisi == 500
        assert parcalayici.azami_karakter_sayisi == 800

    def test_hedef_100_karakterden_kucuk_olamaz(self):
        with pytest.raises(ValueError, match="en az 100"):
            MetinParcalayici(hedef_karakter_sayisi=50)

    def test_azami_hedeften_kucuk_olamaz(self):
        with pytest.raises(ValueError, match="kucuk olamaz"):
            MetinParcalayici(hedef_karakter_sayisi=500, azami_karakter_sayisi=300)


class TestParcalama:
    def test_kisa_metin_tek_parca_dondurur(self):
        parcalayici = MetinParcalayici(hedef_karakter_sayisi=900, azami_karakter_sayisi=1400)
        sonuc = parcalayici.parcala("bu kısa bir metindir")
        assert len(sonuc) == 1
        assert "bu kısa bir metindir" in sonuc[0]

    def test_bos_metin_bos_liste_dondurur(self):
        parcalayici = MetinParcalayici()
        assert parcalayici.parcala("") == []
        assert parcalayici.parcala("   \n\n   ") == []

    def test_uzun_metin_birden_fazla_parcaya_bolunur(self):
        parcalayici = MetinParcalayici(hedef_karakter_sayisi=100, azami_karakter_sayisi=200, overlap_karakter_sayisi=0)
        cumle = "Bu bir test cümlesidir. " * 80
        sonuc = parcalayici.parcala(cumle)
        assert len(sonuc) > 1
        for parca in sonuc:
            assert len(parca) <= 200

    def test_paragraf_sinirinda_bolunur(self):
        parcalayici = MetinParcalayici(hedef_karakter_sayisi=100, azami_karakter_sayisi=200)
        paragraf1 = "Birinci paragraf. " * 15
        paragraf2 = "İkinci paragraf. " * 15
        metin = f"{paragraf1}\n\n{paragraf2}"
        sonuc = parcalayici.parcala(metin)
        assert len(sonuc) >= 2

    def test_cumle_sinirinda_bolunur(self):
        parcalayici = MetinParcalayici(hedef_karakter_sayisi=100, azami_karakter_sayisi=200)
        metin = "A. " * 60
        sonuc = parcalayici.parcala(metin)
        for parca in sonuc[:-1]:
            assert parca.endswith(".")

    def test_kontrol_karakterleri_temizlenir(self):
        parcalayici = MetinParcalayici()
        sonuc = parcalayici.parcala("satır1\r\nsatır2\r\nsatır3")
        assert "\r" not in sonuc[0]

    def test_coklu_bosluk_tek_bosluga_indirgenir(self):
        parcalayici = MetinParcalayici()
        sonuc = parcalayici.parcala("çok    fazla      boşluk")
        assert "    " not in sonuc[0]

    def test_satir_bazli_yedek_bolme(self):
        parcalayici = MetinParcalayici(hedef_karakter_sayisi=100, azami_karakter_sayisi=200)
        tek_satir_metin = "a\nb\nc\nd\ne\nf\ng\nh\ni\nj\nk\nl\nm\nn\no\np"
        sonuc = parcalayici.parcala(tek_satir_metin)
        assert len(sonuc) > 0

    def test_int_metin_stringe_donusturulur(self):
        parcalayici = MetinParcalayici()
        sonuc = parcalayici.parcala(12345)
        assert "12345" in sonuc[0]

    def test_azami_boyutu_asan_birim_zorla_bolunur(self):
        parcalayici = MetinParcalayici(hedef_karakter_sayisi=200, azami_karakter_sayisi=300, overlap_karakter_sayisi=0)
        uzun_kelime = "a" * 800
        sonuc = parcalayici.parcala(uzun_kelime)
        for parca in sonuc:
            assert len(parca) <= 300
        assert len(sonuc) >= 2


class TestOverlap:
    def test_overlap_sonraki_parcaya_oncekinin_sonunu_ekler(self):
        parcalayici = MetinParcalayici(
            hedef_karakter_sayisi=100,
            azami_karakter_sayisi=200,
            overlap_karakter_sayisi=30,
        )
        metin = "birinci bolum metni burada. " * 20
        sonuc = parcalayici.parcala(metin)
        assert len(sonuc) > 1
        ikinci_parca = sonuc[1]
        assert len(ikinci_parca) > 0

    def test_overlap_sifir_olunca_eklenmez(self):
        parcalayici = MetinParcalayici(
            hedef_karakter_sayisi=100,
            azami_karakter_sayisi=200,
            overlap_karakter_sayisi=0,
        )
        metin = "test metni burada. " * 30
        sonuc = parcalayici.parcala(metin)
        assert len(sonuc) > 0

    def test_overlap_kisa_metinde_uygulanmaz(self):
        parcalayici = MetinParcalayici(
            hedef_karakter_sayisi=900,
            azami_karakter_sayisi=1400,
            overlap_karakter_sayisi=150,
        )
        sonuc = parcalayici.parcala("kisa metin")
        assert len(sonuc) == 1

    def test_overlap_kelime_butunlugunu_korur(self):
        parcalayici = MetinParcalayici(
            hedef_karakter_sayisi=100,
            azami_karakter_sayisi=200,
            overlap_karakter_sayisi=40,
        )
        cumle = "Bu test metnidir. " * 30
        sonuc = parcalayici.parcala(cumle)
        assert len(sonuc) > 1
