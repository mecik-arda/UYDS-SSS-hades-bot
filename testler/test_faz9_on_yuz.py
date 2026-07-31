from fastapi.testclient import TestClient

from uygulama.ana import uygulama


istemci = TestClient(uygulama)


def test_faz9_sayfalari_guvenli_sablonlarla_sunulur():
    beklentiler = {
        "/": ("Akıllı Destek Asistanı", 'data-sayfa="sohbet"'),
        "/yonetici": ("Yönetici Merkezi", 'data-sayfa="yonetici"'),
        "/analitik": ("Analitik Görünümü", 'data-sayfa="analitik"'),
    }
    for yol, metinler in beklentiler.items():
        yanit = istemci.get(yol)
        assert yanit.status_code == 200
        assert yanit.headers["content-type"].startswith("text/html")
        assert all(metin in yanit.text for metin in metinler)
        assert '/statik/js/uygulama.js" defer' in yanit.text
        assert '/statik/css/stil.css"' in yanit.text
        assert "<script>" not in yanit.text


def test_faz9_statik_dosyalari_sunulur():
    stil = istemci.get("/statik/css/stil.css")
    betik = istemci.get("/statik/js/uygulama.js")
    assert stil.status_code == 200
    assert stil.headers["content-type"].startswith("text/css")
    assert "--arkaplan" in stil.text
    assert betik.status_code == 200
    assert "text/javascript" in betik.headers["content-type"]
    assert "sseBloklariniAyristir" in betik.text
    assert 'Durum.rol === "YONETICI"' in betik.text
    assert ".innerHTML" in betik.text
    assert ".outerHTML" not in betik.text


def test_faz9_csp_ve_guvenlik_basliklari_sayfalarda_etkin():
    yanit = istemci.get("/")
    assert yanit.headers["x-frame-options"] == "DENY"
    assert yanit.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'self'" in yanit.headers["content-security-policy"]
    assert "script-src 'self'" in yanit.headers["content-security-policy"]
