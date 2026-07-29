# UYDS Akıllı SSS Destek Asistanı

Sürüm 1.0.0 | Faz 1-6 servis çekirdeği tamamlandı | Geliştirme sürümü | MIT Lisansı

## Proje Durumu

HadesBot, UYDS Sık Sorulan Sorular verilerini güvenli biçimde hazırlamak, anlamsal olarak aranabilir hale getirmek ve sonraki fazlarda kaynak kontrollü bir destek asistanına dönüştürmek amacıyla geliştirilmektedir.

Mevcut sürüm; güvenli uygulama altyapısını, SQLite ve FTS5 veri katmanını, Excel içe aktarımını, veri sürümlemeyi, metin parçalamayı, yerel anlamsal vektör üretimini, sorgu genişletmeyi, RRF tabanlı hibrit aramayı, kaynak kontrollü DeepSeek istemcisini, güven eşiği kapısını, SSE olay üretimini ve TTL’li oturum hafızasını içerir. Cross-Encoder model seçimi, kullanıcı API rotaları ve web arayüzü henüz uygulanmamıştır.

| Faz | Kapsam | Durum |
|---|---|---|
| Faz 1 | Ortam, Docker, yapılandırma ve güvenlik altyapısı | Tamamlandı |
| Faz 2 | SQLite, FTS5, veri modelleri ve şifreleme | Tamamlandı |
| Faz 3 | Excel aktarımı, sürümleme ve metin parçalama | Tamamlandı |
| Faz 4 | Vektör gömmeleri ve kurum içi terim haritası | Tamamlandı |
| Faz 5 | Sorgu genişletme, hibrit arama ve RRF | Çekirdek tamamlandı; Cross-Encoder modeli ertelendi |
| Faz 6 | DeepSeek, kaynak kontrollü RAG, SSE ve oturum hafızası | Servis katmanı tamamlandı; canlı çağrı için kurum onaylı anahtar gerekli |
| Faz 7 | API rotaları, kimlik doğrulama ve merkezi hata yönetimi | Beklemede |
| Faz 8 | Geri bildirim, yönetici onayı ve analitik | Beklemede |
| Faz 9 | Kurumsal web arayüzü | Beklemede |
| Faz 10 | Kalıcı testler, benchmark ve güvenlik doğrulaması | Beklemede |

## Veri Gizliliği

UYDS Excel dosyaları, soru-cevap içerikleri, SQLite veritabanları, vektör kayıtları, günlükler, yedekler ve proje çıktıları özel kurumsal veridir. Bu dosyalar GitHub, kişisel bulut depolama, e-posta veya harici dosya paylaşım servislerine aktarılmamalıdır.

`veriler/`, `yedekler/` ve `modeller/` dizinleri sürüm kontrolünden çıkarılmıştır. Kurum içi terim haritasının gerçek içeriği de yalnızca `veriler/es_anlamlilar.json` dosyasında yerel olarak tutulur. Depodaki `es_anlamlilar.example.json` sadece kurumsal veri içermeyen bir şablondur. Gerçek veri yalnızca yetkili yerel çalışma ortamında tutulmalıdır. UYDS metinleri vektör üretimi sırasında dış servislere gönderilmez.

Faz 6 canlı yanıt üretimi etkinleştirildiğinde yalnızca güven eşiğini geçen ilk kaynak parçaları, kullanıcı sorusu ve sınırlı oturum geçmişi yapılandırılmış DeepSeek API adresine gönderilir. Bu özellik kurumun veri işleme ve dış servis politikası onaylanmadan etkinleştirilmemelidir. `DEEPSEEK_API_ANAHTARI` boş bırakıldığında dış çağrı yapılamaz; düşük güvenli sorularda anahtar bulunsa bile DeepSeek çağrısı yapılmaz.

## Tamamlanan Özellikler

### Uygulama ve güvenlik altyapısı

- FastAPI uygulama yaşam döngüsü ve sağlık kontrolü
- Ortam profilleri: `dev`, `test`, `prod`
- Zorunlu ve doğrulanan JWT, veritabanı şifreleme ve yönetici parolası değerleri
- Yapılandırılabilir istek sınırı ve akış tabanlı istek gövdesi boyut kontrolü
- Güvenlik başlıkları ve sınırlı CORS politikası
- SQLite üzerinde merkezi kullanıcı ve IP brute-force sayaçları
- bcrypt tabanlı parola özetleme
- JWT oluşturma, çözme ve RBAC bağımlılık altyapısı
- Hassas değer maskeleyen yapılandırılmış günlükleme
- Non-root Docker kullanıcısı, salt-okunur kök dosya sistemi, capability kaldırma ve `no-new-privileges`
- Salt-okunur model bağlama noktası ve yalnızca veri dizininde kalıcı yazma yetkisi
- Güvenlik düzeltmeleri güncel bağımlılıklar, CPU odaklı PyTorch ve PyJWT ile sınırlandırılmış çalışma zamanı
- Ayrı liveness ve veritabanı/FTS readiness kontrolleri
- PID sınırı ve kontrollü kapanış süresi

