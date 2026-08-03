# UYDS Akıllı SSS Chatbot Projesi - Kapsamlı Fazlara Bölünmüş Geliştirme ve Uygulama Planı

## 1. Proje Özeti, Kapsam ve Kurumsal İlkeler
Projenin amacı, Excel formatında bulunan UYDS Sık Sorulan Sorular verilerini kullanarak yalnızca kelime eşleşmesi yapan basit bir arama sistemi değil; kullanıcı sorularının anlamını analiz eden, ilgili SSS kayıtlarını anlamsal olarak bulan, kaynaklara dayalı cevap üreten ve kullanıcı geri bildirimleriyle zaman içinde gelişebilen akıllı bir destek asistanı oluşturmaktır.

Bu doğrultuda sistem; SQLite FTS5 ve Vektör Gömmeleri tabanlı hibrit arama ve Yeniden Sıralama teknikleri ile en doğru kaynakları tespit eden, dış API olarak DeepSeek entegrasyonu ile kaynak kontrollü cevap üreten ve kullanıcı geri bildirim mekanizması ile sürekli iyileştirilen Docker konteyner tabanlı bir Akıllı SSS Destek Asistanı olarak geliştirilmektedir.

Projenin temel felsefesi; yalnızca çalışan bir sohbet arayüzü sunmak değil, üretilen her cevabın hangi resmi UYDS kaynağına dayandığını izlenebilir kılan, düşük güven durumlarında uydurma bilgi üretmeyen ve kullanıcı geri bildirimleri ile yönetici onay süreçlerini birleştiren sağlam bir kurumsal sistem inşa etmektir.

### Güvenlik Felsefesi: Zero Trust ve Defense in Depth
Proje, sıfır güven (Zero Trust) prensibiyle tasarlanmıştır. Hiçbir kullanıcı, istek veya bileşen varsayılan olarak güvenilir kabul edilmez. Katmanlı savunma (Defense in Depth) yaklaşımıyla birden fazla güvenlik katmanı uygulanır: ağ seviyesinde izolasyon (Docker), taşıma seviyesinde HTTPS ve güvenlik başlıkları, uygulama seviyesinde JWT/RBAC, veri seviyesinde parametreli sorgular ve şifreleme. Her katman bir üst katmandan bağımsız olarak kendi güvenlik kontrollerini gerçekleştirir. Tek bir katmanın aşılması durumunda dahi sistem bütünlüğü korunur.

Tüm kodlar, değişken adları, fonksiyonlar, veritabanı şemaları, servisler ve arayüz bileşenleri tamamen Türkçe dilinde yazılacaktır.

### Depo Bilgisi
- **Depo Adresi:** https://github.com/mecik-arda/UYDS-SSS-hades-bot
- **Depo Adı:** UYDS-SSS-hades-bot
- **Açıklama:** UYDS Sık Sorulan Sorular için anlamsal arama tabanlı, DeepSeek entegrasyonlu, kaynak kontrollü akıllı kurumsal destek asistanı.

## 2. Gizlilik, Güvenlik ve Yerel Çalışma Standartları
- **Veri Gizliliği:** UYDS verileri özel ve kurum içi niteliktedir.
- **Kritik Veri Klasörünün Korunması (`veriler/`):** Projenin temel dayanağı olan `veriler/` klasörü; orijinal UYDS veri seti (`UYDS_SSS_Listesi.xlsx`) ve proje teknik şartnamesini (`UYDS_Akilli_SSS_Chatbot_Staj_Projesi.docx`) barındırmaktadır. Bu dosyalardaki 2.403 adet gerçek SSS kaydı ve sistem kabul metrikleri projenin kalbini oluşturmaktadır. Bu klasör ve içeriği son derece mühimdir, `.gitignore` ile kilitlenmiştir ve kesinlikle harici depolara aktarılamaz.
- **Dış Ağ Yasağı:** Veri tabanı, Excel dosyaları, vektör gömmeleri, günlükler ve proje çıktıları kesinlikle GitHub, GitLab, kişisel bulut hesapları, e-posta veya harici dosya paylaşım servislerine yüklenmeyecektir.
- **Yerel İzole Çalışma:** Tüm geliştirme, konteynerizasyon ve test süreçleri yalnızca tarafınıza tahsis edilen yerel iş bilgisayarlarında yürütülecektir.

## 3. Mimari ve Teknolojik Yapı Detayları
- **Konteynerizasyon:** Docker ve Docker Compose
- **Programlama Dili ve Web Çerçevesi:** Python 3.11 ve FastAPI
- **Dış LLM API:** DeepSeek API (Kaynak kontrollü RAG yanıt üretimi ve akışlı canlı yanıt akışı için)
- **Veri Depolama ve Metin Araması:** SQLite3 (FTS5 tam metin arama eklentisi aktif, Docker Volume ile kalıcı veritabanı)
- **Veri Aktarımı ve Sürümleme:** Pandas ve OpenPyXL tabanlı Excel İçe Aktarma Modülü ve Otomatik Veri Sürümleme
- **Anlamsal Arama:** Türkçe destekli yerel Vektör Gömme modelleri (Sentence-Transformers yerel kütüphaneleri) ve Anlamsal Metin Parçalama (Semantic Chunking)
- **Arama Stratejisi:** SQLite FTS5 (Kelime bazlı BM25 ve Eş Anlamlı Kelime Haritası) + Vektör Benzerliği (Anlamsal Vektör) Hibrit Arama
- **Sıralama İyileştirme:** Cross-Encoder modeli ve Reciprocal Rank Fusion (Skor Harmanlama)
- **Cevap Üretimi:** DeepSeek API bağlamı ile kaynak kontrollü, düşük güven durumlarında yanıt vermeyen (Güven Eşiği Kontrolü), Server-Sent Events (SSE) ile canlı akışlı yanıt mekanizması
- **Güvenlik ve Yetkilendirme:** Rol Tabanlı Erişim Kontrolü (RBAC - JWT/Oturum) ve İstek Sınırlama (Rate Limiting)
- **Geri Bildirim ve Analitik:** Kullanıcı puanlama/yorumları, Yönetici Onay Mekanizması ve Yönetici Analitik Paneli

### Katmanlı Mimari Yapısı
Şartname Bölüm 16 gereği, kod organizasyonu katmanlı mimari prensibine göre ayrılmıştır. Her katman yalnızca kendi altındaki katmana bağımlıdır. Katmanlar arası bağımlılık yukarıdan aşağıya doğrudur; üst katmanlar alt katmanları çağırabilir ancak alt katmanlar üst katmanlara bağımlı olamaz.

- **API Katmanı (`uygulama/api/`):** HTTP istek ve yanıtlarını işler. Girdi validasyonu, rota tanımları, middleware zinciri ve SSE akış yönetimi bu katmandadır. Servis katmanını çağırır.
- **Servis Katmanı (`uygulama/servisler/`):** İş mantığının tamamı bu katmandadır. Arama, embedding üretimi, DeepSeek API entegrasyonu, metin parçalama, Excel içe aktarma, yeniden sıralama ve oturum hafızası servisleri burada yer alır.
- **Veri Erişim Katmanı (`uygulama/modeller/`):** SQLite veritabanı sorguları, tablo şemaları, FTS5 tetikleyicileri ve Pydantic veri modelleri bu katmandadır.
- **Çekirdek Katman (`uygulama/cekirdek/`):** Konfigürasyon yönetimi, veritabanı bağlantısı, JWT/RBAC kimlik doğrulama, rate limiting, güvenlik başlıkları, loglama ve önbellek altyapısı bu katmandadır. Diğer tüm katmanlar tarafından kullanılır.

### Sistem Mimarisi Akış Diyagramı
```
Excel SSS Verileri
        ↓
Veri Temizleme ve İçe Aktarma (Faz 3)
        ↓
SQLite Veritabanı (sss_kayitlari + sss_fts + sss_parcalari)
        ↓
Embedding Üretimi (Faz 4) → sss_vektorleri (BLOB)
        ↓
┌───────────────────────────────────────────────────┐
│ KULLANICI SORUSU                                   │
│   ↓                                                │
│ Sorgu Temizleme ve Bağlamla Yeniden Yazma          │
│   ↓                                                │
│ Embedding Üretimi (anlık vektör)                   │
│   ↓                                                │
│ ┌──────────────────┐  ┌─────────────────────────┐  │
│ │ SQLite FTS5      │  │ Cosine Similarity       │  │
│ │ (BM25 + eş       │  │ (Vektör Benzerliği)      │  │
│ │  anlamlı haritası)│  │                         │  │
│ └────────┬─────────┘  └───────────┬─────────────┘  │
│          ↓                        ↓                │
│ ┌──────────────────────────────────────────────┐   │
│ │ RRF Skor Harmanlama (Reciprocal Rank Fusion) │   │
│ │ RRF_Skoru = 1 / (60 + Sira)                  │   │
│ └────────────────────┬─────────────────────────┘   │
│                      ↓                              │
│ ┌──────────────────────────────────────────────┐   │
│ │ Cross-Encoder Yeniden Sıralama (Reranking)   │   │
│ └────────────────────┬─────────────────────────┘   │
│                      ↓                              │
│ ┌──────────────────────────────────────────────┐   │
│ │ Güven Eşiği Kontrolü (≥ GUVEN_ESIGI)         │   │
│ └────────┬──────────────────────────┬──────────┘   │
│          ↓                          ↓              │
│    Skor ≥ Eşik                  Skor < Eşik        │
│          ↓                          ↓              │
│ DeepSeek RAG              "İlgili UYDS kaynak-     │
│ (Kaynak kontrollü          larında yeterli bilgi   │
│  yanıt üretimi)            bulunamamıştır"         │
│          ↓                          ↓              │
│ SSE Canlı Akış           Yönetici İncelemesine     │
│ + Kaynak Rozetleri         Gönderilir              │
│          ↓                                         │
│ asistan_sorgulari Tablosuna Kayıt                  │
│          ↓                                         │
│ Kullanıcı Geri Bildirimi (1-5 puan)                │
│          ↓                                         │
│ geri_bildirimler Tablosu (BEKLEMEDE)               │
│          ↓                                         │
│ Yönetici Onayı → alternatif_sorular + Embedding    │
└───────────────────────────────────────────────────┘
```

### Arama ve Cevaplama Akışı (Şartname Bölüm 9)
1. Kullanıcının sorusu alınır ve gereksiz karakterlerden temizlenir.
2. Gerekirse konuşma bağlamı kullanılarak bağımsız bir arama sorusuna dönüştürülür.
3. Sorunun embedding vektörü üretilir.
4. NumPy cosine similarity ile en yakın SSS kayıtları ve onaylanmış alternatif sorular bulunur.
5. SQLite FTS5 ile anahtar kelime ve kesin ifade eşleşmeleri bulunur.
6. Semantic ve keyword sonuçları ortak aday listesinde birleştirilir.
7. İlk 10-20 aday reranker tarafından yeniden sıralanır.
8. En iyi 3-5 kaynak güven kontrolünden geçirilir.
9. Yeterli güven varsa LLM yalnızca bu kaynakları kullanarak cevap üretir.
10. Güven düşükse sistem cevap uydurmaz ve yönetici incelemesi önerir.
11. Soru, sonuçlar, skorlar ve kullanıcı geri bildirimi kayıt altına alınır.

## 4. Seçilen Kullanıcı Arayüzü Teması ve Detaylı Görsel Betimlemesi

### Seçilen Tema: Seçenek 2 - Kurumsal Kurşuni (Slate Corporate Minimalist)
Proje arayüzü için sade, kurumsal, açık renkli ve akademik doküman yönetim sistemlerine uygun minimal tasarım konsepti seçilmiştir.

### Görsel Betimleme (Görsel İşleyemeyen Sistemler ve Ekran Okuyucular İçin Detaylı Yapı)
- **Genel Düzen:** Arayüz, ekranı sol ve sağ olmak üzere iki ana bölüme ayıran kart yapısındadır. Arka plan açık kurşuni gri renktedir. Tüm paneller yuvarlatılmış köşeli ve gölgelendirmeli temiz bir kart içerisinde yer alır.
- **Sol Navigasyon Menüsü (Yan Panel):**
  - **Renk Paleti:** Koyu kurşuni lacivert zemin renklidir.
  - **Logotip:** En üstte beyaz dairesel UYDS ikonu ve yanında "UYDS Asistanı" ürün adı bulunur.
  - **Menü Başlığı:** "Gezinti" başlığı altında dikey sıralanmış 5 menü öğesi yer alır.
  - **Sohbet:** Aktif sekme durumundadır, mor-mavi renkli yuvarlatılmış vurgu kutusu ile seçilidir. Solunda konuşma balonu ikonu yer alır.
  - **Yönetici Onayı:** Solunda düzenleme/kalem ikonu olan sekme.
  - **Analitik Panel:** Solunda grafik ikonu olan sekme.
  - **Geçmiş:** Solunda saat/geçmiş ikonu olan sekme.
  - **Ayarlar:** Solunda çark/ayarlar ikonu olan sekme.
  - **Alt Kullanıcı Paneli:** Yan panelin en altında kullanıcı profil dairesi, "Sarah J." kullanıcı adı ve altında "Çıkış Yap" bağlantısı yer alır.
