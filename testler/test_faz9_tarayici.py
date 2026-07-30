import os

import pytest
from playwright.sync_api import expect, sync_playwright


pytestmark = pytest.mark.skipif(
    os.getenv("CANLI_ON_YUZ_TESTI") != "1",
    reason="Canli on yuz sunucusu etkin degil",
)


def test_yonetici_girisi_ve_paneller_gercek_tarayıcıda_calisir():
    konsol_hatalari = []
    with sync_playwright() as playwright:
        tarayici = playwright.chromium.launch(headless=True)
        sayfa = tarayici.new_page()
        sayfa.on(
            "console",
            lambda mesaj: (
                konsol_hatalari.append(mesaj.text)
                if mesaj.type == "error"
                else None
            ),
        )
        sayfa.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded")
        expect(sayfa).to_have_title("Akıllı Destek Asistanı | HadesBot")
        expect(sayfa.locator("#giris-penceresi")).to_be_visible()
        sayfa.locator('input[name="kullanici_adi"]').fill("yonetici")
        sayfa.locator('input[name="sifre"]').fill(
            os.environ["CANLI_YONETICI_SIFRESI"]
        )
        sayfa.locator("#giris-dugmesi").click()
        expect(sayfa.locator("#giris-penceresi")).not_to_be_visible()
        expect(sayfa.locator("#profil-rolu")).to_have_text("Yönetici")
        expect(sayfa.locator('a[href="/yonetici"]')).to_be_visible()
        sayfa.goto(
            "http://127.0.0.1:8000/yonetici",
            wait_until="domcontentloaded",
        )
        expect(sayfa.locator("h1")).to_have_text("Yönetici Merkezi")
        expect(sayfa.locator("#bekleyen-metrigi")).to_have_text("0")
        sayfa.goto(
            "http://127.0.0.1:8000/analitik",
            wait_until="domcontentloaded",
        )
        expect(sayfa.locator("h1")).to_have_text("Analitik Görünümü")
        expect(sayfa.locator("#toplam-soru")).to_have_text("0")
        assert konsol_hatalari == []
        tarayici.close()
