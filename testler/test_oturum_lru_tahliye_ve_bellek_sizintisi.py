import asyncio
from uygulama.servisler.oturum_hafizasi import OturumHafizasi


class TestOturumLRUTahliye:
    _OTURUM_SINIRI = 500
    _TOPLAM_OTURUM = 1000

    def test_oturum_limit_altinda_tahliye_olmaz(self):
        hafiza = OturumHafizasi(
            ttl_dakika=1440,
            maksimum_oturum=50,
        )

        async def senaryo():
            for sira in range(30):
                await hafiza.mesaj_ekle(
                    f"oturum-{sira:04d}",
                    "user",
                    f"Mesaj {sira}",
                )
            return await hafiza.oturum_sayisini_al()

        oturum_sayisi = asyncio.run(senaryo())
        assert oturum_sayisi == 30

    def test_oturum_siniri_asildiginda_en_eski_oturumlar_tahliye_edilir(self):
        hafiza = OturumHafizasi(
            ttl_dakika=1440,
            maksimum_oturum=self._OTURUM_SINIRI,
        )

        async def senaryo():
            for sira in range(self._TOPLAM_OTURUM):
                await hafiza.mesaj_ekle(
                    f"oturum-{sira:04d}",
                    "user",
                    f"Mesaj {sira}",
                )
            return await hafiza.oturum_sayisini_al()

        oturum_sayisi = asyncio.run(senaryo())
        assert oturum_sayisi == self._OTURUM_SINIRI