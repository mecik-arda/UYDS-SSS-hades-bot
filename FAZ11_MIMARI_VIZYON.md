# Faz 11: Veri Ambarı ve Çoklu Veri Kaynağı Entegrasyonu — Sistem Tasarım Dokümanı

## Belge Amacı ve Kapsamı

Bu doküman, HadesBot (UYDS Akıllı SSS Destek Asistanı) projesinin Faz 10 teslimi sonrasında hayata geçirilmesi planlanan Faz 11'in eksiksiz sistem tasarımını, mimari kararlarını, gerekçelerini ve geçiş tetikleyicilerini tanımlar. Doküman, uygulama öncesinde tüm teknik belirsizlikleri gidermek ve jüri değerlendirmesine hazır bir vizyon belgesi sunmak amacıyla hazırlanmıştır.

Faz 10 itibarıyla sistem tekil Excel kaynağından (2.403 SSS kaydı) beslenen, FTS5 + vektör hibrit arama + DeepSeek RAG boru hattına sahip, Docker konteynerinde izole çalışan, 134 test ile doğrulanmış, sıfır hatalı ve production-ready durumdadır. Faz 11 bu temel üzerine inşa edilir.

## Vizyon

Mevcut sistem yalnızca Excel tabanlı statik SSS verileriyle çalışmaktadır. Faz 11, bu dar kapsamı kurumsal bir bilgi yönetim sistemine dönüştürür. PDF, Word, HTML (SharePoint/Confluence) gibi çoklu belge formatlarını okuyup anlamlandıran; manuel yükleme yerine her gece otomatik senkronizasyon yapan; düz metin parçalama yerine tablo, başlık ve madde imi bütünlüğünü koruyan yapısal parçalama uygulayan; vektör aramasına ek olarak kavramlar ve departmanlar arası ilişkileri graf veritabanında haritalandıran; belge bazlı erişim kontrol listeleri (ACL) ile veri sızıntısını sıfıra indiren; bozuk ve şifreli belgeleri karantinaya alarak sistem bütünlüğünü koruyan; belge sürümleme ile geçmiş yönetmeliklere erişimi mümkün kılan bir sisteme geçiş yapılır.

## Mevcut Durum (Faz 10 Sonu)

| Bileşen | Durum |
|---|---|
| Veri kaynağı | Tek: UYDS_SSS_Listesi.xlsx (2.403 kayıt) |
| İçe aktarma | Manuel (excel_ice_aktar.py) |
| Metin parçalama | Karakter sayısı tabanlı, sabit pencere |
| Arama motoru | SQLite FTS5 (BM25) + Vektör (cosine similarity) -> RRF harmanlama |
| Bilgi yapısı | Düz ilişkisel (sss_kayitlari, sss_parcalari), graf yok |
| Belge erişim kontrolü | Yok — tüm kullanıcılar tüm SSS'leri görebilir |
| Belge sürümleme | Yok — güncellenen belge eskisini siler |
| Hata toleransı | Bozuk dosyada tüm içe aktarma durur |
| LLM entegrasyonu | DeepSeek API (kaynak kontrollü RAG) |
| Yeniden sıralama | Cross-Encoder (ms-marco-MiniLM-L-6-v2) |
| Test kapsamı | 134 test, sıfır hata |
| Konteyner | Tek Docker servisi, root'suz, read-only rootfs |

## Hedef Mimari (Faz 11 Sonu)

```
COKLU VERI KAYNAGI                          ETL BORU HATTI
---------------                          --------------
Excel (.xlsx) -------------┐
PDF Belgeleri -------------┤
Word Belgeleri ------------┤
HTML (SharePoint/Confluence)┤--> Belge Ayiklayici --> Yapisal Parcalayici
                            │    (format algilama +     (baslik/tablo/madde
                            │     fallback zinciri +     butunlugu korunur)
                            │     yetki meta verisi)          │
                            │              │                  ▼
                            │              │         ACL Filtresi
                            │              │    (yetki_seviyesi <=
                            │              │     kullanici_yetkisi)
                            │              │                  │
                            │              ▼                  ▼
                            │         Vektorleyici    Karantina Kuyrugu
                            │              │          (bozuk/sifreli)
                            │    ┌─────────┴──────────┐
                            │    ▼                    ▼
                            │ SQLite (FTS5)    Neo4j / NetworkX
                            │ External Content   (GraphRAG)
                            │    │                    │
                            │    └─────────┬──────────┘
                            │              ▼
                            │         Hibrit Arama
                            │         (RRF + Graf skor)
                            │              │
                            │              ▼
                            │         Yetki Filtresi
                            │         (RBAC ACL)
                            │              │
                            │              ▼
                            │         DeepSeek RAG
                            │
                    Cron Motoru (gece 03:00)
                    └─ Artimsal senkronizasyon
                       (yalnizca degisen/guncellenen belgeler,
                        surum zinciri olusturur)
```

## Katmanli Mimari Uyumu

Faz 11 bilesenleri, mevcut katmanli mimariye su sekilde yerlestirilir:

- **API Katmani (uygulama/api/):** Analitik endpoint'leri (13 rota), senkronizasyon tetikleme, vektor durumu izleme, karantina yonetimi, belge surum sorgulama
- **Servis Katmani (uygulama/servisler/):** BelgeAyiklayici, YapisalParcalayici, SenkronizasyonMotoru, BilgiGrafi
- **Model Katmani (uygulama/modeller/):** belge_kayitlari, yapisal_parcalar, parca_vektorleri, belge_kavramlari, graf_dugumleri, graf_iliskileri ORM modelleri
- **Cekirdek Katman (uygulama/cekirdek/):** Yeni konfigurasyon degiskenleri, Cron zamanlayici, ACL yetki esleme motoru

---

## Adim 11.1: Coklu Belge Ayiklayici

### Amac