### Veritabanı altyapısı

- Bağlantı başına SQLite yönetimi
- WAL, foreign key ve busy timeout ayarları
- 12 normal tablo ve bir FTS5 sanal tablosu
- INSERT, UPDATE ve DELETE işlemlerinde FTS5 eşitleme tetikleyicileri
- Tek seferlik ve kayıtlı şema migrasyonları
- Durum, puan ve boolean alanları için veritabanı doğrulama kısıtları
- Arama, sürüm, parça, vektör ve oturum sorgularına uygun indeksler
- Veri sürümleri ile SSS kayıtlarını, kaynak sayfa ve satır anlık görüntüsüyle eşleyen kalıcı ilişki tablosu
- AES-256-GCM ile doğrulanmış veritabanı şifreleme
- PBKDF2-HMAC-SHA256 anahtar türetme
- Bağlantı ömrü boyunca paylaşımlı, şifreleme sırasında özel süreçler arası dosya kilidi
- Temiz kapanışta WAL checkpoint, bütünlük kontrolü ve düz metin temizliği
- Atomik yedekleme, geri yükleme, saklama sınırı ve zamanlama

### Excel veri aktarımı

- Standart `Kategori`, `Soru`, `Cevap`, `Kaynak Doküman` şeması
- Mevcut kurumsal UYDS Excel şeması
- İlk 25 satır içinde dinamik başlık tespiti
- Dosya boyutu, MIME, OOXML imzası ve içerik türü doğrulaması
- ZIP path traversal, sıkıştırma bombası, makro, OLE, ActiveX ve harici bağlantı denetimi
- Formül ve formül enjeksiyonu reddi
- SHA-256 ile aynı dosyanın yeniden aktarılmasını engelleme
- Dosya içindeki birebir mükerrer kayıtları eleme
- Excel çalışma sayfası, satır numarası ve kayıt özeti izlenebilirliği
- Değişmeyen kayıt kimliklerini ve parçalarını koruyan artımlı sürümleme
- Tekil mantıksal anahtarlarda önceki kayıt bağlantısı ve alan bazlı revizyon geçmişi
- Yeni kayıtta 1 ile başlayan ve her içerik revizyonunda bağımsız artan içerik sürümü
- Yalnızca kaldırılan veya değişen kayıtları arşivleme
- Süreçler arası `BEGIN IMMEDIATE` aktarım kilidi ve benzersiz dosya özeti
- Veri yazmadan eklenen, güncellenen, korunan ve kaldırılan kayıtları raporlayan kuru çalışma
- Geçmiş veri üyeliğini yeni ve denetlenebilir bir sürüm olarak etkinleştiren geri alma
- Denetim günlüğü ve veri sürümü geçmişi
- Paragraf, satır ve cümle sınırlarını koruyan metin parçalama

### Yerel anlamsal vektörler

- Olay öncesi sabit committen indirilen `paraphrase-multilingual-MiniLM-L12-v2`
- Yalnızca JSON, tokenizer ve `safetensors` dosyalarına izin veren model allowlist’i
- Resmî LFS SHA-256, dosya boyutu, yerel manifest ve model mimarisi doğrulaması
- Normal çalışma sırasında zorunlu çevrimdışı model yükleme
- Her aktif metin parçası için normalize edilmiş 384 boyutlu Float32 vektör
- Metin SHA-256 özetiyle yalnızca yeni veya değişen parçaları işleyen artımlı üretim
- Pasif SSS kayıtlarına ait vektörlerin temizlenmesi
- BLOB uzunluğu, vektör boyutu ve parça-model benzersizliği için veritabanı koruması
- Doğrulanan kurum içi terim ve eş anlamlı haritası

### Hibrit arama

- Türkçe sorgu normalizasyonu ve kurum içi eş anlamlılarla sorgu genişletme
- SQLite FTS5 BM25 ile yapılandırılabilir kelime arama adayları
- Yerel vektörler üzerinde kosinüs benzerliği ve SSS düzeyinde parça gruplama
- FTS ve vektör sıralarını Reciprocal Rank Fusion ile birleştirme
- Kaynak doküman, sayfa, satır ve aday metni taşıyan arama sonuçları
- Cross-Encoder entegrasyonu için `YenidenSiralayiciProtokolu`
- Yapılandırılabilir FTS alan ağırlıkları ve sonuç başına sorgu genişletme teşhisleri
- Gerçek kosinüs benzerliğini RRF sırasından bağımsız taşıyan güven skoru girdisi

