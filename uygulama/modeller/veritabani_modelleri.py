from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.belge_deposu_modelleri import (
    BELGE_DEPOSU_TABLOLARI,
    BELGE_FTS_TABLOSU,
    BELGE_FTS_TETIKLEYICI_ADLARI,
    BELGE_FTS_TETIKLEYICILERI,
)

SSS_KAYITLARI_TABLOSU = """
CREATE TABLE IF NOT EXISTS sss_kayitlari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategori TEXT NOT NULL,
    soru TEXT NOT NULL,
    cevap TEXT NOT NULL,
    kaynak_dokuman TEXT,
    surum_numarasi INTEGER NOT NULL DEFAULT 1,
    aktif_mi INTEGER NOT NULL DEFAULT 1 CHECK (aktif_mi IN (0, 1)),
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    harici_kod TEXT,
    modul TEXT,
    kullanici_rolu TEXT,
    arama_metni TEXT,
    durum TEXT NOT NULL DEFAULT 'aktif' CHECK (durum IN ('aktif', 'pasif')),
    icerik_surumu INTEGER NOT NULL DEFAULT 1,
    kaynak_sayfa TEXT,
    kaynak_satir INTEGER,
    kayit_ozeti TEXT,
    kayit_anahtari TEXT,
    onceki_kayit_id INTEGER,
    revizyon_numarasi INTEGER NOT NULL DEFAULT 1,
    degisiklik_turu TEXT NOT NULL DEFAULT 'ekleme'
        CHECK (degisiklik_turu IN ('ekleme', 'guncelleme', 'geri_alma')),
    degisen_alanlar TEXT,
    son_gorulen_surum INTEGER,
    aktarim_surumu_id INTEGER,
    FOREIGN KEY (onceki_kayit_id) REFERENCES sss_kayitlari(id) ON DELETE SET NULL,
    FOREIGN KEY (aktarim_surumu_id) REFERENCES veri_surumleri(id) ON DELETE SET NULL
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
    parca_id INTEGER NOT NULL,
    vektor_verisi BLOB NOT NULL,
    model_adi TEXT NOT NULL,
    vektor_boyutu INTEGER NOT NULL DEFAULT 384 CHECK (vektor_boyutu > 0),
    metin_ozeti TEXT NOT NULL,
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sss_id) REFERENCES sss_kayitlari(id) ON DELETE CASCADE,
    FOREIGN KEY (parca_id) REFERENCES sss_parcalari(id) ON DELETE CASCADE,
    UNIQUE (parca_id, model_adi)
)
"""

GERI_BILDIRIMLER_TABLOSU = """
CREATE TABLE IF NOT EXISTS geri_bildirimler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sss_id INTEGER,
    kullanici_sorusu TEXT NOT NULL,
    verilen_cevap TEXT NOT NULL,
    puan INTEGER NOT NULL CHECK (puan BETWEEN 1 AND 5),
    yorum TEXT,
    durum TEXT NOT NULL DEFAULT 'BEKLEMEDE'
        CHECK (durum IN ('BEKLEMEDE', 'ONAYLANDI', 'REDDEDILDI')),
    tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
    secili_sss_id INTEGER,
    FOREIGN KEY (sss_id) REFERENCES sss_kayitlari(id) ON DELETE SET NULL,
    FOREIGN KEY (secili_sss_id) REFERENCES sss_kayitlari(id) ON DELETE SET NULL
)
"""

KULLANICILAR_TABLOSU = """
CREATE TABLE IF NOT EXISTS kullanicilar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_adi TEXT UNIQUE NOT NULL,
    sifre_hash TEXT NOT NULL,
    rol TEXT NOT NULL DEFAULT 'KULLANICI'
        CHECK (rol IN ('KULLANICI', 'YONETICI')),
    aktif_mi INTEGER NOT NULL DEFAULT 1 CHECK (aktif_mi IN (0, 1))
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
        CHECK (durum IN ('aktif', 'arsivlendi')),
    eklenen_kayit_sayisi INTEGER NOT NULL DEFAULT 0,
    guncellenen_kayit_sayisi INTEGER NOT NULL DEFAULT 0,
    korunan_kayit_sayisi INTEGER NOT NULL DEFAULT 0,
    arsivlenen_kayit_sayisi INTEGER NOT NULL DEFAULT 0,
    olusturulan_parca_sayisi INTEGER NOT NULL DEFAULT 0
)
"""