PDF, DOCX, HTML ve Excel formatlarini tek bir arayuz uzerinden okuyup ham metne, basliklara, tablolara, madde imlerine ve yetki meta verisine ayiran servis.

### Bilesenler

**BelgeIcerik veri sinifi:**

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class BelgeIcerik:
    ham_metin: str
    basliklar: list[str]
    tablolar: list[list[list[str]]]
    madde_imleri: list[str]
    sayfa_sayisi: int
    kaynak_dosya: str
    son_degistirilme_tarihi: datetime
    sha256_ozeti: str
    yetki_seviyesi: int
```

**BelgeAyiklayici servis arayuzu:**

```python
class BelgeAyiklayici:
    def pdf_metin_ayikla(dosya_yolu: str) -> BelgeIcerik
    def docx_metin_ayikla(dosya_yolu: str) -> BelgeIcerik
    def html_metin_ayikla(kaynak: str) -> BelgeIcerik
    def excel_metin_ayikla(dosya_yolu: str) -> BelgeIcerik
    def belge_ayikla(dosya_yolu: str) -> BelgeIcerik
    def yetki_meta_verisi_oku(dosya_yolu: str, dosya_formati: str) -> int
```

### Yetki Meta Verisi Okuma (Belge ACL)

Her belge formatindan yetki seviyesi su stratejiyle okunur. Yetki seviyeleri: 0=herkes, 1=personel, 2=yonetici, 3=ust yonetim, 4=sadece IK.

- PDF: Belge metadata'sindan `yetki_seviyesi` ozel anahtarini okur. Bulamazsa BELGE_VARSAYILAN_YETKI degerini kullanir.
- SharePoint HTML: Sayfadaki `<meta name="permission-level" content="2">` etiketini okur.
- Word (DOCX): Belge ozel ozelliklerinden (custom properties) `yetki_seviyesi` anahtarini okur.
- Excel (XLSX): Ilk satirdaki `# YETKI_SEVIYESI: 3` bicimindeki yorum satirini okur.
- Hicbir yerde bulunamazsa BELGE_VARSAYILAN_YETKI (varsayilan: 0) kullanilir.

Bu mekanizma, SharePoint veya IK klasorlerinden otomatik cekilen belgelerin kendi izinlerini ETL boru hattina tasimasini saglar. Boylece "Sadece Yoneticiler Gorebilir" etiketli bir PDF'teki icerik, standart personel tarafindan RAG sorgusuyla alinamaz.

### PDF Tablo Ayiklama: Kademeli Geri Donus (Graceful Degradation) Zinciri

PDF tablo ayiklama, belge formatlarinin en kirilgan noktasidir. PyMuPDF (fitz) tek basina birlesik hucreli ve cizgisiz tablolarda yetersiz kalir. Bu nedenle uc asamali bir geri donus zinciri uygulanir.

```
pdf_tablolari_ayikla(sayfa)
│
├── 1. ADIM: PyMuPDF (fitz) ile tablo tespiti
│   Sayfada dikdortgen tablo yapisi var mi?
│   ├── VAR + cizgili + guven_skoru >= PDF_TABLO_MIN_GUVEN
│   │   └── fitz ile oku, basarili
│   └── YOK veya cizgisiz veya guven_skoru < esik
│       │
├── 2. ADIM: pdfplumber ile dene (opsiyonel bagimlilik)
│   pdfplumber yuklu mu?
│   ├── EVET -> extract_tables() ile oku
│   └── HAYIR
│       │
└── 3. ADIM: Ham metin olarak al
    Tablo bolgesindeki metni satir satir oku,
    bosluk/sekme hizali sutun olarak isaretle.
    parca_turu = "tablo_ham_metin"
```

**Onemli:** Camelot kesinlikle eklenmez. Camelot'un GhostScript bagimliligi Docker imajini agirlastirir ve projenin "air-gapped" calisma prensibini zedeler. pdfplumber opsiyonel bagimliliktir; yuklu degilse sistem tablo islevselligini kaybetmeden ham metin olarak devam eder.

Motor secimi .env uzerinden yapilir:
- PDF_TABLO_MOTORU=auto (varsayilan, yukaridaki zinciri izler)
- PDF_TABLO_MOTORU=fitz (sadece PyMuPDF)
- PDF_TABLO_MOTORU=pdfplumber (sadece pdfplumber)
- PDF_TABLO_MOTORU=ham_metin (tablo ayiklama yok, duz metin)
- PDF_TABLO_MIN_GUVEN=0.7 (fitz'in verdigi guven skoru altinda fallback'e gecilir)

### Yeni Bagimliliklar

Zorunlu: PyMuPDF (fitz), python-docx, beautifulsoup4, lxml
Opsiyonel: pdfplumber (yuklu degilse ham_metin fallback)

---

## Adim 11.2: Yapisal Parcalayici

### Amac

Mevcut karakter sayisi tabanli parcalamanin yerine gececek, belgenin anlamsal yapisini koruyan ileri seviye parcalama servisi.

### Parcalama Stratejileri

- **Baslik Tabanli Bolme:** Baslik hiyerarsisine gore (H1 > H2 > H3) belgeyi bolumlere ayirir. Her parca, baslik zincirini (orn. ["Bolum 3", "3.1 Kayit Islemleri"]) tasir. Bu sayfa RAG yaniti uretilirken baglam kopmasi (chunking loss) engellenir.
- **Tablo Butunlugu:** Tablo iceren bolgelerde tablo bolunmez; tablo basligi ve tum satirlar tek parcada tutulur.
- **Madde Imi Gruplama:** Ardisik madde imleri ayni parcada kalir, baglam butunlugu korunur.
- **Kayan Pencere (Fallback):** Hiyerarsik yapi tespit edilemezse tokenizer tabanli kayan pencere uygulanir.

### Bilesenler

