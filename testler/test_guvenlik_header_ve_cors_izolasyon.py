import pytest
from fastapi.testclient import TestClient
from uygulama.ana import uygulama


@pytest.fixture
def istemci():
    return TestClient(uygulama)


class TestGuvenlikBasliklari:
    BASLIK_BEKLEME_LISTESI = {
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
    }
    CSP_PARCA_BEKLEME_LISTESI = {"default-src", "script-src", "style-src"}

    def _basliklari_kontrol_et(self, yanit, ek_baslik_kontrolleri=None):
        basliklar = {k.lower(): v for k, v in yanit.headers.items()}
        for baslik_adi, beklenen in self.BASLIK_BEKLEME_LISTESI.items():
            assert basliklar.get(baslik_adi) == beklenen, (
                f"{baslik_adi} eksik veya yanlis: {basliklar.get(baslik_adi)}"
            )
        csp = basliklar.get("content-security-policy", "")
        for parca in self.CSP_PARCA_BEKLEME_LISTESI:
            assert parca in csp, f"CSP eksik yonerge: {parca}"
        hsts = basliklar.get("strict-transport-security", "")
        assert "max-age=" in hsts, f"HSTS eksik: {hsts}"
        if ek_baslik_kontrolleri:
            ek_baslik_kontrolleri(basliklar)

    def test_saglik_guvenlik_basliklari(self, istemci):
        yanit = istemci.get("/api/saglik")
        assert yanit.status_code == 200
        self._basliklari_kontrol_et(yanit)

    def test_hazirlik_guvenlik_basliklari(self, istemci):
        yanit = istemci.get("/api/hazirlik")
        self._basliklari_kontrol_et(yanit)

    def test_docs_guvenlik_basliklari(self, istemci):
        yanit = istemci.get("/docs")
        self._basliklari_kontrol_et(yanit)

    def test_openapi_guvenlik_basliklari(self, istemci):
        yanit = istemci.get("/openapi.json")
        self._basliklari_kontrol_et(yanit)

    def test_cors_izinli_origin(self, istemci):
        yanit = istemci.get(
            "/api/saglik",
            headers={"Origin": "http://localhost:8000"},
        )
        assert yanit.status_code == 200
        assert "access-control-allow-origin" in {
            k.lower(): v for k, v in yanit.headers.items()
        }

    def test_cors_yetkisiz_origin(self, istemci):
        yanit = istemci.get(
            "/api/saglik",
            headers={"Origin": "https://kotu-niyetli-site.com"},
        )
        basliklar = {k.lower(): v for k, v in yanit.headers.items()}
        izinli_origin = basliklar.get("access-control-allow-origin", "")
        assert izinli_origin != "https://kotu-niyetli-site.com", (
            "Yetkisiz origin'e izin verildi"
        )

    def test_cors_preflight_izinli_origin(self, istemci):
        yanit = istemci.options(
            "/api/saglik",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert yanit.status_code == 200

    def test_cors_preflight_yetkisiz_origin(self, istemci):
        yanit = istemci.options(
            "/api/saglik",
            headers={
                "Origin": "https://saldiri.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        basliklar = {k.lower(): v for k, v in yanit.headers.items()}
        izinli_origin = basliklar.get("access-control-allow-origin", "")
        assert izinli_origin != "https://saldiri.example.com"