VERI_SURUMU_KAYITLARI_TABLOSU = """
CREATE TABLE IF NOT EXISTS veri_surumu_kayitlari (
    veri_surumu_id INTEGER NOT NULL,
    sss_id INTEGER NOT NULL,
    kaynak_sayfa TEXT NOT NULL,
    kaynak_satir INTEGER NOT NULL,
    kayit_ozeti TEXT NOT NULL,
    PRIMARY KEY (veri_surumu_id, sss_id),
    FOREIGN KEY (veri_surumu_id) REFERENCES veri_surumleri(id) ON DELETE CASCADE,
    FOREIGN KEY (sss_id) REFERENCES sss_kayitlari(id) ON DELETE CASCADE
)
"""

ALTERNATIF_SORULAR_TABLOSU = """
CREATE TABLE IF NOT EXISTS alternatif_sorular (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sss_id INTEGER NOT NULL,
    soru TEXT NOT NULL,
    vektor_verisi BLOB,
    model_adi TEXT,
    vektor_boyutu INTEGER,
    metin_ozeti TEXT,
    kaynak TEXT NOT NULL,
    durum TEXT NOT NULL DEFAULT 'beklemede'
        CHECK (durum IN ('beklemede', 'onaylandi', 'reddedildi')),
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
    guven_skoru REAL CHECK (
        guven_skoru IS NULL OR guven_skoru BETWEEN 0.0 AND 1.0
    ),
    cevaplandi_mi INTEGER NOT NULL DEFAULT 0 CHECK (cevaplandi_mi IN (0, 1)),
    kullanici_adi TEXT,
    model_adi TEXT,
    prompt_surumu TEXT,
    kaynak_sss_idleri TEXT,
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

YENILEME_BELIRTECLERI_TABLOSU = """
CREATE TABLE IF NOT EXISTS yenileme_belirtecleri (
    jti TEXT PRIMARY KEY,
    aile_id TEXT NOT NULL,
    kullanici_adi TEXT NOT NULL,
    belirtec_ozeti TEXT UNIQUE NOT NULL,
    sona_erme_tarihi TEXT NOT NULL,
    olusturulma_tarihi TEXT NOT NULL,
    ip_ozeti TEXT,
    gecersiz_kilindi_mi INTEGER NOT NULL DEFAULT 0
        CHECK (gecersiz_kilindi_mi IN (0, 1)),
    yerine_gecen_jti TEXT,
    FOREIGN KEY (kullanici_adi) REFERENCES kullanicilar(kullanici_adi)
        ON DELETE CASCADE
)
"""

GECERSIZ_ERISIM_BELIRTECLERI_TABLOSU = """
CREATE TABLE IF NOT EXISTS gecersiz_erisim_belirtecleri (
    jti TEXT PRIMARY KEY,
    sona_erme_tarihi TEXT NOT NULL,
    gecersiz_kilinma_tarihi TEXT NOT NULL
)
"""

YONETICI_IMZA_NONCE_TABLOSU = """
CREATE TABLE IF NOT EXISTS yonetici_imza_nonce_kayitlari (
    nonce_ozeti TEXT PRIMARY KEY,
    sona_erme_tarihi TEXT NOT NULL
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
WHEN OLD.soru IS NOT NEW.soru
    OR OLD.cevap IS NOT NEW.cevap
    OR OLD.kategori IS NOT NEW.kategori
    OR OLD.harici_kod IS NOT NEW.harici_kod
    OR OLD.modul IS NOT NEW.modul
    OR OLD.arama_metni IS NOT NEW.arama_metni
    OR OLD.durum IS NOT NEW.durum
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
    VERI_SURUMU_KAYITLARI_TABLOSU,
    ALTERNATIF_SORULAR_TABLOSU,
    ASISTAN_SORGULARI_TABLOSU,
    SISTEM_GUNLUKLERI_TABLOSU,
    GIRIS_DENEMELERI_TABLOSU,
    YENILEME_BELIRTECLERI_TABLOSU,
    GECERSIZ_ERISIM_BELIRTECLERI_TABLOSU,
    YONETICI_IMZA_NONCE_TABLOSU,
    SISTEM_MIGRASYONLARI_TABLOSU,
]

ASISTAN_SORGULARI_EK_KOLONLARI = {
    "kullanici_adi": "TEXT",
    "model_adi": "TEXT",
    "prompt_surumu": "TEXT",
    "kaynak_sss_idleri": "TEXT",
}

