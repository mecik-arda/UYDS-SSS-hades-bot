import asyncio
import json

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.modeller.semalar import AramaAdayi, AramaSonucu
from uygulama.servisler.akis_servisi import AkisServisi
from uygulama.servisler.deepseek_servisi import DeepSeekServisiHatasi
from uygulama.servisler.oturum_hafizasi import OturumHafizasi


def aday_olustur(benzerlik_skoru: float | None) -> AramaAdayi:
    return AramaAdayi(
        sss_id=1,
        parca_id=2,
        aday_metni="Kaynak metni",
        kaynak_dokuman="UYDS Kilavuzu",
        kaynak_sayfa="3",
        kaynak_satir=9,
        fts_sirasi=1,
        vektor_sirasi=1 if benzerlik_skoru is not None else None,
        rrf_skoru=0.03,
        vektor_benzerlik_skoru=benzerlik_skoru,
        yeniden_siralama_skoru=None,
    )


def arama_sonucu_olustur(
    adaylar: tuple[AramaAdayi, ...],
) -> AramaSonucu:
    return AramaSonucu(
        adaylar=adaylar,
        gecen_sure_ms=1.0,
        genisletilmis_fts_sorgusu='"soru"',
        genisletilen_terim_sayisi=0,
        kullanilan_grup_sayisi=0,
        fts_aday_sayisi=len(adaylar),
        vektor_aday_sayisi=len(adaylar),
        birlesik_aday_sayisi=len(adaylar),
        gecersiz_vektor_sayisi=0,
        yeniden_siralama_etkin=False,
    )


class SahteAramaServisi:
    def __init__(self, sonuc: AramaSonucu) -> None:
        self.sonuc = sonuc

    def ara(self, soru: str) -> AramaSonucu:
        return self.sonuc


class SahteDeepSeekServisi:
    def __init__(
        self,
        parcalar: tuple[str, ...] = ("Yanıt",),
        hata: bool = False,
    ) -> None:
        self.parcalar = parcalar
        self.hata = hata
        self.cagrilar = []

    async def yanit_akisini_uret(self, soru, kaynaklar, gecmis):
        self.cagrilar.append((soru, tuple(kaynaklar), tuple(gecmis)))
        if self.hata:
            raise DeepSeekServisiHatasi("Test hatasi")
        for parca in self.parcalar:
            yield parca


def olaylari_topla(servis: AkisServisi, soru: str, oturum_id: str):
    async def topla():
        ham_olaylar = [
            olay
            async for olay in servis.yanit_akisini_uret(soru, oturum_id)
        ]
        mesajlar = await servis._oturum_hafizasi.mesajlari_al(oturum_id)
        return ham_olaylar, mesajlar

    return asyncio.run(topla())


def olayi_ayristir(ham_olay: str) -> tuple[str, dict]:
    satirlar = ham_olay.strip().splitlines()
    olay = satirlar[0].removeprefix("event: ")
    veri = json.loads(satirlar[1].removeprefix("data: "))
    return olay, veri


class TestAkisServisi:
    def test_dusuk_guvende_deepseek_cagrilmaz(self, monkeypatch):
        monkeypatch.setattr(konfigurasyon, "GUVEN_ESIGI", 0.70)
        deepseek = SahteDeepSeekServisi()
        hafiza = OturumHafizasi()
        servis = AkisServisi(
            SahteAramaServisi(
                arama_sonucu_olustur((aday_olustur(0.69),))
            ),
            deepseek,
            hafiza,
        )

        olaylar, mesajlar = olaylari_topla(
            servis,
            "Düşük güvenli soru",
            "oturum-1",
        )

        assert deepseek.cagrilar == []
        assert [olayi_ayristir(olay)[0] for olay in olaylar] == [
            "meta",
            "parca",
            "tamamlandi",
        ]
        assert olayi_ayristir(olaylar[0])[1]["yeterli_guven"] is False
        assert len(mesajlar) == 2

    def test_fts_sonucu_tek_basina_guven_esigini_gecmez(self):
        deepseek = SahteDeepSeekServisi()
        servis = AkisServisi(
            SahteAramaServisi(
                arama_sonucu_olustur((aday_olustur(None),))
            ),
            deepseek,
            OturumHafizasi(),
        )

        olaylar, _ = olaylari_topla(servis, "FTS sorusu", "oturum-1")

        assert deepseek.cagrilar == []
        assert olayi_ayristir(olaylar[0])[1]["guven_skoru"] == 0.0

    def test_yuksek_guvende_akis_ve_oturum_hafizasi_tamamlanir(
        self,
        monkeypatch,
    ):
        monkeypatch.setattr(konfigurasyon, "GUVEN_ESIGI", 0.70)
        deepseek = SahteDeepSeekServisi(("İlk ", "yanıt"))
        hafiza = OturumHafizasi()

        async def gecmis_ekle():
            await hafiza.konusmayi_ekle(
                "oturum-1",
                "Önceki soru",
                "Önceki cevap",
            )

        asyncio.run(gecmis_ekle())
        servis = AkisServisi(
            SahteAramaServisi(
                arama_sonucu_olustur((aday_olustur(0.91),))
            ),
            deepseek,
            hafiza,
        )

        olaylar, mesajlar = olaylari_topla(
            servis,
            "Takip sorusu",
            "oturum-1",
        )

        assert [olayi_ayristir(olay)[0] for olay in olaylar] == [
            "meta",
            "parca",
            "parca",
            "tamamlandi",
        ]
        assert len(deepseek.cagrilar[0][2]) == 2
        assert [mesaj.icerik for mesaj in mesajlar[-2:]] == [
            "Takip sorusu",
            "İlk yanıt",
        ]

    def test_deepseek_hatasi_guvenli_sse_olayi_dondurur(self):
        deepseek = SahteDeepSeekServisi(hata=True)
        servis = AkisServisi(
            SahteAramaServisi(
                arama_sonucu_olustur((aday_olustur(0.95),))
            ),
            deepseek,
            OturumHafizasi(),
        )

        olaylar, mesajlar = olaylari_topla(
            servis,
            "Soru",
            "oturum-1",
        )

        assert [olayi_ayristir(olay)[0] for olay in olaylar] == [
            "meta",
            "hata",
        ]
        assert mesajlar == ()
        assert "Test hatasi" not in olaylar[-1]

    def test_sse_verisi_satir_enjeksiyonuna_karsi_jsonlanir(self):
        deepseek = SahteDeepSeekServisi(("Birinci\nevent: sahte",))
        servis = AkisServisi(
            SahteAramaServisi(
                arama_sonucu_olustur((aday_olustur(0.95),))
            ),
            deepseek,
            OturumHafizasi(),
        )

        olaylar, _ = olaylari_topla(servis, "Soru", "oturum-1")
        parca_olayi = olaylar[1]

        assert parca_olayi.count("\nevent:") == 0
        assert olayi_ayristir(parca_olayi)[1]["metin"] == (
            "Birinci\nevent: sahte"
        )