```python
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
    def baslik_hiyerarsisi_cikar(metin: str) -> list[BaslikDugumu]
    def tablo_bolgelerini_tespit_et(metin: str) -> list[TabloBolgesi]
    def yapisal_parcala(belge_icerik: BelgeIcerik) -> list[YapisalParca]
    def parca_ozetini_hesapla(parca: YapisalParca) -> str
```

### baslik_zinciri Tasarim Gerekcesi

Geleneksel RAG sistemlerinde parcalama (chunking) sonrasi her parca bagimsiz bir metin blogu olarak indekslenir. Bu, su soruna yol acar: "Bolum 3.1'deki tablo" ifadesi, "Bolum 3.1" basligi farkli bir parcadaysa anlamsiz hale gelir. baslik_zinciri alani, her parcaya ust basliklarin tam yolunu ekleyerek bu baglam kopmasini cozer. DeepSeek API'ye gonderilen prompt'a baslik zinciri de eklenir, boylece LLM parcayi daha genis belge baglaminda degerlendirebilir.

### Token Sinirlandirmasi

Parcalama, modelin gercek tokenizer ciktisina gore sinirlandirilir; yalnizca karakter sayisina dayali sinirlandirma yeterli kabul edilmez. Bu, kurallar.md Madde 7'deki gereksinimi karsilar.

---

## Adim 11.3: Belge Deposu ORM Modelleri

### Yeni Tablolar

```
belge_kayitlari
├── id (INTEGER PRIMARY KEY)
├── dosya_adi (TEXT NOT NULL)
├── dosya_formati (TEXT NOT NULL)
├── orijinal_yol (TEXT NOT NULL)
├── son_degistirilme_tarihi (TIMESTAMP)
├── sha256_ozeti (TEXT NOT NULL)
├── sayfa_sayisi (INTEGER)
├── yetki_seviyesi (INTEGER DEFAULT 0)
├── islenme_durumu (TEXT)
├── islenme_tarihi (TIMESTAMP)
├── hata_mesaji (TEXT)
├── karantina_nedeni (TEXT)
├── karantina_tarihi (TIMESTAMP)
├── surum (INTEGER DEFAULT 1)
├── aktif (BOOLEAN DEFAULT 1)
├── onceki_surum_id (INTEGER FK -> belge_kayitlari.id)
└── olusturulma_tarihi (TIMESTAMP)

yapisal_parcalar
├── id (INTEGER PRIMARY KEY)
├── belge_id (INTEGER FK -> belge_kayitlari.id)
├── metin (TEXT NOT NULL)
├── parca_turu (TEXT NOT NULL)
├── baslik_zinciri_json (TEXT)
├── sayfa_numarasi (INTEGER)
├── sira (INTEGER)
├── sha256_ozeti (TEXT)
├── token_sayisi (INTEGER)
├── yetki_seviyesi (INTEGER DEFAULT 0)
├── aktif (BOOLEAN DEFAULT 1)
└── olusturulma_tarihi (TIMESTAMP)

parca_vektorleri
├── id (INTEGER PRIMARY KEY)
├── parca_id (INTEGER FK -> yapisal_parcalar.id)
├── vektor (BLOB NOT NULL)
├── model_surumu (TEXT NOT NULL)
├── vektor_boyutu (INTEGER NOT NULL)
├── olusturulma_tarihi (TIMESTAMP)
├── son_sorgulanma_tarihi (TIMESTAMP)
└── sorgulanma_sayisi (INTEGER)

belge_kavramlari
├── belge_id (INTEGER FK -> belge_kayitlari.id)
├── kavram (TEXT)
├── strateji (TEXT)
├── guven_skoru (REAL)
├── olusturulma_tarihi (TIMESTAMP)
└── PRIMARY KEY (belge_id, kavram, strateji)

graf_dugumleri
├── id (INTEGER PRIMARY KEY)
├── etiket (TEXT NOT NULL)
├── dugum_turu (TEXT NOT NULL)
├── ozellikler_json (TEXT)
└── olusturulma_tarihi (TIMESTAMP)

graf_iliskileri
├── id (INTEGER PRIMARY KEY)
├── kaynak_dugum_id (INTEGER FK -> graf_dugumleri.id)
├── hedef_dugum_id (INTEGER FK -> graf_dugumleri.id)
├── iliski_turu (TEXT NOT NULL)
├── agirlik (REAL DEFAULT 1.0)
└── olusturulma_tarihi (TIMESTAMP)
```

### Belge ACL ve Veri Sizintisi Korumasi

belge_kayitlari tablosundaki `yetki_seviyesi` kolonu, belgenin kimler tarafindan goruntulenebilecegini belirler. yapisal_parcalar tablosundaki `yetki_seviyesi` kolonu belgeden miras alinir ve parca bazli ince ayar yapilmasina olanak tanir.

Yetki seviyeleri:
- 0: Herkes (varsayilan) — Genel SSS'ler, herkese acik yonetmelikler
- 1: Personel — Sadece kurum calisanlari
- 2: Yonetici — Departman yoneticileri
- 3: Ust Yonetim — Mudur ve uzeri
- 4: Sadece IK — Insan Kaynaklari ozel belgeleri

RBAC eslemesi .env uzerinden yapilandirilir: `RBAC_YETKI_ESLEME={"yonetici": 3, "editor": 2, "kullanici": 0}`. Bir kullanici yalnizca kendi yetki seviyesine esit veya dusuk seviyedeki belgelere erisebilir. Standart personel "Mudurlerin maas skalasi nedir?" diye sordugunda, yetki seviyesi 3 olan IK PDF'inden gelen cevap RAG boru hattinda filtrelenir ve sistem "bu konuda bilgim yok" yanitini verir.

### FTS5 External Content Optimizasyonu

belge_fts sanal tablosu, metni kendi icinde tutmaz. Bunun yerine SQLite FTS5'in External Content Tables ozelligi kullanilir. Bu sayede ayni metin hem yapisal_parcalar tablosunda hem de FTS indeksinde tekrar tekrar saklanmaz, disk kullanimi yaklasik yari yariya azalir.

