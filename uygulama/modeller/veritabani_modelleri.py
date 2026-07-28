from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.veritabani import baglam_yoneticisi

SSS_KAYITLARI_TABLOSU = """
CREATE TABLE IF NOT EXISTS sss_kayitlari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategori TEXT NOT NULL,
    soru TEXT NOT NULL,
    cevap TEXT NOT NULL,
    kaynak_dokuman TEXT,
    surum_numarasi INTEGER DEFAULT 1,
    aktif_mi BOOLEAN DEFAULT TRUE,
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    harici_kod TEXT,
    modul TEXT,
    kullanici_rolu TEXT,
    arama_metni TEXT,
    durum TEXT NOT NULL DEFAULT 'aktif',
    icerik_surumu INTEGER NOT NULL DEFAULT 1
)
"""

SSS_PARCALARI_TABLOSU = """
CREATE TABLE IF NOT EXISTS sss_parcalari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sss_id INTEGER NOT NULL,
    parca_metni TEXT NOT NULL,
    parca_sira_no INTEGER NOT NULL,
    FOREIGN KEY (sss_id) REFERENCES sss_kayitlari(id) ON DELETE CASCADE,
    UNIQUE (sss_id, parca_sira_no)
)
"""

SSS_FTS_TABLOSU = """
CREATE VIRTUAL TABLE IF NOT EXISTS sss_fts USING fts5(
    soru,
    cevap,
    kategori,
    harici_kod,
    modul,
    arama_metni
)
"""

SSS_VEKTORLERI_TABLOSU = """
CREATE TABLE IF NOT EXISTS sss_vektorleri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sss_id INTEGER NOT NULL,
    parca_id INTEGER,
    vektor_verisi BLOB NOT NULL,
    model_adi TEXT NOT NULL,
    FOREIGN KEY (sss_id) REFERENCES sss_kayitlari(id) ON DELETE CASCADE,
    FOREIGN KEY (parca_id) REFERENCES sss_parcalari(id) ON DELETE CASCADE
)
"""

GERI_BILDIRIMLER_TABLOSU = """
CREATE TABLE IF NOT EXISTS geri_bildirimler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sss_id INTEGER,
    kullanici_sorusu TEXT NOT NULL,
    verilen_cevap TEXT NOT NULL,
    puan INTEGER NOT NULL,
    yorum TEXT,
    durum TEXT DEFAULT 'BEKLEMEDE',
    tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sss_id) REFERENCES sss_kayitlari(id) ON DELETE SET NULL
)
"""

KULLANICILAR_TABLOSU = """
CREATE TABLE IF NOT EXISTS kullanicilar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_adi TEXT UNIQUE NOT NULL,
    sifre_hash TEXT NOT NULL,
    rol TEXT NOT NULL DEFAULT 'KULLANICI',
    aktif_mi BOOLEAN DEFAULT TRUE
)
"""

VERI_SURUMLERI_TABLOSU = """
CREATE TABLE IF NOT EXISTS veri_surumleri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dosya_adi TEXT NOT NULL,
    surum_numarasi INTEGER NOT NULL,
    aktarilan_kayit_sayisi INTEGER NOT NULL,
    aktarim_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    dosya_ozeti TEXT,
    onceki_surum_numarasi INTEGER,
    durum TEXT NOT NULL DEFAULT 'aktif'
)
"""

ALTERNATIF_SORULAR_TABLOSU = """
CREATE TABLE IF NOT EXISTS alternatif_sorular (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sss_id INTEGER NOT NULL,
    soru TEXT NOT NULL,
    vektor_verisi BLOB,
    kaynak TEXT NOT NULL,
    durum TEXT NOT NULL DEFAULT 'beklemede',
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sss_id) REFERENCES sss_kayitlari(id) ON DELETE CASCADE
)
"""

