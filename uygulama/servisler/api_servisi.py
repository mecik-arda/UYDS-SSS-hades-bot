import json
from datetime import datetime, timezone

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.servisler.pii_maskeleyici import PiiMaskeleyici
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.semalar import GeriBildirimIstegi
from uygulama.servisler.deepseek_servisi import PROMPT_SURUMU
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
        arama: str | None = None,
    ) -> tuple[list[dict], int]:
        ofset = (sayfa - 1) * sayfa_basina
        temiz_arama = arama.strip() if arama else ""
        with baglam_yoneticisi() as baglanti:
            if temiz_arama:
                arama_kalibi = f"%{temiz_arama}%"
                toplam = baglanti.execute(
                    """
                    SELECT COUNT(*)
                    FROM sss_kayitlari
                    WHERE durum = 'aktif'
                      AND (? IS NULL OR kategori = ?)
                      AND (
                          soru LIKE ? ESCAPE '\\'
                          OR kategori LIKE ? ESCAPE '\\'
                          OR COALESCE(modul, '') LIKE ? ESCAPE '\\'
                          OR CAST(id AS TEXT) = ?
                      )
                    """,
                    (
                        kategori,
                        kategori,
                        arama_kalibi,
                        arama_kalibi,
                        arama_kalibi,
                        temiz_arama,
                    ),
                ).fetchone()[0]
                satirlar = baglanti.execute(
                    """
                    SELECT id, kategori, soru, kaynak_dokuman, modul
                    FROM sss_kayitlari
                    WHERE durum = 'aktif'
                      AND (? IS NULL OR kategori = ?)
                      AND (
                          soru LIKE ? ESCAPE '\\'
                          OR kategori LIKE ? ESCAPE '\\'
                          OR COALESCE(modul, '') LIKE ? ESCAPE '\\'
                          OR CAST(id AS TEXT) = ?
                      )
                    ORDER BY id
                    LIMIT ? OFFSET ?
                    """,
                    (
                        kategori,
                        kategori,
                        arama_kalibi,
                        arama_kalibi,
                        arama_kalibi,
                        temiz_arama,
                        sayfa_basina,
                        ofset,
                    ),
                ).fetchall()
            elif kategori:
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

    def isletim_durumunu_al(self) -> dict:
        return {
            "arama": {
                "hibrit_arama": True,
                "vektor_modeli": konfigurasyon.VEKTOR_MODEL_ADI,
                "yeniden_siralama": konfigurasyon.YENIDEN_SIRALAMA_ETKIN,
                "deepseek_modeli": konfigurasyon.DEEPSEEK_MODEL_ADI,
                "deepseek_yapilandirildi": bool(
                    konfigurasyon.DEEPSEEK_API_ANAHTARI.strip()
                    or konfigurasyon.DEEPSEEK_API_ANAHTAR_DOSYASI.strip()
                ),
            },
            "belgeler": {
                "senkronizasyon": konfigurasyon.SENKRONIZASYON_AKTIF,
                "artimsal_dakika": konfigurasyon.ARTIMSAL_SENKRONIZASYON_DAKIKA,
                "desteklenen_formatlar": [
                    deger.strip()
                    for deger in konfigurasyon.BELGE_DESTEK_FORMATLAR.split(",")
                    if deger.strip()
                ],
                "acl": konfigurasyon.BELGE_ACL_AKTIF,
                "surumleme": konfigurasyon.BELGE_SURUMLE_AKTIF,
                "bilgi_grafi": konfigurasyon.GRAF_AKTIF,
            },
            "veri_yonetimi": {
                "excel_ice_aktarma": "bakim_araci",
                "excel_kuru_calistirma": True,
                "surum_geri_alma": "bakim_araci",
                "yedekleme": "docker_ve_bakim_araci",
                "disk_sifreleme": True,
            },
            "otomasyon": {
                "eposta_raporu": konfigurasyon.EPOSTA_RAPORLAMA_AKTIF,
                "veri_temizligi": konfigurasyon.VERI_TEMIZLIK_AKTIF,
                "pii_maskeleme": konfigurasyon.PII_MASKELEME_AKTIF,
                "soru_gizleme": konfigurasyon.KULLANICI_SORULARINI_GIZLE,
                "niyet_siniflandirma": konfigurasyon.NIYET_SINIFLANDIRMA_AKTIF,
            },
        }

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

    def vektor_durumunu_al(self) -> dict:
        with baglam_yoneticisi() as baglanti:
            toplam = baglanti.execute(
                """
                SELECT COUNT(*)
                FROM parca_vektorleri
                WHERE model_surumu = ?
                """,
                (konfigurasyon.VEKTOR_MODEL_ADI,),
            ).fetchone()[0]
            sss_vektor = baglanti.execute(
                """
                SELECT COUNT(*)
                FROM sss_vektorleri
                WHERE model_adi = ?
                """,
                (konfigurasyon.VEKTOR_MODEL_ADI,),
            ).fetchone()[0]
            eksik_belge_vektoru = baglanti.execute(
                """
                SELECT COUNT(*)
                FROM yapisal_parcalar AS parca
                WHERE parca.aktif = 1
                  AND NOT EXISTS (
                      SELECT 1
                      FROM parca_vektorleri AS vektor
                      WHERE vektor.parca_id = parca.id
                        AND vektor.model_surumu = ?
                  )
                """,
                (konfigurasyon.VEKTOR_MODEL_ADI,),
            ).fetchone()[0]
            eksik_sss_vektoru = baglanti.execute(
                """
                SELECT COUNT(*)
                FROM sss_parcalari AS parca
                INNER JOIN sss_kayitlari AS kayit ON kayit.id = parca.sss_id
                WHERE kayit.durum = 'aktif'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM sss_vektorleri AS vektor
                      WHERE vektor.parca_id = parca.id
                        AND vektor.model_adi = ?
                  )
                """,
                (konfigurasyon.VEKTOR_MODEL_ADI,),
            ).fetchone()[0]
            tumu = toplam + sss_vektor
            return {
                "toplam_vektor": tumu,
                "eksik_vektor": eksik_belge_vektoru + eksik_sss_vektoru,
                "model_surumu": konfigurasyon.VEKTOR_MODEL_ADI,
            }

    def belge_dagilimini_al(self) -> dict:
        with baglam_yoneticisi() as baglanti:
            format_satirlari = baglanti.execute(
                """
                SELECT dosya_formati, COUNT(*) AS adet
                FROM belge_kayitlari
                WHERE aktif = 1
                GROUP BY dosya_formati
                """
            ).fetchall()
            formata_gore = {
                satir["dosya_formati"]: satir["adet"]
                for satir in format_satirlari
            }
            yetki_satirlari = baglanti.execute(
                """
                SELECT yetki_seviyesi, COUNT(*) AS adet
                FROM belge_kayitlari
                WHERE aktif = 1
                GROUP BY yetki_seviyesi
                """
            ).fetchall()
            yetkiye_gore = {
                str(satir["yetki_seviyesi"]): satir["adet"]
                for satir in yetki_satirlari
            }
            toplam_belge = baglanti.execute(
                "SELECT COUNT(*) FROM belge_kayitlari WHERE aktif = 1"
            ).fetchone()[0]
        return {
            "formata_gore": formata_gore,
            "yetkiye_gore": yetkiye_gore,
            "toplam_belge": toplam_belge,
        }

    def senkronizasyon_durumunu_al(self) -> dict:
        with baglam_yoneticisi() as baglanti:
            son_senkro = baglanti.execute(
                """
                SELECT islenme_tarihi, islenme_durumu
                FROM belge_kayitlari
                WHERE islenme_tarihi IS NOT NULL
                ORDER BY islenme_tarihi DESC
                LIMIT 1
                """
            ).fetchone()
            bekleyen = baglanti.execute(
                """
                SELECT COUNT(*)
                FROM belge_kayitlari
                WHERE islenme_durumu = 'beklemede' AND aktif = 1
                """
            ).fetchone()[0]
        return {
            "son_senkronizasyon": (
                son_senkro["islenme_tarihi"] if son_senkro else None
            ),
            "aktif": konfigurasyon.SENKRONIZASYON_AKTIF,
            "bekleyen_belge": bekleyen,
        }

    def karantina_belgelerini_al(self) -> dict:
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                """
                SELECT id, dosya_adi, dosya_formati, karantina_nedeni,
                       karantina_tarihi, hata_mesaji
                FROM belge_kayitlari
                WHERE islenme_durumu = 'karantina'
                ORDER BY karantina_tarihi DESC
                LIMIT 100
                """
            ).fetchall()
            karantinalar = [dict(satir) for satir in satirlar]
            toplam = len(karantinalar)
        return {"karantinalar": karantinalar, "toplam": toplam}

    def kavram_bulutunu_al(self) -> dict:
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                """
                SELECT kavram, COUNT(*) AS adet
                FROM belge_kavramlari
                GROUP BY kavram
                ORDER BY adet DESC
                LIMIT 30
                """
            ).fetchall()
            kavramlar = [
                {"etiket": satir["kavram"], "deger": satir["adet"]}
                for satir in satirlar
            ]
        return {"kavramlar": kavramlar}

    def graf_istatistik_al(self) -> dict:
        with baglam_yoneticisi() as baglanti:
            dugum_sayisi = baglanti.execute(
                "SELECT COUNT(*) FROM graf_dugumleri"
            ).fetchone()[0]
            iliski_sayisi = baglanti.execute(
                "SELECT COUNT(*) FROM graf_iliskileri"
            ).fetchone()[0]
        yogunluk = round(
            (2 * iliski_sayisi) / (dugum_sayisi * (dugum_sayisi - 1)), 4
        ) if dugum_sayisi > 1 else 0.0
        return {
            "dugum_sayisi": dugum_sayisi,
            "iliski_sayisi": iliski_sayisi,
            "yogunluk": yogunluk,
        }

    def belge_surumlerini_al(self, dosya_yolu: str | None = None) -> dict:
        with baglam_yoneticisi() as baglanti:
            if dosya_yolu:
                satirlar = baglanti.execute(
                    """
                    SELECT id, dosya_adi, orijinal_yol, surum, aktif,
                           son_degistirilme_tarihi, islenme_durumu,
                           onceki_surum_id
                    FROM belge_kayitlari
                    WHERE orijinal_yol = ?
                    ORDER BY surum DESC
                    """,
                    (dosya_yolu,),
                ).fetchall()
            else:
                satirlar = baglanti.execute(
                    """
                    SELECT id, dosya_adi, orijinal_yol, surum, aktif,
                           son_degistirilme_tarihi, islenme_durumu,
                           onceki_surum_id
                    FROM belge_kayitlari
                    ORDER BY orijinal_yol, surum DESC
                    LIMIT 500
                    """
                ).fetchall()
        return {"surumler": [dict(satir) for satir in satirlar]}

    def parca_istatistiklerini_al(self) -> dict:
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                """
                SELECT parca_turu, COUNT(*) AS adet,
                       ROUND(AVG(token_sayisi), 2) AS ortalama_token
                FROM yapisal_parcalar
                WHERE aktif = 1
                GROUP BY parca_turu
                ORDER BY adet DESC
                """
            ).fetchall()
            toplam = baglanti.execute(
                "SELECT COUNT(*) FROM yapisal_parcalar WHERE aktif = 1"
            ).fetchone()[0]
        return {
            "toplam_parca": toplam,
            "turler": [dict(satir) for satir in satirlar],
        }

    def sorgu_trendini_al(self) -> dict:
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                """
                SELECT DATE(olusturulma_tarihi) AS tarih,
                       COUNT(*) AS toplam,
                       SUM(CASE WHEN cevaplandi_mi = 1 THEN 1 ELSE 0 END) AS cevaplanan
                FROM asistan_sorgulari
                WHERE olusturulma_tarihi >= DATETIME('now', '-30 days')
                GROUP BY DATE(olusturulma_tarihi)
                ORDER BY tarih
                """
            ).fetchall()
        return {"gunler": [dict(satir) for satir in satirlar]}

    def yetim_kavramlari_al(self) -> dict:
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                """
                SELECT dugum.id, dugum.etiket
                FROM graf_dugumleri AS dugum
                WHERE dugum.dugum_turu = 'kavram'
                  AND NOT EXISTS (
                      SELECT 1 FROM graf_iliskileri AS iliski
                      WHERE iliski.hedef_dugum_id = dugum.id
                         OR iliski.kaynak_dugum_id = dugum.id
                  )
                ORDER BY dugum.etiket
                LIMIT 100
                """
            ).fetchall()
        return {"kavramlar": [dict(satir) for satir in satirlar]}

    def belge_analitik_raporunu_al(self) -> dict:
        return {
            "belge_dagilimi": self.belge_dagilimini_al(),
            "vektor_durumu": self.vektor_durumunu_al(),
            "senkronizasyon": self.senkronizasyon_durumunu_al(),
            "karantina": self.karantina_belgelerini_al(),
            "kavram_bulutu": self.kavram_bulutunu_al(),
            "graf": self.graf_istatistik_al(),
            "parcalar": self.parca_istatistiklerini_al(),
            "sorgu_trendi": self.sorgu_trendini_al(),
        }

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
        cevapsiz_listesi = [dict(satir) for satir in cevapsizlar]
        if konfigurasyon.KULLANICI_SORULARINI_GIZLE:
            for cevapsiz_kayit in cevapsiz_listesi:
                cevapsiz_kayit["kullanici_sorusu"] = "[GIZLI]"
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
            "cevapsiz_kalan_sorular": cevapsiz_listesi,
        }

    def cevapsiz_sorgulari_listele(
        self,
        sayfa: int,
        sayfa_basina: int,
    ) -> tuple[list[dict], int]:
        with baglam_yoneticisi() as baglanti:
            toplam = baglanti.execute(
                """
                SELECT COUNT(*)
                FROM asistan_sorgulari
                WHERE cevaplandi_mi = 0
                    OR guven_skoru < ?
                """,
                (konfigurasyon.GUVEN_ESIGI,),
            ).fetchone()[0]
            satirlar = baglanti.execute(
                """
                SELECT
                    id,
                    kullanici_sorusu,
                    guven_skoru,
                    cevaplandi_mi,
                    kullanici_adi,
                    olusturulma_tarihi
                FROM asistan_sorgulari
                WHERE cevaplandi_mi = 0
                    OR guven_skoru < ?
                ORDER BY olusturulma_tarihi DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (
                    konfigurasyon.GUVEN_ESIGI,
                    sayfa_basina,
                    (sayfa - 1) * sayfa_basina,
                ),
            ).fetchall()
        sonuclar = [dict(satir) for satir in satirlar]
        if konfigurasyon.KULLANICI_SORULARINI_GIZLE:
            for kayit in sonuclar:
                kayit["kullanici_sorusu"] = "[GIZLI]"
        return sonuclar, int(toplam)

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
        maskeli_soru = soru
        if konfigurasyon.PII_MASKELEME_AKTIF:
            maskeli_soru = PiiMaskeleyici.tumunu_maskele(soru)
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
                    maskeli_soru,
                    cevap,
                    guven_skoru,
                    int(cevaplandi_mi),
                    kullanici_adi,
                    konfigurasyon.DEEPSEEK_MODEL_ADI,
                    PROMPT_SURUMU,
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