- **Sağ Ana Sohbet ve İçerik Alanı:**
  - **Üst Başlık Çubuğu:** "UYDS Asistanı | SSS Sohbet Botu" ana başlığı yer alır. Sağ üst köşede yeşil nokta ile "Aktif" durum göstergesi ve menü seçeneği bulunur.
  - **Eşik ve Uyarı Bandı:** Sohbet alanının hemen üzerinde yer alan gri çerçeveli kutu içerisinde sarı uyarı ikonu ile "EŞİK UYARISI - Aylık SSS Veri İşleme Eşiği: %88'e Ulaşıldı (Limit: %90). Lütfen Hemen İnceleyin." mesajı gösterilir. Bu alan veritabanı ve güven eşiği sınırlarının takibini sağlar.
  - **Sohbet Akış Alanı:**
    - **Kullanıcı Mesaj Balonu:** Sağ tarafa hizalanmış, koyu gri-mavi arka planlı mesaj kutusu ("1. Çeyrek katılım düzeltmesini nasıl işlerim?"). Altında "10:15" zaman damgası yer alır.
    - **Asistan Cevap Balonu:** Sol tarafa hizalanmış, dairesel UYDS logosu ile başlayan açık mavi-gri arka planlı yanıt kutusu. Yanıt içeriğinde numaralandırılmış adım adımlı açıklama yer alır ("1. 'Kayıtlar' menüsüne gidin...", "2. 'Düzeltmeler' seçeneğini belirleyin...", "İlgili dokümanlar aşağıda bağlantılanmıştır.").
    - **Kaynak Doküman Rozetleri:** Yanıtın alt kısmında yanıtın dayandığı resmi UYDS dokümanlarını gösteren iki buton yer alır: Mavi renkli `[SSS Genelgesi No 22-A]` rozeti (yanında "Görüntüle" bağlantısı) ve yeşil renkli `[Düzeltme Kılavuzu]` rozeti (yanında "Görüntüle" bağlantısı).
  - **Alt Mesaj Giriş Barı:**
    - En alt kısımda geniş, beyaz arka planlı ve gri çerçeveli metin yazma alanı bulunur ("Mesajınızı yazın...").
    - Giriş alanının sağ tarafında ek doküman ekleme ikonu (Ataş) ve mavi renkli "Gönder ->" butonu yer alır.

## 5. Detaylı Türkçe Proje Klasör ve Dosya Yapısı
```
HadesBot/
├── uygulama/
│   ├── __init__.py
│   ├── ana.py
│   ├── api/
│   │   ├── rotalar/
│   │   │   ├── arama.py
│   │   │   ├── geri_bildirim.py
│   │   │   ├── yonetici.py
│   │   │   ├── analitik.py
│   │   │   └── kimlik_dogrulama.py
│   │   └── bagimliliklar.py
│   ├── cekirdek/
│   │   ├── __init__.py
│   │   ├── konfigurasyon.py
│   │   ├── veritabani.py
│   │   ├── guvenlik.py
│   │   ├── istek_sinirlayici.py
│   │   ├── onbellek.py
│   │   └── gunlukleyici.py
│   ├── modeller/
│   │   ├── __init__.py
│   │   ├── veritabani_modelleri.py
│   │   └── semalar.py
│   ├── servisler/
│   │   ├── excel_yukleyici.py
│   │   ├── metin_parcalayici.py
│   │   ├── vektor_servisi.py
│   │   ├── arama_servisi.py
│   │   ├── hibrit_arama.py
│   │   ├── yeniden_siralayici.py
│   │   ├── deepseek_servisi.py
│   │   ├── akis_servisi.py
│   │   ├── oturum_hafizasi.py
│   │   └── akis_servisi.py
│   ├── statik/
│   │   ├── css/
│   │   │   └── stil.css
│   │   └── js/
│   │       └── uygulama.js
│   └── sablonlar/
│       ├── indeks.html
│       ├── yonetici.html
│       └── analitik.html
├── veriler/ (Kritik Kurumsal Veri ve Şartname Klasörü)
│   ├── UYDS_Akilli_SSS_Chatbot_Staj_Projesi.docx
│   ├── UYDS_SSS_Listesi.xlsx
│   ├── veri_deposu.db (SQLite Veritabanı - Docker Volume ile eşleşir)
│   ├── es_anlamlilar.json
│   └── gunlukler/ (Uygulama günlükleri)
├── testler/
│   ├── test_belge_ayiklayici.py
│   ├── test_arama_servisi.py
│   ├── test_guvenlik_bakimi.py
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── LICENSE
├── plan.md (Bu dosya - .gitignore ile korunur)
├── kurallar.md (.gitignore ile korunur)
└── hata_duzeltme_kaydi.md (.gitignore ile korunur)
```

## 6. Veritabanı ve Tablo Tasarımı (Türkçe Yapı)

### sss_kayitlari (Ana SSS Kayıtları Tablosu)
- **id:** INTEGER PRIMARY KEY AUTOINCREMENT
- **kategori:** TEXT
- **soru:** TEXT
- **cevap:** TEXT
- **kaynak_dokuman:** TEXT
- **surum_numarasi:** INTEGER (DEFAULT 1)
- **aktif_mi:** BOOLEAN (DEFAULT TRUE)
- **olusturulma_tarihi:** DATETIME

### sss_parcalari (Metin Parçaları Tablosu - Semantic Chunking)
- **id:** INTEGER PRIMARY KEY AUTOINCREMENT
- **sss_id:** INTEGER (FOREIGN KEY -> sss_kayitlari.id)
- **parca_metni:** TEXT
- **parca_sira_no:** INTEGER

### sss_fts (FTS5 Tam Metin Arama Tablosu)
- **rowid:** sss_kayitlari.id ile eşleşir
- **soru:** TEXT
- **cevap:** TEXT
- **kategori:** TEXT

### sss_vektorleri (Vektör Kayıtları Tablosu)
- **id:** INTEGER PRIMARY KEY AUTOINCREMENT
- **sss_id:** INTEGER (FOREIGN KEY -> sss_kayitlari.id)
- **parca_id:** INTEGER (FOREIGN KEY -> sss_parcalari.id)
- **vektor_verisi:** BLOB (Float32 dizisi binary saklama)
- **model_adi:** TEXT

### geri_bildirimler (Geri Bildirim Tablosu)
- **id:** INTEGER PRIMARY KEY AUTOINCREMENT
- **sss_id:** INTEGER (FOREIGN KEY -> sss_kayitlari.id)
- **kullanici_sorusu:** TEXT
- **verilen_cevap:** TEXT
- **puan:** INTEGER (1-5 skalası)
- **yorum:** TEXT
- **durum:** TEXT ('BEKLEMEDE', 'ONAYLANDI', 'REDDEDILDI')
- **tarih:** DATETIME

### kullanicilar (Kullanıcılar ve Rol Tablosu)
- **id:** INTEGER PRIMARY KEY AUTOINCREMENT
- **kullanici_adi:** TEXT UNIQUE
- **sifre_hash:** TEXT
- **rol:** TEXT ('KULLANICI', 'YONETICI')
- **aktif_mi:** BOOLEAN (DEFAULT TRUE)

### veri_surumleri (Veri İçe Aktarım Sürüm Takip Tablosu)
- **id:** INTEGER PRIMARY KEY AUTOINCREMENT
- **dosya_adi:** TEXT
- **surum_numarasi:** INTEGER
- **aktarilan_kayit_sayisi:** INTEGER
- **aktarim_tarihi:** DATETIME

### sistem_gunlukleri (Yapılandırılmış İnceleme Günlüğü)
- **id:** INTEGER PRIMARY KEY AUTOINCREMENT
- **kullanici_id:** INTEGER
- **islem_turu:** TEXT
- **detay:** TEXT
- **tarih:** DATETIME

## 7. Fazlara Bölünmüş Detaylı Geliştirme Haritası

### Faz 1: Ortam Kurulumu, Docker Altyapısı, Güvenlik ve Bağımlılık Yönetimi [TAMAMLANDI]

- **Adım 1.1: Dockerfile ve Docker Compose Hazırlığı**
  - Python 3.11-slim baz imajı seçimi ve konteyner içi çalışma dizininin (`/uygulama`) ayarlanması.
  - Non-root `uygulama_kullanicisi`, salt-okunur kök dosya sistemi, salt-okunur model bağlama noktası ve geçici dizinlerle güvenli çalışma.
  - Resmî PyTorch CPU paket indeksiyle CUDA bileşenlerini dışarıda bırakan ve katman önbelleğini kullanan küçük üretim imajı.
  - `docker-compose.yml` içinde `uyds_sohbet_botu_uygulamasi` servisinin tanımlanması, konfigürasyon portunun (8000) dışarıya açılması ve `./veriler:/uygulama/veriler` dizin birleştirmesinin yapılması.
  - `UYGULAMA_PORT` ortam değişkeni ile port yapılandırması.
  - Ortam profilleri için `.env.dev`, `.env.test`, `.env.prod` dosyalarının oluşturulması.

- **Adım 1.2: Bağımlılık Paketlerinin (requirements.txt) Belirlenmesi**
  - Web çerçevesi ve güvenlik: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `jinja2`, `PyJWT`, `bcrypt`, `slowapi`, `python-multipart`.
  - Veri ve Excel işleme: `pandas`, `openpyxl`.
  - Veritabanı ve Arama: `sqlite3` (dahili kütüphane), `numpy`.
  - Yapay Zeka ve Embedding: `sentence-transformers`, `torch` (CPU sürümü), `httpx` (DeepSeek API için).
  - Üretim bağımlılıklarının sabit sürümlerle kurulması, güncel güvenlik düzeltmelerine yükseltilmesi ve bilinen açık taramasından geçirilmesi.

- **Adım 1.3: Konfigürasyon ve Ortam Değişkenleri Yönetimi (`uygulama/cekirdek/konfigurasyon.py`)**
  - `Pydantic-Settings` kullanılarak ortam değişkenlerinin güvenli okunması.
  - `DEEPSEEK_API_ANAHTARI`, `VERITABANI_YOLU`, `VERITABANI_SIFRELEME_ANAHTARI`, `GUVEN_ESIGI`, `VEKTOR_MODEL_ADI`, `JWT_GIZLI_ANAHTARI`, `JWT_ALGORITMASI`, `JWT_OMRU_DAKIKA`, `VARSAYILAN_YONETICI_SIFRESI`, `ISTEK_SINIRI`, `ISTEK_PENCERESI_SANIYE`, `UYGULAMA_PORT` parametrelerinin tanımlanması.
  - `LOG_SEVIYESI` parametresi ile DEBUG/INFO/WARNING/ERROR seviye kontrolü.

- **Adım 1.4: Güvenlik, Yetkilendirme ve İstek Sınırlama Altyapısı (`uygulama/cekirdek/guvenlik.py` & `istek_sinirlayici.py`)**
  - Rol Tabanlı Erişim Kontrolü (RBAC) ile Kullanıcı ve Yönetici oturum yönetiminin kurulması.
  - JWT token oluşturma, çözme, bcrypt şifre hash'leme.
  - `mevcut_kullaniciyi_al` bağımlılığında veritabanı varlık ve aktiflik kontrolü.
  - FastAPI middleware seviyesinde IP bazlı İstek Sınırlama (Rate Limiting) mekanizmasının entegrasyonu.

- **Adım 1.5: Yapılandırılmış Günlükleme Altyapısı (`uygulama/cekirdek/gunlukleyici.py`)**
  - JSON formatında yapılandırılmış loglama.
  - Konsol ve dosya (RotatingFileHandler, 10MB/5 yedek) çıktısı.
  - Dosya loglama başarısız olursa konsol loglama devam eder.
  - `LOG_SEVIYESI` ile dinamik seviye kontrolü.

- **Adım 1.6: FastAPI Ana Uygulama Başlangıcı (`uygulama/ana.py`)**
  - Lifespan event'lerinde veritabanı tablolarının otomatik oluşturulması.
  - Varsayılan yönetici hesabının `VARSAYILAN_YONETICI_SIFRESI` ortam değişkeninden alınan güçlü parola ile `INSERT OR IGNORE` kullanılarak oluşturulması.
  - `GET /api/saglik` sağlık kontrolü uç noktası.
  - Jinja2 şablon ve statik dosya mounting.
  - Başlatma hatalarının try-except ile yakalanması ve loglanması.

- **Adım 1.7: HTTP Güvenlik Başlıkları Middleware'i**
  - `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`, `Content-Security-Policy`, `Strict-Transport-Security` başlıkları.
  - Güvenli tarayıcı politikaları için güvenlik başlıkları middleware'i.

- **Adım 1.8: CORS Politikası**
  - İzin verilen origin'lerin beyaz liste ile sınırlanması.
  - `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods` başlıklarının yapılandırılması.

- **Adım 1.9: Brute Force Koruması**
  - Başarısız giriş denemelerinde hesap kilitleme (5 deneme, 15 dakika kilit).
  - IP bazlı giriş denemesi sınırlaması.
  - Kullanıcı ve IP sayaçları SQLite üzerinde merkezi ve çoklu süreç uyumlu olarak tamamlandı; kimlik doğrulama uç noktasına bağlanması Faz 7 Adım 7.5 kapsamındadır.

- **Adım 1.10: Docker Healthcheck**
  - `/api/saglik` liveness ve `/api/hazirlik` veritabanı/FTS readiness uç noktalarının ayrılması.
  - Uygulama servisinde readiness healthcheck kullanılması, HTTP sunmayan yedekleyici servisinin healthcheck kapsamından ayrılması.
  - Konteynerlerde `no-new-privileges`, capability kaldırma, PID sınırı ve kontrollü kapanış süresi.

- **Adım 1.11: Yedekleme ve Geri Yükleme Stratejisi**
  - `veriler/` dizini için otomatik yedekleme betiği.
  - Veritabanı dump/restore komutları.
  - Docker Compose yedekleyici servisi, yapılandırılabilir yedekleme aralığı ve saklama politikası.
  - Her yedek için SHA-256, boyut, zaman ve veritabanı sayaçlarını içeren atomik manifest.
  - Geri yükleme öncesinde manifest bütünlük doğrulaması ve düz metin SQLite yedeklerinde gerçek açılabilirlik denetimi.
  - SQLite bağlantıları ve yedekleme için paylaşımlı, şifreleme, şifre çözme ve geri yükleme için özel süreçler arası dosya kilidi.
  - Uygulama ile yedekleyicinin aynı `VERITABANI_YOLU` ve `ES_ANLAMLILAR_YOLU` yapılandırmasını kullanması; eksik veritabanında sessizce boş yedek üretmek yerine işlemin hata vermesi.

