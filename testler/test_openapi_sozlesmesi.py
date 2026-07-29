from uygulama.ana import uygulama


def test_faz7_openapi_rota_sozlesmesi_sabit():
    sema = uygulama.openapi()
    beklenen_islemler = {
        "/api/saglik": {"get"},
        "/api/hazirlik": {"get"},
        "/api/v1/kimlik-dogrulama/giris": {"post"},
        "/api/v1/kimlik-dogrulama/yenile": {"post"},
        "/api/v1/kimlik-dogrulama/cikis": {"post"},
        "/api/v1/arama": {"post"},
        "/api/v1/sss": {"get"},
        "/api/v1/geri-bildirim": {"post"},
        "/api/v1/yonetici/geri-bildirimler": {"get"},
        "/api/v1/yonetici/geri-bildirim/onay": {"post"},
        "/api/v1/yonetici/yeniden-indeksle": {"post"},
        "/api/v1/analitik": {"get"},
    }

    for yol, yontemler in beklenen_islemler.items():
        assert yol in sema["paths"]
        assert yontemler.issubset(sema["paths"][yol])

    islem_kimlikleri = [
        islem["operationId"]
        for yol in sema["paths"].values()
        for yontem, islem in yol.items()
        if yontem in {"get", "post", "put", "patch", "delete"}
    ]
    assert len(islem_kimlikleri) == len(set(islem_kimlikleri))
    assert "OAuth2PasswordBearer" in sema["components"]["securitySchemes"]


def test_kritik_yonetici_rotalari_hmac_basliklarini_zorunlu_tutar():
    sema = uygulama.openapi()
    for yol in (
        "/api/v1/yonetici/geri-bildirim/onay",
        "/api/v1/yonetici/yeniden-indeksle",
    ):
        parametreler = sema["paths"][yol]["post"]["parameters"]
        zorunlu_basliklar = {
            parametre["name"]
            for parametre in parametreler
            if parametre["in"] == "header" and parametre["required"]
        }
        assert {
            "X-UYDS-Zaman",
            "X-UYDS-Nonce",
            "X-UYDS-Imza",
        }.issubset(zorunlu_basliklar)
