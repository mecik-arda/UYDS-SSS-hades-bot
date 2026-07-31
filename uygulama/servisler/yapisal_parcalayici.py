import hashlib
import re
from dataclasses import dataclass

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.servisler.belge_ayiklayici import BelgeIcerik


@dataclass(frozen=True)
class BaslikDugumu:
    seviye: int
    metin: str
    alt_basliklar: list["BaslikDugumu"]


@dataclass(frozen=True)
class TabloBolgesi:
    baslangic_satir: int
    bitis_satir: int
    ham_metin: str


@dataclass(frozen=True)
class YapisalParca:
    metin: str
    parca_turu: str
    baslik_zinciri: list[str]
    kaynak_belge: str
    sayfa_numarasi: int | None
    sira: int
    sha256_ozeti: str
    token_sayisi: int
    yetki_seviyesi: int


class YapisalParcalayici:
    def yapisal_parcala(
        self,
        belge_icerik: BelgeIcerik,
    ) -> list[YapisalParca]:
        parcalar = []
        sira = 0
        aktif_baslik_zinciri = []
        satirlar = belge_icerik.ham_metin.splitlines()
        tablo_bolgeleri = self.tablo_bolgelerini_tespit_et(satirlar)
        tablo_indeksleri = {
            indeks
            for bolge in tablo_bolgeleri
            for indeks in range(
                bolge.baslangic_satir,
                bolge.bitis_satir + 1,
            )
        }
        for bolge in tablo_bolgeleri:
            sira += 1
            parcalar.append(
                YapisalParca(
                    metin=bolge.ham_metin,
                    parca_turu="tablo",
                    baslik_zinciri=list(aktif_baslik_zinciri),
                    kaynak_belge=belge_icerik.kaynak_dosya,
                    sayfa_numarasi=belge_icerik.sayfa_sayisi,
                    sira=sira,
                    sha256_ozeti=hashlib.sha256(
                        bolge.ham_metin.encode("utf-8")
                    ).hexdigest(),
                    token_sayisi=konfigurasyon.PARCALAMA_MAKS_TOKEN,
                    yetki_seviyesi=belge_icerik.yetki_seviyesi,
                )
            )
        madde_imleri_grubu = []
        for indeks, satir in enumerate(satirlar):
            temiz = satir.strip()
            if not temiz or indeks in tablo_indeksleri:
                if madde_imleri_grubu:
                    sira += 1
                    parcalar.append(
                        self._parca_olustur(
                            "\n".join(madde_imleri_grubu),
                            "madde_imleri",
                            aktif_baslik_zinciri,
                            belge_icerik,
                            sira,
                        )
                    )
                    madde_imleri_grubu = []
                continue
            if self._baslik_satiri_mi(temiz):
                if madde_imleri_grubu:
                    sira += 1
                    parcalar.append(
                        self._parca_olustur(
                            "\n".join(madde_imleri_grubu),
                            "madde_imleri",
                            aktif_baslik_zinciri,
                            belge_icerik,
                            sira,
                        )
                    )
                    madde_imleri_grubu = []
                seviye = self._baslik_seviyesini_bul(temiz)
                aktif_baslik_zinciri = (
                    aktif_baslik_zinciri[: seviye - 1]
                    + [temiz]
                )
                sira += 1
                parcalar.append(
                    self._parca_olustur(
                        temiz,
                        "baslik",
                        aktif_baslik_zinciri,
                        belge_icerik,
                        sira,
                    )
                )
                continue
            if re.match(r"^[\-\*••]\s", temiz):
                madde_imleri_grubu.append(
                    temiz.lstrip("-*•" + "•" + " ").strip()
                )
                continue
            sira += 1
            parcalar.append(
                self._parca_olustur(
                    temiz,
                    "paragraf",
                    aktif_baslik_zinciri,
                    belge_icerik,
                    sira,
                )
            )
        return parcalar

    def _parca_olustur(
        self,
        metin: str,
        parca_turu: str,
        baslik_zinciri: list[str],
        belge_icerik: BelgeIcerik,
        sira: int,
    ) -> YapisalParca:
        return YapisalParca(
            metin=metin,
            parca_turu=parca_turu,
            baslik_zinciri=list(baslik_zinciri),
            kaynak_belge=belge_icerik.kaynak_dosya,
            sayfa_numarasi=belge_icerik.sayfa_sayisi,
            sira=sira,
            sha256_ozeti=hashlib.sha256(
                metin.encode("utf-8")
            ).hexdigest(),
            token_sayisi=konfigurasyon.PARCALAMA_MAKS_TOKEN,
            yetki_seviyesi=belge_icerik.yetki_seviyesi,
        )

    def tablo_bolgelerini_tespit_et(
        self,
        satirlar: list[str],
    ) -> list[TabloBolgesi]:
        bolgeler = []
        tablo_icinde = False
        baslangic = 0
        for indeks, satir in enumerate(satirlar):
            temiz = satir.strip()
            if not temiz:
                continue
            tablo_gostergesi = (
                "|" in temiz
                and temiz.count("|") >= 2
                and len(temiz) > 10
            )
            if tablo_gostergesi and not tablo_icinde:
                tablo_icinde = True
                baslangic = indeks
            elif not tablo_gostergesi and tablo_icinde:
                bolgeler.append(
                    TabloBolgesi(
                        baslangic_satir=baslangic,
                        bitis_satir=indeks - 1,
                        ham_metin="\n".join(
                            satirlar[baslangic:indeks]
                        ),
                    )
                )
                tablo_icinde = False
        if tablo_icinde:
            bolgeler.append(
                TabloBolgesi(
                    baslangic_satir=baslangic,
                    bitis_satir=len(satirlar) - 1,
                    ham_metin="\n".join(
                        satirlar[baslangic:]
                    ),
                )
            )
        return bolgeler

    def _baslik_satiri_mi(self, metin: str) -> bool:
        return bool(
            re.match(
                r"^#+\s",
                metin,
            )
            or re.match(
                r"^[\d.]+\s+\w",
                metin,
            )
        )

    def _baslik_seviyesini_bul(self, metin: str) -> int:
        if metin.startswith("#"):
            return len(metin) - len(metin.lstrip("#"))
        return 1

    def parca_ozetini_hesapla(
        self,
        parca: YapisalParca,
    ) -> str:
        return hashlib.sha256(
            parca.metin.encode("utf-8")
        ).hexdigest()