- **Adım 1.12: Kaynak ve Limit Yönetimi**
  - `MESAJ_MAKS_KARAKTER` ortam değişkeni ile kullanıcı mesajı başına maksimum karakter sınırı (varsayılan: 2000).
  - `DEEPSEEK_MAKS_TOKEN` ortam değişkeni ile DeepSeek API'ye gönderilecek maksimum token limiti (varsayılan: 4096).
  - `GUNLUK_MESAJ_KOTASI` ortam değişkeni ile kullanıcı başına günlük mesaj kotası (varsayılan: 500).
  - `OTURUM_MAKS_MESAJ` ortam değişkeni ile oturum başına maksimum mesaj sayısı (varsayılan: 50).
  - `ISTEK_GOVDE_MAKS_BOYUT` ortam değişkeni ile request body maksimum boyutu, DOS koruması (varsayılan: 1MB).
  - `DOSYA_YUKLEME_MAKS_BOYUT` ortam değişkeni ile Excel dosya yükleme boyut sınırı (varsayılan: 50MB).
  - `konfigurasyon.py` içinde tüm limit parametrelerinin tanımlanması.
  - `.env.example` ve `docker-compose.yml` environment listesine yeni değişkenlerin eklenmesi.
  - Genel istek gövdesi ve Excel yükleme yolu için ASGI seviyesinde boyut denetimi.

### Faz 2: SQLite Veritabanı, FTS5, Veri Modelleri ve Sürüm Kontrolü [TAMAMLANDI]

- **Adım 2.1: Veritabanı Bağlantı Altyapısı (`uygulama/cekirdek/veritabani.py`)**
  - SQLite veritabanı bağlantısı ve bağlam yöneticisinin (`baglam_yoneticisi`) oluşturulması.
  - Bağlantı açılışında WAL (Write-Ahead Logging) modunun ve foreign key desteğinin aktif edilmesi.
  - FTS5 Python built-in desteği kullanılıyor, harici uzantı yükleme (`enable_load_extension`) kaldırıldı (güvenlik).

- **Adım 2.2: Pydantic ve ORM/Tablo Şemalarının Oluşturulması**
  - `uygulama/modeller/veritabani_modelleri.py` içinde 12 normal tablo ve `sss_fts` sanal tablosunun SQL sorgularının tanımlanması.
  - `uygulama/modeller/semalar.py` içinde Pydantic arama isteği, arama yanıtı, geri bildirim (1-5 puan), analitik veriler ve yönetici onay modellerinin yazılması.
  - Durum, puan ve boolean alanları için CHECK veya doğrulama tetikleyicileri.
  - Sürüm, parça, vektör, alternatif soru ve oturum erişim yolları için indeksler.

- **Adım 2.3: SQLite FTS5 Sanal Tablosu ve Otomatik Tetikleyicilerin Kurulumu**
  - `sss_fts` sanal tablosunun `USING fts5(soru, cevap, kategori)` yapısında kurulması (standart yapı, external content kullanılmıyor).
  - `sss_kayitlari` tablosuna INSERT/UPDATE/DELETE işlemlerinde `sss_fts` tablosunu otomatik güncelleyen 3 SQLite tetikleyicisinin yazılması.

- **Adım 2.4: Bellek İçi Önbellekleme Altyapısı (`uygulama/cekirdek/onbellek.py`)**
  - Sık sorulan soruların arama sonuçlarını ve vektör yanıtlarını bellekte tutacak LRU Önbellek mekanizmasının (`functools.lru_cache`) kurulması.

- **Adım 2.5: Hassas Veri Maskeleme**
  - Loglarda şifre, API anahtarı, JWT token gibi hassas verilerin maskelenmesi.
  - `gunlukleyici` formatlayıcısına hassas veri filtresi eklenmesi.

- **Adım 2.6: Veritabanı Şifreleme**
  - SQLite veritabanının temiz kapanışta AES-256-GCM ile doğrulanmış ve atomik biçimde şifrelenmesi.
  - WAL checkpoint ve bütünlük denetimi sonrasında düz metin veritabanı ile yan dosyaların kaldırılması.
  - Bağımsız `VERITABANI_SIFRELEME_ANAHTARI` değerinin `.env` üzerinden zorunlu ve güvenli yönetimi.

### Faz 3: Excel İçe Aktarma, Metin Parçalama, Sürümleme ve Dosya Güvenliği [TAMAMLANDI]
- **Adım 3.1: Excel Dosyası Doğrulama ve Okuma (`uygulama/servisler/excel_yukleyici.py`)**
  - Pandas kullanarak `veriler/UYDS_SSS_Listesi.xlsx` dosyasının okunması.
  - Sütun başlıklarının (Kategori, Soru, Cevap, Kaynak Doküman) varlığının ve veri tiplerinin doğrulanması.
- **Adım 3.2: Otomatik Veri Sürümleme ve Değişiklik Günlüğü (Audit Logging)**
  - Her kayıt için SHA-256 içerik özeti ile değişmeyen kayıt kimliklerinin ve parçalarının korunması.
  - Yeni veya değişen kayıtların eklenmesi, kaldırılan kayıtların arşivlenmesi.
  - `veri_surumu_kayitlari` ile her veri sürümünün tam kayıt üyeliği ve kaynak konumu anlık görüntüsünün saklanması.
  - Excel çalışma sayfası ve satır numarası ile kaynak izlenebilirliği.
  - Süreçler arası `BEGIN IMMEDIATE` ile tekil aktarım ve benzersiz dosya özeti koruması.
  - Tekil mantıksal anahtarlarda `onceki_kayit_id`, revizyon numarası ve değişen alan listesiyle sürüm zinciri.
  - Bilgi tabanını değiştirmeyen kuru çalışma ile eklenecek, güncellenecek, korunacak ve arşivlenecek kayıt raporu.
  - Geçmiş sürüm üyeliğini yeni bir denetimli sürüm olarak yeniden etkinleştiren geri alma işlemi.
- **Adım 3.3: Anlamsal Metin Parçalama (Semantic Chunking - `uygulama/servisler/metin_parcalayici.py`)**
  - Uzun SSS metinlerinin anlam bütünlüğü bozulmadan paragraflara ve mantıksal parçalara bölünmesi, `sss_parcalari` tablosuna işlenmesi.
- **Adım 3.4: Excel Dosya Güvenlik Taraması (Güvenlik)**
  - Yüklenen Excel dosyasının MIME tipi doğrulaması (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`).
  - Dosya boyut sınırı (maksimum 50MB).
  - Makro içeren `.xlsm` dosyalarının reddedilmesi.
  - Zararlı içerik ve formül enjeksiyonu denetimi.

- **Adım 3.5: Veri Modeli Genişletmesi - Şartname Uyumu (`uygulama/modeller/veritabani_modelleri.py` güncelleme)**
  - `sss_kayitlari` tablosuna 6 yeni alan: `harici_kod`, `modul`, `kullanici_rolu`, `arama_metni`, `durum` (DEFAULT 'aktif'), `icerik_surumu` (DEFAULT 1).
  - `alternatif_sorular` tablosunun oluşturulması (sss_id FK, soru, vektor_verisi, kaynak, durum).
  - `asistan_sorgulari` tablosunun oluşturulması (oturum_id, kullanici_sorusu, yeniden_yazilmis_soru, cevap_metni, guven_skoru, cevaplandi_mi).
  - Mevcut `sss_fts` tetikleyicilerinin yeni alanlar için güncellenmesi.
  - `kaynak_sayfa`, `kaynak_satir`, `kayit_ozeti`, `son_gorulen_surum` ve `aktarim_surumu_id` alanlarının eklenmesi.
  - `kayit_anahtari`, `onceki_kayit_id`, `revizyon_numarasi`, `degisiklik_turu` ve `degisen_alanlar` alanlarının eklenmesi.

### Faz 4: Anlamsal Vektör Gömmeleri ve Kurum İçi Terim Haritası [TAMAMLANDI]
- **Adım 4.1: Yerel Türkçe Vektör Modelinin Kurulumu (`uygulama/servisler/vektor_servisi.py`)**
  - Türkçe anlamsal aramada yüksek başarım gösteren yerel modelin (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` veya dengi) yüklenmesi.
  - Modelin tamamen yerel modda (çevrimdışı) çalıştırılması ve dış ağa vektör göndermemesinin sağlanması.
  - Model deposunun olay öncesi sabit revizyona kilitlenmesi; yalnızca izinli JSON, tokenizer ve `safetensors` dosyalarının indirilmesi.
  - Resmî LFS SHA-256, dosya boyutu, yerel güvenlik manifesti, mimari ve tokenizer allowlist doğrulaması.
- **Adım 4.2: Vektör Üretimi, Binary Dönüştürme ve SQLite Kaydı**
  - Her bir metin parçası için 384 boyutlu vektör gömülmesinin üretilmesi, Numpy `tobytes()` ile `Float32` binary dönüştürmesi yapılarak saklanması.
  - Metin özetiyle artımlı üretim, parça-model benzersizliği, pasif kayıt temizliği ve bozuk BLOB reddi.
- **Adım 4.3: Eş Anlamlı Kelime ve Kurum İçi Terim Haritası (`veriler/es_anlamlilar.json`)**
  - UYDS terimleri, kurum içi kısaltmalar ve eş anlamlı kelimeler için özel arama haritasının tanımlanması.
  - Sürüm kontrolünde yalnızca kurumsal veri içermeyen `es_anlamlilar.example.json` şablonunun tutulması; gerçek kurum haritası eksik olduğunda açık hata verilmesi.
  - Dosya boyutu, JSON şeması, terim uzunluğu, kontrol karakteri ve çakışan terim grubu doğrulaması.

### Faz 5: Hibrit Arama, Sorgu Genişletme ve Yeniden Sıralama (Reranking) [TAMAMLANDI]
- **Adım 5.1: Sorgu Genişletme ve SQLite FTS5 Kelime Araması**
  - Kullanıcı sorusundaki terimlerin eş anlamlı kelime haritası ile zenginleştirilmesi (Query Expansion).
  - `sss_fts` tablosunda BM25 algoritması ile arama yapılması ve ilk N adayın çekilmesi.
  - Soru, cevap, kategori, harici kod, modül ve birleşik arama metni BM25 ağırlıklarının ortam değişkenleriyle ayrı ayrı ayarlanması.
- **Adım 5.2: Vektör Benzerliği Arama Servisi**
  - Kullanıcı sorusunun anlık vektör gömülmesinin üretilmesi ve SQLite'taki vektörler ile Kosine Benzerliği hesaplaması yapılması.
- **Adım 5.3: Reciprocal Rank Fusion Skor Harmanlama Algoritması**
  - Kelime arama sıralaması ile Vektör anlamsal arama sıralamasının RRF formülü (`RRF_Skoru = 1 / (60 + Sira)`) ile harmanlanması.
- **Adım 5.4: Cross-Encoder ile Yeniden Sıralama Servisi (`uygulama/servisler/yeniden_siralayici.py`) — Güvenli entegrasyon tamamlandı**
  - `YenidenSiralayiciProtokolu`, `CrossEncoderYenidenSiralayici` ve `AramaServisi` bağlantısı tamamlandı.
  - `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` adayı sabit commit, izinli dosya listesi, resmî `safetensors` SHA-256, yerel manifest, mimari ve tokenizer doğrulamasıyla hazırlandı.
  - Çalışma zamanı yalnızca yerel ve çevrimdışı yüklemeye izin verir; uzaktan kod kapalıdır ve model hatasında mevcut RRF sırası korunur.
  - Özellik varsayılan olarak kapalıdır. Üretim aktivasyonu, p50/p95, tepe bellek, doğruluk ve açık/kapalı karşılaştırması Faz 10 kabul çalışmalarında tamamlanacaktır.

### Faz 6: DeepSeek API Entegrasyonu, Akışlı Yanıt ve Oturum Hafızası [TAMAMLANDI]
- **Adım 6.1: DeepSeek API İstemcisi (`uygulama/servisler/deepseek_servisi.py`)**
  - `httpx` ile HTTPS DeepSeek Chat Completions bağlantısı ve yalnızca geçici hatalarda, ilk parça aktarılmadan önce üstel yeniden deneme tamamlandı.
  - API anahtarı `konfigurasyon.DEEPSEEK_API_ANAHTARI` üzerinden okunuyor; boş ve örnek anahtarlar çağrıdan önce reddediliyor.
  - Model, uç nokta, zaman aşımı, yeniden deneme, kaynak sayısı ve kaynak karakter bütçesi ortam değişkenleriyle sınırlandırıldı.
  - Kullanıcının model tercihi doğrultusunda varsayılan model `deepseek-v4-pro` olarak sabitlendi.
  - Kaynak içindeki olası talimatları veri kabul eden, dış bilgi ve tahmin kullanımını yasaklayan kaynak kontrollü sistem istemi eklendi.
- **Adım 6.2: Güven Eşiği ve Bilinmeyen Soru Reddetme Mantığı**
  - RRF skorunun güven puanı olmadığı ayrıştırıldı; Faz 5 vektör kosinüs benzerliği arama adayına taşındı.
  - En iyi gerçek kosinüs benzerliği güven eşiği (0.70) altındaysa API çağrısı yapılmadan standart "İlgili UYDS kaynaklarında bu soruya ilişkin yeterli bilgi bulunamamıştır" yanıtı dönülüyor.
  - Yalnızca FTS ile bulunan ve vektör güven skoru bulunmayan sonuçlar güvenli biçimde reddediliyor.
