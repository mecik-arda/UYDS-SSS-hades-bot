from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.cekirdek.gunlukleyici import gunlukleyici

SSS_KAYITLARI_TABLOSU = """
CREATE TABLE IF NOT EXISTS sss_kayitlari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategori TEXT NOT NULL,
    soru TEXT NOT NULL,
    cevap TEXT NOT NULL,
    kaynak_dokuman TEXT,
    surum_numarasi INTEGER DEFAULT 1,
    aktif_mi BOOLEAN DEFAULT TRUE,
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

SSS_PARCALARI_TABLOSU = """
CREATE TABLE IF NOT EXISTS sss_parcalari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sss_id INTEGER NOT NULL,
    parca_metni TEXT NOT NULL,
    parca_sira_no INTEGER NOT NULL,
    FOREIGN KEY (sss_id) REFERENCES sss_kayitlari(id) ON DELETE CASCADE
)
"""

SSS_FTS_TABLOSU = """
CREATE VIRTUAL TABLE IF NOT EXISTS sss_fts USING fts5(
    soru,
    cevap,
    kategori
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
    aktarim_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
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

FTS_INSERT_TETIKLEYICI = """
CREATE TRIGGER IF NOT EXISTS sss_fts_ekleme_tetik
AFTER INSERT ON sss_kayitlari
BEGIN
    INSERT INTO sss_fts(rowid, soru, cevap, kategori)
    VALUES (NEW.id, NEW.soru, NEW.cevap, NEW.kategori);
END
"""

FTS_SILME_TETIKLEYICI = """
CREATE TRIGGER IF NOT EXISTS sss_fts_silme_tetik
AFTER DELETE ON sss_kayitlari
BEGIN
    INSERT INTO sss_fts(sss_fts, rowid, soru, cevap, kategori)
    VALUES ('delete', OLD.id, OLD.soru, OLD.cevap, OLD.kategori);
END
"""

FTS_GUNCELLEME_TETIKLEYICI = """
CREATE TRIGGER IF NOT EXISTS sss_fts_guncelleme_tetik
AFTER UPDATE ON sss_kayitlari
BEGIN
    INSERT INTO sss_fts(sss_fts, rowid, soru, cevap, kategori)
    VALUES ('delete', OLD.id, OLD.soru, OLD.cevap, OLD.kategori);
    INSERT INTO sss_fts(rowid, soru, cevap, kategori)
    VALUES (NEW.id, NEW.soru, NEW.cevap, NEW.kategori);
END
"""

TABLO_SORGULARI = [
    SSS_KAYITLARI_TABLOSU,
    SSS_PARCALARI_TABLOSU,
    SSS_VEKTORLERI_TABLOSU,
    GERI_BILDIRIMLER_TABLOSU,
    KULLANICILAR_TABLOSU,
    VERI_SURUMLERI_TABLOSU,
    SISTEM_GUNLUKLERI_TABLOSU,
    SSS_FTS_TABLOSU,
]

TETIKLEYICI_SORGULARI = [
    FTS_INSERT_TETIKLEYICI,
    FTS_SILME_TETIKLEYICI,
    FTS_GUNCELLEME_TETIKLEYICI,
]

VARSAYILAN_YONETICI_SORGUSU = """
INSERT OR IGNORE INTO kullanicilar (kullanici_adi, sifre_hash, rol, aktif_mi)
VALUES ('yonetici', ?, 'YONETICI', TRUE)
"""


def tablolari_olustur():
    with baglam_yoneticisi() as baglanti:
        for sorgu in TABLO_SORGULARI:
            try:
                baglanti.execute(sorgu)
            except Exception as hata:
                gunlukleyici.error(f"Tablo olusturma hatasi: {hata}")
                raise
        for sorgu in TETIKLEYICI_SORGULARI:
            try:
                baglanti.execute(sorgu)
            except Exception as hata:
                gunlukleyici.warning(f"Tetikleyici olusturulurken uyari: {hata}")
    gunlukleyici.info("Veritabani tablolari ve tetikleyiciler basariyla olusturuldu")


def varsayilan_yonetici_olustur(sifre_hash: str):
    with baglam_yoneticisi() as baglanti:
        baglanti.execute(VARSAYILAN_YONETICI_SORGUSU, (sifre_hash,))
    gunlukleyici.info("Varsayilan yonetici kullanicisi kontrol edildi")