```sql
CREATE VIRTUAL TABLE belge_fts USING fts5(
    parca_id UNINDEXED,
    baslik_zinciri,
    belge_adi,
    content='yapisal_parcalar',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
```

Yazma islemi:

```python
veritabani.execute(
    "INSERT INTO belge_fts(belge_fts, rowid, parca_id, baslik_zinciri, belge_adi) "
    "VALUES ('delete', ?, ?, ?, ?)",
    (yeni_parca.id, yeni_parca.id, baslik_zinciri_json, belge_adi)
)
```

Bu yapi, yapisal_parcalar tablosundan DELETE yapildiginda FTS indeksini otomatik temizler. Mevcut sss_fts tablosu icin de ayni optimizasyon Faz 11 kapsaminda opsiyonel olarak uygulanabilir.

### Vektor Izleme Kolonlari

parca_vektorleri tablosundaki son_sorgulanma_tarihi ve sorgulanma_sayisi kolonlari, vektor veritabani gecis tetikleyicilerinin izlenmesi icin kullanilir. Bu kolonlar her kosinus benzerligi sorgusunda guncellenir ve yonetici panelinden izlenebilir.

---

## Adim 11.4: Otomatik Senkronizasyon Motoru

### Amac

Manuel veri yukleme yerine, yapilandirilmis belge dizinlerini periyodik olarak tarayip yalnizca yeni ve guncellenmis belgeleri isleyen cron tabanli otomatik sistem. Bozuk, sifreli veya taninmayan belgeleri karantinaya alir, sistem butunlugunu korur. Ayni dosya adiyla gelen yeni belgeleri surum zinciri olusturarak arsivler.

### Calisma Prensibi

1. Yapilandirilmis BELGE_DIZINLERI listesindeki tum dizinleri tara (rekursif)
2. Desteklenen formatlardaki dosyalari bul
3. Her dosya icin SHA-256 ozetini hesapla
4. belge_kayitlari tablosunda ayni yol ve ozete sahip kayit varsa atla
5. Ayni dosya_adi, farkli sha256_ozeti varsa surumle (eskisini aktif=false yap, yenisini surum+1 ile ekle)
6. Ozet degismisse veya yeni dosyaysa isleme kuyruguna ekle
7. Sirayla: belge ayiklama -> yapisal parcalama -> vektorleme -> FTS indeksleme -> kavram cikarma
8. Herhangi bir adimda hata olusursa belgeyi karantinaya al, kalan belgelere devam et
9. Silinmis dosyalari tespit et ve ilgili parcalari/vektorleri/FTS girdilerini temizle

### Bilesenler

```python
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
    yeni_dosyalar: list[DosyaBilgisi]
    guncellenen_dosyalar: list[DosyaBilgisi]
    silinen_dosyalar: list[str]
    karantinaya_alinanlar: list[tuple[DosyaBilgisi, str]]
    degisiklik_var_mi: bool

@dataclass(frozen=True)
class SenkronizasyonSonucu:
    baslangic_zamani: datetime
    bitis_zamani: datetime
    islenen_belge_sayisi: int
    yeni_parca_sayisi: int
    silinen_parca_sayisi: int
    karantina_sayisi: int
    surumlenen_belge_sayisi: int
    hata_sayisi: int
    hata_mesajlari: list[str]
    karantina_mesajlari: list[str]
    sure_saniye: float

class SenkronizasyonMotoru:
    def dizin_tara(dizin_yollari: list[str]) -> list[DosyaBilgisi]
    def degisiklikleri_bul(taranan: list[DosyaBilgisi]) -> SenkronizasyonPlani
    def senkronize_et(plan: SenkronizasyonPlani) -> SenkronizasyonSonucu
    def tam_senkronizasyon() -> SenkronizasyonSonucu
    def artimsal_senkronizasyon() -> SenkronizasyonSonucu
```

### Cron Entegrasyonu

uygulama/ana.py lifespan icinde asyncio.create_task() ile arka plan zamanlayici baslatilir:

- SENKRONIZASYON_SAATI (varsayilan: "03:00"): Her gece tam senkronizasyon
- ARTIMSAL_SENKRONIZASYON_DAKIKA (varsayilan: 30): Her yarim saatte bir hizli degisiklik taramasi
- SENKRONIZASYON_AKTIF=false ile tum zamanlayici devre disi birakilabilir
- SENKRONIZASYON_ZAMAN_ASIMI_SANIYE (varsayilan: 3600): Tek bir senkronizasyon islemi icin maksimum sure

### Hata Yonetimi ve Karantina (Dead Letter Queue)

Senkronizasyon sirasinda bir belge islenirken hata olusursa, belge karantinaya alinir ve sistem calismaya devam eder (fail-safe). Karantina durumu su kosullarda tetiklenir:

| Hata Kodu | Durum | Aciklama |
|---|---|---|
| PDF_SIFRELI | karantina | PDF parola korumali, icerik okunamadi |
| PDF_BOZUK | karantina | PDF yapisi gecersiz, PyMuPDF hata verdi |
| DOCX_BOZUK | karantina | Word dosyasi bozuk ZIP arsivi |
| FORMAT_TANINMADI | karantina | Dosya uzantisi hicbir desteklenen formata uymuyor |
| DOSYA_COK_BUYUK | karantina | Dosya boyutu BELGE_MAKS_BOYUT_MB degerini asti |
| METIN_BOS | karantina | Belge okundu ama icerik tamamen bos |
| VIRUS_TARAMASI_BASARISIZ | karantina | Dis virus tarayici reddetti (opsiyonel) |

Karantina akisi:
1. Ilgili belgenin islenme_durumu "karantina" olarak guncellenir
2. karantina_nedeni kolonuna hata kodu yazilir
3. karantina_tarihi kolonuna zaman damgasi eklenir
4. Kalan belgelerin islenmesine devam edilir
5. Karantina sayisi SenkronizasyonSonucu'nda raporlanir
6. Karantina sayisi > SENKRONIZASYON_MAKS_HATA (varsayilan: 5) ise uyari log'u basilir

