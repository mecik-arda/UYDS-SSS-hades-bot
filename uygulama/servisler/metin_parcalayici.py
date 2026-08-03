import re

from uygulama.cekirdek.konfigurasyon import konfigurasyon


class MetinParcalayici:
    def __init__(
        self,
        hedef_karakter_sayisi: int = 900,
        azami_karakter_sayisi: int = 1400,
        overlap_karakter_sayisi: int | None = None,
    ) -> None:
        if hedef_karakter_sayisi < 100:
            raise ValueError("Hedef parca boyutu en az 100 karakter olmalidir")
        if azami_karakter_sayisi < hedef_karakter_sayisi:
            raise ValueError("Azami parca boyutu hedef boyuttan kucuk olamaz")
        self.hedef_karakter_sayisi = hedef_karakter_sayisi
        self.azami_karakter_sayisi = azami_karakter_sayisi
        if overlap_karakter_sayisi is None:
            overlap_karakter_sayisi = konfigurasyon.PARCA_OVERLAP_KARAKTER
        self.overlap_karakter_sayisi = max(overlap_karakter_sayisi, 0)

    def parcala(self, metin: str) -> list[str]:
        temiz_metin = self._metni_temizle(metin)
        if not temiz_metin:
            return []
        mantiksal_birimler = self._mantiksal_birimleri_olustur(temiz_metin)
        parcalar: list[str] = []
        guncel_parca = ""
        for birim in mantiksal_birimler:
            for uygun_birim in self._uzun_birimi_bol(birim):
                aday = f"{guncel_parca}\n\n{uygun_birim}".strip()
                if guncel_parca and len(aday) > self.hedef_karakter_sayisi:
                    parcalar.append(guncel_parca)
                    guncel_parca = self._overlap_ekle(guncel_parca, uygun_birim)
                else:
                    guncel_parca = aday
        if guncel_parca:
            parcalar.append(guncel_parca)
        return parcalar

    def _overlap_ekle(self, onceki_parca: str, yeni_birim: str) -> str:
        if self.overlap_karakter_sayisi <= 0:
            return yeni_birim
        if len(onceki_parca) <= self.overlap_karakter_sayisi:
            return yeni_birim
        overlap_metni = onceki_parca[-self.overlap_karakter_sayisi :]
        bosluk_konumu = overlap_metni.find(" ")
        if bosluk_konumu > 0:
            overlap_metni = overlap_metni[bosluk_konumu:].lstrip()
        if not overlap_metni:
            return yeni_birim
        return f"{overlap_metni} {yeni_birim}"

    def _metni_temizle(self, metin: str) -> str:
        satirlar = [
            re.sub(r"[ \t]+", " ", satir).strip()
            for satir in str(metin).replace("\r\n", "\n").replace("\r", "\n").split("\n")
        ]
        return "\n".join(satirlar).strip()

    def _mantiksal_birimleri_olustur(self, metin: str) -> list[str]:
        paragraflar = [
            paragraf.strip()
            for paragraf in re.split(r"\n\s*\n+", metin)
            if paragraf.strip()
        ]
        if len(paragraflar) > 1:
            return paragraflar
        satirlar = [satir.strip() for satir in metin.split("\n") if satir.strip()]
        return satirlar or [metin]

    def _uzun_birimi_bol(self, birim: str) -> list[str]:
        if len(birim) <= self.azami_karakter_sayisi:
            return [birim]
        cumleler = [
            cumle.strip()
            for cumle in re.split(r"(?<=[.!?])\s+", birim)
            if cumle.strip()
        ]
        if len(cumleler) == 1:
            return [
                birim[baslangic : baslangic + self.azami_karakter_sayisi].strip()
                for baslangic in range(0, len(birim), self.azami_karakter_sayisi)
            ]
        parcalar: list[str] = []
        guncel = ""
        for cumle in cumleler:
            aday = f"{guncel} {cumle}".strip()
            if guncel and len(aday) > self.azami_karakter_sayisi:
                parcalar.append(guncel)
                guncel = cumle
            else:
                guncel = aday
        if guncel:
            parcalar.append(guncel)
        return parcalar