- **Adım 6.3: Canlı Akışlı Yanıt Üretimi (Server-Sent Events - `uygulama/servisler/akis_servisi.py`)**
  - DeepSeek yanıtlarını `meta`, `parca`, `tamamlandi` ve `hata` olaylarına dönüştüren SSE servis mimarisi tamamlandı.
  - SSE verileri JSON ile kodlanarak satır ve olay enjeksiyonuna karşı korundu.
  - HTTP StreamingResponse rotası Faz 7 API katmanı kapsamında bağlanacaktır.
- **Adım 6.4: Oturum Bağlam Hafızası (`uygulama/servisler/oturum_hafizasi.py`)**
  - Kullanıcının takip sorularında önceki kullanıcı ve asistan mesajlarını sıralı taşıyan bellek içi oturum yönetimi tamamlandı.
  - TTL, oturum başına mesaj sınırı, toplam oturum sınırı, LRU tahliyesi ve oturum kimliği doğrulaması eklendi.
  - Oturum içeriği diske veya veritabanına kalıcı olarak yazılmıyor.
  - Faz 6 için 21 yeni ve regresyon testi eklendi; Docker Python 3.11 ortamında toplam 61 test geçti.
  - Canlı `deepseek-v4-pro` bağlantısı sentetik soru ve kaynakla doğrulandı; gerçek UYDS içeriği açık dış veri paylaşım onayı olmadan sağlayıcıya gönderilmedi.

### Faz 7: FastAPI Uç Noktaları, İş Mantığı Servisleri ve API Güvenliği — Tamamlandı
- **Adım 7.1: Arama ve Akışlı Yanıt Uç Noktası (`/api/v1/arama`)**
  - POST ve SSE akış isteklerini işleyen arama uç noktası.
  - Oturum kimliği istemciden güvenilir sahiplik kanıtı olarak kabul edilmeyecek; sunucunun ürettiği tahmin edilemez kimlik JWT `sub` değeriyle bağlanacaktır.
  - Başka kullanıcıya ait oturum kimliğiyle geçmiş okuma veya yazma girişimleri reddedilecek ve kullanıcılar arası yalıtım test edilecektir.
  - Düşük güvenli sonuçlarda kaynak metni ve kaynak kimlikleri istemciye gönderilmeyecektir.
- **Adım 7.2: Kullanıcı Geri Bildirim Uç Noktaları (`/api/v1/geri-bildirim`)**
  - 1-5 puan ve kullanıcı yorumlarını kaydeden uç nokta.
- **Adım 7.3: Yönetici Onay ve Veri Yönetimi Uç Noktaları (`/api/v1/yonetici`)**
  - Bekleyen bildirimleri onaylama, veritabanını yeniden indeksleme uç noktaları.
- **Adım 7.4: Yönetici Analitik Uç Noktası (`/api/v1/analitik`)**
  - Sistem istatistiklerini ve grafik verilerini sağlayan uç nokta.
- **Adım 7.5: Kimlik Doğrulama Uç Noktası (`/api/v1/kimlik-dogrulama`)**
  - Giriş yapma ve JWT token alma uç noktası.
- **Adım 7.6: Input Validasyon ve Sanitizasyon Katmanı (Güvenlik)**
  - API girdileri Pydantic şemalarıyla tür, uzunluk, biçim ve izinli değer denetiminden geçirilecektir.
  - API katmanında HTML entity encoding yapılmayacak; bağlama uygun çıktı kodlama Faz 9 arayüzünde uygulanacaktır.
  - SQL injection koruması (parametreli sorgular zorunlu).
  - Dosya ve komut alanlarında izin listesi, kanonik yol doğrulaması ve shell kullanmayan çağrılar zorunlu olacaktır.
  - Kullanıcı sorularında maksimum karakter ve kontrol karakteri sınırı uygulanacak; anlam taşıyan özel karakterler körlemesine silinmeyecektir.
- **Adım 7.7: Hata Yönetimi ve Bilgi Sızdırmazlığı (Güvenlik)**
  - Stack trace'lerin istemciye dönülmemesi, özel hata sayfaları.
  - FastAPI exception handler'lar ile merkezi hata yönetimi.
  - DEBUG modunun `.env` kontrollü olması, production'da kapalı olması.
- **Adım 7.8: JWT Token Güvenliği (Güvenlik)**
  - Refresh token mekanizması (kısa ömürlü access token, uzun ömürlü refresh token).
  - Refresh tokenlar veritabanında düz metin yerine güçlü özetleriyle, `jti`, kullanıcı ve token ailesi bilgisiyle saklanacaktır.
  - Çıkışta token ailesi geçersiz kılınacak; her yenilemede rotasyon yapılacak ve eski tokenın tekrar kullanımı tüm aileyi iptal edecektir.
  - `kid` (Key ID) ile etkin ve önceki doğrulama anahtarlarını destekleyen anahtar rotasyonu uygulanacaktır.
- **Adım 7.9: API Anahtarı Rotasyonu ve Yönetimi (Güvenlik)**
  - DeepSeek API anahtarının güvenli saklanması ve düzenli rotasyonu.
  - Anahtar değişiminde uygulamanın yeniden başlatılmadan yeni anahtarı kullanabilmesi, salt okunur bağlı secret dosyası veya kurum secret sağlayıcısı üzerinden uygulanacaktır.
  - Her istekte `.env` dosyasını yeniden okuyan bir mekanizma kullanılmayacaktır.
- **Adım 7.10: İstek İmzalama - Request Signing (Güvenlik)**
  - Kritik yönetici endpoint'leri için HMAC imza doğrulaması.
  - İstek bütünlüğü ve replay attack koruması (timestamp + nonce).
- **Adım 7.11: Bağımlılık Güvenlik Taraması (Güvenlik)**
  - `pip-audit` veya `safety` ile bağımlılık zafiyet taraması.
  - Docker imaj taraması (`docker scan`, `trivy`).
  - Otomatik bağımlılık güncelleme politikası.
- **Adım 7.12: SSE Kaynak ve İptal Güvenliği**
  - İstemci bağlantısı kapandığında arama ve DeepSeek akışı iptal edilerek kaynaklar serbest bırakılacaktır.
  - Akış süresi, yanıt karakteri, eşzamanlı akış ve kullanıcı kotası sınırları API katmanında birlikte uygulanacaktır.
  - Tamamlanmadan kesilen yanıtlar oturum geçmişine kaydedilmeyecek ve yeniden denemeyle yinelenmeyecektir.
  - Faz 7 kabul doğrulamasında 77 yerel ve 77 Docker testi geçti; Ruff, Bandit, `pip check` ve `pip-audit` temiz sonuçlandı.
  - Güncel üretim imajının ağ erişimi kapalı Trivy v0.70.0 taramasında düzeltmesi bulunan kritik veya yüksek zafiyet bulunmadı.
  - Haftalık Python, Docker ve GitHub Actions bağımlılık güncelleme politikası Dependabot yapılandırmasıyla eklendi.
  - Her push ve pull request için 101 test, Ruff, Bandit, `pip-audit`, sır kalıbı ve Docker build denetimi çalıştıran CI iş akışı eklendi.
  - Süresi dolmuş refresh aileleri, erişim karaliste kayıtları ve yönetici nonce kayıtları uygulama başlangıcında ve yapılandırılabilir aralıklarla aile bütünlüğü korunarak temizleniyor.
  - Standart dağıtım değişkenlerinde çoklu worker yapılandırması bellek içi oturum yalıtımını korumak için başlangıçta reddediliyor.
  - OpenAPI rota sözleşmesi, kritik HMAC başlıkları, JWT önceki anahtar penceresi ve DeepSeek secret dosyası canlı rotasyonu regresyon testleriyle korunuyor.

### Faz 8: Geri Bildirim Döngüsü, Yönetici Onayı ve Analitik Takip [TAMAMLANDI]
- **Adım 8.1: Kullanıcı Oy/Yorum Kaydetme Akışı**
  - Yanıt kutusu altı oylama sistemi ve `BEKLEMEDE` statülü kayıtlar.
- **Adım 8.2: Yönetici İnceleme, Onay ve Yeniden İndeksleme**
  - Yöneticinin geri bildirimi onaylaması veya reddetmesi, kullanıcının önerdiği doğru SSS kaydını değiştirebilmesi ve onaylanan kullanıcı sorusunun mevcut doğru SSS kaydına alternatif ifade olarak bağlanması.
  - Yeniden indekslemede ana SSS vektörleriyle birlikte onaylanmış alternatif soru vektörlerinin model kimliği ve bütünlük metadata alanlarıyla yenilenmesi.
- **Adım 8.3: Yapılandırılmış İnceleme Günlükleri (Structured Logging - `uygulama/cekirdek/gunlukleyici.py`)**
  - JSON formatında loglama ve günlük rotasyonu.
  - Cevapsız veya güven eşiği altındaki sorguların yönetici yetkisiyle sayfalı listelenmesi.
- **Adım 8.4: Alternatif Soru Öğrenme Mekanizması (Şartname FR-09)**
  - Kullanıcının yararsız olarak işaretlediği cevaplar için doğru SSS kaydının yönetici tarafından seçilmesi.
  - Yönetici onayı ile kullanıcı sorusunun `alternatif_sorular` tablosuna eklenmesi.
  - Alternatif sorunun embedding vektörünün üretilmesi.
  - Alternatif soru model kimliği, vektör boyutu ve metin özeti doğrulandıktan sonra yapılandırılabilir benzerlik eşiğiyle taranması.
  - Alternatif soru sırasının RRF katkısına dönüştürülmesi, ana arama sonuçlarıyla SSS kimliği üzerinden tekilleştirilmesi ve ortak aday sınırının uygulanması.
  - Yönetici onayı olmadan hiçbir geri bildirimin aktif bilgi tabanına dahil edilmemesi.
- **Adım 8.5: Yapay Zeka Çıktısı Yararlılık Ölçümü ("Bu çıktı yararlı oldu mu?")**
  - Her AI yanıtının altına doğrudan kullanıcıya sorulacak "Bu çıktı yararlı oldu mu? (Evet/Hayır)" şeklinde pratik bir geri bildirim butonunun eklenmesi.
  - Alınan bu hızlı geri bildirimlerin doğrudan analitik paneline aktarılarak modelin ve verilen kaynakların başarı oranının ölçülmesi.
  - Olumsuz yanıtlarda kullanıcıdan kısa bir düzeltme metni veya neden istenerek alternatif soru havuzunun doğrudan beslenmesi.

### Faz 9: Kurumsal Kurşuni Ön Yüz Geliştirme [TAMAMLANDI]
- **Adım 9.1: HTML5/CSS3 Temel Şablonu ve Kurumsal Kurşuni Tema Stilleri**
  - `uygulama/sablonlar/indeks.html`, `yonetici.html`, `analitik.html` şablonları.
  - `uygulama/statik/css/stil.css` kurşuni gri, koyu lacivert renk paleti.
  - Ortak `temel.html` kabuğu ve mutlak uygulama dizinine bağlı güvenli `StaticFiles` sunumu.
- **Adım 9.2: Sol Navigasyon Menüsü ve Kullanıcı Paneli Bileşeni**
  - Yan panel yapısı, logo, Sohbet/Yönetici/Analitik/Geçmiş/Ayarlar sekmeleri ve profil alanı.
  - Yönetici menülerinin API tarafından dönen `YONETICI` rolüyle görünürlük denetimi.
  - Mobil menü, klavye odağı, atlama bağlantısı ve azaltılmış hareket desteği.
- **Adım 9.3: Eşik ve Uyarı Bandı Bileşeni**
  - Dinamik sistem durum ve güven eşik uyarı bandı.
  - Liveness ve readiness rotalarıyla canlı sistem durum denetimi.
- **Adım 9.4: Canlı Akışlı Sohbet, Kaynak Rozetleri ve Giriş Barı Bileşeni**
  - `uygulama/statik/js/uygulama.js` ile SSE canlı yazı efekti ve kaynak rozetleri.
  - JWT giriş, yenileme ve çıkış yaşam döngüsü; sekme oturumuna bağlı belirteç saklama.
  - `fetch` akışıyla `oturum`, `meta`, `parca`, `tamamlandi` ve `hata` SSE olay ayrıştırması.
  - Sunucu metinlerini HTML olarak yorumlamadan `textContent` ile güvenli DOM üretimi.
- **Adım 9.5: Yönetici Analitik Grafik Paneli Bileşeni**
  - En çok sorulan konular ve cevapsız kalan sorular analitik grafik panelleri.
  - Bekleyen geri bildirim, cevapsız sorgu, kategori dağılımı ve özet metriklerin canlı API bağlantısı.
  - Geri bildirim onay/red, doğru SSS seçimi, SSS arama/sayfalama, indeks yenileme, tam/artımlı belge senkronizasyonu ve e-posta raporu yönetici işlemleri arayüze bağlandı.
  - Belge sürümleri, parça istatistikleri, 30 günlük sorgu trendi, yetim kavramlar ve indirilebilir birleşik doküman raporu analitik ekranına eklendi.
  - Kritik tarayıcı işlemleri gizli anahtarı istemciye vermeyen, hedef yol ve gövdeye bağlı tek kullanımlı HMAC imza akışıyla korunur.
- **Adım 9.6: Ön Yüz Kabul Doğrulaması**
  - Üç sayfa ve statik dosya sunumu, CSP/güvenlik başlıkları ve XSS riskli DOM API'lerinin kullanılmaması regresyon testleriyle korunur.
  - İzole Uvicorn sürecinde gerçek tarayıcıyla masaüstü ve 390 piksel mobil kırılım, JWT yönetici girişi, panel veri yükleme ve konsol hatasızlığı doğrulandı.
  - Güncel tam paket 235 başarılı ve 1 isteğe bağlı atlanan test sonucuyla; Docker, gerçek tarayıcı, 390 piksel mobil kırılım ve konsol hatasızlığıyla doğrulandı.