### Belge Surumleme (Document Versioning)

Ayni dosya_adi ile farkli sha256_ozeti'ne sahip bir belge tespit edildiginde surumleme devreye girer:

1. Mevcut aktif kayit bulunur (dosya_adi = X, aktif = true)
2. Mevcut kaydin aktif degeri false yapilir
3. Yeni kayit olusturulur: surum = onceki.surum + 1, onceki_surum_id = onceki.id, aktif = true
4. Eski kaydin parcalari ve vektorleri silinmez, yapisal_parcalar.aktif = false yapilir
5. Eski surumler BELGE_MAKS_SURUM_SAKLA (varsayilan: 10) adedini asarsa en eski surumun parcalari ve vektorleri temizlenir

Bu sayede "2024 yilindaki eski yonetmelige gore izin hakkim ne kadardi?" gibi tarih referansli sorgularda sistem dogru surume erisebilir. RAG boru hattinda varsayilan olarak yalnizca aktif=true belgelerde arama yapilir; kullanici sorgusu bir tarih referansi iceriyorsa aktif=false kayitlar da taranir.

---

## RAG Boru Hatti ACL Filtreleme ve Surum Bazli Arama

### Yetki Seviyesi Filtreleme

Hibrit arama sonuclari, kullaniciya sunulmadan once su filtreden gecirilir:

1. Kullanicinin JWT'sinden `rol` claim'i okunur
2. Rol, RBAC_YETKI_ESLEME konfigurasyonu ile yetki seviyesine donusturulur
3. Arama sonuclarindan `WHERE parca.yetki_seviyesi <= kullanici_yetki_seviyesi` kosuluyla filtrelenir
4. Filtreleme RRF harmanlamasindan SONRA, DeepSeek RAG cagrisindan ONCE uygulanir
5. Filtre sonrasi hic sonuc kalmazsa sistem "bu konuda bilgim yok" yaniti verir (veri sizintisi olmaz)

### Surum Bazli Arama

Kullanici sorgusu bir tarih referansi iceriyorsa ("2024 yilinda", "eski yonetmelige gore", "onceki duzenlemede"):

1. Sorgudan tarih referansi cikarilir (regex: `\b(20\d{2})\b` veya "eski", "onceki", "gecmis" anahtar kelimeleri)
2. Varsayilan aktif=true filtresi kaldirilir, aktif=false parcalar da taramaya dahil edilir
3. Sonuclar belgenin son_degistirilme_tarihi'ne gore kullanicinin referans verdigi tarihe en yakin surume gore siralanir
4. DeepSeek prompt'una "Kullanici {yil} yilina ait bir duzenlemeyi soruyor. Yanitini bu tarihteki yonetmelige gore ver." yonergesi eklenir

---

## Adim 11.5: GraphRAG / Bilgi Grafi

### Amac

Vektor aramasina ek olarak, kavramlar ve SSS'ler arasindaki iliskileri graf veritabaninda modelleyerek arama dogrulugunu artiran katman.

### Graf Semasi

```
(:Belge {dosya_adi, format, tarih, yetki_seviyesi})
(:SSS_Kaydi {sss_id, soru, kategori, modul})
(:Kavram {ad, tur})
(:Departman {ad})

ILISKILER:
(:Belge)-[:ICERIR]->(:SSS_Kaydi)
(:SSS_Kaydi)-[:ATIFTA_BULUNUR]->(:Kavram)
(:SSS_Kaydi)-[:AITTIR]->(:Departman)
(:Kavram)-[:ILISKILI]->(:Kavram)
(:SSS_Kaydi)-[:BENZER]->(:SSS_Kaydi)
```

### Aramaya Graf Katkisi

Hibrit arama (FTS + Vektor) sonucuna ek olarak graf skorlamasi uygulanir:
1. Kullanici sorgusundan kavramlar cikarilir
2. Bu kavramlarin graf komsuluklari taranir (GRAF_KOMSULUK_DERINLIK kadar, varsayilan 2 adim)
3. Dogrudan eslesmeyen ama graf uzerinden 1-2 adim uzakliktaki SSS kayitlarina bonus skor verilir (GRAF_BONUS_SKORU, varsayilan 0.15)
4. Bonus skor, RRF harmanlama asamasinda nihai skora eklenir

### Bilesenler

```python
class BilgiGrafi:
    def kavram_cikar(metin: str, strateji: str = None) -> list[tuple[str, float]]
    def graf_komsuluk_skoru(sss_id: int, sorgu_kavramlari: list[str]) -> float
    def graf_ile_genislet(sorgu: str, aday_sssler: list[int]) -> list[tuple[int, float]]
    def graf_olustur() -> None
    def iliski_ekle(kaynak_etiket: str, hedef_etiket: str, iliski_turu: str) -> None
```

### Kavram Cikarma: Kademeli Strateji (TF-IDF -> SpaCy NER -> LLM)

Tek bir yonteme kilitlenmek yerine, maliyet ve dogruluk dengesini gozeten uc kademeli bir strateji uygulanir.

```
kavram_cikar(metin, strateji)
│
├── STRATEJI "hafif" (varsayilan, cevrimdisi, ucretsiz)
│   ├── Turkce durak kelimeleri temizle
│   ├── TF-IDF ile belgeye ozgu anahtar terimleri cikar (ilk %15)
│   ├── Terim Haritasi (mevcut terim_haritasi.py) ile kurum jargonu filtrele
│   └── n-gram birlestirme: PMI ile bigram/trigram yakala
│
├── STRATEJI "ner" (SpaCy Turkce NER, yerel, opsiyonel bagimlilik)
│   ├── tr_core_news_md modeli
│   ├── ORG, PERSON, LOCATION, DATE varliklarini cikar
│   └── Strateji "hafif" sonuclariyla birlestir (union)
│
└── STRATEJI "llm" (DeepSeek API, pahali, istege bagli)
    ├── Yalnizca belge basina bir kez, ilk islemede calisir
    ├── Sonuclar belge_kavramlari tablosunda onbellege alinir
    ├── Ayni belge ikinci kez islenmez
    └── Yalnizca yeni/guncellenmis belgeler icin API cagrisi yapilir
```