GERI_BILDIRIMLER_EK_KOLONLARI = {
    "secili_sss_id": (
        "INTEGER REFERENCES sss_kayitlari(id) ON DELETE SET NULL"
    ),
}

ALTERNATIF_SORULAR_EK_KOLONLARI = {
    "model_adi": "TEXT",
    "vektor_boyutu": "INTEGER",
    "metin_ozeti": "TEXT",
}

SSS_KAYITLARI_EK_KOLONLARI = {
    "harici_kod": "TEXT",
    "modul": "TEXT",
    "kullanici_rolu": "TEXT",
    "arama_metni": "TEXT",
    "durum": "TEXT NOT NULL DEFAULT 'aktif'",
    "icerik_surumu": "INTEGER NOT NULL DEFAULT 1",
    "kaynak_sayfa": "TEXT",
    "kaynak_satir": "INTEGER",
    "kayit_ozeti": "TEXT",
    "kayit_anahtari": "TEXT",
    "onceki_kayit_id": "INTEGER REFERENCES sss_kayitlari(id) ON DELETE SET NULL",
    "revizyon_numarasi": "INTEGER NOT NULL DEFAULT 1",
    "degisiklik_turu": "TEXT NOT NULL DEFAULT 'ekleme'",
    "degisen_alanlar": "TEXT",
    "son_gorulen_surum": "INTEGER",
    "aktarim_surumu_id": "INTEGER REFERENCES veri_surumleri(id) ON DELETE SET NULL",
}

VERI_SURUMLERI_EK_KOLONLARI = {
    "dosya_ozeti": "TEXT",
    "onceki_surum_numarasi": "INTEGER",
    "durum": "TEXT NOT NULL DEFAULT 'aktif'",
    "eklenen_kayit_sayisi": "INTEGER NOT NULL DEFAULT 0",
    "guncellenen_kayit_sayisi": "INTEGER NOT NULL DEFAULT 0",
    "korunan_kayit_sayisi": "INTEGER NOT NULL DEFAULT 0",
    "arsivlenen_kayit_sayisi": "INTEGER NOT NULL DEFAULT 0",
    "olusturulan_parca_sayisi": "INTEGER NOT NULL DEFAULT 0",
}

VERI_SURUMU_KAYITLARI_EK_KOLONLARI = {
    "kaynak_sayfa": "TEXT",
    "kaynak_satir": "INTEGER",
    "kayit_ozeti": "TEXT",
}

SSS_VEKTORLERI_EK_KOLONLARI = {
    "vektor_boyutu": "INTEGER NOT NULL DEFAULT 384",
    "metin_ozeti": "TEXT",
    "olusturulma_tarihi": "DATETIME",
}

INDEX_SORGULARI = [
    """
    CREATE UNIQUE INDEX IF NOT EXISTS veri_surumleri_dosya_ozeti_benzersiz
    ON veri_surumleri(dosya_ozeti)
    WHERE dosya_ozeti IS NOT NULL
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS sss_kayitlari_aktif_ozet_benzersiz
    ON sss_kayitlari(kayit_ozeti)
    WHERE durum = 'aktif' AND kayit_ozeti IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS sss_kayitlari_durum_surum
    ON sss_kayitlari(durum, son_gorulen_surum)
    """,
    """
    CREATE INDEX IF NOT EXISTS sss_kayitlari_anahtar_durum
    ON sss_kayitlari(kayit_anahtari, durum)
    """,
    """
    CREATE INDEX IF NOT EXISTS sss_kayitlari_onceki_kayit
    ON sss_kayitlari(onceki_kayit_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS veri_surumu_kayitlari_sss_surum
    ON veri_surumu_kayitlari(sss_id, veri_surumu_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS sss_parcalari_sss_id
    ON sss_parcalari(sss_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS sss_vektorleri_sss_parca_model
    ON sss_vektorleri(sss_id, parca_id, model_adi)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS sss_vektorleri_parca_model_benzersiz
    ON sss_vektorleri(parca_id, model_adi)
    WHERE parca_id IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS alternatif_sorular_durum_sss
    ON alternatif_sorular(durum, sss_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS asistan_sorgulari_oturum_tarih
    ON asistan_sorgulari(oturum_id, olusturulma_tarihi)
    """,
    """
    CREATE INDEX IF NOT EXISTS asistan_sorgulari_kullanici_tarih
    ON asistan_sorgulari(kullanici_adi, olusturulma_tarihi)
    """,
    """
    CREATE INDEX IF NOT EXISTS yenileme_belirtecleri_aile
    ON yenileme_belirtecleri(aile_id, gecersiz_kilindi_mi)
    """,
    """
    CREATE INDEX IF NOT EXISTS yenileme_belirtecleri_kullanici
    ON yenileme_belirtecleri(kullanici_adi, sona_erme_tarihi)
    """,
]