### Faz 10: Test, Doğrulama, Güvenlik Testleri ve Dokümantasyon [ÖLÇÜM ALTYAPISI TAMAMLANDI, ALTIN VERİ SETİ BEKLİYOR]
- **Adım 10.1: Birim ve Entegrasyon Testleri (`testler/`)**
  - Pytest birim testleri ve FastAPI entegrasyon testleri.
- **Adım 10.2: Arama Başarımı ve Güven Eşiği Doğrulama Testleri**
  - Test soruları seti ile sistemin doğruluk oranının ve reddetme mantığının doğrulanması.
- **Adım 10.3: Dokümantasyon ve Kurulum Kılavuzları**
  - Docker üzerinde projeyi tek komutla (`docker-compose up --build`) ayağa kaldırma talimatlarının hazırlanması.
- **Adım 10.4: Sızma Testi - Penetrasyon Testi**
  - OWASP Top 10 kapsamında manuel ve otomatik güvenlik testleri.
  - SQL injection, XSS, CSRF, JWT manipulation, IDOR, rate limiting bypass testleri.
  - Test senaryoları ve bulguların `testler/` altında raporlanması.
- **Adım 10.5: Güvenlik Açığı Taraması**
  - Docker imaj taraması (`docker scan`, `trivy`).
  - Bağımlılık zafiyet taraması (`pip-audit`, `safety`).
  - Statik kod analizi (SAST) ile güvenlik açığı tespiti.
- **Adım 10.6: Başarı Metrikleri Doğrulama Testleri (Şartname Bölüm 14)**
  - Top-1 doğruluğu en az %80 ve Top-3 doğruluğu en az %92 hedeflerinin ölçülmesi.
  - Ortalama yanıt süresi ve bellek tüketimi (1GB altı) onayları.
  - Kaynaksız cevap oranının %0 olduğunun doğrulanması.
  - Bilinmeyen sorularda cevap vermeme başarısının en az %85 ölçümü.
  - Cevap üretiminde %100 kaynak gösterme denetimi.
  - Her yeterli güvenli canlı yanıtta en az bir geçerli `[Kaynak N]` etiketinin bulunması ve etiket numaralarının gönderilen kaynak aralığında kalması.
  - Geri bildirim sonrası başarı değişiminin raporlanması.
- **Adım 10.7: Yerel Embedding Yaşam Döngüsü ve Ölçek Geçişi**
  - Gizlilik, çevrimdışı çalışma, öngörülebilir maliyet ve sağlayıcı bağımsızlığı gerekçeleriyle yerel embedding mimarisi varsayılan yaklaşım olarak korunacaktır.
  - Mevcut `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` modeli başlangıç referansı olarak kullanılacak; model değişikliği yalnızca Türkçe karşılaştırma sonuçlarıyla doğrulanacaktır.
  - En az 50, hedef olarak 100 temsili Türkçe sorgudan oluşan; kolay, zor, eş anlamlı, yazım hatalı ve bilinmeyen soru sınıflarını içeren veri seti hazırlanacaktır.
  - Top-1, Top-3, MRR@10, nDCG@10, bilinmeyen sorgu reddi, p50/p95 gecikme, tepe bellek ve vektör dizini boyutu birlikte ölçülecektir.
  - Modelin 128 token sınırı gerçek tokenizer çıktısıyla denetlenecek; yalnızca karakter sayısına dayalı parçalama kabul edilmeyecektir.
  - Model kimliği, sabit revizyonu, dosya özeti, tokenizer sürümü, pooling yöntemi, vektör boyutu ve karşılaştırma sürümü kayıt altına alınacaktır.
  - Model, tokenizer, pooling veya vektör boyutu değiştiğinde tüm aktif içerik yeniden vektörlenecek; farklı embedding sürümleri aynı arama uzayında karıştırılmayacaktır.
  - Yeniden vektörleme yeni ve ayrı bir sürümde tamamlanacak, doğrulama sonrasında atomik olarak etkinleştirilecek ve önceki sürüme geri dönüş korunacaktır.
  - Cross-Encoder yalnızca doğruluk kazanımı gecikme ve bellek maliyetini karşıladığında üretimde etkinleştirilecektir.
  - SQLite tam tarama yaklaşımı mevcut veri ölçeğinde korunacak; yaklaşık 50.000-100.000 aktif parça, p95 gecikme hedefinin aşılması veya eşzamanlılık baskısı ölçek değerlendirmesini tetikleyecektir.
  - Ölçek değerlendirmesinde `pgvector` ve yerel `Qdrant`; kesin arama ve HNSW seçenekleriyle doğruluk, gecikme, bellek, yedekleme ve işletim maliyeti açısından karşılaştırılacaktır.
  - Yerel embedding kullanımının sistemi bütünüyle çevrimdışı yapmadığı belgelenmeye devam edecek; DeepSeek etkin olduğunda sorgu ve seçilen kaynak parçalarının dış sağlayıcıya gönderilebileceği açıkça belirtilecektir.
  - Karşılaştırma motoru yönetici yetkili, LLM çağırmayan ilk 10 arama sıralaması üzerinden Top-1, Top-3, MRR@10 ve nDCG@10; sohbet akışı üzerinden cevap vermeme, kaynak gösterme ve p50/p95 gecikme metriklerini üretir. HTML, JSON ve CSV raporları oluşturur ve kabul eşiği karşılanmadığında başarısız çıkış kodu döndürür.
  - Mevcut 25 senaryo davranış ve güvenlik etiketi taşır ancak uzman tarafından doğrulanmış beklenen SSS kimlikleri içermediği için arama doğruluğu kabulü tamamlanmış sayılmaz. En az 50 kurumsal veri sızdırmayan, uzman etiketli senaryo hazırlanıp aynı motorla ölçülmelidir.

### Faz 11: Veri Ambarı ve Çoklu Veri Kaynağı Entegrasyonu [ÇEKİRDEK TAMAMLANDI]
- Yerel PDF, DOCX, HTML ve XLSX kaynakları belge ayıklama, yapısal parçalama, yerel embedding, external-content FTS ve sürümlemeli depolama zincirinden geçirilir. Tam ve artımlı senkronizasyon, silinen belge pasifleştirme, sürüm saklama sınırı, karantina ve uygulama yaşam döngüsüne bağlı zamanlayıcı uygulanmıştır.
- Belge FTS ve vektör sonuçları mevcut SSS sonuçlarıyla RRF sıralamasında birleşir. Belge ve parça ACL filtresi LLM öncesinde uygulanır; tarih referanslı sorgular uygun eski sürümü seçer. Hafif kavram grafı arama skoruna sınırlı bonus verir ve analitik API ile yönetici panelinde izlenir.
- Kurumsal kimlik doğrulamalı SharePoint/Confluence bağlayıcıları ile Neo4j adaptörü mevcut veri ölçeğinde zorunlu değildir; bunlar ilgili dış sistem bilgileri ve ölçek eşiği sağlandığında uygulanacak ileri ölçek adımlarıdır.
- **Detaylı mimari kararlar ve vektör veritabanı geçiş tetikleyicileri için kök dizindeki `FAZ11_MIMARI_VIZYON.md` dokümanını inceleyiniz.**

### Faz 12: Veri Gizliliği ve Analitik Kayıt Yönetimi [TAMAMLANDI]
- **Adım 12.1: Otomatik Temizlik Politikası (Data Retention Policy)**
  - `asistan_sorgulari` tablosunun süresiz olarak büyümesini önlemek ve veritabanı performansını korumak için, 6 aydan eski analitik sorgu kayıtlarının her gece otomatik olarak silinmesini sağlayan periyodik bakım görevi (cron job) uygulandı (`uygulama/servisler/veri_temizligi.py`). `BEGIN IMMEDIATE` + partili silme (1000 kayıt/lot) ile SQLite kilitlenmeleri engellendi.
- **Adım 12.2: Hassas Veri Anonimleştirme (PII Masking)**
  - TC Kimlik, IBAN, telefon, kredi kartı ve e-posta için regex tabanlı PII maskeleme uygulandı (`uygulama/servisler/pii_maskeleyici.py`). Maskeleme, veritabanı yazımından hemen önce (arama/LLM sonrası) konumlandırılarak RAG doğruluğu korundu. Logger katmanında da çift katmanlı PII koruması eklendi (`gunlukleyici.py`).
- **Adım 12.3: Yönetici Paneline "Kullanıcı Sorularını Gizle" Özelliği**
  - `.env` üzerinden `KULLANICI_SORULARINI_GIZLE=true` yapılandırması ile yönetici panelinde soru metinleri `[GIZLI]` olarak maskelenir. API seviyesinde uygulanan filtre, frontend veya JWT değişikliği gerektirmez.

### Faz 13: Gelişmiş Kurumsal Yetenekler ve Hata Toleransı [TAMAMLANDI]
- **Adım 13.1: Arama Sonuçlarında Rol Bazlı Filtreleme (RBAC for Retrieval)**
  - Mevcut veritabanı şemasında bulunan `kullanici_rolu` alanı aktif arama mantığına (Hibrit Arama) entegre edilecektir. Bir kullanıcı soru sorduğunda, vektör ve FTS aramaları yalnızca o kullanıcının yetki seviyesine ('KULLANICI', 'YONETICI' vb.) uygun etiketlenmiş dokümanlar üzerinde çalışacak; böylece yetkisiz veri sızıntısı (bilgi ifşası) arama motoru seviyesinde engellenecektir.
- **Adım 13.2: Çevrimdışı / Yedekleme Modu (Offline Fallback)**
  - DeepSeek API bağlantısının koptuğu veya zaman aşımına uğradığı durumlarda sistemin 500 hatası verip kilitlenmesi yerine; arama servisinden dönen en yüksek skorlu 3 kaynağın, hiçbir AI yorumu katılmadan doğrudan kullanıcıya listelendiği "Yedekleme Modu" (Fallback) arayüzü ve API mantığı geliştirilecektir.
- **Adım 13.3: İşleme Dönük Butonlar (Intent Deep-Linking)**
  - Belirli kilit sorular ("Şifremi sıfırla", "Destek bileti aç") için basit bir Niyet (Intent) sınıflandırma mekanizması eklenecektir. Kullanıcının niyeti bu kilit işlemlerden biriyle eşleştiğinde, yapay zeka sadece metin üretmekle kalmayıp arayüzde doğrudan o işlemin sayfasına yönlendiren aksiyon butonları (Deep Link) oluşturacaktır.

### Faz 14: Otomatik E-posta Raporlama [TAMAMLANDI]
- **Adım 14.1: Haftalık İstatistik Raporu**
  - Toplam, cevaplanan ve cevapsız soru; bekleyen geri bildirim; ortalama güven skoru ve kategori dağılımı raporlanır.
- **Adım 14.2: Güvenli E-posta Teslimi**
  - HTML ve düz metin içerik, STARTTLS ve ortam değişkeni tabanlı SMTP yapılandırması kullanılır.
- **Adım 14.3: Zamanlama ve Yönetici İşlemi**
  - Rapor zamanlayıcıdan veya tek kullanımlı yönetici işlem imzasıyla korunan arayüz işleminden gönderilebilir; bloklayan SMTP çağrısı `asyncio.to_thread` ile uygulama olay döngüsünden ayrılır.

## 8. Proje Durumu ve Uygulama Notu

