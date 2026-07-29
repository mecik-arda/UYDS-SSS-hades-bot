import json
from datetime import datetime, timezone

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.semalar import GeriBildirimIstegi
from uygulama.servisler.vektor_servisi import VektorServisi


class ApiServisiHatasi(ValueError):
    def __init__(self, mesaj: str) -> None:
        super().__init__(mesaj)


class ApiServisi:
    def sss_kayitlarini_listele(
        self,
        sayfa: int,
        sayfa_basina: int,
        kategori: str | None,
    ) -> tuple[list[dict], int]:
        ofset = (sayfa - 1) * sayfa_basina
        with baglam_yoneticisi() as baglanti:
            if kategori:
                temiz_kategori = kategori.strip()
                toplam = baglanti.execute(
                    """
                    SELECT COUNT(*)
                    FROM sss_kayitlari
                    WHERE durum = 'aktif' AND kategori = ?
                    """,
                    (temiz_kategori,),
                ).fetchone()[0]
                satirlar = baglanti.execute(
                    """
                    SELECT id, kategori, soru, kaynak_dokuman, modul
                    FROM sss_kayitlari
                    WHERE durum = 'aktif' AND kategori = ?
                    ORDER BY id
                    LIMIT ? OFFSET ?
                    """,
                    (temiz_kategori, sayfa_basina, ofset),
                ).fetchall()
            else:
                toplam = baglanti.execute(
                    """
                    SELECT COUNT(*)
                    FROM sss_kayitlari
                    WHERE durum = 'aktif'
                    """
                ).fetchone()[0]
                satirlar = baglanti.execute(
                    """
                    SELECT id, kategori, soru, kaynak_dokuman, modul
                    FROM sss_kayitlari
                    WHERE durum = 'aktif'
                    ORDER BY id
                    LIMIT ? OFFSET ?
                    """,
                    (sayfa_basina, ofset),
                ).fetchall()
        return [dict(satir) for satir in satirlar], toplam

    def geri_bildirim_kaydet(
        self,
        istek: GeriBildirimIstegi,
    ) -> int:
        with baglam_yoneticisi() as baglanti:
            if istek.sss_id is not None:
                kayit = baglanti.execute(
                    """
                    SELECT 1
                    FROM sss_kayitlari
                    WHERE id = ? AND durum = 'aktif'
                    """,
                    (istek.sss_id,),
                ).fetchone()
                if kayit is None:
                    raise ApiServisiHatasi("Aktif SSS kaydi bulunamadi")
            imlec = baglanti.execute(
                """
                INSERT INTO geri_bildirimler (
                    sss_id,
                    kullanici_sorusu,
                    verilen_cevap,
                    puan,
                    yorum
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    istek.sss_id,
                    istek.kullanici_sorusu,
                    istek.verilen_cevap,
                    istek.puan,
                    istek.yorum,
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
                    tarih
                FROM geri_bildirimler
                WHERE durum = 'BEKLEMEDE'
                ORDER BY tarih, id
                LIMIT ? OFFSET ?
                """,
                (sayfa_basina, (sayfa - 1) * sayfa_basina),
            ).fetchall()
        return [dict(satir) for satir in satirlar], toplam

    def geri_bildirim_durumunu_guncelle(
        self,
        geri_bildirim_id: int,
        islem: str,
    ) -> str:
        yeni_durum = "ONAYLANDI" if islem == "ONAYLA" else "REDDEDILDI"
        with baglam_yoneticisi() as baglanti:
            imlec = baglanti.execute(
                """
                UPDATE geri_bildirimler
                SET durum = ?
                WHERE id = ? AND durum = 'BEKLEMEDE'
                """,
                (yeni_durum, geri_bildirim_id),
            )
            if imlec.rowcount != 1:
                raise ApiServisiHatasi(
                    "Bekleyen geri bildirim bulunamadi"
                )
        return yeni_durum

    def analitik_verisini_al(self) -> dict:
        with baglam_yoneticisi() as baglanti:
            toplam_soru = baglanti.execute(
                "SELECT COUNT(*) FROM asistan_sorgulari"
            ).fetchone()[0]
            geri_bildirim_ozeti = baglanti.execute(
                """
                SELECT COUNT(*) AS toplam, COALESCE(AVG(puan), 0) AS ortalama
                FROM geri_bildirimler
                """
            ).fetchone()
            bekleyen = baglanti.execute(
                """
                SELECT COUNT(*)
                FROM geri_bildirimler
                WHERE durum = 'BEKLEMEDE'
                """
            ).fetchone()[0]
            kategoriler = baglanti.execute(
                """
                SELECT kategori, COUNT(*) AS adet
                FROM sss_kayitlari
                WHERE durum = 'aktif'
                GROUP BY kategori
                ORDER BY adet DESC, kategori
                LIMIT 10
                """
            ).fetchall()
            cevapsizlar = baglanti.execute(
                """
                SELECT kullanici_sorusu, guven_skoru, olusturulma_tarihi
                FROM asistan_sorgulari
                WHERE cevaplandi_mi = 0
                ORDER BY olusturulma_tarihi DESC
                LIMIT 20
                """
            ).fetchall()
        return {
            "toplam_soru_sayisi": toplam_soru,
            "toplam_geri_bildirim_sayisi": geri_bildirim_ozeti["toplam"],
            "ortalama_puan": round(
                float(geri_bildirim_ozeti["ortalama"]),
                2,
            ),
            "bekleyen_onay_sayisi": bekleyen,
            "en_cok_sorulan_kategoriler": [
                dict(satir) for satir in kategoriler
            ],
            "cevapsiz_kalan_sorular": [
                dict(satir) for satir in cevapsizlar
            ],
        }

    def gunluk_kota_kullanildi_mi(self, kullanici_adi: str) -> bool:
        bugun = datetime.now(timezone.utc).date().isoformat()
        with baglam_yoneticisi() as baglanti:
            sayi = baglanti.execute(
                """
                SELECT COUNT(*)
                FROM asistan_sorgulari
                WHERE kullanici_adi = ?
                    AND olusturulma_tarihi >= ?
                """,
                (kullanici_adi, bugun),
            ).fetchone()[0]
        return sayi >= konfigurasyon.GUNLUK_MESAJ_KOTASI

    def sorguyu_kaydet(
        self,
        kullanici_adi: str,
        oturum_id: str,
        soru: str,
        cevap: str,
        guven_skoru: float,
        cevaplandi_mi: bool,
        kaynak_sss_idleri: list[int],
    ) -> None:
        with baglam_yoneticisi() as baglanti:
            baglanti.execute(
                """
                INSERT INTO asistan_sorgulari (
                    oturum_id,
                    kullanici_sorusu,
                    cevap_metni,
                    guven_skoru,
                    cevaplandi_mi,
                    kullanici_adi,
                    model_adi,
                    prompt_surumu,
                    kaynak_sss_idleri
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    oturum_id,
                    soru,
                    cevap,
                    guven_skoru,
                    int(cevaplandi_mi),
                    kullanici_adi,
                    konfigurasyon.DEEPSEEK_MODEL_ADI,
                    "faz6-v1",
                    json.dumps(kaynak_sss_idleri, separators=(",", ":")),
                ),
            )

    def fts_ve_vektorleri_yeniden_indeksle(
        self,
        vektor_servisi: VektorServisi,
    ) -> tuple[int, object]:
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
        vektor_sonucu = vektor_servisi.vektorleri_uret(tumunu_yenile=True)
        return fts_sayisi, vektor_sonucu

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