DOGRULAMA_TETIKLEYICILERI = [
    """
    CREATE TRIGGER IF NOT EXISTS sss_kayitlari_dogrula_ekle
    BEFORE INSERT ON sss_kayitlari
    WHEN NEW.aktif_mi NOT IN (0, 1)
        OR NEW.durum NOT IN ('aktif', 'pasif')
        OR NEW.degisiklik_turu NOT IN ('ekleme', 'guncelleme', 'geri_alma')
        OR NEW.icerik_surumu < 1
        OR NEW.revizyon_numarasi < 1
        OR (NEW.durum = 'aktif' AND NEW.aktif_mi != 1)
        OR (NEW.durum = 'pasif' AND NEW.aktif_mi != 0)
    BEGIN
        SELECT RAISE(ABORT, 'Gecersiz SSS kaydi durumu');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS sss_kayitlari_dogrula_guncelle
    BEFORE UPDATE ON sss_kayitlari
    WHEN NEW.aktif_mi NOT IN (0, 1)
        OR NEW.durum NOT IN ('aktif', 'pasif')
        OR NEW.degisiklik_turu NOT IN ('ekleme', 'guncelleme', 'geri_alma')
        OR NEW.icerik_surumu < 1
        OR NEW.revizyon_numarasi < 1
        OR (NEW.durum = 'aktif' AND NEW.aktif_mi != 1)
        OR (NEW.durum = 'pasif' AND NEW.aktif_mi != 0)
    BEGIN
        SELECT RAISE(ABORT, 'Gecersiz SSS kaydi durumu');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS geri_bildirim_dogrula_ekle
    BEFORE INSERT ON geri_bildirimler
    WHEN NEW.puan NOT BETWEEN 1 AND 5
        OR NEW.durum NOT IN ('BEKLEMEDE', 'ONAYLANDI', 'REDDEDILDI')
    BEGIN
        SELECT RAISE(ABORT, 'Gecersiz geri bildirim');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS geri_bildirim_dogrula_guncelle
    BEFORE UPDATE ON geri_bildirimler
    WHEN NEW.puan NOT BETWEEN 1 AND 5
        OR NEW.durum NOT IN ('BEKLEMEDE', 'ONAYLANDI', 'REDDEDILDI')
    BEGIN
        SELECT RAISE(ABORT, 'Gecersiz geri bildirim');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS sss_vektorleri_dogrula_ekle
    BEFORE INSERT ON sss_vektorleri
    WHEN NEW.parca_id IS NULL
        OR NEW.vektor_boyutu < 1
        OR NEW.metin_ozeti IS NULL
        OR trim(NEW.metin_ozeti) = ''
        OR length(NEW.vektor_verisi) != NEW.vektor_boyutu * 4
    BEGIN
        SELECT RAISE(ABORT, 'Gecersiz SSS vektoru');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS sss_vektorleri_dogrula_guncelle
    BEFORE UPDATE ON sss_vektorleri
    WHEN NEW.parca_id IS NULL
        OR NEW.vektor_boyutu < 1
        OR NEW.metin_ozeti IS NULL
        OR trim(NEW.metin_ozeti) = ''
        OR length(NEW.vektor_verisi) != NEW.vektor_boyutu * 4
    BEGIN
        SELECT RAISE(ABORT, 'Gecersiz SSS vektoru');
    END
    """,
]

DOGRULAMA_TETIKLEYICI_ADLARI = (
    "sss_kayitlari_dogrula_ekle",
    "sss_kayitlari_dogrula_guncelle",
    "geri_bildirim_dogrula_ekle",
    "geri_bildirim_dogrula_guncelle",
    "sss_vektorleri_dogrula_ekle",
    "sss_vektorleri_dogrula_guncelle",
)

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
INSERT INTO kullanicilar (kullanici_adi, sifre_hash, rol, aktif_mi)
VALUES ('yonetici', ?, 'YONETICI', TRUE)
ON CONFLICT(kullanici_adi) DO UPDATE SET
    sifre_hash = excluded.sifre_hash,
    rol = 'YONETICI',
    aktif_mi = TRUE
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