### Kaynak kontrollü yanıt üretimi

- Yapılandırılabilir HTTPS DeepSeek Chat Completions istemcisi ve yerel geliştirme adresi desteği
- Yalnızca geçici ağ ve servis hatalarında, ilk çıktı parçasından önce üstel yeniden deneme
- Kaynak metnindeki talimatları veri kabul eden ve dış bilgi kullanımını yasaklayan sistem istemi
- İlk kaynak sayısını ve kaynak başına karakter sayısını sınırlayan bağlam bütçesi
- Gerçek vektör kosinüs benzerliğine dayalı `GUVEN_ESIGI` kapısı
- Eşik altındaki ve yalnızca FTS ile bulunan sorularda dış API çağrısı yapmadan standart ret yanıtı
- JSON kodlamalı `meta`, `parca`, `tamamlandi` ve `hata` SSE olayları
- Satır enjeksiyonuna dayanıklı SSE veri çerçeveleme
- TTL, mesaj sayısı ve toplam oturum sayısı sınırlı bellek içi konuşma hafızası
- API anahtarı veya sağlayıcı hata ayrıntısını kullanıcı akışına taşımayan hata yönetimi
- Sentetik veritabanı ve sahte HTTP taşıyıcısıyla çalışan 61 birim ve servis entegrasyon testi

## Mevcut Veri Akışı

```mermaid
flowchart TD
    A["UYDS Excel dosyası"] --> B["Dosya ve OOXML güvenlik doğrulaması"]
    B --> C["Sütun tespiti ve veri temizleme"]
    C --> D["Mükerrer dosya ve kayıt denetimi"]
    D --> E["Kayıt özeti ve kaynak satırı üretme"]
    E --> N["Mantıksal anahtar ve revizyon karşılaştırması"]
    N --> F["Artımlı veri sürümü oluşturma"]
    F --> J["Değişmeyen kayıt kimliklerini koruma"]
    F --> K["Yeni ve kaldırılan kayıtları işleme"]
    J --> L["Sürüm-kayıt eşleme geçmişi"]
    K --> L
    L --> M["SQLite aktif ve arşiv kayıtları"]
    M --> G["Mantıksal metin parçaları"]
    M --> H["FTS5 tam metin indeksi"]
    G --> I["Çevrimdışı MiniLM vektör üretimi"]
    I --> O["SQLite Float32 vektör BLOB kayıtları"]
```

Gerçek UYDS çalışma kitabında 2.399 veri satırı okunmuş, birebir mükerrer bir satır elendikten sonra 2.398 benzersiz kayıt ve 4.075 metin parçası oluşturulmuştur. Gerçek içerikler ve üretilen veritabanı sürüm kontrolüne dahil edilmez.

## Planlanan Özellikler

- Türkçe retrieval benchmarkı sonrasında Cross-Encoder model seçimi ve gerçek yeniden sıralama
- JWT giriş, yenileme ve çıkış rotaları
- Faz 6 servislerini kullanan kimlik doğrulamalı arama ve SSE HTTP rotaları
- Kullanıcı geri bildirimi ve yönetici onayı
- Analitik ve yönetici panelleri
- Kurumsal web arayüzü
- Benchmark, pytest ve güvenlik testi altyapısı

## Teknoloji Yığını

| Bileşen | Teknoloji | Kullanım durumu |
|---|---|---|
| Programlama dili | Python 3.11 | Aktif |
| Web çatısı | FastAPI | Aktif |
| ASGI sunucusu | Uvicorn | Aktif |
| Veritabanı | SQLite3 ve FTS5 | Aktif |
| Veri işleme | Pandas ve OpenPyXL | Aktif |
| Veri doğrulama | Pydantic ve Pydantic-Settings | Aktif |
| Şifreleme | cryptography, AES-256-GCM | Aktif |
| Parola güvenliği | bcrypt | Aktif |
| İstek sınırlama | SlowAPI | Aktif |
| Konteyner | Docker ve Docker Compose | Aktif |
| Vektör gömmeleri | Sentence-Transformers ve NumPy | Aktif |
| Yeniden sıralama | Cross-Encoder | Entegrasyon sözleşmesi hazır; model seçimi ertelendi |
| LLM istemcisi | HTTPX ve DeepSeek Chat Completions API | Aktif; canlı çağrı kurum onaylı anahtar gerektirir |
| Web arayüzü | Jinja2, HTML, CSS ve JavaScript | Faz 9 için planlandı |

## Ön Koşullar

Docker ile çalıştırma:

- Docker Engine 20.10 veya üzeri
- Docker Compose V2

Yerel çalıştırma:

- Python 3.11
- Proje bağımlılıkları için izole sanal ortam

DeepSeek API anahtarı uygulamanın başlaması, yerel arama ve düşük güvenli soru reddi için gerekli değildir. Güven eşiğini geçen bir soruda canlı kaynak kontrollü yanıt üretmek için kurum tarafından onaylanmış bir anahtar zorunludur.

## Kurulum

Depoyu klonlayın:

```text
git clone https://github.com/mecik-arda/UYDS-SSS-hades-bot.git
cd UYDS-SSS-hades-bot
```

Ortam dosyasını ve yerel terim haritasını oluşturun:

```text
copy .env.example .env
if not exist veriler mkdir veriler
copy es_anlamlilar.example.json veriler\es_anlamlilar.json
```

Linux veya macOS:

```text
cp .env.example .env
mkdir -p veriler
cp es_anlamlilar.example.json veriler/es_anlamlilar.json
```

`.env` içinde en az şu üç değeri güçlü ve benzersiz değerlerle değiştirin:

- `VERITABANI_SIFRELEME_ANAHTARI`
- `JWT_GIZLI_ANAHTARI`
- `VARSAYILAN_YONETICI_SIFRESI`

Orijinal çalışma kitabını aşağıdaki konuma yerleştirin:

```text
veriler/UYDS_SSS_Listesi.xlsx
```

Gerçek Excel dosyasını Git’e eklemeyin.

`veriler/es_anlamlilar.json` içeriğini yalnızca yetkili yerel ortamda kurum terimleriyle düzenleyin. Uygulama bu dosya eksikse örnek veya varsayılan kurumsal içerik kullanmaz ve açık hata verir.

## Yapılandırma

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `ORTAM_PROFILI` | Etkin ortam profili | `prod` |
| `DEEPSEEK_API_ANAHTARI` | Canlı DeepSeek yanıtı için kurum onaylı anahtar | Boş |
| `DEEPSEEK_API_ADRESI` | HTTPS Chat Completions uç noktası | `https://api.deepseek.com/chat/completions` |
| `DEEPSEEK_MODEL_ADI` | Kullanılacak DeepSeek model kimliği | `deepseek-v4-flash` |
| `DEEPSEEK_ZAMAN_ASIMI_SANIYE` | Dış API istek zaman aşımı | `120` |
| `DEEPSEEK_YENIDEN_DENEME_SAYISI` | Geçici hata sonrası ek deneme sayısı | `2` |
| `DEEPSEEK_YENIDEN_DENEME_TABAN_SANIYE` | Üstel beklemenin başlangıç süresi | `0.5` |
| `DEEPSEEK_KAYNAK_SAYISI` | Yanıt üretimine gönderilecek azami kaynak | `5` |
| `DEEPSEEK_KAYNAK_MAKS_KARAKTER` | Kaynak başına bağlam karakter sınırı | `6000` |
| `VERITABANI_YOLU` | SQLite dosya yolu | `veriler/veri_deposu.db` |
| `VERITABANI_SIFRELEME_ANAHTARI` | En az 32 karakterli şifreleme anahtarı | Zorunlu |
| `GUVEN_ESIGI` | DeepSeek çağrısı için asgari kosinüs benzerliği | `0.70` |
| `VEKTOR_MODEL_ADI` | Veritabanında saklanan model kimliği | `paraphrase-multilingual-MiniLM-L12-v2` |
| `VEKTOR_MODEL_YOLU` | Doğrulanmış yerel model dizini | `modeller/paraphrase-multilingual-MiniLM-L12-v2` |
| `VEKTOR_BOYUTU` | Beklenen embedding boyutu | `384` |
| `VEKTOR_TOPLU_ISLEM_BOYUTU` | Tek model çağrısında işlenen parça sayısı | `32` |
| `ES_ANLAMLILAR_YOLU` | Kuruma özel terim haritası | `veriler/es_anlamlilar.json` |
| `JWT_GIZLI_ANAHTARI` | En az 32 karakterli JWT anahtarı | Zorunlu |
| `JWT_ALGORITMASI` | JWT imza algoritması | `HS256` |
| `JWT_OMRU_DAKIKA` | Erişim belirteci ömrü | `30` |
| `VARSAYILAN_YONETICI_SIFRESI` | En az 12 karakterli yönetici parolası | Zorunlu |
| `ISTEK_SINIRI` | Pencere başına istek sayısı | `100` |
| `ISTEK_PENCERESI_SANIYE` | İstek sınırı penceresi | `60` |
| `UYGULAMA_PORT` | Dış HTTP portu | `8000` |
| `MESAJ_MAKS_KARAKTER` | Kullanıcı mesajı karakter sınırı | `2000` |
| `DEEPSEEK_MAKS_TOKEN` | LLM çıktı token sınırı | `4096` |
| `GUNLUK_MESAJ_KOTASI` | Gelecek kullanıcı günlük kotası | `500` |
| `OTURUM_MAKS_MESAJ` | Oturum başına saklanan mesaj sınırı | `50` |
| `OTURUM_TTL_DAKIKA` | Hareketsiz oturum yaşam süresi | `30` |
| `OTURUM_MAKS_SAYI` | Bellekte tutulacak toplam oturum sınırı | `1000` |
| `ISTEK_GOVDE_MAKS_BOYUT` | Genel istek gövdesi sınırı | `1048576` |
| `DOSYA_YUKLEME_MAKS_BOYUT` | Excel yükleme sınırı | `52428800` |
| `LOG_SEVIYESI` | Günlük seviyesi | `INFO` |
| `RRF_K` | Reciprocal Rank Fusion sabiti | `60` |
| `FTS_ADAY_SAYISI` | FTS5 tarafından alınacak azami aday | `50` |
| `VEKTOR_ADAY_SAYISI` | Vektör aramasından alınacak azami aday | `50` |
| `RRF_ADAY_SAYISI` | Harmanlama sonrasında korunacak azami aday | `20` |
| `FTS_SORU_AGIRLIGI` | BM25 soru alanı ağırlığı | `1.0` |
| `FTS_CEVAP_AGIRLIGI` | BM25 cevap alanı ağırlığı | `1.0` |
| `FTS_KATEGORI_AGIRLIGI` | BM25 kategori alanı ağırlığı | `1.0` |
| `FTS_HARICI_KOD_AGIRLIGI` | BM25 harici kod alanı ağırlığı | `1.0` |
| `FTS_MODUL_AGIRLIGI` | BM25 modül alanı ağırlığı | `1.0` |
| `FTS_ARAMA_METNI_AGIRLIGI` | BM25 birleşik arama metni ağırlığı | `1.0` |
| `MAKSIMUM_YEDEK_SAYISI` | Saklanacak yedek sayısı | `10` |
| `YEDEKLEME_ARALIGI_SAAT` | Zamanlanmış yedek aralığı | `24` |

