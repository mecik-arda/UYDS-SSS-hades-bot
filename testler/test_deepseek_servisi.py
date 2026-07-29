import asyncio
import json

import httpx
import pytest

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.modeller.semalar import AramaAdayi
from uygulama.servisler.deepseek_servisi import (
    DeepSeekServisi,
    DeepSeekServisiHatasi,
    DeepSeekYapilandirmaHatasi,
)
from uygulama.servisler.oturum_hafizasi import OturumMesaji


def aday_olustur() -> AramaAdayi:
    return AramaAdayi(
        sss_id=7,
        parca_id=11,
        aday_metni="Resmi kaynak metni",
        kaynak_dokuman="Kilavuz",
        kaynak_sayfa="4",
        kaynak_satir=20,
        fts_sirasi=1,
        vektor_sirasi=1,
        rrf_skoru=0.03,
        vektor_benzerlik_skoru=0.91,
        yeniden_siralama_skoru=None,
    )


def akisi_topla(akis):
    async def topla():
        return [parca async for parca in akis]

    return asyncio.run(topla())


class TestDeepSeekServisi:
    def test_akis_parcalari_ve_kaynakli_istek_dogru_olusturulur(
        self,
        monkeypatch,
    ):
        istekler = []

        def yanitla(istek: httpx.Request) -> httpx.Response:
            istekler.append(istek)
            govde = (
                'data: {"choices":[{"delta":{"content":"Merhaba"}}]}\n\n'
                ': keep-alive\n\n'
                'data: {"choices":[{"delta":{"content":" dünya"}}]}\n\n'
                'data: [DONE]\n\n'
            )
            return httpx.Response(
                200,
                text=govde,
                headers={"Content-Type": "text/event-stream"},
            )

        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_API_ANAHTARI",
            "test_deepseek_anahtari",
        )
        istemci = httpx.AsyncClient(transport=httpx.MockTransport(yanitla))
        servis = DeepSeekServisi(istemci=istemci)

        parcalar = akisi_topla(
            servis.yanit_akisini_uret(
                "Nasıl yapılır?",
                [aday_olustur()],
                [OturumMesaji(rol="user", icerik="Önceki soru")],
            )
        )
        asyncio.run(istemci.aclose())

        assert parcalar == ["Merhaba", " dünya"]
        assert istekler[0].headers["authorization"] == (
            "Bearer test_deepseek_anahtari"
        )
        govde = json.loads(istekler[0].content)
        assert govde["model"] == "deepseek-v4-pro"
        assert govde["stream"] is True
        assert govde["thinking"] == {"type": "disabled"}
        assert govde["messages"][1]["content"] == "Önceki soru"
        assert "Resmi kaynak metni" in govde["messages"][-1]["content"]

    def test_gecici_hata_sonrasinda_yeniden_dener(self, monkeypatch):
        istek_sayisi = 0
        beklemeler = []

        def yanitla(istek: httpx.Request) -> httpx.Response:
            nonlocal istek_sayisi
            istek_sayisi += 1
            if istek_sayisi == 1:
                return httpx.Response(503)
            return httpx.Response(
                200,
                text=(
                    'data: {"choices":[{"delta":{"content":"Tamam"}}]}\n\n'
                    "data: [DONE]\n\n"
                ),
            )

        async def bekle(saniye: float) -> None:
            beklemeler.append(saniye)

        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_API_ANAHTARI",
            "test_deepseek_anahtari",
        )
        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_YENIDEN_DENEME_SAYISI",
            1,
        )
        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_YENIDEN_DENEME_TABAN_SANIYE",
            0.25,
        )
        istemci = httpx.AsyncClient(transport=httpx.MockTransport(yanitla))
        servis = DeepSeekServisi(istemci=istemci, bekleme_islevi=bekle)

        parcalar = akisi_topla(
            servis.yanit_akisini_uret("Soru", [aday_olustur()])
        )
        asyncio.run(istemci.aclose())

        assert parcalar == ["Tamam"]
        assert istek_sayisi == 2
        assert beklemeler == [0.25]

    def test_istemci_hatasi_yeniden_denenmez(self, monkeypatch):
        istek_sayisi = 0

        def yanitla(istek: httpx.Request) -> httpx.Response:
            nonlocal istek_sayisi
            istek_sayisi += 1
            return httpx.Response(400)

        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_API_ANAHTARI",
            "test_deepseek_anahtari",
        )
        istemci = httpx.AsyncClient(transport=httpx.MockTransport(yanitla))
        servis = DeepSeekServisi(istemci=istemci)

        with pytest.raises(DeepSeekServisiHatasi):
            akisi_topla(servis.yanit_akisini_uret("Soru", [aday_olustur()]))
        asyncio.run(istemci.aclose())

        assert istek_sayisi == 1

    def test_yapilandirilmamis_api_anahtari_reddedilir(self, monkeypatch):
        monkeypatch.setattr(konfigurasyon, "DEEPSEEK_API_ANAHTARI", "")
        servis = DeepSeekServisi()

        with pytest.raises(DeepSeekYapilandirmaHatasi):
            akisi_topla(servis.yanit_akisini_uret("Soru", [aday_olustur()]))

    def test_bozuk_akis_verisi_reddedilir(self, monkeypatch):
        def yanitla(istek: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="data: {bozuk}\n\n")

        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_API_ANAHTARI",
            "test_deepseek_anahtari",
        )
        istemci = httpx.AsyncClient(transport=httpx.MockTransport(yanitla))
        servis = DeepSeekServisi(istemci=istemci)

        with pytest.raises(DeepSeekServisiHatasi):
            akisi_topla(servis.yanit_akisini_uret("Soru", [aday_olustur()]))
        asyncio.run(istemci.aclose())
