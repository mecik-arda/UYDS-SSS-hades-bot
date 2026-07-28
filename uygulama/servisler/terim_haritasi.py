import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from uygulama.cekirdek.konfigurasyon import konfigurasyon

AZAMI_TERIM_DOSYASI_BOYUTU = 1024 * 1024


class TerimHaritasiHatasi(ValueError):
    pass


class TerimHaritasi:
    def __init__(
        self,
        dosya_yolu: str | Path | None = None,
    ) -> None:
        self.dosya_yolu = Path(
            dosya_yolu or konfigurasyon.ES_ANLAMLILAR_YOLU
        ).expanduser()
        self._harita: dict[str, tuple[str, ...]] | None = None
        self._ters_harita: dict[str, str] | None = None

    def yukle(self) -> dict[str, tuple[str, ...]]:
        kaynak_yolu = self.dosya_yolu
        if not kaynak_yolu.is_file():
            raise FileNotFoundError(
                f"Yerel es anlamli terim haritasi bulunamadi: {kaynak_yolu}"
            )
        if kaynak_yolu.stat().st_size > AZAMI_TERIM_DOSYASI_BOYUTU:
            raise TerimHaritasiHatasi("Terim haritasi izin verilen boyutu asiyor")
        try:
            ham_harita = json.loads(kaynak_yolu.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as hata:
            raise TerimHaritasiHatasi("Terim haritasi okunamadi") from hata
        harita = self._haritayi_dogrula(ham_harita)
        ters_harita = {}
        for ana_terim, es_anlamlilar in harita.items():
            for terim in (ana_terim, *es_anlamlilar):
                onceki_ana_terim = ters_harita.get(terim)
                if onceki_ana_terim and onceki_ana_terim != ana_terim:
                    raise TerimHaritasiHatasi(
                        f"Terim birden fazla grupta yer aliyor: {terim}"
                    )
                ters_harita[terim] = ana_terim
        self._harita = harita
        self._ters_harita = ters_harita
        return dict(harita)

    def es_anlamlilari_al(self, terim: str) -> tuple[str, ...]:
        if self._harita is None or self._ters_harita is None:
            self.yukle()
        normalize_edilmis_terim = self._terimi_normalize_et(terim)
        ana_terim = self._ters_harita.get(normalize_edilmis_terim)
        if ana_terim is None:
            return ()
        grup = (ana_terim, *self._harita[ana_terim])
        return tuple(deger for deger in grup if deger != normalize_edilmis_terim)

    def _haritayi_dogrula(
        self,
        ham_harita: Any,
    ) -> dict[str, tuple[str, ...]]:
        if not isinstance(ham_harita, dict) or not ham_harita:
            raise TerimHaritasiHatasi("Terim haritasi bos olmayan nesne olmalidir")
        dogrulanmis_harita = {}
        for ham_ana_terim, ham_es_anlamlilar in ham_harita.items():
            if not isinstance(ham_ana_terim, str):
                raise TerimHaritasiHatasi("Ana terimler metin olmalidir")
            if not isinstance(ham_es_anlamlilar, list) or not ham_es_anlamlilar:
                raise TerimHaritasiHatasi(
                    "Her ana terimin en az bir es anlamlisi olmalidir"
                )
            ana_terim = self._terimi_normalize_et(ham_ana_terim)
            es_anlamlilar = []
            for ham_es_anlamli in ham_es_anlamlilar:
                if not isinstance(ham_es_anlamli, str):
                    raise TerimHaritasiHatasi("Es anlamlilar metin olmalidir")
                es_anlamli = self._terimi_normalize_et(ham_es_anlamli)
                if es_anlamli != ana_terim and es_anlamli not in es_anlamlilar:
                    es_anlamlilar.append(es_anlamli)
            if not es_anlamlilar:
                raise TerimHaritasiHatasi(
                    f"Es anlamli grubu bos kaldi: {ana_terim}"
                )
            if ana_terim in dogrulanmis_harita:
                raise TerimHaritasiHatasi(f"Yinelenen ana terim: {ana_terim}")
            dogrulanmis_harita[ana_terim] = tuple(es_anlamlilar)
        return dogrulanmis_harita

    def _terimi_normalize_et(self, terim: str) -> str:
        temiz_terim = re.sub(r"\s+", " ", terim.strip().casefold())
        if not temiz_terim:
            raise TerimHaritasiHatasi("Terim bos olamaz")
        if any(unicodedata.category(karakter).startswith("C") for karakter in temiz_terim):
            raise TerimHaritasiHatasi("Terim kontrol karakteri iceremez")
        if len(temiz_terim) > 200:
            raise TerimHaritasiHatasi("Terim 200 karakteri asamaz")
        return temiz_terim
