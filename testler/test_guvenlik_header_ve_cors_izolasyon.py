import pytest
from starlette.testclient import TestClient as StarletteTestClient
from uygulama.cekirdek.guvenlik_basliklari import GuvenlikBasliklariMiddleware
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route


def _test_uygulamasi_olustur():
    async def anasayfa(istek):
        return PlainTextResponse("OK")

    uygulama = Starlette(
        routes=[Route("/api/saglik", anasayfa)],
        middleware=[
            GuvenlikBasliklariMiddleware,
            CORSMiddleware(
                app=None,
                allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
                allow_credentials=True,
                allow_methods=["GET", "POST", "PUT", "DELETE"],
                allow_headers=["Authorization", "Content-Type"],
            ),
        ],
    )
    return uygulama


@pytest.fixture
def istemci():
    uygulama = Starlette(
        routes=[Route("/api/saglik", _anasayfa_goruntuleyici)],
    )
    uygulama.add_middleware(GuvenlikBasliklariMiddleware)
    uygulama.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    return StarletteTestClient(uygulama)


async def _anasayfa_goruntuleyici(istek):
    return PlainTextResponse("OK")


class TestGuvenlikBasliklari:
    BASLIK_BEKLEME_LISTESI = {
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
    }

    def _basliklari_kontrol_et(self, yanit):
        basliklar = {k.lower(): v for k, v in yanit.headers.items()}
        for baslik_adi, beklenen in self.BASLIK_BEKLEME_LISTESI.items():
            assert basliklar.get(baslik_adi) == beklenen, (
                f"{baslik_adi} eksik veya yanlis: {basliklar.get(baslik_adi)}"
            )
        csp = basliklar.get("content-security-policy", "")
        assert "default-src" in csp, "CSP default-src eksik"
        hsts = basliklar.get("strict-transport-security", "")
        assert "max-age=" in hsts, f"HSTS eksik: {hsts}"

    def test_saglik_guvenlik_basliklari(self, istemci):
        yanit = istemci.get("/api/saglik")
        assert yanit.status_code == 200
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
        assert izinli_origin != "https://kotu-niyetli-site.com"