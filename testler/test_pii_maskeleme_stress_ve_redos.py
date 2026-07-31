import time
from uygulama.servisler.pii_maskeleyici import PiiMaskeleyici


class TestPiiMaskelemePerformans:
    def test_50k_karakter_maskeleme_suresi_10ms_altinda(self):
        buyuk_metin = "Bu bir test mesajidir. " * 2500
        baslangic = time.monotonic()
        PiiMaskeleyici.tumunu_maskele(buyuk_metin)
        gecen_ms = (time.monotonic() - baslangic) * 1000
        assert gecen_ms < 10, f"Maskeleme suresi {gecen_ms:.2f}ms, 10ms altinda olmali"


class TestPiiMaskelemeEdgeCaseler:
    def test_sifirla_baslayan_11_hane_tc_maskelenmez(self):
        sonuc = PiiMaskeleyici.tc_kimlik_maskele("TC:01234567890")
        assert sonuc == "TC:01234567890"

    def test_eksik_haneli_iban_maskelenmez(self):
        sonuc = PiiMaskeleyici.iban_maskele("TR12345")
        assert sonuc == "TR12345"

    def test_tldsiz_eposta_maskelenmez(self):
        sonuc = PiiMaskeleyici.eposta_maskele("user@domain")
        assert sonuc == "user@domain"

    def test_gecerli_tc_kimlik_maskelenir(self):
        sonuc = PiiMaskeleyici.tc_kimlik_maskele("TC:12345678901")
        assert sonuc == "TC:***********"

    def test_gecerli_iban_sondan_4_hane_korunur(self):
        sonuc = PiiMaskeleyici.iban_maskele("TR330006100519786457841326")
        assert sonuc.endswith("1326")

    def test_gecerli_telefon_maskelenir(self):
        sonuc = PiiMaskeleyici.telefon_maskele("Ara:05551234567")
        assert sonuc == "Ara:05*********"

    def test_gecerli_kredi_karti_sondan_4_hane_korunur(self):
        sonuc = PiiMaskeleyici.kredi_karti_maskele("Kart:4532015112830366")
        assert sonuc.endswith("0366")