Strateji secimi .env uzerinden yapilir:
- GRAF_KAVRAM_STRATEJISI=hafif (varsayilan)
- GRAF_KAVRAM_STRATEJISI=ner (SpaCy yuklu olmali)
- GRAF_KAVRAM_STRATEJISI=llm (DeepSeek API anahtari gerekli)
- GRAF_LLM_KAVRAM_AKTIF=false (llm stratejisi secili olsa bile API cagrisini acar/kapatir)
- GRAF_LLM_KAVRAM_MAKS_TOKEN=200 (kavram cikarma basina maksimum token)

### Neo4j / NetworkX Fallback Mimarisi

Birincil graf motoru Neo4j'dur. Ancak Neo4j bir dis bagimliliktir ve air-gapped calisma prensibine aykiri olabilir. Bu nedenle:

- NEO4J_AKTIF=false (varsayilan): networkx + SQLite (graf_dugumleri, graf_iliskileri tablolari) kullanilir
- NEO4J_AKTIF=true: Neo4j baglantisi kurulur, graf islemleri Cypher sorgulari ile yapilir
- Gecis otomatiktir: NEO4J_AKTIF degeri degistiginde sistem yeniden baslatilir, graf yeniden insa edilir

NetworkX fallback, kucuk olcekli (10.000 dugum alti) graflar icin yeterlidir. Neo4j, graf 10.000 dugumu astiginda veya karmasik graf sorgulari (PageRank, Community Detection) gerektiginde devreye alinmalidir.

---

## Adim 11.6: Analitik API Rotalari

### Endpoint Listesi

- GET /api/analitik/ozet — Toplam belge, SSS, parca sayisi; son senkronizasyon durumu
- GET /api/analitik/belge-dagilimi — Formata gore belge dagilimi
- GET /api/analitik/senkronizasyon-durumu — Son senkronizasyon zamani, islenen/atlanan/hata/karantina sayisi
- GET /api/analitik/karantina-durumu — Karantinadaki belge sayisi, nedenlere gore dagilim, karantina listesi
- GET /api/analitik/belge-surumleri — Bir belgenin tum surumlerini, tarihlerini ve aktiflik durumunu listeler
- GET /api/analitik/kavram-bulutu — En sik gecen kavramlar (graf dugum frekansi)
- GET /api/analitik/departman-iliskileri — Departmanlar arasi SSS capraz referanslari
- GET /api/analitik/benzer-sssler — Cosine > 0.85 benzer SSS ciftleri
- GET /api/analitik/yetim-kavramlar — Hicbir SSS'ye baglanmamis graf dugumleri
- GET /api/analitik/parca-istatistikleri — Parca turu dagilimi, ortalama token sayisi
- GET /api/analitik/sorgu-trendi — Arama sorgu trendi (mevcut asistan_sorgulari uzerinden)
- GET /api/analitik/vektor-durumu — parca_vektorleri satir sayisi, disk boyutu, ortalama sorgu suresi, esik asimi uyarisi
- GET /api/analitik/rapor/dokuman — Tum analitik raporu disa aktar

Tum endpoint'ler mevcut yonetici yetkilendirme altyapisi (JWT + HMAC imza) ile korunur.

---

## Adim 11.7: Yonetici Analitik On Yuzu

Canvas API kullanilarak sunucusuz grafikler (harici JavaScript kutuphanesi kullanilmaz, projenin izole ruhuna bagli kalinir):

- Belge formati pasta grafigi
- Kavram iliski agi (force-directed graph)
- Senkronizasyon durum cizelgesi
- Karantinadaki Belgeler tablosu (Dead Letter Queue arayuzu): Dosya Adi, Karantina Nedeni, Tarih, Dosya Boyutu, Islem (Yeniden Dene / Sil / Yoksay) sutunlari
- Belge Surum Gecmisi paneli: secili belgenin tum surumlerini, tarihlerini, aktiflik durumunu ve surumler arasi gecis dugmelerini gosterir
- Son 30 gun sorgu trendi cizgi grafigi
- Departman bazli SSS dagilimi sutun grafigi
- Vektor durumu gostergesi (esik asimi uyarisi)

Tum grafikler Canvas 2D API ile cizilir, data-label attribute'lari ile erisilebilirlik saglanir.

---

## Vektor Veritabani Gecis Tetikleyicileri

Asagidaki kosullardan herhangi biri gerceklestiginde sqlite-vec veya pgvector gecisi zorunlu hale gelir ve Faz 13 (Bakim) planina eklenir:

- Aktif parca_vektorleri satir sayisi >= 50.000
- p95 kosinus benzerligi hesaplama gecikmesi >= 200ms
- Eszamanli sorgu sayisi >= 10 oldugunda ortalama yanit suresi >= 2 saniye

Geciste degerlendirilecek adaylar (oncelik sirasiyla):

1. sqlite-vec: SQLite eklentisi, Docker imajina embed edilir. En hafif gecis, air-gapped uyumlu. Mevcut SQLite altyapisini korur.
2. pgvector: Ayri PostgreSQL konteyneri, docker-compose.yml'a eklenir. Daha guclu ama ikinci bir veritabani bakim yuku getirir.
3. Qdrant: Yerel binary, ayri konteyner. En yuksek performans ama en agir bakim yuku.

Gecis tamamlanana kadar mevcut SQLite BLOB yapisi korunur. Senkronizasyon motoru parca_vektorleri tablosunun satir sayisini izler ve esik asiminda uyari log'u basar.