`.env.dev`, `.env.test` ve `.env.prod` dosyaları gizli bilgi içermeyen profil değerlerini taşır. Gizli değerler yalnızca Git dışında tutulan `.env` dosyasına yazılmalıdır.

## Excel Verilerini İçe Aktarma

İçe aktarım sırasında uygulama kapalı olmalıdır.

Yerel Python ortamında varsayılan dosyayı aktarın:

```text
python excel_ice_aktar.py
```

Başka bir `.xlsx` dosyasını aktarın:

```text
python excel_ice_aktar.py veriler/yeni_sss_surumu.xlsx
```

Veritabanındaki aktif veriyi değiştirmeden aktarım farklarını inceleyin:

```text
python excel_ice_aktar.py veriler/yeni_sss_surumu.xlsx --kuru-calistir
```

Geçmiş bir veri sürümünü yeni ve denetlenebilir bir sürüm olarak etkinleştirin:

```text
python excel_ice_aktar.py --surum-geri-al 3
```

Daha önce aktarılmış ancak artık arşivlenmiş bir Excel dosyası yeniden verilirse aktarım açık bir hatayla durur. Aynı veriyi yeniden etkinleştirmek için dosyayı tekrar yüklemek yerine ilgili sürüm numarasıyla `--surum-geri-al` kullanılmalıdır.

Docker ile aktarım:

```text
docker compose build
docker compose run --rm uyds_sohbet_botu_uygulamasi python excel_ice_aktar.py
```

Komut JSON biçiminde şu alanları döndürür:

- `surum_numarasi`
- `aktarilan_kayit_sayisi`
- `olusturulan_parca_sayisi`
- `arsivlenen_kayit_sayisi`
- `eklenen_kayit_sayisi`
- `guncellenen_kayit_sayisi`
- `korunan_kayit_sayisi`
- `yinelenen_dosya`
- `dosya_ozeti`

Kuru çalışma çıktısı toplam, eklenen, güncellenen, korunan ve arşivlenen kayıt sayılarını; dosyanın daha önce görülüp görülmediğini ve SHA-256 özetini döndürür. Geri alma çıktısı hedef ve yeni sürüm numaralarıyla etkinleştirilen, korunan ve arşivlenen kayıt sayılarını döndürür.

Aktarım tamamlandığında düz metin SQLite dosyası AES-256-GCM ile şifrelenir.

## Yerel Vektör Modeli ve Embedding Üretimi

