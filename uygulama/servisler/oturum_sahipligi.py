import asyncio
import secrets
from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic
from typing import Callable

from uygulama.cekirdek.konfigurasyon import konfigurasyon


class OturumSahipligiHatasi(PermissionError):
    def __init__(self, mesaj: str) -> None:
        super().__init__(mesaj)


@dataclass
class OturumSahipligiKaydi:
    kullanici_adi: str
    son_erisim_ani: float


class OturumSahipligiServisi:
    def __init__(
        self,
        zaman_saglayici: Callable[[], float] = monotonic,
    ) -> None:
        self._zaman_saglayici = zaman_saglayici
        self._ttl_saniye = konfigurasyon.OTURUM_TTL_DAKIKA * 60
        self._maksimum_oturum = konfigurasyon.OTURUM_MAKS_SAYI
        self._kayitlar: OrderedDict[str, OturumSahipligiKaydi] = OrderedDict()
        self._kilit = asyncio.Lock()

    async def oturum_al_veya_olustur(
        self,
        kullanici_adi: str,
        oturum_id: str | None,
    ) -> str:
        async with self._kilit:
            simdi = self._zaman_saglayici()
            self._suresi_dolanlari_temizle(simdi)
            if oturum_id is None:
                return self._oturum_olustur(kullanici_adi, simdi)
            kayit = self._kayitlar.get(oturum_id)
            if kayit is None or kayit.kullanici_adi != kullanici_adi:
                raise OturumSahipligiHatasi(
                    "Oturum bulunamadi veya kullaniciya ait degil"
                )
            kayit.son_erisim_ani = simdi
            self._kayitlar.move_to_end(oturum_id)
            return oturum_id

    async def kullanicinin_oturumlarini_sil(
        self,
        kullanici_adi: str,
    ) -> tuple[str, ...]:
        async with self._kilit:
            silinecekler = tuple(
                oturum_id
                for oturum_id, kayit in self._kayitlar.items()
                if kayit.kullanici_adi == kullanici_adi
            )
            for oturum_id in silinecekler:
                del self._kayitlar[oturum_id]
            return silinecekler

    def _oturum_olustur(self, kullanici_adi: str, simdi: float) -> str:
        while len(self._kayitlar) >= self._maksimum_oturum:
            self._kayitlar.popitem(last=False)
        oturum_id = secrets.token_urlsafe(48)
        self._kayitlar[oturum_id] = OturumSahipligiKaydi(
            kullanici_adi=kullanici_adi,
            son_erisim_ani=simdi,
        )
        return oturum_id

    def _suresi_dolanlari_temizle(self, simdi: float) -> None:
        silinecekler = [
            oturum_id
            for oturum_id, kayit in self._kayitlar.items()
            if simdi - kayit.son_erisim_ani >= self._ttl_saniye
        ]
        for oturum_id in silinecekler:
            del self._kayitlar[oturum_id]
