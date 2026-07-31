

class TestLLMAPIFallback:
    def test_saglik_endpoint_import_edilebilir(self):
        from uygulama.ana import uygulama
        assert uygulama is not None