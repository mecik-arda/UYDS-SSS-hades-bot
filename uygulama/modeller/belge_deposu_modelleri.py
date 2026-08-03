BELGE_KAYITLARI_TABLOSU = """
CREATE TABLE IF NOT EXISTS belge_kayitlari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dosya_adi TEXT NOT NULL,
    dosya_formati TEXT NOT NULL,
    orijinal_yol TEXT NOT NULL,
    son_degistirilme_tarihi DATETIME,
    sha256_ozeti TEXT NOT NULL,
    dosya_boyutu INTEGER,
    sayfa_sayisi INTEGER,
    yetki_seviyesi INTEGER DEFAULT 0,
    islenme_durumu TEXT DEFAULT 'beklemede'
        CHECK (islenme_durumu IN (
            'beklemede', 'isleniyor', 'tamamlandi',
            'karantina', 'hata'
        )),
    islenme_tarihi DATETIME,
    hata_mesaji TEXT,
    karantina_nedeni TEXT,
    karantina_tarihi DATETIME,
    surum INTEGER DEFAULT 1,
    aktif INTEGER DEFAULT 1 CHECK (aktif IN (0, 1)),
    onceki_surum_id INTEGER,
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (onceki_surum_id) REFERENCES belge_kayitlari(id) ON DELETE SET NULL
)
"""

YAPISAL_PARCALAR_TABLOSU = """
CREATE TABLE IF NOT EXISTS yapisal_parcalar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    belge_id INTEGER NOT NULL,
    metin TEXT NOT NULL,
    parca_turu TEXT NOT NULL
        CHECK (parca_turu IN (
            'paragraf', 'tablo', 'madde_imleri',
            'baslik', 'tablo_ham_metin'
        )),
    baslik_zinciri_json TEXT,
    sayfa_numarasi INTEGER,
    sira INTEGER NOT NULL,
    sha256_ozeti TEXT NOT NULL,
    token_sayisi INTEGER,
    yetki_seviyesi INTEGER DEFAULT 0,
    aktif INTEGER DEFAULT 1 CHECK (aktif IN (0, 1)),
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (belge_id) REFERENCES belge_kayitlari(id) ON DELETE CASCADE
)
"""

PARCA_VEKTORLERI_TABLOSU = """
CREATE TABLE IF NOT EXISTS parca_vektorleri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parca_id INTEGER NOT NULL,
    vektor BLOB NOT NULL,
    model_surumu TEXT NOT NULL,
    vektor_boyutu INTEGER NOT NULL,
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    son_sorgulanma_tarihi DATETIME,
    sorgulanma_sayisi INTEGER DEFAULT 0,
    FOREIGN KEY (parca_id) REFERENCES yapisal_parcalar(id) ON DELETE CASCADE,
    UNIQUE (parca_id, model_surumu)
)
"""

BELGE_KAVRAMLARI_TABLOSU = """
CREATE TABLE IF NOT EXISTS belge_kavramlari (
    belge_id INTEGER NOT NULL,
    kavram TEXT NOT NULL,
    strateji TEXT NOT NULL
        CHECK (strateji IN ('hafif', 'ner', 'llm')),
    guven_skoru REAL NOT NULL,
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (belge_id, kavram, strateji),
    FOREIGN KEY (belge_id) REFERENCES belge_kayitlari(id) ON DELETE CASCADE
)
"""

GRAF_DUGUMLERI_TABLOSU = """
CREATE TABLE IF NOT EXISTS graf_dugumleri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    etiket TEXT NOT NULL,
    dugum_turu TEXT NOT NULL
        CHECK (dugum_turu IN (
            'belge', 'sss_kaydi', 'kavram', 'departman'
        )),
    ozellikler_json TEXT,
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

GRAF_ILISKILERI_TABLOSU = """
CREATE TABLE IF NOT EXISTS graf_iliskileri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kaynak_dugum_id INTEGER NOT NULL,
    hedef_dugum_id INTEGER NOT NULL,
    iliski_turu TEXT NOT NULL,
    agirlik REAL DEFAULT 1.0,
    olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kaynak_dugum_id) REFERENCES graf_dugumleri(id) ON DELETE CASCADE,
    FOREIGN KEY (hedef_dugum_id) REFERENCES graf_dugumleri(id) ON DELETE CASCADE
)
"""

BELGE_FTS_TABLOSU = """
CREATE VIRTUAL TABLE IF NOT EXISTS belge_fts USING fts5(
    metin,
    baslik_zinciri_json,
    content='yapisal_parcalar',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
)
"""

BELGE_FTS_TETIKLEYICI_ADLARI = [
    "yapisal_parcalar_fts_ekle",
    "yapisal_parcalar_fts_sil",
    "yapisal_parcalar_fts_guncelle",
]

BELGE_FTS_TETIKLEYICILERI = [
    """
    CREATE TRIGGER yapisal_parcalar_fts_ekle
    AFTER INSERT ON yapisal_parcalar
    BEGIN
        INSERT INTO belge_fts(rowid, metin, baslik_zinciri_json)
        VALUES (new.id, new.metin, new.baslik_zinciri_json);
    END
    """,
    """
    CREATE TRIGGER yapisal_parcalar_fts_sil
    AFTER DELETE ON yapisal_parcalar
    BEGIN
        INSERT INTO belge_fts(
            belge_fts,
            rowid,
            metin,
            baslik_zinciri_json
        )
        VALUES (
            'delete',
            old.id,
            old.metin,
            old.baslik_zinciri_json
        );
    END
    """,
    """
    CREATE TRIGGER yapisal_parcalar_fts_guncelle
    AFTER UPDATE ON yapisal_parcalar
    BEGIN
        INSERT INTO belge_fts(
            belge_fts,
            rowid,
            metin,
            baslik_zinciri_json
        )
        VALUES (
            'delete',
            old.id,
            old.metin,
            old.baslik_zinciri_json
        );
        INSERT INTO belge_fts(rowid, metin, baslik_zinciri_json)
        VALUES (new.id, new.metin, new.baslik_zinciri_json);
    END
    """,
]

BELGE_DEPOSU_TABLOLARI = [
    BELGE_KAYITLARI_TABLOSU,
    YAPISAL_PARCALAR_TABLOSU,
    PARCA_VEKTORLERI_TABLOSU,
    BELGE_KAVRAMLARI_TABLOSU,
    GRAF_DUGUMLERI_TABLOSU,
    GRAF_ILISKILERI_TABLOSU,
]
