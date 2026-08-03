import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.servisler.belge_ayiklayici import (
    BelgeAyiklamaHatasi,
    BelgeAyiklayici,
)
from uygulama.servisler.bilgi_grafi import BilgiGrafi
from uygulama.servisler.vektor_servisi import VektorServisi
from uygulama.servisler.yapisal_parcalayici import YapisalParcalayici


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
    def __init__(
        self,
        vektor_servisi: VektorServisi | None = None,
    ) -> None:
        self._belge_ayiklayici = BelgeAyiklayici()
        self._yapisal_parcalayici = YapisalParcalayici()
        self._bilgi_grafi = BilgiGrafi()
        self._vektor_servisi = vektor_servisi or VektorServisi()

    def dizin_tara(self, dizin_yollari: list[str]) -> list[DosyaBilgisi]:
        dosyalar = []
        for dizin_yolu in dizin_yollari:
            yol = Path(dizin_yolu)
            if not yol.is_dir():
                continue
            tarayici = (
                yol.rglob("*")
                if konfigurasyon.BELGE_ALT_DIZINLER_DAHIL
                else yol.glob("*")
            )
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

    def degisiklikleri_bul(
        self,
        taranan: list[DosyaBilgisi],
        taranan_dizinler: list[Path] | None = None,
    ) -> SenkronizasyonPlani:
        from uygulama.cekirdek.veritabani import baglam_yoneticisi

        taranan_haritasi = {dosya.dosya_yolu: dosya for dosya in taranan}
        with baglam_yoneticisi() as baglanti:
            mevcut_satirlar = baglanti.execute(
                """
                SELECT orijinal_yol, sha256_ozeti
                FROM belge_kayitlari
                WHERE aktif = 1 AND islenme_durumu = 'tamamlandi'
                """
            ).fetchall()
        mevcut_haritasi = {
            satir["orijinal_yol"]: satir["sha256_ozeti"]
            for satir in mevcut_satirlar
        }
        yeni_dosyalar = []
        guncellenen_dosyalar = []
        for yol, dosya in taranan_haritasi.items():
            mevcut_ozet = mevcut_haritasi.get(yol)
            if mevcut_ozet is None:
                yeni_dosyalar.append(dosya)
            elif mevcut_ozet != dosya.sha256_ozeti:
                guncellenen_dosyalar.append(dosya)
        silinen_dosyalar = []
        if taranan_dizinler:
            for mevcut_yol in set(mevcut_haritasi) - set(taranan_haritasi):
                cozulmus_yol = Path(mevcut_yol).resolve()
                if any(
                    cozulmus_yol.is_relative_to(dizin)
                    for dizin in taranan_dizinler
                ):
                    silinen_dosyalar.append(mevcut_yol)
            silinen_dosyalar.sort()
        return SenkronizasyonPlani(
            yeni_dosyalar=yeni_dosyalar,
            guncellenen_dosyalar=guncellenen_dosyalar,
            silinen_dosyalar=silinen_dosyalar,
        )

    def tam_senkronizasyon(self) -> SenkronizasyonSonucu:
        dizinler = [
            deger.strip()
            for deger in konfigurasyon.BELGE_DIZINLERI.split(",")
            if deger.strip()
        ]
        taranan_dizinler = [
            Path(dizin).resolve()
            for dizin in dizinler
            if Path(dizin).is_dir()
        ]
        taranan = self.dizin_tara(
            [str(dizin) for dizin in taranan_dizinler]
        )
        return self.senkronize_et(
            self.degisiklikleri_bul(taranan, taranan_dizinler)
        )

    def artimsal_senkronizasyon(self) -> SenkronizasyonSonucu:
        return self.tam_senkronizasyon()

    def senkronize_et(
        self,
        plan: SenkronizasyonPlani,
    ) -> SenkronizasyonSonucu:
        baslangic = datetime.now(timezone.utc)
        islenen_belge_sayisi = 0
        yeni_parca_sayisi = 0
        silinen_parca_sayisi = 0
        karantina_sayisi = 0
        surumlenen_belge_sayisi = 0
        hata_mesajlari = []
        for silinen_yol in plan.silinen_dosyalar:
            silinen_parca_sayisi += self._belgeyi_pasiflestir(silinen_yol)
        for dosya in plan.yeni_dosyalar + plan.guncellenen_dosyalar:
            try:
                icerik = self._belge_ayiklayici.belge_ayikla(
                    dosya.dosya_yolu
                )
                parcalar = self._yapisal_parcalayici.yapisal_parcala(icerik)
                if not parcalar:
                    raise BelgeAyiklamaHatasi(
                        "Belgeden aranabilir parca uretilemedi",
                        "METIN_BOS",
                    )
                vektorler = self._vektor_servisi.metinleri_vektore_donustur(
                    [parca.metin for parca in parcalar]
                )
                surumlendi = self._belgeyi_kaydet(
                    dosya,
                    icerik,
                    parcalar,
                    vektorler,
                )
                if surumlendi:
                    surumlenen_belge_sayisi += 1
                islenen_belge_sayisi += 1
                yeni_parca_sayisi += len(parcalar)
            except Exception as hata:
                hata_kodu = (
                    hata.hata_kodu
                    if isinstance(hata, BelgeAyiklamaHatasi)
                    else type(hata).__name__.upper()
                )
                gunlukleyici.warning(
                    "Senkronizasyon: %s karantinaya alindi: %s",
                    dosya.dosya_adi,
                    hata_kodu,
                )
                self._karantinaya_al(dosya, hata_kodu, str(hata))
                karantina_sayisi += 1
                hata_mesajlari.append(
                    f"{dosya.dosya_adi}: {hata_kodu}"
                )
        if len(hata_mesajlari) > konfigurasyon.SENKRONIZASYON_MAKS_HATA:
            gunlukleyici.error(
                "Senkronizasyon hata esigi asildi: %s",
                len(hata_mesajlari),
            )
        return SenkronizasyonSonucu(
            baslangic_zamani=baslangic,
            bitis_zamani=datetime.now(timezone.utc),
            islenen_belge_sayisi=islenen_belge_sayisi,
            yeni_parca_sayisi=yeni_parca_sayisi,
            silinen_parca_sayisi=silinen_parca_sayisi,
            karantina_sayisi=karantina_sayisi,
            surumlenen_belge_sayisi=surumlenen_belge_sayisi,
            hata_sayisi=len(hata_mesajlari),
            hata_mesajlari=hata_mesajlari,
        )

    def _belgeyi_kaydet(
        self,
        dosya,
        icerik,
        parcalar,
        vektorler,
    ) -> bool:
        from uygulama.cekirdek.veritabani import baglam_yoneticisi

        with baglam_yoneticisi() as baglanti:
            mevcut = baglanti.execute(
                """
                SELECT id, surum
                FROM belge_kayitlari
                WHERE orijinal_yol = ? AND aktif = 1
                ORDER BY surum DESC LIMIT 1
                """,
                (dosya.dosya_yolu,),
            ).fetchone()
            yeni_surum = 1
            onceki_surum_id = None
            if mevcut is not None:
                onceki_surum_id = mevcut["id"]
                yeni_surum = mevcut["surum"] + 1
                baglanti.execute(
                    "UPDATE belge_kayitlari SET aktif = 0 WHERE id = ?",
                    (onceki_surum_id,),
                )
                baglanti.execute(
                    "UPDATE yapisal_parcalar SET aktif = 0 WHERE belge_id = ?",
                    (onceki_surum_id,),
                )
            imlec = baglanti.execute(
                """
                INSERT INTO belge_kayitlari (
                    dosya_adi, dosya_formati, orijinal_yol,
                    son_degistirilme_tarihi, sha256_ozeti,
                    dosya_boyutu, sayfa_sayisi, yetki_seviyesi,
                    surum, onceki_surum_id, islenme_durumu,
                    islenme_tarihi, aktif
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'tamamlandi', ?, 1)
                """,
                (
                    dosya.dosya_adi,
                    dosya.dosya_formati,
                    dosya.dosya_yolu,
                    dosya.son_degistirilme_tarihi.isoformat(),
                    icerik.sha256_ozeti,
                    dosya.dosya_boyutu,
                    icerik.sayfa_sayisi,
                    icerik.yetki_seviyesi,
                    yeni_surum,
                    onceki_surum_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            belge_id = int(imlec.lastrowid)
            parca_kimlikleri = []
            for parca in parcalar:
                parca_imleci = baglanti.execute(
                    """
                    INSERT INTO yapisal_parcalar (
                        belge_id, metin, parca_turu,
                        baslik_zinciri_json, sayfa_numarasi,
                        sira, sha256_ozeti, token_sayisi,
                        yetki_seviyesi, aktif
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        belge_id,
                        parca.metin,
                        parca.parca_turu,
                        json.dumps(parca.baslik_zinciri, ensure_ascii=False),
                        parca.sayfa_numarasi,
                        parca.sira,
                        parca.sha256_ozeti,
                        parca.token_sayisi,
                        parca.yetki_seviyesi,
                    ),
                )
                parca_kimlikleri.append(int(parca_imleci.lastrowid))
            baglanti.executemany(
                """
                INSERT INTO parca_vektorleri (
                    parca_id, vektor, model_surumu, vektor_boyutu
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    (
                        parca_id,
                        self._vektor_servisi.vektoru_bloba_donustur(vektor),
                        self._vektor_servisi.model_adi,
                        self._vektor_servisi.vektor_boyutu,
                    )
                    for parca_id, vektor in zip(
                        parca_kimlikleri,
                        vektorler,
                        strict=True,
                    )
                ),
            )
            kavramlar = self._bilgi_grafi.kavram_cikar(icerik.ham_metin)
            baglanti.executemany(
                """
                INSERT OR REPLACE INTO belge_kavramlari (
                    belge_id, kavram, strateji, guven_skoru
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    (belge_id, kavram, "hafif", 1.0)
                    for kavram in kavramlar
                ),
            )
            belge_dugumu = baglanti.execute(
                """
                INSERT INTO graf_dugumleri (
                    etiket, dugum_turu, ozellikler_json
                ) VALUES (?, 'belge', ?)
                """,
                (
                    dosya.dosya_adi,
                    json.dumps(
                        {"belge_id": belge_id, "surum": yeni_surum},
                        ensure_ascii=False,
                    ),
                ),
            ).lastrowid
            for kavram in kavramlar:
                kavram_dugumu = baglanti.execute(
                    """
                    SELECT id FROM graf_dugumleri
                    WHERE etiket = ? AND dugum_turu = 'kavram'
                    LIMIT 1
                    """,
                    (kavram,),
                ).fetchone()
                if kavram_dugumu is None:
                    kavram_dugumu_id = baglanti.execute(
                        """
                        INSERT INTO graf_dugumleri (
                            etiket, dugum_turu, ozellikler_json
                        ) VALUES (?, 'kavram', '{}')
                        """,
                        (kavram,),
                    ).lastrowid
                else:
                    kavram_dugumu_id = kavram_dugumu["id"]
                baglanti.execute(
                    """
                    INSERT INTO graf_iliskileri (
                        kaynak_dugum_id, hedef_dugum_id,
                        iliski_turu, agirlik
                    ) VALUES (?, ?, 'ATIFTA_BULUNUR', 1.0)
                    """,
                    (belge_dugumu, kavram_dugumu_id),
                )
            self._eski_surumleri_temizle(baglanti, dosya.dosya_yolu)
        return onceki_surum_id is not None

    def _eski_surumleri_temizle(self, baglanti, dosya_yolu: str) -> None:
        satirlar = baglanti.execute(
            """
            SELECT id FROM belge_kayitlari
            WHERE orijinal_yol = ?
            ORDER BY surum DESC
            """,
            (dosya_yolu,),
        ).fetchall()
        silinecekler = satirlar[konfigurasyon.BELGE_MAKS_SURUM_SAKLA:]
        baglanti.executemany(
            "DELETE FROM belge_kayitlari WHERE id = ?",
            ((satir["id"],) for satir in silinecekler),
        )

    def _belgeyi_pasiflestir(self, dosya_yolu: str) -> int:
        from uygulama.cekirdek.veritabani import baglam_yoneticisi

        with baglam_yoneticisi() as baglanti:
            belgeler = baglanti.execute(
                "SELECT id FROM belge_kayitlari WHERE orijinal_yol = ? AND aktif = 1",
                (dosya_yolu,),
            ).fetchall()
            belge_kimlikleri = [satir["id"] for satir in belgeler]
            if not belge_kimlikleri:
                return 0
            silinen = 0
            for belge_id in belge_kimlikleri:
                silinen += baglanti.execute(
                    "UPDATE yapisal_parcalar SET aktif = 0 WHERE belge_id = ? AND aktif = 1",
                    (belge_id,),
                ).rowcount
            baglanti.executemany(
                "UPDATE belge_kayitlari SET aktif = 0 WHERE id = ?",
                ((belge_id,) for belge_id in belge_kimlikleri),
            )
        return int(silinen)

    def _karantinaya_al(
        self,
        dosya: DosyaBilgisi,
        hata_kodu: str,
        hata_mesaji: str,
    ) -> None:
        from uygulama.cekirdek.veritabani import baglam_yoneticisi

        with baglam_yoneticisi() as baglanti:
            baglanti.execute(
                """
                INSERT INTO belge_kayitlari (
                    dosya_adi, dosya_formati, orijinal_yol,
                    sha256_ozeti, dosya_boyutu,
                    islenme_durumu, karantina_nedeni,
                    karantina_tarihi, hata_mesaji, aktif
                ) VALUES (?, ?, ?, ?, ?, 'karantina', ?, ?, ?, 0)
                """,
                (
                    dosya.dosya_adi,
                    dosya.dosya_formati,
                    dosya.dosya_yolu,
                    dosya.sha256_ozeti,
                    dosya.dosya_boyutu,
                    hata_kodu,
                    datetime.now(timezone.utc).isoformat(),
                    hata_mesaji[:2000],
                ),
            )

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
                hedef += timedelta(days=1)
            artimsal_hedef = simdi + timedelta(
                minutes=konfigurasyon.ARTIMSAL_SENKRONIZASYON_DAKIKA
            )
            calisma_hedefi = min(hedef, artimsal_hedef)
            await asyncio.sleep((calisma_hedefi - simdi).total_seconds())
            calistirilacak = (
                self.tam_senkronizasyon
                if calisma_hedefi == hedef
                else self.artimsal_senkronizasyon
            )
            await asyncio.wait_for(
                asyncio.to_thread(calistirilacak),
                timeout=konfigurasyon.SENKRONIZASYON_ZAMAN_ASIMI_SANIYE,
            )

    def periyodik_senkronizasyon_baslat(self) -> asyncio.Task | None:
        if not konfigurasyon.SENKRONIZASYON_AKTIF:
            return None
        return asyncio.create_task(
            self._zamanlanmis_senkronizasyon_gorevi()
        )