ASISTAN_SORGULARI_TABLOSU = """
CREATE TABLE IF NOT EXISTS asistan_sorgulari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    oturum_id TEXT,
    kullanici_sorusu TEXT NOT NULL,
    yeniden_yazilmis_soru TEXT,
    cevap_metni TEXT,
    guven_skoru REAL,
    cevaplandi_mi INTEGER NOT NULL DEFAULT 0,
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

SISTEM_GUNLUKLERI_TABLOSU = """
CREATE TABLE IF NOT EXISTS sistem_gunlukleri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_id INTEGER,
    islem_turu TEXT NOT NULL,
    detay TEXT,
    tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id) ON DELETE SET NULL
)
"""

GIRIS_DENEMELERI_TABLOSU = """
CREATE TABLE IF NOT EXISTS giris_deneme_kayitlari (
    kimlik_ozeti TEXT PRIMARY KEY,
    basarisiz_deneme_sayisi INTEGER NOT NULL DEFAULT 0,
    kilitlenme_tarihi TEXT,
    son_deneme_tarihi TEXT NOT NULL
)
"""

SISTEM_MIGRASYONLARI_TABLOSU = """
CREATE TABLE IF NOT EXISTS sistem_migrasyonlari (
    migrasyon_adi TEXT PRIMARY KEY,
    uygulanma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

FTS_INSERT_TETIKLEYICI = """
CREATE TRIGGER sss_fts_ekleme_tetik
AFTER INSERT ON sss_kayitlari
WHEN NEW.durum = 'aktif'
BEGIN
    INSERT INTO sss_fts(rowid, soru, cevap, kategori, harici_kod, modul, arama_metni)
    VALUES (
        NEW.id,
        NEW.soru,
        NEW.cevap,
        NEW.kategori,
        NEW.harici_kod,
        NEW.modul,
        NEW.arama_metni
    );
END
"""

FTS_SILME_TETIKLEYICI = """
CREATE TRIGGER sss_fts_silme_tetik
AFTER DELETE ON sss_kayitlari
BEGIN
    DELETE FROM sss_fts WHERE rowid = OLD.id;
END
"""

FTS_GUNCELLEME_TETIKLEYICI = """
CREATE TRIGGER sss_fts_guncelleme_tetik
AFTER UPDATE ON sss_kayitlari
BEGIN
    DELETE FROM sss_fts WHERE rowid = OLD.id;
    INSERT INTO sss_fts(rowid, soru, cevap, kategori, harici_kod, modul, arama_metni)
    SELECT
        NEW.id,
        NEW.soru,
        NEW.cevap,
        NEW.kategori,
        NEW.harici_kod,
        NEW.modul,
        NEW.arama_metni
    WHERE NEW.durum = 'aktif';
END
"""

FTS_YENIDEN_DOLDURMA_SORGUSU = """
INSERT INTO sss_fts(rowid, soru, cevap, kategori, harici_kod, modul, arama_metni)
SELECT id, soru, cevap, kategori, harici_kod, modul, arama_metni
FROM sss_kayitlari
WHERE durum = 'aktif'
"""

TABLO_SORGULARI = [
    SSS_KAYITLARI_TABLOSU,
    SSS_PARCALARI_TABLOSU,
    SSS_VEKTORLERI_TABLOSU,
    GERI_BILDIRIMLER_TABLOSU,
    KULLANICILAR_TABLOSU,
    VERI_SURUMLERI_TABLOSU,
    ALTERNATIF_SORULAR_TABLOSU,
    ASISTAN_SORGULARI_TABLOSU,
    SISTEM_GUNLUKLERI_TABLOSU,
    GIRIS_DENEMELERI_TABLOSU,
    SISTEM_MIGRASYONLARI_TABLOSU,
]

SSS_KAYITLARI_EK_KOLONLARI = {
    "harici_kod": "TEXT",
    "modul": "TEXT",
    "kullanici_rolu": "TEXT",
    "arama_metni": "TEXT",
    "durum": "TEXT NOT NULL DEFAULT 'aktif'",
    "icerik_surumu": "INTEGER NOT NULL DEFAULT 1",
}

VERI_SURUMLERI_EK_KOLONLARI = {
    "dosya_ozeti": "TEXT",
    "onceki_surum_numarasi": "INTEGER",
    "durum": "TEXT NOT NULL DEFAULT 'aktif'",
}

TETIKLEYICI_SORGULARI = [
    FTS_INSERT_TETIKLEYICI,
    FTS_SILME_TETIKLEYICI,
    FTS_GUNCELLEME_TETIKLEYICI,
]

TETIKLEYICI_SILME_SORGULARI = [
    "DROP TRIGGER IF EXISTS sss_fts_ekleme_tetik",
    "DROP TRIGGER IF EXISTS sss_fts_silme_tetik",
    "DROP TRIGGER IF EXISTS sss_fts_guncelleme_tetik",
]

VARSAYILAN_YONETICI_SORGUSU = """
INSERT OR IGNORE INTO kullanicilar (kullanici_adi, sifre_hash, rol, aktif_mi)
VALUES ('yonetici', ?, 'YONETICI', TRUE)
"""


def _eksik_kolonlari_ekle(
    baglanti,
    tablo_adi: str,
    kolon_tanimlari: dict[str, str],
) -> None:
    mevcut_kolonlar = {
        satir["name"]
        for satir in baglanti.execute(f"PRAGMA table_info({tablo_adi})").fetchall()
    }
    for kolon_adi, kolon_tanimi in kolon_tanimlari.items():
        if kolon_adi not in mevcut_kolonlar:
            baglanti.execute(
                f"ALTER TABLE {tablo_adi} ADD COLUMN {kolon_adi} {kolon_tanimi}"
            )


def _fts_tablosunu_hazirla(baglanti) -> None:
    beklenen_kolonlar = {
        "soru",
        "cevap",
        "kategori",
        "harici_kod",
        "modul",
        "arama_metni",
    }
    mevcut_kolonlar = {
        satir["name"]
        for satir in baglanti.execute("PRAGMA table_info(sss_fts)").fetchall()
    }
    fts_yeniden_olusturulmali = mevcut_kolonlar != beklenen_kolonlar
    for sorgu in TETIKLEYICI_SILME_SORGULARI:
        baglanti.execute(sorgu)
    if fts_yeniden_olusturulmali:
        baglanti.execute("DROP TABLE IF EXISTS sss_fts")
    baglanti.execute(SSS_FTS_TABLOSU)
    for sorgu in TETIKLEYICI_SORGULARI:
        baglanti.execute(sorgu)
    if fts_yeniden_olusturulmali:
        baglanti.execute(FTS_YENIDEN_DOLDURMA_SORGUSU)


def _arama_metnini_bir_kez_geriye_doldur(baglanti) -> None:
    migrasyon_adi = "faz3_arama_metni_geriye_doldurma_v1"
    migrasyon_var_mi = baglanti.execute(
        """
        SELECT 1
        FROM sistem_migrasyonlari
        WHERE migrasyon_adi = ?
        """,
        (migrasyon_adi,),
    ).fetchone()
    if migrasyon_var_mi:
        return
    baglanti.execute(
        """
        UPDATE sss_kayitlari
        SET arama_metni = trim(kategori || ' ' || soru || ' ' || cevap)
        WHERE arama_metni IS NULL OR trim(arama_metni) = ''
        """
    )
    baglanti.execute(
        """
        INSERT INTO sistem_migrasyonlari (migrasyon_adi)
        VALUES (?)
        """,
        (migrasyon_adi,),
    )


def tablolari_olustur() -> None:
    with baglam_yoneticisi() as baglanti:
        for sorgu in TABLO_SORGULARI:
            baglanti.execute(sorgu)
        _eksik_kolonlari_ekle(
            baglanti,
            "sss_kayitlari",
            SSS_KAYITLARI_EK_KOLONLARI,
        )
        _eksik_kolonlari_ekle(
            baglanti,
            "veri_surumleri",
            VERI_SURUMLERI_EK_KOLONLARI,
        )
        _arama_metnini_bir_kez_geriye_doldur(baglanti)
        baglanti.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            veri_surumleri_dosya_ozeti_benzersiz
            ON veri_surumleri(dosya_ozeti)
            WHERE dosya_ozeti IS NOT NULL
            """
        )
        _fts_tablosunu_hazirla(baglanti)
    gunlukleyici.info(
        "Veritabani tablolari, genisletmeleri ve FTS tetikleyicileri hazirlandi"
    )


def varsayilan_yonetici_olustur(sifre_hash: str) -> None:
    with baglam_yoneticisi() as baglanti:
        baglanti.execute(VARSAYILAN_YONETICI_SORGUSU, (sifre_hash,))
    gunlukleyici.info("Varsayilan yonetici kullanicisi kontrol edildi")