def _icerik_surumlerini_bir_kez_duzelt(baglanti) -> None:
    migrasyon_adi = "faz3_icerik_surumu_semantigi_v1"
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
        SET icerik_surumu = revizyon_numarasi
        WHERE icerik_surumu != revizyon_numarasi
        """
    )
    baglanti.execute(
        """
        INSERT INTO sistem_migrasyonlari (migrasyon_adi)
        VALUES (?)
        """,
        (migrasyon_adi,),
    )


def _vektor_kayitlarini_bir_kez_temizle(baglanti) -> None:
    migrasyon_adi = "faz4_vektor_benzersizligi_v1"
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
        DELETE FROM sss_vektorleri
        WHERE parca_id IS NULL
            OR id NOT IN (
                SELECT MAX(id)
                FROM sss_vektorleri
                GROUP BY parca_id, model_adi
            )
        """
    )
    baglanti.execute(
        """
        INSERT INTO sistem_migrasyonlari (migrasyon_adi)
        VALUES (?)
        """,
        (migrasyon_adi,),
    )


def _belge_fts_tablosunu_hazirla(baglanti) -> None:
    mevcut_kolonlar = [
        satir["name"]
        for satir in baglanti.execute(
            "PRAGMA table_info('belge_fts')"
        ).fetchall()
    ]
    beklenen_kolonlar = ["metin", "baslik_zinciri_json"]
    yeniden_olusturulmali = mevcut_kolonlar != beklenen_kolonlar
    for tetikleyici_adi in BELGE_FTS_TETIKLEYICI_ADLARI:
        baglanti.execute(f"DROP TRIGGER IF EXISTS {tetikleyici_adi}")
    if yeniden_olusturulmali:
        baglanti.execute("DROP TABLE IF EXISTS belge_fts")
    baglanti.execute(BELGE_FTS_TABLOSU)
    for sorgu in BELGE_FTS_TETIKLEYICILERI:
        baglanti.execute(sorgu)
    if yeniden_olusturulmali:
        baglanti.execute(
            "INSERT INTO belge_fts(belge_fts) VALUES ('rebuild')"
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
        _eksik_kolonlari_ekle(
            baglanti,
            "veri_surumu_kayitlari",
            VERI_SURUMU_KAYITLARI_EK_KOLONLARI,
        )
        _eksik_kolonlari_ekle(
            baglanti,
            "sss_vektorleri",
            SSS_VEKTORLERI_EK_KOLONLARI,
        )
        _eksik_kolonlari_ekle(
            baglanti,
            "asistan_sorgulari",
            ASISTAN_SORGULARI_EK_KOLONLARI,
        )
        _eksik_kolonlari_ekle(
            baglanti,
            "geri_bildirimler",
            GERI_BILDIRIMLER_EK_KOLONLARI,
        )
        _eksik_kolonlari_ekle(
            baglanti,
            "alternatif_sorular",
            ALTERNATIF_SORULAR_EK_KOLONLARI,
        )
        _arama_metnini_bir_kez_geriye_doldur(baglanti)
        _icerik_surumlerini_bir_kez_duzelt(baglanti)
        _vektor_kayitlarini_bir_kez_temizle(baglanti)
        for sorgu in INDEX_SORGULARI:
            baglanti.execute(sorgu)
        for tetikleyici_adi in DOGRULAMA_TETIKLEYICI_ADLARI:
            baglanti.execute(f"DROP TRIGGER IF EXISTS {tetikleyici_adi}")
        for sorgu in DOGRULAMA_TETIKLEYICILERI:
            baglanti.execute(sorgu)
        _fts_tablosunu_hazirla(baglanti)
        for sorgu in BELGE_DEPOSU_TABLOLARI:
            baglanti.execute(sorgu)
        _eksik_kolonlari_ekle(
            baglanti,
            "belge_kayitlari",
            {"dosya_boyutu": "INTEGER"},
        )
        _belge_fts_tablosunu_hazirla(baglanti)
    gunlukleyici.info(
        "Veritabani tablolari, genisletmeleri ve FTS tetikleyicileri hazirlandi"
    )


def varsayilan_yonetici_olustur(sifre_hash: str) -> None:
    with baglam_yoneticisi() as baglanti:
        baglanti.execute(VARSAYILAN_YONETICI_SORGUSU, (sifre_hash,))
    gunlukleyici.info("Varsayilan yonetici kullanicisi kontrol edildi")
