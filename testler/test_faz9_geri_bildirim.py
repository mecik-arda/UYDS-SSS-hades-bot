from fastapi.testclient import TestClient

from uygulama.ana import uygulama


istemci = TestClient(uygulama)


def test_faz9_js_geri_bildirim_fonksiyonlari_mevcut():
    betik = istemci.get("/statik/js/uygulama.js")
    assert betik.status_code == 200
    assert "text/javascript" in betik.headers["content-type"]
    assert "geriBildirimCubugunuGoster" in betik.text
    assert "yildizlariOlustur" in betik.text


def test_faz9_js_geri_bildirim_api_yolu_mevcut():
    betik = istemci.get("/statik/js/uygulama.js")
    assert betik.status_code == 200
    assert "/api/v1/geri-bildirim" in betik.text


def test_faz9_geri_bildirim_metni_duzgun():
    betik = istemci.get("/statik/js/uygulama.js")
    assert betik.status_code == 200
    assert "Bu cevap faydali oldu mu?" in betik.text
    assert "Evet" in betik.text
    assert "Hayir" in betik.text
    assert "Gonder" in betik.text