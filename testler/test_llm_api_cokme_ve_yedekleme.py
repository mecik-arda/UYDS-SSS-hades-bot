

class TestLLMApiYedekleme:
    def test_saglik_uc_noktasi_ice_aktarilabilir(self):
        from uygulama.ana import uygulama
        assert uygulama is not None