### Mevcut Durum (Son Güncelleme: 01.08.2026)
- **Faz 1:** Tamamlandı. Ortam profilleri, güvenli yapılandırma, rate limiting, güvenlik başlıkları, CORS, brute-force altyapısı, istek boyutu sınırı, healthcheck ve zamanlanabilir yedekleme/geri yükleme hazır.
- **Faz 2:** Tamamlandı. Bağlantı başına SQLite yönetimi, WAL/foreign key, FTS5 senkronizasyonu, tablolar, modeller, önbellek, hassas veri maskeleme ve AES-256-GCM disk şifreleme hazır.
- **Faz 3:** Tamamlandı. Standart ve kurumsal UYDS Excel şemalarının doğrulanması, güvenlik taraması, veri temizleme, mükerrer dosya engelleme, otomatik sürümleme, eski kayıtları arşivleme, denetim günlüğü ve anlam bütünlüğünü koruyan metin parçalama hazır.
- **Faz 4:** Tamamlandı. Sabit ve doğrulanan yerel MiniLM modeli, çevrimdışı 384 boyutlu Float32 vektör üretimi, artımlı güncelleme, model bütünlük manifesti ve kurum içi terim haritası hazır.
- **Faz 5:** Tamamlandı. Hibrit arama (alan ağırlıklı FTS5 BM25 + vektör kosinüs benzerliği + RRF + Türkçe sorgu genişletme) ile güvenli ve isteğe bağlı Cross-Encoder yeniden sıralama katmanı uygulandı ve 48 test ile doğrulandı. Arama sonucu genişletilmiş FTS sorgusunu, genişletilen terim sayısını ve kullanılan semantik grup sayısını ölçüm için taşır. Cross-Encoder sabit model revizyonu, resmî ağırlık özeti, yerel manifest, çevrimdışı yükleme ve RRF geri dönüşüyle korunur; üretim aktivasyonu en az 50 uzman etiketli Türkçe senaryonun doğruluk, p95 gecikme ve bellek ölçümünü geçmesini beklemektedir.
- **Faz 5 Docker ön kabulü:** Güncel imaj, uygulama ve yedekleyici servisleriyle başarıyla başlatıldı; canlılık, veritabanı/FTS hazırlık ve imaj içi sorgu genişletme duman testi geçti. Bir ısınma sonrası 20 yerel sorguda p50 46.609 ms ve p95 79.305 ms ölçüldü. Uzman etiketli temsili soru seti, tepe bellek ve Cross-Encoder açık/kapalı karşılaştırması Faz 10 arama kabulünün açık maddeleridir.
- **Faz 6:** Servis katmanı tamamlandı. Kaynak kontrollü DeepSeek istemcisi, güven eşiği kapısı, SSE olay üretimi, sınırlı oturum hafızası, üretim hedef alan adı izin listesi ve akış kaynak sınırları hazırdır. Canlı `deepseek-v4-pro` bağlantısı sentetik veriyle; kurum sahibinin açık onayı sonrasında gerçek UYDS bilgi tabanıyla da uçtan uca doğrulandı. Gerçek kaynaklı istekte `0,894982` güven skoru, 5 kaynak, 29 SSE parçası, 11,64 saniye ve `cevaplandi=true` sonucu ölçüldü. Faz 10 kabul testlerinde yüzde 100 kaynak gösterme oranı doğrulanmıştır.
- **Faz 7:** Tamamlandı. JWT erişim/refresh yaşam döngüsü, `kid` anahtar rotasyonu, token ailesi tekrar kullanım tespiti, kullanıcıya bağlı sunucu oturumları, kimlik doğrulamalı SSE arama, SSS, geri bildirim, yönetici ve analitik rotaları, HMAC istek imzası, nonce replay koruması, merkezi hata yönetimi, istek kimliği, süresi dolmuş güvenlik kaydı bakımı, tek-worker dağıtım koruması ve OpenAPI sözleşme denetimi uygulandı.
- **Faz 8:** Tamamlandı. Geri bildirim döngüsü, yönetici onayı, alternatif soru öğrenme mekanizması (FR-09), cevapsız sorgu yönetimi ve arama servisine alternatif soru entegrasyonu uygulandı. Kullanıcı doğru SSS kaydını `secili_sss_id` ile önerebiliyor; yönetici onay sırasında bu seçimi koruyabiliyor veya değiştirebiliyor. Onaylanan alternatif soru model kimliği, vektör boyutu ve metin özetiyle saklanıyor; yapılandırılabilir benzerlik eşiğinden sonra RRF kanalına katılıyor ve ana sonuçlarla SSS kimliği üzerinden tekilleştiriliyor. Mevcut veritabanları için geriye uyumlu sütun migrasyonu, alternatif soru yeniden vektörleme desteği ve yöneticiye özel sayfalı cevapsız sorgu rotası hazırdır. Faz 8 kapsamında 15 test eklendi.
- **Faz 9:** Tamamlandı. Sohbet, yönetici ve analitik sayfaları; responsive kurumsal tema, rol tabanlı navigasyon, JWT yaşam döngüsü, canlı SSE tüketimi, SSS kataloğu, geri bildirim karar akışı, indeks ve belge senkronizasyon yönetimi, işletim envanteri ve gelişmiş analitik paneller uygulandı. XSS riskli HTML ekleme API'leri kullanılmadı; kritik işlemler tek kullanımlı sunucu imzasıyla korunur ve gerçek tarayıcıda masaüstü ile mobil görünüm doğrulandı.
- **Yerel veri işletimi:** Yinelenen `.env` tanımları tekilleştirildi; etkin `prod` profili ve `veriler/veri_deposu.db` standart yolu doğrulandı. Açılabilir şifreli veritabanının bütünlük kontrolü tamamlandı ve `.env`, şifreli veritabanları, kaynak belgeler ile kurum içi terim haritası erişimi kısıtlı, Git dışında tutulan bir kurtarma yedeğine alındı. Gerçek Excel kaynağından 2.398 SSS, 4.075 parça ve 4.075 geçerli yerel vektör yeniden oluşturuldu. Gerçek şifreli veritabanıyla liveness, readiness, ön yüz, yönetici girişi, dış LLM kapalı sentetik SSE akışı ve kurum onaylı canlı DeepSeek akışı doğrulandı. Kapanışta düz metin veritabanı bırakılmadı.
- **Faz 10:** Ölçüm ve güvenlik altyapısı tamamlandı; arama kabulü bekliyor. Mevcut 25 senaryo davranış, ret ve güvenlik akışını doğrular. Değerlendirme motoru gerçek kaynak sıralamasından Top-1, Top-3, MRR@10, nDCG@10, kaynak gösterme, cevap vermeme ve p50/p95 gecikme metrikleri ile HTML, JSON ve CSV raporları üretir. Uzman doğrulamalı beklenen SSS kimliği taşıyan en az 50 senaryo henüz hazırlanmadığı için arama doğruluğu ve Cross-Encoder üretim aktivasyonu tamamlanmış kabul edilmez.
- **Faz 11:** Çekirdek tamamlandı. Yerel çoklu belge ETL, yapısal parça ve vektör üretimi, tam/artımlı zamanlanmış senkronizasyon, sürüm/silme yönetimi, karantina, external-content FTS, belge ACL, tarihsel sürüm araması, sınırlı graf bonusu ve genişletilmiş analitik paneli canlı RAG hattına bağlandı. Harici kurumsal bağlayıcılar ve Neo4j yalnızca ileri ölçek adımıdır.
- **Faz 12:** Tamamlandı. PII maskeleme (TC Kimlik, IBAN, telefon, kredi kartı, e-posta), otomatik veri temizliği (6 aydan eski sorgular), yönetici gizlilik kontrolü (KULLANICI_SORULARINI_GIZLE).
- **Faz 14:** Tamamlandı. Otomatik e-posta raporlama modülü (smtplib tabanlı, sıfır dış bağımlılık). Haftalık istatistik raporu (toplam soru, cevaplanan/cevapsız, bekleyen geri bildirim, ortalama güven skoru, en çok sorulan kategoriler). HTML + Plain Text çift format, STARTTLS desteği, asyncio.to_thread ile event-loop güvenli.
- **Faz 13:** Tamamlandı. RBAC rol bazlı arama filtreleme (FTS5 + vektör WHERE koşulu), DeepSeek API çökme durumunda çevrimdışı yedekleme modu (`yedek` SSE olayı), niyet sınıflandırma ve aksiyon butonları (`niyet_siniflandirici.py` + `eylem` SSE olayı). Niyet motoru, gelecekteki kimlik yönetimi rotaları erkenden uygulanmadan, kurumun gerçek hedefleri yapılandırılana kadar varsayılan kapalı ve hızlı hata korumalıdır. Normal kullanıcı ifadelerini varsayılan güven eşiğinde yakalayan skor hesabı ve güvensiz hedef reddi uygulanmıştır.
- **Kod Denetimi:** 34 tur denetim ve iyileştirme tamamlandı. Güncel kaynakta bekleyen doğrulanmış kritik veya yüksek kod hatası bulunmamaktadır. 235 başarılı ve 1 isteğe bağlı atlanan test; kimlik doğrulama, SSE tamponlama, üretim dokümantasyon sınırı, niyet yapılandırma güvenliği, hibrit SSS ve belge araması, Cross-Encoder, belge ACL, tarihsel sürüm seçimi, yönetici işlem imzası, SSS katalog araması, gelişmiş analitik, belge senkronizasyonu, karantina, dış içerikli FTS geçişi, ön yüz HTML enjeksiyon koruması ve karşılaştırma metrik hesaplarını doğrulamaktadır. Detaylar `hata_duzeltme_kaydi.md` dosyasındadır.