Faz 11 kapsaminda (2.403 SSS + birkac duzine ek belge) parca sayisi tahmini 15.000-20.000 araliginda kalacaktir. Bu olcekte SQLite BLOB + NumPy tam tarama hala rahatlikla calisir. Fiili gecis Faz 13 Bakim'a birakilir.

---

## Yeni Dosyalar ve Degisiklikler

### Yeni Dosyalar

```
uygulama/servisler/belge_ayiklayici.py
uygulama/servisler/yapisal_parcalayici.py
uygulama/servisler/senkronizasyon_motoru.py
uygulama/servisler/bilgi_grafi.py
uygulama/modeller/belge_deposu_modelleri.py
uygulama/api/rotalar/analitik.py
uygulama/statik/js/analitik.js
testler/test_belge_ayiklayici.py
testler/test_yapisal_parcalayici.py
testler/test_senkronizasyon_motoru.py
testler/test_bilgi_grafi.py
testler/test_analitik_api.py
testler/test_acl_rag_boru_hatti.py
testler/test_surum_bazli_arama.py
testler/test_graf_rrf_harmanlayici.py
testler/test_fts_external_content.py
.github/workflows/faz11-dogrulama.yml
```

### Degisecek Dosyalar

```
uygulama/ana.py
uygulama/api/bagimliliklar.py
uygulama/sablonlar/analitik.html
uygulama/servisler/arama_servisi.py
docker-compose.yml
.env.example
requirements.txt
```

---

## Yeni Bagimliliklar

### Zorunlu

- PyMuPDF (fitz) >= 1.23.0
- python-docx >= 1.0.0
- beautifulsoup4 >= 4.12.0
- lxml >= 4.9.0
- networkx >= 3.2

### Opsiyonel

- pdfplumber >= 0.10.0 — yuklu degilse PDF tablo ayiklama ham_metin fallback ile calisir
- spacy >= 3.7, tr_core_news_md — yuklu degilse kavram cikarma "hafif" strateji ile calisir
- neo4j >= 5.15.0 — yuklu degilse NetworkX fallback ile calisir

---

## Konfigurasyon Degiskenleri

```
# Belge Deposu
BELGE_DIZINLERI=veriler/belgeler/,veriler/mevzuat/
BELGE_TARAMA_RECURSIVE=true
BELGE_DESTEK_FORMATLAR=xlsx,pdf,docx,html
BELGE_VARSAYILAN_YETKI=0
BELGE_MAKS_BOYUT_MB=50

# Belge ACL ve RBAC
BELGE_ACL_AKTIF=true
RBAC_YETKI_ESLEME={"yonetici": 3, "editor": 2, "kullanici": 0}

# Belge Surumleme
BELGE_SURUMLE_AKTIF=true
BELGE_MAKS_SURUM_SAKLA=10

# PDF Tablo
PDF_TABLO_MOTORU=auto
PDF_TABLO_MIN_GUVEN=0.7

# Senkronizasyon
SENKRONIZASYON_AKTIF=true
SENKRONIZASYON_SAATI=03:00
ARTIMSAL_SENKRONIZASYON_DAKIKA=30
SENKRONIZASYON_ZAMAN_ASIMI_SANIYE=3600
SENKRONIZASYON_MAKS_HATA=5

# Yapisal Parcalama
YAPISAL_PARCALAMA_AKTIF=true
PARCALAMA_MAKS_TOKEN=512
PARCALAMA_ORTAK_TOKEN=64

# Bilgi Grafi
GRAF_AKTIF=true
NEO4J_AKTIF=false
NEO4J_URI=bolt://localhost:7687
NEO4J_KULLANICI=neo4j
NEO4J_SIFRE=sifre123
GRAF_KOMSULUK_DERINLIK=2
GRAF_BONUS_SKORU=0.15
GRAF_KAVRAM_STRATEJISI=hafif
GRAF_NER_MODELI=tr_core_news_md
GRAF_LLM_KAVRAM_AKTIF=false
GRAF_LLM_KAVRAM_MAKS_TOKEN=200

# Vektor Gecis Esikleri
VEKTOR_GECIS_PARCAS_SINIRI=50000
VEKTOR_GECIS_P95_GECIKME_MS=200
VEKTOR_GECIS_ESZAMANLI_SORGU=10
VEKTOR_GECIS_YANIT_SURESI_SN=2
```

---

## Test Kapsami

| Test Dosyasi | Hedef Test Sayisi | Kapsam |
|---|---|---|
| test_belge_ayiklayici.py | 18 | PDF/DOCX/HTML/Excel okuma, format algilama, fallback zinciri, yetki meta verisi okuma, hata durumlari |
| test_yapisal_parcalayici.py | 15 | Baslik hiyerarsisi, tablo butunlugu, madde imi gruplama, token siniri |
| test_senkronizasyon_motoru.py | 16 | Tam/artimsal senkronizasyon, degisiklik tespiti, silinen dosya temizligi, karantina durumlari (7 hata kodu), surumleme zinciri, hata toleransi |
| test_bilgi_grafi.py | 10 | Kavram cikarma (3 strateji), graf olusturma, komsuluk skoru, NetworkX fallback |
| test_analitik_api.py | 13 | 13 endpoint, parametre dogrulama, yetkilendirme, karantina durumu, surum sorgulama, vektor durumu esik kontrolu, ACL yetki filtreleme |
| test_acl_rag_boru_hatti.py | 8 | Uctan uca RAG filtreleme: %99 cosine similarity olsa bile yetkisiz parca RAG promptuna sizmaz, filtre RRF sonrasi/LLM oncesi dogru konumda, tum yetki seviyeleri icin pozitif/negatif testler |
| test_surum_bazli_arama.py | 7 | Tarih referansli sorgularda aktif=false filtresi otomatik kalkar, dogru surum bulunur; tarihsiz sorguda her zaman en guncel surum; "eski yonetmelige gore" gibi referanssiz ifadelerde en yakin onceki surume yonlendirme |
| test_graf_rrf_harmanlayici.py | 6 | RRF matematigi: GRAF_BONUS_SKORU=0.15 FTS5 tam eslesme skorunu ezmez, graf skoru yalnizca komsu dugumlere bonus verir, ilgisiz sonuclari yukari cekmez, FTS+vektor+graf uc skorun RRF harmanlamasi dogru |
| test_fts_external_content.py | 6 | External Content butunlugu: yapisal_parcalar'dan silinen kayit belge_fts'ten otomatik temizlenir, oksuz indeks kalmaz; guncellemede eski/yeni indeks cakismasi olmaz; disk kullanimi yariya iner |
| Toplam | 99 | |

