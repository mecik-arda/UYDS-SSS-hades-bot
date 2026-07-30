import hashlib

import numpy as np

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.semalar import GeriBildirimIstegi
from uygulama.servisler.vektor_servisi import VektorServisi, VektorUretimSonucu


class GeriBildirimServisiHatasi(ValueError):
    def __init__(self, mesaj: str) -> None:
        super().__init__(mesaj)


class GeriBildirimServisi:
    def __init__(self, vektor_servisi: VektorServisi) -> None:
        self.vektor_servisi = vektor_servisi

    def geri_bildirim_kaydet(
        self,
        istek: GeriBildirimIstegi,
    ) -> int:
        with baglam_yoneticisi() as baglanti:
            if istek.sss_id is not None:
                self._aktif_sss_varligini_dogrula(
                    baglanti,
                    istek.sss_id,
                    "Aktif SSS kaydi bulunamadi",
                )
            if istek.secili_sss_id is not None:
                self._aktif_sss_varligini_dogrula(
                    baglanti,
                    istek.secili_sss_id,
                    "Secili SSS kaydi bulunamadi",
                )
            imlec = baglanti.execute(
                """
                INSERT INTO geri_bildirimler (
                    sss_id,
                    kullanici_sorusu,
                    verilen_cevap,
                    puan,
                    yorum,
                    secili_sss_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    istek.sss_id,
                    istek.kullanici_sorusu,
                    istek.verilen_cevap,
                    istek.puan,
                    istek.yorum,
                    istek.secili_sss_id,
                ),
            )
        return int(imlec.lastrowid)

    def bekleyen_geri_bildirimleri_listele(
        self,
        sayfa: int,
        sayfa_basina: int,
    ) -> tuple[list[dict], int]:
        with baglam_yoneticisi() as baglanti:
            toplam = baglanti.execute(
                """
                SELECT COUNT(*)
                FROM geri_bildirimler
                WHERE durum = 'BEKLEMEDE'
                """
            ).fetchone()[0]
            satirlar = baglanti.execute(
                """
                SELECT
                    id,
                    sss_id,
                    kullanici_sorusu,
                    verilen_cevap,
                    puan,
                    yorum,
                    durum,
                    tarih,
                    secili_sss_id
                FROM geri_bildirimler
                WHERE durum = 'BEKLEMEDE'
                ORDER BY tarih, id
                LIMIT ? OFFSET ?
                """,
                (sayfa_basina, (sayfa - 1) * sayfa_basina),
            ).fetchall()
        return [dict(satir) for satir in satirlar], toplam

    def geri_bildirimi_onayla(
        self,
        geri_bildirim_id: int,
        yonetici_secili_sss_id: int | None = None,
    ) -> dict:
        with baglam_yoneticisi() as baglanti:
            satir = baglanti.execute(
                """
                SELECT
                    id,
                    sss_id,
                    kullanici_sorusu,
                    verilen_cevap,
                    puan,
                    yorum,
                    durum,
                    secili_sss_id
                FROM geri_bildirimler
                WHERE id = ? AND durum = 'BEKLEMEDE'
                """,
                (geri_bildirim_id,),
            ).fetchone()
            if satir is None:
                raise GeriBildirimServisiHatasi(
                    "Bekleyen geri bildirim bulunamadi"
                )
            geri_bildirim = dict(satir)
            hedef_sss_id = (
                yonetici_secili_sss_id
                if yonetici_secili_sss_id is not None
                else geri_bildirim.get("secili_sss_id")
            )
            if hedef_sss_id is not None:
                self._aktif_sss_varligini_dogrula(
                    baglanti,
                    hedef_sss_id,
                    "Onay icin secilen aktif SSS kaydi bulunamadi",
                )
            geri_bildirim["secili_sss_id"] = hedef_sss_id
            baglanti.execute(
                """
                UPDATE geri_bildirimler
                SET durum = 'ONAYLANDI',
                    secili_sss_id = ?
                WHERE id = ? AND durum = 'BEKLEMEDE'
                """,
                (hedef_sss_id, geri_bildirim_id),
            )
            alternatif_soru_id = self._alternatif_soru_ekle(
                baglanti,
                geri_bildirim,
            )
        return {
            "id": geri_bildirim_id,
            "yeni_durum": "ONAYLANDI",
            "alternatif_soru_id": alternatif_soru_id,
        }

    def _aktif_sss_varligini_dogrula(
        self,
        baglanti,
        sss_id: int,
        hata_mesaji: str,
    ) -> None:
        kayit = baglanti.execute(
            """
            SELECT 1
            FROM sss_kayitlari
            WHERE id = ? AND durum = 'aktif'
            """,
            (sss_id,),
        ).fetchone()
        if kayit is None:
            raise GeriBildirimServisiHatasi(hata_mesaji)

    def geri_bildirimi_reddet(
        self,
        geri_bildirim_id: int,
    ) -> str:
        with baglam_yoneticisi() as baglanti:
            imlec = baglanti.execute(
                """
                UPDATE geri_bildirimler
                SET durum = 'REDDEDILDI'
                WHERE id = ? AND durum = 'BEKLEMEDE'
                """,
                (geri_bildirim_id,),
            )
            if imlec.rowcount != 1:
                raise GeriBildirimServisiHatasi(
                    "Bekleyen geri bildirim bulunamadi"
                )
        return "REDDEDILDI"

    def _alternatif_soru_ekle(
        self,
        baglanti,
        geri_bildirim: dict,
    ) -> int | None:
        if geri_bildirim.get("secili_sss_id") is None:
            return None
        soru = geri_bildirim["kullanici_sorusu"]
        sss_id = geri_bildirim["secili_sss_id"]
        vektor = self.vektor_servisi.metni_vektore_donustur(soru)
        vektor_blobu = self.vektor_servisi.vektoru_bloba_donustur(vektor)
        metin_ozeti = hashlib.sha256(soru.encode("utf-8")).hexdigest()
        mevcut = baglanti.execute(
            """
            SELECT id
            FROM alternatif_sorular
            WHERE sss_id = ? AND soru = ?
            ORDER BY id
            LIMIT 1
            """,
            (sss_id, soru),
        ).fetchone()
        if mevcut is not None:
            alternatif_soru_id = int(mevcut["id"])
            baglanti.execute(
                """
                UPDATE alternatif_sorular
                SET vektor_verisi = ?,
                    model_adi = ?,
                    vektor_boyutu = ?,
                    metin_ozeti = ?,
                    kaynak = ?,
                    durum = 'onaylandi'
                WHERE id = ?
                """,
                (
                    vektor_blobu,
                    self.vektor_servisi.model_adi,
                    self.vektor_servisi.vektor_boyutu,
                    metin_ozeti,
                    "kullanici_geri_bildirimi",
                    alternatif_soru_id,
                ),
            )
            return alternatif_soru_id
        imlec = baglanti.execute(
            """
            INSERT INTO alternatif_sorular (
                sss_id,
                soru,
                vektor_verisi,
                model_adi,
                vektor_boyutu,
                metin_ozeti,
                kaynak,
                durum
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'onaylandi')
            """,
            (
                sss_id,
                soru,
                vektor_blobu,
                self.vektor_servisi.model_adi,
                self.vektor_servisi.vektor_boyutu,
                metin_ozeti,
                "kullanici_geri_bildirimi",
            ),
        )
        return int(imlec.lastrowid)

    def alternatif_sorulari_ara(
        self,
        sorgu_vektoru: np.ndarray,
        aday_sayisi: int,
    ) -> list[dict]:
        if aday_sayisi <= 0:
            return []
        sorgu_array = np.asarray(sorgu_vektoru, dtype=np.float32)
        if sorgu_array.shape != (self.vektor_servisi.vektor_boyutu,):
            raise ValueError("Sorgu vektor boyutu gecersiz")
        if not np.isfinite(sorgu_array).all():
            raise ValueError("Sorgu vektoru sonlu olmayan deger iceriyor")
        sorgu_norm = float(np.linalg.norm(sorgu_array))
        if sorgu_norm <= 0:
            return []
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                """
                SELECT a.id, a.sss_id, a.soru, a.vektor_verisi,
                       a.vektor_boyutu, a.metin_ozeti,
                       s.kaynak_dokuman
                FROM alternatif_sorular a
                JOIN sss_kayitlari s ON s.id = a.sss_id
                WHERE a.durum = 'onaylandi'
                    AND a.vektor_verisi IS NOT NULL
                    AND a.model_adi = ?
                    AND a.vektor_boyutu = ?
                    AND s.durum = 'aktif'
                """,
                (
                    self.vektor_servisi.model_adi,
                    self.vektor_servisi.vektor_boyutu,
                ),
            ).fetchall()
        if not satirlar:
            return []
        skorlu_sonuclar = []
        for satir in satirlar:
            beklenen_ozet = hashlib.sha256(
                satir["soru"].encode("utf-8")
            ).hexdigest()
            if satir["metin_ozeti"] != beklenen_ozet:
                gunlukleyici.warning(
                    "Alternatif soru vektor ozeti gecersiz: alternatif_soru_id=%s",
                    satir["id"],
                )
                continue
            try:
                aday_vektor = self.vektor_servisi.blobu_vektore_donustur(
                    satir["vektor_verisi"]
                )
            except (ValueError, TypeError, IndexError):
                gunlukleyici.warning(
                    "Alternatif soru vektoru gecersiz: alternatif_soru_id=%s",
                    satir["id"],
                )
                continue
            if not np.isfinite(aday_vektor).all():
                continue
            aday_norm = float(np.linalg.norm(aday_vektor))
            if abs(aday_norm - 1.0) > 0.01:
                continue
            benzerlik = (
                float(np.dot(sorgu_array, aday_vektor))
                / (sorgu_norm * aday_norm)
                if sorgu_norm > 0 and aday_norm > 0
                else 0.0
            )
            skorlu_sonuclar.append(
                {
                    "alternatif_soru_id": satir["id"],
                    "sss_id": satir["sss_id"],
                    "soru": satir["soru"],
                    "kaynak_dokuman": satir["kaynak_dokuman"],
                    "benzerlik_skoru": benzerlik,
                }
            )
        skorlu_sonuclar.sort(key=lambda x: x["benzerlik_skoru"], reverse=True)
        return skorlu_sonuclar[:aday_sayisi]

    def fts_ve_vektorleri_yeniden_indeksle(
        self,
    ) -> tuple[int, VektorUretimSonucu]:
        with baglam_yoneticisi() as baglanti:
            baglanti.execute("DELETE FROM sss_fts")
            baglanti.execute(
                """
                INSERT INTO sss_fts (
                    rowid,
                    soru,
                    cevap,
                    kategori,
                    harici_kod,
                    modul,
                    arama_metni
                )
                SELECT
                    id,
                    soru,
                    cevap,
                    kategori,
                    harici_kod,
                    modul,
                    arama_metni
                FROM sss_kayitlari
                WHERE durum = 'aktif'
                """
            )
            fts_sayisi = baglanti.execute(
                "SELECT COUNT(*) FROM sss_fts"
            ).fetchone()[0]
        vektor_sonucu = self.vektor_servisi.vektorleri_uret(tumunu_yenile=True)
        guncellenen_alternatifler = self._alternatif_soru_vektorlerini_yenile()
        gunlukleyici.info(
            "Yeniden indeksleme tamamlandi: fts=%d, vektor=%d, alternatif=%d",
            fts_sayisi,
            vektor_sonucu.uretilen_vektor_sayisi,
            guncellenen_alternatifler,
        )
        return fts_sayisi, vektor_sonucu

    def _alternatif_soru_vektorlerini_yenile(self) -> int:
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                """
                SELECT id, soru
                FROM alternatif_sorular
                WHERE durum = 'onaylandi'
                """
            ).fetchall()
            guncellenen = 0
            for satir in satirlar:
                vektor = self.vektor_servisi.metni_vektore_donustur(
                    satir["soru"]
                )
                vektor_blobu = self.vektor_servisi.vektoru_bloba_donustur(
                    vektor
                )
                metin_ozeti = hashlib.sha256(
                    satir["soru"].encode("utf-8")
                ).hexdigest()
                baglanti.execute(
                    """
                    UPDATE alternatif_sorular
                    SET vektor_verisi = ?,
                        model_adi = ?,
                        vektor_boyutu = ?,
                        metin_ozeti = ?
                    WHERE id = ?
                    """,
                    (
                        vektor_blobu,
                        self.vektor_servisi.model_adi,
                        self.vektor_servisi.vektor_boyutu,
                        metin_ozeti,
                        satir["id"],
                    ),
                )
                guncellenen += 1
        return guncellenen

    def sistem_gunlugu_kaydet(
        self,
        kullanici_adi: str,
        islem_turu: str,
        detay: str,
    ) -> None:
        with baglam_yoneticisi() as baglanti:
            baglanti.execute(
                """
                INSERT INTO sistem_gunlukleri (
                    kullanici_id,
                    islem_turu,
                    detay
                )
                SELECT id, ?, ?
                FROM kullanicilar
                WHERE kullanici_adi = ?
                """,
                (islem_turu, detay, kullanici_adi),
            )