Model hazırlama işlemi yalnızca genel model dosyalarını indirir; UYDS verisini okumaz veya dışarı göndermez. İndirme aracı model kimliğini ve olay öncesi revizyonu sabit tutar, yalnızca izinli dosyaları alır ve resmî LFS SHA-256 değerlerini doğrular:

```text
python vektor_modelini_hazirla.py
```

Model hazırlandıktan sonra aktif SSS parçalarının vektörlerini üretin:

```text
python vektorleri_olustur.py
```

Vektör durumunu modeli belleğe yüklemeden inceleyin:

```text
python vektorleri_olustur.py --durum
```

Seçili modele ait bütün aktif vektörleri yeniden üretin:

```text
python vektorleri_olustur.py --tumunu-yenile
```

Tam yenileme mevcut aktif vektörleri önceden silmez. Model yükleme veya üretim hatasında tamamlanmamış kayıtlar önceki geçerli vektörlerini korur; yalnızca başarıyla üretilen toplu işlemler atomik olarak güncellenir.

Docker kullanırken model hazırlama işlemi ana makinede bir kez yapılır. `modeller/` dizini uygulama konteynerine salt-okunur bağlanır. Normal vektör üretimi `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` ve `HF_DATASETS_OFFLINE` değerlerini zorunlu olarak etkinleştirir.

## Uygulamayı Çalıştırma

Docker:

```text
docker compose up --detach --build
```

### Docker Compose servis yapısı

Docker Desktop içindeki `hadesbot` satırı tek başına bir konteyner değildir. Docker Compose tarafından oluşturulan proje grubudur ve aşağıdaki iki bağımsız konteyneri birlikte gösterir:

| Docker Desktop adı | Compose servisi | Görev |
|---|---|---|
| `uyds_asistani` | `uyds_sohbet_botu_uygulamasi` | FastAPI uygulamasını, sağlık kontrollerini, veritabanı işlemlerini ve yerel vektör modelini çalıştırır. Dışarıya `8000` portunu açar. |
| `hadesbot-uyds_yedekleyici-1` | `uyds_yedekleyici` | Yapılandırılan aralıkta veritabanı ve kurum içi terim haritası yedeklerini oluşturur. Dışarıya HTTP portu açmaz. |

İki konteyner aynı `hadesbot-uygulama:yerel` imajından oluşturulur ancak farklı komutlarla ayrı süreçler olarak çalışır. Aynı Compose ağına ve ana makinedeki `veriler/` dizinine bağlanırlar. Uygulama konteyneri ayrıca `modeller/` dizinini salt-okunur bağlar. Docker Desktop’ta `hadesbot` satırının solundaki ok kullanılarak iki konteyner ayrı ayrı görüntülenebilir.

Servislerin durumunu görüntüleme:

```text
docker compose ps
```

Canlı günlükleri izleme:

```text
docker compose logs --follow
```

Konteynerleri Docker Desktop listesinde tutarak durdurma:

```text
docker compose stop
```

Konteynerleri ve Compose ağını kaldırma:

```text
docker compose down
```

`docker compose down` çalışan konteynerleri durdurur ve Docker Desktop listesinden kaldırır. Oluşturulan imajı, proje kaynaklarını ve ana makinedeki `veriler/` ile `modeller/` dizinlerini silmez. `docker compose up --detach` komutu konteynerleri yeniden oluşturup arka planda başlatır.

Yerel Python:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.13.0+cpu
python -m pip install -r requirements.txt
uvicorn uygulama.ana:uygulama --host 127.0.0.1 --port 8000
```

Linux veya macOS sanal ortam etkinleştirme:

```text
source .venv/bin/activate
```

Mevcut erişim adresleri:

- Sağlık kontrolü: `http://localhost:8000/api/saglik`
- Hazırlık kontrolü: `http://localhost:8000/api/hazirlik`
- Swagger arayüzü: `http://localhost:8000/docs`
- OpenAPI şeması: `http://localhost:8000/openapi.json`

Kök `/` rotası ve kullanıcı arayüzü henüz mevcut değildir.

## API Durumu

### Uygulanan rotalar

| Yöntem | Rota | Açıklama | Yetki |
|---|---|---|---|
| `GET` | `/api/saglik` | Uygulama süreci liveness durumu | Herkese açık |
| `GET` | `/api/hazirlik` | Veritabanı, şema ve FTS5 readiness durumu | Herkese açık |

### Faz 7 ve sonrasında planlanan rotalar