---

## Basari Kriterleri

- PDF, DOCX, HTML ve XLSX formatlarinin tamami hatasiz okunabilmeli
- PDF tablo fallback zinciri her seviyede dogru calismali (fitz -> pdfplumber -> ham_metin)
- Yapisal parcalama, tablo iceren belgelerde tablolari bolmemeli (butunluk orani: yuzde 100)
- Belge ACL filtreleme ile yetkisiz erisimde veri sizintisi orani: yuzde 0
- Yetki seviyesi tum belge formatlarindan dogru okunabilmeli; bulunamadiginda varsayilan deger kullanilmali
- Karantina durumunda sistem cokmemeli, kalan belgelerin islenmesine devam edilmeli (fail-safe)
- Tum karantina nedenleri (7 hata kodu) dogru sekilde siniflandirilmali
- Belge surumleme zinciri eksiksiz olusmali; surum gecmisi sorgulama dogrulugu: yuzde 100
- Eski surumler BELGE_MAKS_SURUM_SAKLA sinirini astiginda en eski surum temizlenmeli
- Tarih referansli sorgularda RAG boru hatti dogru surumu secmeli
- Artimsal senkronizasyon 2.403 SSS + 50 ek belge icin 30 saniyeden kisa surmeli
- Bilgi grafi sorguya eklenen SSS kayitlari icin Top-1 dogrulugunu en az yuzde 2 artirmali
- FTS5 external content tablosu disk kullanimini yariya indirmeli
- Neo4j kapaliyken NetworkX fallback sorunsuz calismali
- Kavram cikarma onbellegi ayni belge icin tekrar API cagrisi yapmamali
- 99 yeni test, tumu mevcut 134 testle birlikte yesil olmali
- Canvas grafikleri harici kutuphane olmadan render edilmeli (tarayicida 1 saniyeden kisa sure)
- Vektor gecis esikleri asildiginda uyari log'u basilmali
- Tum kod, degisken ve veritabani adlandirmalari Turkce olmali
- Sifir yorum satiri, sifir placeholder kod, sifir emoji

---

## Juri Sunumu Icin Yurutucu Ozet

Faz 10 itibariyla HadesBot, tekil Excel kaynagindan beslenen, 134 test ile dogrulanmis, Docker'da izole calisan, sifir hatali ve production-ready bir SSS asistanidir. Faz 11, bu temel uzerine su yedi ana eksende genislemeyi hedefler:

1. **Coklu Belge Destegi:** PDF, Word, HTML ve Excel formatlarini okuyup yapisal olarak parcalayan, kademeli geri donus (graceful degradation) stratejisiyle hicbir bagimlilik eksikliginde cokmeyen bir ETL boru hatti.

2. **Belge ACL ve Veri Sizintisi Korumasi:** SharePoint ve kurum icı kaynaklardan belge yetki meta verisini okuyan, RAG boru hattinda kullanici yetki seviyesine gore filtreleme yaparak yetkisiz erisimi sifira indiren katman.

3. **Karantina ve Dead Letter Queue:** Bozuk, sifreli veya taninmayan belgeleri 7 farkli hata koduyla siniflandirip karantinaya alan, sistem butunlugunu koruyan fail-safe hata yonetimi.

4. **Belge Surumleme (Zaman Makinesi):** Ayni dosya adiyla gelen guncellemeleri surum zinciri olusturarak arsivleyen, tarih referansli sorgularda dogru surume erisimi saglayan sistem.

5. **Otomatik Senkronizasyon:** Manuel veri yukleme yerine, her gece belge dizinlerini tarayip yalnizca degisen dosyalari isleyen cron tabanli artimsal sistem.

6. **Yapisal Parcalama:** Baslik hiyerarsisi, tablo butunlugu ve madde imi gruplamasi ile baglam kopmasini (chunking loss) tamamen cozen ileri seviye metin parcalama.

7. **GraphRAG:** TF-IDF -> SpaCy NER -> LLM kademeli stratejisiyle kavram cikaran, Neo4j / NetworkX fallback mimarisiyle satici bagimliligi olusturmayan bilgi grafi katmani.

Sistemin vektor arama kapasitesi sinirlarina yaklasmasi durumunda (50.000 parca, 200ms p95 gecikme, 10 eszamanli kullanici) sqlite-vec veya pgvector gecisi icin tetikleyici esikler tanimlanmistir. Tum mimari kararlar; veri guvenligi (ACL), sistem dayanikliligi (karantina), veri yonetisimi (surumleme), maliyet optimizasyonu ve graceful degradation prensipleri gozetilerek gerekcelendirilmistir.

Faz 11 toplam 99 yeni test (5 birim/entegrasyon + 4 uctan uca/guvenlik testi) ile mevcut 134 testin uzerine eklenerek toplam 233 teste ulasir. Bu testler yalnizca sistemin calistigini degil; Zero Trust uyumlu oldugunu (test_acl_rag_boru_hatti.py), zamansal tutarlilik sagladigini (test_surum_bazli_arama.py), RRF matematiginin dogru calistigini (test_graf_rrf_harmanlayici.py) ve FTS5 disk butunlugunu korudugunu (test_fts_external_content.py) kanitlar.
