import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.servisler.belge_ayiklayici import (
    BelgeAyiklamaHatasi,
    BelgeAyiklayici,
)


@dataclass(frozen=True)
class DosyaBilgisi:
    dosya_yolu: str
    dosya_adi: str
    dosya_formati: str
    son_degistirilme_tarihi: datetime
    sha256_ozeti: str
    dosya_boyutu: int


@dataclass(frozen=True)
class SenkronizasyonPlani:
    yeni_dosyalar: list[DosyaBilgisi] = field(default_factory=list)
    guncellenen_dosyalar: list[DosyaBilgisi] = field(default_factory=list)
    silinen_dosyalar: list[str] = field(default_factory=list)
    karantinaya_alinanlar: list[tuple[DosyaBilgisi, str]] = field(
        default_factory=list
    )

    @property
    def degisiklik_var_mi(self) -> bool:
        return bool(
            self.yeni_dosyalar
            or self.guncellenen_dosyalar
            or self.silinen_dosyalar
        )


@dataclass(frozen=True)
class SenkronizasyonSonucu:
    baslangic_zamani: datetime
    bitis_zamani: datetime
    islenen_belge_sayisi: int = 0
    yeni_parca_sayisi: int = 0
    silinen_parca_sayisi: int = 0
    karantina_sayisi: int = 0
    surumlenen_belge_sayisi: int = 0
    hata_sayisi: int = 0
    hata_mesajlari: list[str] = field(default_factory=list)

    @property
    def sure_saniye(self) -> float:
        return (
            self.bitis_zamani - self.baslangic_zamani
        ).total_seconds()


class SenkronizasyonMotoru:
    def __init__(self) -> None:
        self._belge_ayiklayici = BelgeAyiklayici()

    def dizin_tara(self, dizin_yollari: list[str]) -> list[DosyaBilgisi]:
        dosyalar = []
        for dizin_yolu in dizin_yollari:
            yol = Path(dizin_yolu)
            if not yol.is_dir():
                continue
            tarayici = yol.rglob("*") if konfigurasyon.BELGE_TARAMA_RECURSIVE else yol.glob("*")
            for dosya in tarayici:
                if not dosya.is_file():
                    continue
                uzanti = dosya.suffix.lower()
                if uzanti.lstrip(".") not in konfigurasyon.BELGE_DESTEK_FORMATLAR.split(","):
                    continue
                sha256_ozeti = hashlib.sha256(
                    dosya.read_bytes()
                ).hexdigest()
                dosyalar.append(
                    DosyaBilgisi(
                        dosya_yolu=str(dosya),
                        dosya_adi=dosya.name,
                        dosya_formati=uzanti,
                        son_degistirilme_tarihi=datetime.fromtimestamp(
                            dosya.stat().st_mtime,
                            tz=timezone.utc,
                        ),
                        sha256_ozeti=sha256_ozeti,
                        dosya_boyutu=dosya.stat().st_size,
                    )
                )
        return dosyalar

    def tam_senkronizasyon(self) -> SenkronizasyonSonucu:
        baslangic = datetime.now(timezone.utc)
        dizinler = [
            d.strip()
            for d in konfigurasyon.BELGE_DIZINLERI.split(",")
            if d.strip()
        ]
        taranan = self.dizin_tara(dizinler)
        sonuc = SenkronizasyonSonucu(
            baslangic_zamani=baslangic,
            bitis_zamani=datetime.now(timezone.utc),
            islenen_belge_sayisi=len(taranan),
        )
        for dosya in taranan:
            try:
                self._belge_ayiklayici.belge_ayikla(dosya.dosya_yolu)
            except BelgeAyiklamaHatasi as hata:
                gunlukleyici.warning(
                    "Senkronizasyon: %s karantinaya alindi: %s",
                    dosya.dosya_adi,
                    hata.hata_kodu,
                )
        return sonuc

    async def _zamanlanmis_senkronizasyon_gorevi(self) -> None:
        while True:
            simdi = datetime.now()
            saat, dakika = map(
                int,
                konfigurasyon.SENKRONIZASYON_SAATI.split(":"),
            )
            hedef = simdi.replace(
                hour=saat,
                minute=dakika,
                second=0,
                microsecond=0,
            )
            if simdi >= hedef:
                hedef += __import__("datetime").timedelta(days=1)
            await asyncio.sleep((hedef - simdi).total_seconds())
            self.tam_senkronizasyon()

    def periyodik_senkronizasyon_baslat(self) -> asyncio.Task | None:
        if not konfigurasyon.SENKRONIZASYON_AKTIF:
            return None
        return asyncio.create_task(
            self._zamanlanmis_senkronizasyon_gorevi()
        )