| Yöntem | Rota | Açıklama |
|---|---|---|
| `POST` | `/api/v1/kimlik-dogrulama/giris` | JWT ile kullanıcı girişi |
| `POST` | `/api/v1/arama` | Hibrit SSS araması ve kaynaklı yanıt |
| `POST` | `/api/v1/geri-bildirim` | Yanıta puan ve yorum ekleme |
| `GET` | `/api/v1/yonetici/bekleyen-bildirimler` | Onay kuyruğu |
| `POST` | `/api/v1/yonetici/onay` | Geri bildirim kararı |
| `POST` | `/api/v1/yonetici/excel-yukle` | Yetkili Excel yükleme |
| `GET` | `/api/v1/analitik` | Kullanım istatistikleri |

## Yedekleme ve Geri Yükleme

Tek seferlik yedek:

```text
python yedekle.py yedekle
```

Bir yedeği geri yükleme:

```text
python yedekle.py geri-yukle veri_deposu_YYYYMMDD_HHMMSS_ffffff.db
```

Zamanlanmış yedekleme:

```text
python yedekle.py zamanla --aralik-saat 24
```

Her yedek dosyasının yanında `.manifest.json` uzantılı bir bütünlük manifesti oluşturulur. Manifest; SHA-256 dosya özeti, dosya boyutu, UTC oluşturulma zamanı ve düz metin SQLite yedeklerinde aktif kayıt sayısı, FTS5 satır sayısı, veri sürümü ile `quick_check` sonucunu içerir. Geri yükleme öncesinde manifest varsa dosya adı, boyut ve SHA-256 özeti zorunlu olarak doğrulanır. Eski manifestsiz yedekler geriye dönük uyumluluk için kabul edilir.

Docker Compose içindeki `uyds_yedekleyici` servisi zamanlanmış yedeklemeyi otomatik yürütür. Uygulama ve yedekleyici aynı `VERITABANI_YOLU` ile `ES_ANLAMLILAR_YOLU` değerlerini kullanır. Yapılandırılan açık veya şifreli veritabanı bulunamazsa yedekleme başarısız olur; yalnızca terim dosyasını yedekleyip başarılı görünmez. Geri yükleme ve elle Excel aktarımı öncesinde uygulama durdurulmalıdır.

Veritabanı bağlantıları ve yedekleme süreçler arasında paylaşımlı dosya kilidi taşır. Şifreleme, şifre çözme ve geri yükleme işlemleri özel kilit alarak açık SQLite bağlantılarının tamamlanmasını bekler; böylece uygulama ile yedekleyici aynı veri dosyasında yarışmaz.

## Doğrulama

Sözdizimi ve import derlemesi:

```text
python -m compileall -q uygulama excel_ice_aktar.py yedekle.py vektorleri_olustur.py vektor_modelini_hazirla.py
```

Docker Compose yapılandırması:

```text
docker compose config --quiet
```

Faz 3 doğrulamalarında:

- 2.398 benzersiz SSS kaydı aktarıldı.
- 4.075 mantıksal metin parçası oluşturuldu.
- Aktif kayıt ve FTS5 satır sayıları eşleşti.
- Aynı dosyanın ikinci aktarımı yeni sürüm oluşturmadı.
- Kuru çalışma bilgi tabanına veya veri sürümü geçmişine kayıt eklemedi.
- Tek cevap değişikliği 1 revizyon ve 2.397 korunan kayıt olarak sınıflandırıldı.
- Revizyon kaydı önceki SSS kimliği, revizyon numarası ve değişen alanlarla bağlandı.
- Geçmiş veri sürümü yeni bir sürüm olarak geri alındı ve FTS5 üyeliği eşleşti.
- Yedek manifesti, gerçek geri yükleme ve bozuk yedek reddi doğrulandı.
- Eski Faz 2 şeması veri kaybı olmadan yükseltildi.
- Hatalı MIME, makro uzantısı ve formül içeriği reddedildi.
- Parçalı büyük istek gövdesi 413 yanıtıyla reddedildi.
- Merkezi brute-force sayacı süreçler arasında ve eşzamanlı erişimde doğrulandı.
- Şifreli kapanış sonrasında düz metin veritabanı bırakılmadı.

Faz 4 doğrulamalarında:

- Sabit model revizyonu ve üç büyük LFS dosyasının resmî SHA-256 değerleri doğrulandı.
- Model dizininde çalıştırılabilir özel kod, pickle veya güvensiz ağırlık biçimi bulunmadı.
- Windows Defender özel model taraması tehdit bulmadı.
- Model ağ kapalıyken iki deneme metni için normalize edilmiş 384 boyutlu vektör üretti.
- Gerçek UYDS verisindeki 4.075 parçanın tamamı güncel CPU konteynerinde 126,766 saniyede vektörleştirildi.
- 4.075 vektörün BLOB boyutu, sonlu değerleri ve birim normu doğrulandı.
- İkinci çalıştırma 0 yeni üretim ve 4.075 korunan vektör raporladı.
- Metni değişen tek parçada yalnızca bir vektör yenilendi, pasif kaydın vektörü temizlendi.
- Eski vektör şemasındaki tekrarlar temizlenerek benzersiz parça-model indeksine yükseltildi.
- CPU odaklı Docker imajı yaklaşık 3,10 GB'den 459 MB'ye düşürüldü.
- Konteyner bağımlılık taramasında bilinen güvenlik açığı bulunmadı; yerel `torch==2.13.0+cpu` sürüm eki PyPI çözümlemesi dışında kaldı.
- Uygulama ve yedekleyici salt-okunur kök dosya sistemiyle çalıştırıldı.
- Açık bağlantı sırasında şifreleme denemesi özel kilidin serbest kalmasını bekledi ve veri yarışı oluşmadı.

Faz 5 ve Faz 6 için kalıcı pytest paketi mevcuttur. Toplam 61 test Docker içindeki Python 3.11 çalışma ortamında geçmektedir. Retrieval benchmarkı, başarı metrikleri ve geniş güvenlik doğrulaması Faz 10 kapsamında eklenecektir.

## Proje Yapısı

```text
HadesBot/
├── uygulama/
│   ├── ana.py
│   ├── api/
│   ├── cekirdek/
│   │   ├── gunlukleyici.py
│   │   ├── guvenlik.py
│   │   ├── guvenlik_basliklari.py
│   │   ├── istek_boyutu.py
│   │   ├── istek_sinirlayici.py
│   │   ├── konfigurasyon.py
│   │   ├── onbellek.py
│   │   ├── dosya_kilidi.py
│   │   └── veritabani.py
│   ├── modeller/
│   │   ├── semalar.py
│   │   └── veritabani_modelleri.py
│   ├── sablonlar/
│   ├── servisler/
│   │   ├── akis_servisi.py
│   │   ├── arama_servisi.py
│   │   ├── deepseek_servisi.py
│   │   ├── excel_yukleyici.py
│   │   ├── hibrit_arama.py
│   │   ├── metin_parcalayici.py
│   │   ├── model_guvenligi.py
│   │   ├── oturum_hafizasi.py
│   │   ├── sorgu_genisletici.py
│   │   ├── terim_haritasi.py
│   │   ├── vektor_servisi.py
│   │   └── yeniden_siralayici.py
│   └── statik/
├── testler/
│   ├── test_akis_servisi.py
│   ├── test_arama_servisi.py
│   ├── test_deepseek_servisi.py
│   ├── test_hibrit_arama.py
│   ├── test_oturum_hafizasi.py
│   └── test_sorgu_genisletici.py
├── excel_ice_aktar.py
├── es_anlamlilar.example.json
├── vektor_modelini_hazirla.py
├── vektorleri_olustur.py
├── yedekle.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .env.dev
├── .env.test
├── .env.prod
└── README.md
```

`api/`, `sablonlar/` ve `statik/` dizinlerinin işlevsel içerikleri ilgili gelecek fazlarda eklenecektir. Faz 5 ve Faz 6 servis testleri `testler/` dizininde bulunmaktadır.

## Bilinen Sınırlamalar

- Yalnızca sağlık ve hazırlık kontrolü rotaları uygulanmıştır.
- FTS5 BM25 ile yerel vektör benzerliğini RRF üzerinden birleştiren Faz 5 çekirdek hibrit arama hazırdır.
- Cross-Encoder model seçimi, Türkçe retrieval benchmarkı ile ölçülmek üzere ertelenmiştir.
- Faz 6 yanıt üretimi servis katmanında hazırdır; kullanıcıya açık SSE HTTP rotası Faz 7 kapsamında eklenecektir.
- Gerçek DeepSeek sağlayıcı çağrısı kurum onaylı API anahtarı olmadığı için yerel kabul turunda yapılmamıştır.
- Kimlik doğrulama servisleri hazır olsa da HTTP giriş rotası henüz yoktur.
- Kullanıcı arayüzü, yönetici paneli ve analitik ekranları henüz yoktur.
- Desteklenen varsayılan dağıtım tek Uvicorn worker kullanır.
- Veritabanı çalışma sırasında düz metin SQLite olarak açıktır ve temiz kapanışta şifrelenir.
- Mantıksal anahtarı birden fazla aktif kayda karşılık gelen belirsiz gruplar otomatik revizyon zincirine bağlanmaz; yanlış eşleşmeyi önlemek için ekleme ve arşivleme olarak işlenir.
- Kalıcı otomatik test paketi Faz 10’da oluşturulacaktır.

## Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Ayrıntılar `LICENSE` dosyasındadır.
