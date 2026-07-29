import asyncio

import pytest

from uygulama.servisler.oturum_hafizasi import (
    OturumHafizasi,
    OturumHafizasiHatasi,
)


def calistir(beklenebilir):
    return asyncio.run(beklenebilir)


class DegisebilirSaat:
    def __init__(self) -> None:
        self.deger = 0.0

    def __call__(self) -> float:
        return self.deger


class TestOturumHafizasi:
    def test_mesajlar_sirayla_saklanir(self):
        hafiza = OturumHafizasi(ttl_dakika=5, maksimum_mesaj=4)

        async def senaryo():
            await hafiza.konusmayi_ekle("oturum-1", "Soru", "Cevap")
            return await hafiza.mesajlari_al("oturum-1")

        mesajlar = calistir(senaryo())

        assert [mesaj.rol for mesaj in mesajlar] == ["user", "assistant"]
        assert [mesaj.icerik for mesaj in mesajlar] == ["Soru", "Cevap"]

    def test_mesaj_siniri_en_yeni_kayitlari_korur(self):
        hafiza = OturumHafizasi(ttl_dakika=5, maksimum_mesaj=3)

        async def senaryo():
            for sira in range(5):
                await hafiza.mesaj_ekle(
                    "oturum-1",
                    "user",
                    f"Mesaj {sira}",
                )
            return await hafiza.mesajlari_al("oturum-1")

        mesajlar = calistir(senaryo())

        assert [mesaj.icerik for mesaj in mesajlar] == [
            "Mesaj 2",
            "Mesaj 3",
            "Mesaj 4",
        ]

    def test_ttl_sonunda_oturum_silinir(self):
        saat = DegisebilirSaat()
        hafiza = OturumHafizasi(
            ttl_dakika=1,
            zaman_saglayici=saat,
        )

        async def senaryo():
            await hafiza.mesaj_ekle("oturum-1", "user", "Soru")
            saat.deger = 60.0
            return await hafiza.mesajlari_al("oturum-1")

        assert calistir(senaryo()) == ()

    def test_oturum_kapasitesi_en_eski_oturumu_cikarir(self):
        hafiza = OturumHafizasi(
            ttl_dakika=5,
            maksimum_oturum=2,
        )

        async def senaryo():
            await hafiza.mesaj_ekle("oturum-1", "user", "Bir")
            await hafiza.mesaj_ekle("oturum-2", "user", "İki")
            await hafiza.mesaj_ekle("oturum-3", "user", "Üç")
            return (
                await hafiza.mesajlari_al("oturum-1"),
                await hafiza.oturum_sayisini_al(),
            )

        ilk_oturum, oturum_sayisi = calistir(senaryo())

        assert ilk_oturum == ()
        assert oturum_sayisi == 2

    @pytest.mark.parametrize(
        "oturum_id",
        ["", "../oturum", "a" * 129, "boşluk içerir"],
    )
    def test_gecersiz_oturum_kimligi_reddedilir(self, oturum_id):
        hafiza = OturumHafizasi()

        with pytest.raises(OturumHafizasiHatasi):
            calistir(hafiza.mesajlari_al(oturum_id))

    def test_bos_mesaj_reddedilir(self):
        hafiza = OturumHafizasi()

        with pytest.raises(OturumHafizasiHatasi):
            calistir(hafiza.mesaj_ekle("oturum-1", "user", "   "))

    def test_paralel_konusmalar_mesaj_ciftlerini_bozmaz(self):
        hafiza = OturumHafizasi(maksimum_mesaj=10)

        async def senaryo():
            await asyncio.gather(
                hafiza.konusmayi_ekle("oturum-1", "Soru A", "Cevap A"),
                hafiza.konusmayi_ekle("oturum-1", "Soru B", "Cevap B"),
            )
            return await hafiza.mesajlari_al("oturum-1")

        mesajlar = calistir(senaryo())
        icerikler = [mesaj.icerik for mesaj in mesajlar]

        assert icerikler in [
            ["Soru A", "Cevap A", "Soru B", "Cevap B"],
            ["Soru B", "Cevap B", "Soru A", "Cevap A"],
        ]
