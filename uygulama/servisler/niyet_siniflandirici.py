import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.gunlukleyici import gunlukleyici


@dataclass(frozen=True)
class NiyetEslesmesi:
    niyet_adi: str
    buton_metni: str
    hedef_url: str
    guven_skoru: float
    buton_tipi: str = "birincil"


@dataclass(frozen=True)
class NiyetSonucu:
    eslesmeler: tuple[NiyetEslesmesi, ...] = field(default_factory=tuple)

    @property
    def eslesme_var_mi(self) -> bool:
        return len(self.eslesmeler) > 0


class NiyetSiniflandirici:
    def __init__(self, eylemler_yolu: str | None = None) -> None:
        self._eylemler_yolu = eylemler_yolu or konfigurasyon.NIYET_EYLEMLERI_YOLU
        self._eylemler: list[dict] = []
        self._yukle()

    def _yukle(self) -> None:
        yol = Path(self._eylemler_yolu)
        if not yol.is_file():
            gunlukleyici.warning(
                "Niyet eylemleri dosyasi bulunamadi: %s", self._eylemler_yolu
            )
            return
        try:
            with yol.open(encoding="utf-8") as dosya:
                veri = json.load(dosya)
            if isinstance(veri, dict) and isinstance(veri.get("eylemler"), list):
                self._eylemler = veri["eylemler"]
            else:
                gunlukleyici.warning("Niyet eylemleri dosyasi gecersiz format")
        except (json.JSONDecodeError, OSError) as hata:
            gunlukleyici.warning("Niyet eylemleri yuklenemedi: %s", type(hata).__name__)

    def siniflandir(self, soru: str) -> NiyetSonucu:
        if not konfigurasyon.NIYET_SINIFLANDIRMA_AKTIF or not self._eylemler:
            return NiyetSonucu()
        temiz_soru = soru.strip().lower()
        eslesmeler = []
        for eylem in self._eylemler:
            guven_skoru = self._eylem_skorunu_hesapla(temiz_soru, eylem)
            if guven_skoru >= konfigurasyon.NIYET_GUVEN_ESIGI:
                eslesmeler.append(
                    NiyetEslesmesi(
                        niyet_adi=eylem.get("niyet_adi", ""),
                        buton_metni=eylem.get("buton_metni", ""),
                        hedef_url=eylem.get("hedef_url", ""),
                        guven_skoru=round(guven_skoru, 4),
                        buton_tipi=eylem.get("buton_tipi", "birincil"),
                    )
                )
        eslesmeler.sort(key=lambda e: -e.guven_skoru)
        return NiyetSonucu(eslesmeler=tuple(eslesmeler[:3]))

    def _eylem_skorunu_hesapla(self, temiz_soru: str, eylem: dict) -> float:
        anahtar_kelimeler = eylem.get("anahtar_kelimeler", [])
        if not anahtar_kelimeler:
            return 0.0
        eslesen = 0
        for kelime in anahtar_kelimeler:
            if kelime.lower() in temiz_soru:
                eslesen += 1
        kelime_skoru = eslesen / len(anahtar_kelimeler) if anahtar_kelimeler else 0.0
        kaliplar = eylem.get("kaliplar", [])
        kalip_skoru = 0.0
        if kaliplar:
            eslesen_kalip = 0
            for kalip in kaliplar:
                try:
                    if re.search(kalip, temiz_soru, re.IGNORECASE):
                        eslesen_kalip += 1
                except re.error:
                    gunlukleyici.warning("Gecersiz regex kalibi: %s", kalip)
                    continue
            kalip_skoru = eslesen_kalip / len(kaliplar)
        return round(kelime_skoru * 0.6 + kalip_skoru * 0.4, 4)