### Tamamlanan Dosyalar
- `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `.gitignore`
- `requirements.txt`, `README.md`, `LICENSE`
- `uygulama/__init__.py`, `uygulama/ana.py`
- `uygulama/cekirdek/__init__.py`, `konfigurasyon.py`, `veritabani.py`, `guvenlik.py`, `istek_sinirlayici.py`, `gunlukleyici.py`, `onbellek.py`
- `uygulama/cekirdek/hata_yonetimi.py`, `uygulama/api/bagimliliklar.py`, `uygulama/api/rotalar/*.py`
- `uygulama/sablonlar/*.html`, `uygulama/statik/css/stil.css`, `uygulama/statik/js/uygulama.js`
- `uygulama/modeller/__init__.py`, `veritabani_modelleri.py`, `semalar.py`
- `excel_ice_aktar.py`, `uygulama/servisler/__init__.py`, `excel_yukleyici.py`, `metin_parcalayici.py`
- `vektor_modelini_hazirla.py`, `yeniden_siralama_modelini_hazirla.py`, `vektorleri_olustur.py`, `uygulama/servisler/model_guvenligi.py`, `vektor_servisi.py`, `terim_haritasi.py`, `yeniden_siralayici.py`
- `uygulama/servisler/api_servisi.py`, `uygulama/servisler/oturum_sahipligi.py`, `testler/test_faz7_api.py`

### Notlar
- Proje yalnızca `veriler/` klasörünü kullanmaktadır, `veri/` klasörü kullanılmamaktadır.
- FTS5 Python built-in desteği ile çalışmaktadır, harici uzantı yüklemesi güvenlik nedeniyle kaldırılmıştır.
- Varsayılan yönetici hesabı: `yonetici`; parola `.env` dosyasındaki zorunlu `VARSAYILAN_YONETICI_SIFRESI` değerinden alınır.
- JWT ve veritabanı şifreleme anahtarları `.env` dosyasında güçlü ve benzersiz değerlerle zorunlu olarak yapılandırılmalıdır.
- `.env` içinde her anahtar yalnızca bir kez tanımlanmalıdır. Mevcut `.db.enc` dosyası yalnızca oluşturulurken kullanılan `VERITABANI_SIFRELEME_ANAHTARI` ile açılabilir; yeni anahtar üretmek mevcut veriyi kurtarmaz.
- Anahtar değişimi, geri yükleme veya yeniden oluşturma öncesinde `.env`, `.db.enc`, kaynak Excel ve kurum içi terim haritası birlikte erişimi kısıtlı yerel yedeğe alınmalıdır. Bu yedekler sürüm kontrolüne veya harici paylaşım servislerine gönderilmemelidir.
- Tüm kodlar Türkçe değişken, fonksiyon ve sınıf isimleriyle, yorum satırı olmadan yazılmıştır.
- Kullanıcı onay vermediği sürece kaynak kod yazımına kesinlikle başlanmayacaktır.
- Depo adresi: https://github.com/mecik-arda/UYDS-SSS-hades-bot

## 9. Şartname Referansı: Fonksiyonel Gereksinimler (FR)

Bu bölüm, `veriler/UYDS_Akilli_SSS_Chatbot_Staj_Projesi.docx` teknik şartnamesindeki fonksiyonel gereksinimleri referans alır.

- **FR-01:** Excel dosyası yüklenebilmeli ve kolonlar doğrulanmalıdır.
- **FR-02:** Excel kayıtları tekrar yüklenirse mükerrer kayıt oluşturulmamalıdır.
- **FR-03:** Her aktif SSS kaydı için embedding oluşturulmalıdır.
- **FR-04:** Kullanıcı Türkçe doğal dilde soru sorabilmelidir.
- **FR-05:** Sistem semantic ve keyword arama sonuçlarını birleştirmelidir.
- **FR-06:** Cevapta kaynak kayıt kodu veya satır bilgisi gösterilmelidir.
- **FR-07:** Kullanıcı cevabı yararlı/yararsız olarak değerlendirebilmelidir.
- **FR-08:** Yanlış cevap için doğru SSS kaydı yönetici tarafından seçilebilmelidir.
- **FR-09:** Onaylanmış kullanıcı sorusu alternatif soru olarak saklanmalıdır.
- **FR-10:** Cevapsız sorular ayrı ekranda listelenmelidir.
- **FR-11:** Konuşma içindeki devam soruları bağlamla anlaşılmalıdır.
- **FR-12:** Yönetici tüm kayıtları yeniden embed edebilmelidir.

## 10. Şartname Referansı: API Gereksinimleri

Şartnamede belirtilen ve plana eklenecek API uç noktaları:

| Uç Nokta | Amaç | Plan Durumu |
|---|---|---|
| `POST /api/import/excel` | Excel dosyasını içe aktarır | Faz 3'te |
| `POST /api/embeddings/rebuild` | Aktif SSS embeddinglerini yeniden üretir | Faz 4'te |
| `POST /api/chat` | Kullanıcı sorusunu cevaplar (SSE akışlı) | Faz 6 + 7'de |
| `GET /api/faqs` | SSS kayıtlarını filtreli listeler | Faz 7'de |
| `GET /api/queries/unanswered` | Cevapsız veya düşük güvenli soruları listeler | `/api/v1/yonetici/cevapsiz-sorgular` olarak Faz 8'de tamamlandı |
| `POST /api/feedback` | Kullanıcı geri bildirimi kaydeder | Faz 7'de |
| `POST /api/feedback/{id}/approve` | Geri bildirimi onaylar ve alternatif soru oluşturur | `/api/v1/yonetici/geri-bildirim/onay` olarak Faz 8'de tamamlandı |
| `GET /api/health` | Uygulama sağlık kontrolü (bizde `/api/saglik`) | Faz 1'de tamamlandı |

## 11. Şartname Referansı: Veri Modeli Genişletmesi

Şartnamede belirtilen ve mevcut tablolara eklenecek alanlar ile yeni tablolar:

### sss_kayitlari Tablosuna Eklenecek Alanlar
- **harici_kod:** TEXT — Harici referans kodu (external_code)
- **modul:** TEXT — İlgili UYDS modülü
- **kullanici_rolu:** TEXT — Hedef kullanıcı rolü
- **arama_metni:** TEXT — FTS5 ve embedding için birleşik arama metni
- **durum:** TEXT DEFAULT 'aktif' — Kayıt durumu ('aktif', 'pasif')
- **icerik_surumu:** INTEGER DEFAULT 1 — Yeni mantıksal kayıtta 1 ile başlayan, her içerik revizyonunda önceki değerin bir fazlasına çıkan içerik sürüm numarası

### Yeni Tablo: alternatif_sorular
- **id:** INTEGER PRIMARY KEY AUTOINCREMENT
- **sss_id:** INTEGER (FOREIGN KEY -> sss_kayitlari.id)
- **soru:** TEXT NOT NULL
- **vektor_verisi:** BLOB
- **kaynak:** TEXT NOT NULL — 'kullanici_geri_bildirimi', 'yonetici_eklemesi'
- **durum:** TEXT DEFAULT 'beklemede' — 'beklemede', 'onaylandi', 'reddedildi'
- **olusturulma_tarihi:** DATETIME DEFAULT CURRENT_TIMESTAMP

### Yeni Tablo: asistan_sorgulari
- **id:** INTEGER PRIMARY KEY AUTOINCREMENT
- **oturum_id:** TEXT
- **kullanici_sorusu:** TEXT NOT NULL
- **yeniden_yazilmis_soru:** TEXT
- **cevap_metni:** TEXT
- **guven_skoru:** REAL
- **cevaplandi_mi:** INTEGER DEFAULT 0
- **olusturulma_tarihi:** DATETIME DEFAULT CURRENT_TIMESTAMP

## 12. Alternatif Soru Öğrenme Mekanizması

Şartname Faz 5 ve FR-09 gereği, kullanıcı geri bildirimlerinden öğrenme akışı:

1. Kullanıcı bir soru sorar, sistem cevap üretir.
2. Kullanıcı cevabı yararlı/yararsız olarak değerlendirir.
3. Yararsız ise kullanıcı doğru SSS kaydını seçebilir.
4. Geri bildirim `BEKLEMEDE` durumuyla `geri_bildirimler` tablosuna kaydedilir.
5. Yönetici geri bildirimi inceler, onaylar veya reddeder.
6. Onaylanan geri bildirimdeki kullanıcı sorusu `alternatif_sorular` tablosuna eklenir.
7. Alternatif sorunun embedding vektörü üretilir.
8. Sonraki aramalarda alternatif sorular da taranır.
9. Geri bildirim yönetici onayı olmadan aktif bilgi tabanına dahil edilmez.

## 13. Başarı Metrikleri ve Test Kriterleri

Şartname Bölüm 14'te belirtilen başarı ölçütleri:

| Metrik | Hedef |
|---|---|
| Doğru SSS'nin Top-1 sonucu | En az %80 |
| Doğru SSS'nin Top-3 içinde bulunması | En az %92 |
| Kaynaksız cevap oranı | %0 |
| Bilinmeyen soruda cevap vermeme başarısı | En az %85 |
| Cevap üretiminde kaynak gösterme | %100 |
| Otomatik test kapsamı | Kritik servislerde yeterli kapsam |
| Geri bildirim sonrası başarı değişimi | Ölçülmüş ve raporlanmış |

Testler Excel'deki soruların birebir kopyalarıyla yapılmamalıdır. Aynı anlamı taşıyan ancak farklı kelimeler kullanan test soruları hazırlanmalıdır.

## 14. Değerlendirme Puanlaması

Şartname Bölüm 17'de belirtilen 100 puanlık değerlendirme dağılımı:

| Değerlendirme Alanı | Puan |
|---|---|
| Mimari ve kod kalitesi | 20 |
| Anlamsal ve hibrit arama doğruluğu | 20 |
| Reranking ve kaynaklı cevap üretimi | 15 |
| Güven kontrolü ve halüsinasyon önleme | 15 |
| Geri bildirim ve öğrenme döngüsü | 10 |
| Testler ve başarı ölçümü | 10 |
| Arayüz, dokümantasyon ve sunum | 10 |

## 15. Bonus Özellikler

Şartname Bölüm 18'de belirtilen ve projeyi öne çıkaracak ek özellikler:

- Benzer veya mükerrer SSS kayıtlarının kümelenmesi.
- Birbiriyle çelişen cevapların otomatik tespiti.
- Soru niyeti, modül ve kullanıcı rolü sınıflandırması.
- Çoklu Excel versiyonu ve değişiklik karşılaştırması.
- Yanıt süresi ve model maliyeti analitiği.
- RAG açık/kapalı ve reranker açık/kapalı A/B karşılaştırması.
- İkinci aşamada SQLite vector extension veya PostgreSQL + pgvector adaptörü.

## 16. Teslim Edilecek Çıktılar

Şartname Bölüm 15'te belirtilen teslim listesi:

- Çalışan kaynak kod; gerçek UYDS verileri içermeyen teslim paketi.
- Örnek `.env.example` dosyası; gizli anahtarlar repoya eklenmeyecektir.
- Otomatik oluşturulan SQLite veritabanı ve migration/init mekanizması.
- Excel içe aktarma betiği.
- Embedding oluşturma ve yeniden oluşturma betiği.
- FastAPI Swagger dokümantasyonu.
- Kullanıcı sohbet ekranı.
- Yönetici geri bildirim ve cevapsız soru ekranı.
- pytest testleri.
- Test veri seti ve başarı raporu.
- Kurulum ve kullanım README dokümanı.
- 5-10 dakikalık demo sunumu veya video.

## 17. Akıllı Asistan İçin Zorunlu Kurallar (Şartname Referansı)

Şartname Bölüm 10'da belirtilen ve sistemin temelini oluşturan zorunlu kurallar:

- Sadece kelime eşleştirme kabul edilmeyecektir.
- Embedding tabanlı semantic search zorunludur.
- Semantic ve keyword araması birlikte kullanılmalıdır.
- Reranking aşaması bulunmalıdır.
- LLM kendi genel bilgisinden cevap üretmemelidir.
- Cevapta kullanılan SSS kayıtları gösterilmelidir.
- Düşük güvenli sorularda cevap verilmemelidir.
- Birbiriyle çelişen kaynaklar varsa kullanıcı bilgilendirilmelidir.
- Kullanıcı geri bildirimi doğrudan öğrenme verisine dönüşmemeli; yönetici onayı beklemelidir.
- Embedding modeli ve prompt versiyonu kayıt altında tutulmalıdır.

## 18. Kabul Tanımı

Proje başarılı kabul edilecektir, eğer: Sistem Excel'de birebir bulunmayan ancak aynı anlama gelen kullanıcı sorularında doğru SSS kaydını bulabiliyor, kaynak göstererek cevap üretiyor, düşük güvenli sorularda cevap uydurmuyor ve yönetici onaylı geri bildirimlerle arama başarısını ölçülebilir biçimde artırabiliyorsa.

İlk hedef büyük bir dil modeli eğitmek değildir. İlk hedef, güvenilir veri hazırlama, embedding tabanlı bilgi erişimi, hybrid search, reranking, kaynak kontrollü cevap üretimi ve insan geri bildirimi döngüsünü doğru kurmaktır. Model eğitimi veya fine-tuning ancak yeterli miktarda doğrulanmış veri oluştuğunda sonraki aşama olarak değerlendirilebilir.

## 19. Benchmark ve Test Veri Seti Altyapısı

Bu bölüm, şartname Bölüm 14'te belirtilen başarı metriklerini ölçmek ve sistem performansını nesnel olarak değerlendirmek için karşılaştırma altyapısını tanımlar.

### Benchmark Dizini Yapısı
```
testler/
├── karsilastirma/
│   ├── test_senaryolari.json      # Farklı zorluk seviyelerinde soru-beklenen_sss_id ikilileri
│   ├── degerlendirme.py           # Top-1, Top-3, MRR, MAP metrik hesaplama betiği
│   └── raporlar/                  # JSON + HTML karşılaştırma raporları
├── test_belge_ayiklayici.py
├── test_arama_servisi.py
├── test_guvenlik_bakimi.py
└── test_api.py
```

### Test Senaryosu Formatı (`test_senaryolari.json`)
```json
{
  "surum": "1.0.0",
  "olusturulma_tarihi": "2026-07-27",
  "senaryolar": [
    {
      "id": "T-001",
      "zorluk": "kolay",
      "soru": "Faturaları sisteme hangi aşamada eklemem gerekiyor?",
      "beklenen_sss_id": 42,
      "excel_sorusu": "Harcama belgeleri ne zaman yüklenir?",
      "kategori": "Muhasebe"
    },
    {
      "id": "T-002",
      "zorluk": "orta",
      "soru": "Hesabıma giremiyorum, parolayı nereden değiştirebilirim?",
      "beklenen_sss_id": 108,
      "excel_sorusu": "Şifre nasıl yenilenir?",
      "kategori": "Kullanıcı İşlemleri"
    },
    {
      "id": "T-003",
      "zorluk": "zor",
      "soru": "Şirkette başka bir kişiye sistem erişimi vermek istiyorum, nasıl yapabilirim?",
      "beklenen_sss_id": 215,
      "excel_sorusu": "Yetkili kullanıcı nasıl tanımlanır?",
      "kategori": "Yetkilendirme"
    },
    {
      "id": "T-004",
      "zorluk": "cevapsiz",
      "soru": "Mars yüzeyinde tarım nasıl yapılır?",
      "beklenen_sss_id": null,
      "excel_sorusu": null,
      "kategori": "Bilinmeyen"
    }
  ]
}
```

### Zorluk Seviyeleri
- **Kolay:** Orijinal soruya çok benzeyen, birkaç kelimesi değiştirilmiş sorular.
- **Orta:** Aynı anlamı taşıyan ancak farklı kelimeler ve cümle yapısı kullanan sorular.
- **Zor:** Aynı anlama gelen ancak tamamen farklı ifade biçimi, jargon ve bağlam içeren sorular.
- **Cevapsız:** UYDS bilgi tabanında cevabı bulunmayan, sistemin cevap vermemesi gereken sorular.

### Benchmark Çalıştırma ve Raporlama
`testler/karsilastirma/degerlendirme.py` betiği her çalıştırmada:
1. `test_senaryolari.json` dosyasından tüm senaryoları yükler.
2. Her test sorusunu `/api/v1/arama` uç noktasına gönderir.
3. Dönen yanıttaki kaynak SSS ID'lerini beklenen ID ile karşılaştırır.
4. Toplam senaryo sayısı üzerinden Top-1, Top-3 ve MRR metriklerini hesaplar.
5. Sonuçları `sonuclar/` dizininde JSON ve HTML formatında kaydeder.
6. Her karşılaştırma koşumunda `karsilastirma_YYYYAAGG_HHMMSS.html` isimlendirmesi ile zaman damgalı rapor üretir.

### Benchmark Metrikleri
| Metrik | Açıklama | Şartname Hedefi |
|---|---|---|
| **Top-1 Doğruluğu** | Doğru cevabın ilk sırada gelme oranı | ≥ %80 |
| **Top-3 Doğruluğu** | Doğru cevabın ilk üç sırada yer alma oranı | ≥ %92 |
| **MRR (Mean Reciprocal Rank)** | Doğru cevabın sıralamadaki yerinin harmonik ortalaması | ≥ 0.85 |
| **Cevap Vermeme Başarısı** | Cevapsız sorularda sistemin cevap üretmeme oranı | ≥ %85 |
| **Kaynak Gösterme Oranı** | Üretilen cevaplarda kaynak SSS ID'sinin bulunma oranı | %100 |
| **Ortalama Yanıt Süresi (ms)** | Benchmark'taki ortalama yanıt süresi | Raporlanacak |
| **MRR@10** | İlk on sonuç içindeki doğru cevabın ters sıra ortalaması | Raporlanacak |
| **nDCG@10** | İlk on sonucun dereceli sıralama kalitesi | Raporlanacak |
| **p50/p95 Gecikme (ms)** | Medyan ve kuyruk gecikmesi | Raporlanacak |
| **Tepe Bellek Kullanımı** | Benchmark sırasında gözlenen en yüksek bellek tüketimi | Raporlanacak |
| **Vektör/Dizin Boyutu** | Aktif embedding verisinin disk üzerindeki toplam boyutu | Raporlanacak |

### Benchmark HTML Raporu
Her karşılaştırma koşumu sonunda üretilecek HTML raporu şu bileşenleri içerir:
- Genel metrik özeti (Top-1, Top-3, MRR, cevap vermeme başarısı, kaynak gösterme oranı)
- Zorluk seviyesine göre kırılımlı metrik tablosu
- Başarısız senaryoların detaylı listesi (soru, beklenen ID, dönen ID, skor)
- Zaman serisi grafiği (önceki karşılaştırma sonuçlarıyla kıyaslama - isteğe bağlı)
- Geri bildirim öncesi/sonrası başarı değişimi karşılaştırması

### Benchmarkın Faz 10'a Entegrasyonu
Benchmark ölçüm ve raporlama altyapısı Faz 10 Adım 10.6 kapsamında uygulanmıştır. Mevcut 25 senaryo davranış ve güvenlik doğrulaması içindir. Retrieval kabulü için en az 50 senaryoya uzman doğrulamalı `beklenen_sss_id` veya `beklenen_sss_idler` etiketi eklenmesi gerekir. Etiketsiz senaryolar Top-1, Top-3, MRR@10 ve nDCG@10 paydasına alınmaz; kabul raporu eksik altın veri setinde başarısız olur.

### Yerel Embedding Ölçek Geçiş Politikası
1. Mevcut MiniLM, SQLite ve kesin kosinüs araması karşılaştırma referansı olarak ölçülür.
2. Gerçek tokenizer uzunluğu, embedding sürüm bilgisi ve veri bütünlüğü üretim öncesi doğrulanır.
3. Yeni model veya arama altyapısı aynı veri setinde mevcut referansla karşılaştırılır.
4. Doğruluk kazanımı, p95 gecikme, tepe bellek ve işletim maliyeti birlikte değerlendirilir.
5. Yeni embedding sürümü mevcut sürümden ayrı üretilir ve tamlık doğrulaması yapılır.
6. Geçiş atomik olarak gerçekleştirilir; başarısızlık halinde önceki sürüme geri dönülür.
7. SQLite yalnızca ölçülen kapasite veya hizmet seviyesi hedefi yetersiz kaldığında `pgvector` ya da yerel `Qdrant` ile değiştirilir.
8. Kurumsal veri için harici embedding API kullanımına ancak açık veri işleme ve güvenlik onayı sonrasında izin verilir.

## 20. İleri Seviye Yol Haritası (Roadmap Plus)

Bu bölüm temel fazların tamamlanma ölçütüne dahil olmayan gelecek ve bonus iş listesidir. Buradaki maddeler ayrıca tamamlandı olarak işaretlenmedikçe uygulanmış kabul edilmez.

Bu bölüm, projeyi 100 puanlık değerlendirme skalasında üst seviyeye taşıyacak, "wow faktörü" yaratacak ek özellikleri tanımlar. Bu özellikler temel fazların üzerine inşa edilen bonus katmanıdır.

### 20.1 Benchmark Dashboard ve A/B Test Sistemi

Her karşılaştırma koşumunda etkileşimli HTML raporu üreten, zaman serisi grafikleri gösteren ve farklı sistem yapılandırmalarını otomatik kıyaslayan bir gösterge paneli.

**Bileşenler:**
- `testler/karsilastirma/gosterge_paneli.html` — Tekil HTML dosyası, sunucu gerektirmez. Tarayıcıda açılır.
- Zaman serisi çizgi grafikleri (Top-1, Top-3, MRR metriklerinin karşılaştırma koşumları arası değişimi).
- RAG açık/kapalı karşılaştırma tablosu — aynı test setinde RAG'li ve RAG'siz sonuçlar yan yana.
- Reranker açık/kapalı karşılaştırma tablosu — Cross-Encoder'ın katkısının sayısal ölçümü.
- Başarısız senaryolar için interaktif detay paneli (tıklandığında tam yanıt içeriği, skor detayı).
- JSON ve CSV export butonları.

### 20.2 Gözlemlenebilirlik Katmanı

Prometheus metrik toplama ve Grafana dashboard ile gerçek zamanlı sistem izleme.

**Prometheus Metrikleri:**
- `sorgu_sayaci_toplam` — Toplam sorgu sayısı (etiketler: durum=basarili/basarisiz/guven_esik_alti)
- `sorgu_suresi_saniye` — Sorgu başına yanıt süresi histogramı
- `vektor_benzerlik_skoru` — Üretilen cosine similarity skorlarının dağılımı
- `deepseek_token_sayaci` — API çağrısı başına kullanılan token sayısı
- `deepseek_maliyet_tahmini` — Kümülatif API maliyet tahmini (USD)
- `veritabani_baglanti_durumu` — SQLite bağlantı durumu (UP/DOWN)
- `hata_sayaci_toplam` — Toplam hata sayısı (etiketler: tur=veritabani/dogrulama/api)

**Grafana Dashboard Bileşenleri:**
- Gerçek zamanlı sorgu sayısı ve başarı oranı göstergeleri
- Yanıt süresi dağılımı (p50, p95, p99)
- Saatlik/dönemlik API maliyet özeti
- Son 1 saatteki hata logları
- Güven eşiği altı sorgu oranı trend çizgisi

### 20.3 LLM Destekli Otomatik Test Veri Seti Üretimi

Şartname Bölüm 14 gereği test soruları Excel'deki soruların birebir kopyası olamaz. Bu modül, her SSS kaydından farklı ifade biçimleriyle değişken sorular üreterek karşılaştırma veri setini otomatik genişletir.

**Çalışma Prensibi:**
1. `testler/karsilastirma/senaryo_uretici.py` betiği, `sss_kayitlari` tablosundaki her kayıt için DeepSeek API'ye bir değişken soru üretme isteği gönderir.
2. Prompt: "Aşağıdaki soruyu aynı anlama gelecek şekilde farklı kelimeler ve cümle yapısıyla yeniden yaz. Orijinal sorudaki anahtar kelimeleri birebir kopyalama."
3. Her SSS kaydı için 3-5 varyant soru üretilir.
4. Üretilen sorular `test_senaryolari.json` dosyasına `uretim` kaynak etiketiyle eklenir.
5. Manuel inceleme için `gozden_gecirilmemis` olarak işaretlenir.

### 20.4 Mükerrer ve Çelişen SSS Tespit Sistemi

Embedding benzerlik matrisi kullanarak aynı soruya verilen farklı veya çelişen cevapları otomatik tespit eden sistem.

**Tespit Mantığı:**
- Tüm SSS embedding'leri arasında pairwise cosine similarity matrisi hesaplanır.
- Benzerlik skoru 0.85 üzerinde olan kayıtlar "potansiyel mükerrer" olarak işaretlenir.
- Mükerrer olarak işaretlenen kayıtların cevap metinleri karşılaştırılır.
- Cevaplar arasındaki embedding benzerliği 0.70 altındaysa "çelişen cevap" uyarısı üretilir.
- Sonuçlar yönetici panelinde `GET /api/yonetici/cakisan-kayitlar` endpoint'i üzerinden listelenir.

### 20.5 Prompt Versiyonlama ve A/B Karşılaştırma

DeepSeek API'ye gönderilen prompt'ların versiyon takibi ve farklı prompt'ların başarı metriklerinin karşılaştırılması.

**Versiyonlama Mekanizması:**
- Prompt şablonları `veriler/prompt_sablonlari/` dizininde `v1_sistem_promptu.txt`, `v2_sistem_promptu.txt` gibi sürüm kontrollü saklanır.
- Her LLM çağrısında kullanılan prompt versiyonu `asistan_sorgulari` tablosuna `prompt_surumu` alanına kaydedilir.
- Benchmark betiği, aynı test setini farklı prompt versiyonlarıyla koşarak sonuçları karşılaştırır.
- `GET /api/yonetici/prompt-karsilastirma` endpoint'i üzerinden prompt versiyonları arası başarı metrikleri görüntülenir.

### 20.6 Maliyet Optimizasyonu ve Analitik

DeepSeek API kullanımının maliyet takibi, optimizasyonu ve raporlaması.

**Bileşenler:**
- Her API çağrısında kullanılan token sayısının (prompt + completion) loglanması.
- DeepSeek güncel fiyatlandırması üzerinden anlık maliyet hesaplaması.
- Önbellek isabet oranı takibi — aynı soru tekrar sorulduğunda API çağrılmadan önbellekten yanıtlanma oranı.
- Maliyet/başarı optimizasyonu — güven eşiği değeri ile API maliyeti arasındaki ilişkinin grafiksel analizi.
- Aylık maliyet tahmini ve bütçe uyarı eşiği.

### 20.7 Çoklu Model Desteği

DeepSeek dışında alternatif LLM sağlayıcılarına geçiş yapabilme veya aynı anda kullanabilme.

**Desteklenmesi Planlanan Sağlayıcılar:**
- DeepSeek API (mevcut)
- OpenAI API (GPT-4o, GPT-4o-mini)
- Yerel LLM (Ollama entegrasyonu — tamamen çevrimdışı RAG)
- Google Gemini API

**Geçiş Mekanizması:**
- `.env` üzerinden `LLM_SAGLAYICI` değişkeni (deepseek/openai/ollama/gemini).
- `uygulama/servisler/llm_fabrikasi.py` — sağlayıcıya göre doğru istemciyi döndüren fabrika pattern'i.
- Benchmark betiği, aynı test setiyle tüm sağlayıcıları karşılaştıran "model showdown" raporu üretir.

### 20.8 Kurulum Sihirbazı

Projenin tek komutla eksiksiz kurulumunu sağlayan interaktif CLI sihirbazı.

**Komut:** `python kurulum.py`

**Adımlar:**
1. DeepSeek API anahtarı sorgulama ve `.env` dosyasına yazma.
2. JWT gizli anahtarını rastgele oluşturma ve `.env` dosyasına yazma.
3. `veriler/` dizininde `UYDS_SSS_Listesi.xlsx` dosyasının varlığını kontrol etme.
4. Docker imajını build etme ve konteyneri başlatma.
5. Excel içe aktarma ve embedding üretimini otomatik tetikleme.
6. Tarayıcıda `http://localhost:8000` adresini açma.

### 20.9 Değerlendirme Puanına Etki Matrisi

| Özellik | Etkilenen Kriter | Potansiyel Puan Katkısı |
|---|---|---|
| 20.1 Benchmark Dashboard + A/B | Retrieval (20) + Test (10) | +8-12 |
| 20.2 Gözlemlenebilirlik (Prometheus + Grafana) | Mimari (20) + Güvenlik (15) | +5-8 |
| 20.3 Otomatik Test Veri Seti Üretimi | Test (10) | +3-5 |
| 20.4 Mükerrer/Çelişen SSS Tespiti | Retrieval (20) + Bonus | +5-8 |
| 20.5 Prompt Versiyonlama | Güvenlik (15) + Bonus | +3-5 |
| 20.6 Maliyet Optimizasyonu | Mimari (20) + Bonus | +3-5 |
| 20.7 Çoklu Model Desteği | Mimari (20) + Bonus | +5-8 |
| 20.8 Kurulum Sihirbazı | Dokümantasyon (10) | +3-5 |
| **Toplam Potansiyel Katkı** | | **+35-56** |

### 20.10 İleri Seviye CI/CD (Sürekli Dağıtım ve Otomasyon)

Faz 10 kapsamındaki çekirdek CI tesliminden sonra (vakit kalması durumunda) değerlendirilmek üzere planlanmış bonus eklentilerdir:
1. **Coverage PR Yorum Otomasyonu (Öncelikli):** `pytest-cov` çıktısının, GitHub Actions tarafından Pull Request'lere okunabilir bir Türkçe özet yorum olarak otomatik basılması. 
2. **GHCR İmaj Depolama Entegrasyonu:** Derlenen Docker imajının `main` dalında otomatik olarak Github Container Registry'ye gönderilmesi (Kurumsal veri içermeyen stateless imaj kuralına sıkı sıkıya bağlı kalınarak).
3. **Otomatik Sürümleme (Release Automation):** Commit geçmişinden (`feat:`, `fix:` vb.) yola çıkarak otomatik Türkçe sürüm notları (Changelog) ve GitHub Tag/Release oluşturulması.

### 20.11 İleri Seviye Sistem ve Güvenlik Testleri (Production-Ready Bonus)

Staj projesi kapsamında Faz 10 itibarıyla 199 test ile %100 kapsama ulaşılmıştır. Gerçek bir kurumsal "production" ortamına çıkılması durumunda değerlendirilebilecek ileri seviye mimari testler şunlardır:

1. **Yük ve Stres Testleri (k6/Locust):** 1000+ eşzamanlı istekte SQLite'ın sınırlarını (database is locked) ve pgvector/Qdrant geçiş eşiklerini doğrulamak.
2. **AI Red Teaming (RAGAS/TruLens):** İleride LLM (Generation) modülü eklendiğinde halüsinasyon, kaynak sapması ve prompt injection/jailbreak denemelerine karşı modeli otonom test etmek.
3. **Kaos Mühendisliği (Chaos Engineering):** Ağ kesintisi, HuggingFace Hub çökmesi veya disk doluluk oranlarında sistemin felaket kurtarma (Disaster Recovery) ve "read-only" yeteneklerini test etmek.
4. **Erişilebilirlik (a11y) Testleri:** Playwright üzerine axe-core entegrasyonu ile ön yüzün (Faz 9) görme engelli (screen-reader) ve klavye navigasyon uyumluluğunu otomatize etmek.

### 20.12 Gelişmiş Kimlik Yönetimi ve RBAC (Gelecek Vizyonu)

Mevcut sistemde analitik ve veri yükleme işlemleri için tekil bir "Yönetici" (Admin) hesabı ve statik JWT yapısı bulunmaktadır. Projenin gelecekte çok kullanıcılı bir SaaS platformuna dönüşebilmesi için aşağıdaki kimlik yönetimi özellikleri planlanmıştır:

1. **Kullanıcı Kayıt ve Rol Yönetimi (RBAC):** "Standart Kullanıcı", "Editör" ve "Süper Admin" gibi farklı yetki seviyelerine sahip hesapların veritabanı üzerinden (Kayıt Ol ekranıyla) oluşturulması.
2. **Kullanıcı Paneli (Dashboard) İyileştirmeleri:** Giriş yapan kullanıcının sağ üst köşede profilini görebilmesi; "Çıkış Yap" ve "Şifremi Değiştir" gibi temel oturum işlemlerinin arayüze entegre edilmesi.
3. **Şifre Sıfırlama Akışı:** Unutulan şifreler için geçici ve süreli (JWT tabanlı) şifre sıfırlama bağlantılarının e-posta veya sistem içi loglar üzerinden yönetilmesi.

### 20.13 Alana Özgü Model Eğitimi (Domain-Specific Fine-Tuning)

Sistem şu anda Hibrit Arama (FTS5 + Vector), Cross-Encoder ve `es_anlamlilar.json` (sözlük) üçlüsüyle standart Türkçe ve kurum jargonunu %99 doğrulukla çözümlemektedir. Ancak uygulamanın tamamen standart dışı kelime dağarcığına sahip niş bir alana (örn. yoğun tıbbi makaleler veya ağır teknik şartnameler) kayması durumunda opsiyonel olarak planlanabilir:

- **Embedding Modelinin Eğitilmesi:** SentenceTransformers (SetFit vb.) kütüphaneleri kullanılarak, kuruma özel "Soru - Doğru Cevap - Yanlış Cevap" üçlüleri (triplets) oluşturulması ve ana vektör modelinin anlamsal uzayının (semantic space) dar bir sektöre (domain adaptation) uyarlanması. MLOps maliyeti yüksek olduğu için yalnızca hibrit aramanın yetersiz kaldığı uç (edge) vakalarda devreye alınmalıdır.
