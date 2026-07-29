import asyncio
import re
from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic
from typing import Callable, Literal

from uygulama.cekirdek.konfigurasyon import konfigurasyon

_OTURUM_KIMLIGI_KALIBI = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


@dataclass(frozen=True)
class OturumMesaji:
    rol: Literal["user", "assistant"]
    icerik: str


@dataclass
class _OturumKaydi:
    mesajlar: list[OturumMesaji]
    son_erisim_ani: float


class OturumHafizasiHatasi(ValueError):
    def __init__(self, mesaj: str) -> None:
        super().__init__(mesaj)


class OturumHafizasi:
    def __init__(
        self,
        ttl_dakika: int | None = None,
        maksimum_mesaj: int | None = None,
        maksimum_oturum: int | None = None,
        zaman_saglayici: Callable[[], float] = monotonic,
    ) -> None:
        self._ttl_saniye = float(
            (
                ttl_dakika
                if ttl_dakika is not None
                else konfigurasyon.OTURUM_TTL_DAKIKA
            )
            * 60
        )
        self._maksimum_mesaj = (
            maksimum_mesaj
            if maksimum_mesaj is not None
            else konfigurasyon.OTURUM_MAKS_MESAJ
        )
        self._maksimum_oturum = (
            maksimum_oturum
            if maksimum_oturum is not None
            else konfigurasyon.OTURUM_MAKS_SAYI
        )
        self._maksimum_karakter = max(
            konfigurasyon.MESAJ_MAKS_KARAKTER,
            konfigurasyon.DEEPSEEK_MAKS_TOKEN * 8,
        )
        if self._ttl_saniye <= 0:
            raise OturumHafizasiHatasi("Oturum TTL degeri pozitif olmalidir")
        if self._maksimum_mesaj <= 0 or self._maksimum_oturum <= 0:
            raise OturumHafizasiHatasi("Oturum sinirlari pozitif olmalidir")
        self._zaman_saglayici = zaman_saglayici
        self._oturumlar: OrderedDict[str, _OturumKaydi] = OrderedDict()
        self._kilit = asyncio.Lock()

    async def mesajlari_al(self, oturum_id: str) -> tuple[OturumMesaji, ...]:
        self._oturum_id_dogrula(oturum_id)
        async with self._kilit:
            simdi = self._zaman_saglayici()
            self._suresi_dolanlari_temizle(simdi)
            kayit = self._oturumlar.get(oturum_id)
            if kayit is None:
                return ()
            kayit.son_erisim_ani = simdi
            self._oturumlar.move_to_end(oturum_id)
            return tuple(kayit.mesajlar)

    async def mesaj_ekle(
        self,
        oturum_id: str,
        rol: Literal["user", "assistant"],
        icerik: str,
    ) -> None:
        self._oturum_id_dogrula(oturum_id)
        temiz_icerik = self._mesaji_dogrula(rol, icerik)
        async with self._kilit:
            simdi = self._zaman_saglayici()
            self._suresi_dolanlari_temizle(simdi)
            self._mesaji_kaydet(oturum_id, rol, temiz_icerik, simdi)

    async def konusmayi_ekle(
        self,
        oturum_id: str,
        kullanici_mesaji: str,
        asistan_mesaji: str,
    ) -> None:
        self._oturum_id_dogrula(oturum_id)
        temiz_kullanici_mesaji = self._mesaji_dogrula(
            "user",
            kullanici_mesaji,
        )
        temiz_asistan_mesaji = self._mesaji_dogrula(
            "assistant",
            asistan_mesaji,
        )
        async with self._kilit:
            simdi = self._zaman_saglayici()
            self._suresi_dolanlari_temizle(simdi)
            self._mesaji_kaydet(
                oturum_id,
                "user",
                temiz_kullanici_mesaji,
                simdi,
            )
            self._mesaji_kaydet(
                oturum_id,
                "assistant",
                temiz_asistan_mesaji,
                simdi,
            )

    async def oturumu_sil(self, oturum_id: str) -> bool:
        self._oturum_id_dogrula(oturum_id)
        async with self._kilit:
            return self._oturumlar.pop(oturum_id, None) is not None

    async def oturum_sayisini_al(self) -> int:
        async with self._kilit:
            self._suresi_dolanlari_temizle(self._zaman_saglayici())
            return len(self._oturumlar)

    def _oturum_id_dogrula(self, oturum_id: str) -> None:
        if not _OTURUM_KIMLIGI_KALIBI.fullmatch(oturum_id):
            raise OturumHafizasiHatasi("Gecersiz oturum kimligi")

    def _mesaji_dogrula(
        self,
        rol: Literal["user", "assistant"],
        icerik: str,
    ) -> str:
        temiz_icerik = icerik.strip()
        if rol not in {"user", "assistant"}:
            raise OturumHafizasiHatasi("Gecersiz oturum mesaji rolu")
        if not temiz_icerik:
            raise OturumHafizasiHatasi("Bos oturum mesaji saklanamaz")
        if len(temiz_icerik) > self._maksimum_karakter:
            raise OturumHafizasiHatasi("Oturum mesaji karakter sinirini asiyor")
        return temiz_icerik

    def _mesaji_kaydet(
        self,
        oturum_id: str,
        rol: Literal["user", "assistant"],
        icerik: str,
        simdi: float,
    ) -> None:
        kayit = self._oturumlar.get(oturum_id)
        if kayit is None:
            self._kapasite_ac()
            kayit = _OturumKaydi(mesajlar=[], son_erisim_ani=simdi)
            self._oturumlar[oturum_id] = kayit
        kayit.mesajlar.append(OturumMesaji(rol=rol, icerik=icerik))
        if len(kayit.mesajlar) > self._maksimum_mesaj:
            kayit.mesajlar = kayit.mesajlar[-self._maksimum_mesaj :]
        kayit.son_erisim_ani = simdi
        self._oturumlar.move_to_end(oturum_id)

    def _suresi_dolanlari_temizle(self, simdi: float) -> None:
        silinecekler = [
            oturum_id
            for oturum_id, kayit in self._oturumlar.items()
            if simdi - kayit.son_erisim_ani >= self._ttl_saniye
        ]
        for oturum_id in silinecekler:
            del self._oturumlar[oturum_id]

    def _kapasite_ac(self) -> None:
        while len(self._oturumlar) >= self._maksimum_oturum:
            self._oturumlar.popitem(last=False)
