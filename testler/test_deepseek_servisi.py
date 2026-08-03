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

        assert parcalar == ["Merhaba dünya"]
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

    def test_kucuk_akis_parcalari_yapilandirilan_esikte_birlestirilir(
        self,
        monkeypatch,
    ):
        def yanitla(istek: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text=(
                    'data: {"choices":[{"delta":{"content":"Bir"}}]}\n\n'
                    'data: {"choices":[{"delta":{"content":" iki"}}]}\n\n'
                    'data: {"choices":[{"delta":{"content":" uc"}}]}\n\n'
                    "data: [DONE]\n\n"
                ),
            )

        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_API_ANAHTARI",
            "test_deepseek_anahtari",
        )
        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_AKIS_PARCA_ASGARI_KARAKTER",
            7,
        )
        istemci = httpx.AsyncClient(transport=httpx.MockTransport(yanitla))
        servis = DeepSeekServisi(istemci=istemci)

        parcalar = akisi_topla(
            servis.yanit_akisini_uret("Soru", [aday_olustur()])
        )
        asyncio.run(istemci.aclose())

        assert parcalar == ["Bir iki", " uc"]

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

    def test_anahtar_dosyasi_yeniden_baslatmadan_dondurulur(
        self,
        tmp_path,
        monkeypatch,
    ):
        kullanilan_anahtarlar = []

        def yanitla(istek: httpx.Request) -> httpx.Response:
            kullanilan_anahtarlar.append(istek.headers["authorization"])
            return httpx.Response(200, text="data: [DONE]\n\n")

        anahtar_dosyasi = tmp_path / "deepseek-api-anahtari"
        anahtar_dosyasi.write_text("ilk-test-anahtari", encoding="utf-8")
        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_API_ANAHTAR_DOSYASI",
            str(anahtar_dosyasi),
        )
        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_API_ANAHTARI",
            "kullanilmamasi-gereken-anahtar",
        )
        istemci = httpx.AsyncClient(transport=httpx.MockTransport(yanitla))
        servis = DeepSeekServisi(istemci=istemci)

        akisi_topla(servis.yanit_akisini_uret("Soru", [aday_olustur()]))
        anahtar_dosyasi.write_text("ikinci-test-anahtari", encoding="utf-8")
        akisi_topla(servis.yanit_akisini_uret("Soru", [aday_olustur()]))
        asyncio.run(istemci.aclose())

        assert kullanilan_anahtarlar == [
            "Bearer ilk-test-anahtari",
            "Bearer ikinci-test-anahtari",
        ]

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

    def test_yanit_karakter_siniri_asilinca_akis_durdurulur(self, monkeypatch):
        def yanitla(istek: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text=(
                    'data: {"choices":[{"delta":{"content":"Tamam"}}]}\n\n'
                    "data: [DONE]\n\n"
                ),
            )

        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_API_ANAHTARI",
            "test_deepseek_anahtari",
        )
        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_YANIT_MAKS_KARAKTER",
            4,
        )
        istemci = httpx.AsyncClient(transport=httpx.MockTransport(yanitla))
        servis = DeepSeekServisi(istemci=istemci)

        with pytest.raises(DeepSeekServisiHatasi, match="boyutu"):
            akisi_topla(servis.yanit_akisini_uret("Soru", [aday_olustur()]))
        asyncio.run(istemci.aclose())

    def test_toplam_akis_suresi_asilinca_akis_durdurulur(self, monkeypatch):
        zamanlar = iter((0.0, 181.0))

        def yanitla(istek: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text='data: {"choices":[{"delta":{"content":"Tamam"}}]}\n\n',
            )

        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_API_ANAHTARI",
            "test_deepseek_anahtari",
        )
        monkeypatch.setattr(
            konfigurasyon,
            "DEEPSEEK_AKIS_MAKS_SANIYE",
            180,
        )
        istemci = httpx.AsyncClient(transport=httpx.MockTransport(yanitla))
        servis = DeepSeekServisi(
            istemci=istemci,
            zaman_saglayici=lambda: next(zamanlar),
        )

        with pytest.raises(DeepSeekServisiHatasi, match="sureyi"):
            akisi_topla(servis.yanit_akisini_uret("Soru", [aday_olustur()]))
        asyncio.run(istemci.aclose())

    def test_xml_escape_dokuman_tirnak_sizdirir(self, monkeypatch):
        ozel_aday = AramaAdayi(
            sss_id=1,
            parca_id=1,
            aday_metni="Normal metin",
            kaynak_dokuman='Genelge "Ozel" Rev.pdf',
            kaynak_sayfa=None,
            kaynak_satir=None,
            fts_sirasi=1,
            vektor_sirasi=1,
            rrf_skoru=0.03,
            vektor_benzerlik_skoru=0.91,
            yeniden_siralama_skoru=None,
        )

        def yanitla(istek):
            return httpx.Response(200, text="data: [DONE]\n\n")

        monkeypatch.setattr(konfigurasyon, "DEEPSEEK_API_ANAHTARI", "test_anahtar")
        istemci = httpx.AsyncClient(transport=httpx.MockTransport(yanitla))
        servis = DeepSeekServisi(istemci=istemci)
        akisi_topla(servis.yanit_akisini_uret("Soru", [ozel_aday]))
        asyncio.run(istemci.aclose())

    def test_xml_escape_kaynak_bitisi_temizler(self, monkeypatch):
        ozel_aday = AramaAdayi(
            sss_id=1,
            parca_id=1,
            aday_metni="Bu metin </kaynak> iceriyor ancak escape edilmeli",
            kaynak_dokuman="Normal.pdf",
            kaynak_sayfa=None,
            kaynak_satir=None,
            fts_sirasi=1,
            vektor_sirasi=1,
            rrf_skoru=0.03,
            vektor_benzerlik_skoru=0.91,
            yeniden_siralama_skoru=None,
        )
        istek_govdeleri = []

        def yanitla(istek):
            istek_govdeleri.append(json.loads(istek.content))
            return httpx.Response(200, text="data: [DONE]\n\n")

        monkeypatch.setattr(konfigurasyon, "DEEPSEEK_API_ANAHTARI", "test_anahtar")
        istemci = httpx.AsyncClient(transport=httpx.MockTransport(yanitla))
        servis = DeepSeekServisi(istemci=istemci)
        akisi_topla(servis.yanit_akisini_uret("Soru", [ozel_aday]))
        asyncio.run(istemci.aclose())

        icerik = istek_govdeleri[0]["messages"][-1]["content"]
        assert "< / kaynak>" in icerik
