# UYDS Akıllı SSS Destek Asistanı

[![Faz 1-14 doğrulama](https://github.com/mecik-arda/UYDS-SSS-hades-bot/actions/workflows/faz1-14-dogrulama.yml/badge.svg)](https://github.com/mecik-arda/UYDS-SSS-hades-bot/actions/workflows/faz1-14-dogrulama.yml)
[![CodeQL](https://github.com/mecik-arda/UYDS-SSS-hades-bot/actions/workflows/codeql.yml/badge.svg)](https://github.com/mecik-arda/UYDS-SSS-hades-bot/actions/workflows/codeql.yml)

Sürüm 1.0.0 | Faz 1-9 ve 12-14 tamamlandı, Faz 10 ölçüm altyapısı ve Faz 11 çekirdek hattı tamamlandı | Geliştirme sürümü | MIT Lisansı

## Proje Durumu

HadesBot, UYDS Sık Sorulan Sorular verilerini güvenli biçimde hazırlayan, anlamsal olarak aranabilir hale getiren ve kaynak kontrollü yanıt üreten kurumsal bir destek asistanı olarak geliştirilmektedir.

Mevcut sürüm; güvenli uygulama altyapısını, SQLite ve FTS5 veri katmanını, Excel içe aktarımını, veri sürümlemeyi, metin parçalamayı, yerel anlamsal vektör üretimini, sorgu genişletmeyi, RRF tabanlı hibrit aramayı, güvenli ve isteğe bağlı Cross-Encoder yeniden sıralama katmanını, kaynak kontrollü DeepSeek istemcisini, güven eşiği kapısını, SSE olay üretimini, kullanıcıya bağlı oturum hafızasını, kimlik doğrulamalı API rotalarını, yönetici onaylı alternatif soru öğrenme döngüsünü, responsive kurumsal web arayüzünü, PII maskeleme ve veri saklama süresi temizliğini (Faz 12), RBAC rol bazlı arama filtrelemeyi, DeepSeek API çökme durumunda çevrimdışı yedekleme modunu ve niyet sınıflandırma tabanlı aksiyon butonlarını (Faz 13) içerir. Cross-Encoder varsayılan olarak kapalıdır; üretimde etkinleştirilmesi Faz 10 Türkçe arama karşılaştırması ve kaynak ölçümü sonucuna bağlıdır.

Faz 11 çekirdek hattı, yerel PDF/DOCX/HTML/XLSX belgelerini otomatik olarak ayıklar, yapısal parçalara böler, yerel modelle vektörler ve sürümlemeli belge deposuna yazar. Belge FTS ve vektör sonuçları ACL ve tarihsel sürüm filtresinden sonra mevcut SSS sonuçlarıyla RRF üzerinden birleşerek kaynak kontrollü RAG akışına katılır.

| Faz | Kapsam | Durum |
|---|---|---|
| Faz 1 | Ortam, Docker, yapılandırma ve güvenlik altyapısı | Tamamlandı |
| Faz 2 | SQLite, FTS5, veri modelleri ve şifreleme | Tamamlandı |
| Faz 3 | Excel aktarımı, sürümleme ve metin parçalama | Tamamlandı |
| Faz 4 | Vektör gömmeleri ve kurum içi terim haritası | Tamamlandı |
| Faz 5 | Sorgu genişletme, hibrit arama, RRF ve güvenli Cross-Encoder katmanı | Tamamlandı; Cross-Encoder üretim aktivasyonu karşılaştırma ölçümünü bekliyor |
| Faz 6 | DeepSeek, kaynak kontrollü RAG, SSE ve oturum hafızası | Tamamlandı; canlı bağlantı sentetik ve kurum onaylı gerçek kaynaklarla doğrulandı |
| Faz 7 | API rotaları, kimlik doğrulama ve merkezi hata yönetimi | Tamamlandı |
| Faz 8 | Alternatif soru öğrenme döngüsü ve genişletilmiş analitik iş akışı | Tamamlandı |
| Faz 9 | Kurumsal web arayüzü | Tamamlandı; sohbet, tam işlevli yönetici işletim merkezi ve gelişmiş analitik ekranı |
| Faz 10 | Arama karşılaştırması, kabul ölçümleri ve geniş güvenlik doğrulaması | Ölçüm ve güvenlik altyapısı tamamlandı; en az 50 uzman etiketli arama senaryosu bekleniyor |
| Faz 11 | Veri Ambarı ve Çoklu Veri Kaynağı Entegrasyonu | Çekirdek tamamlandı; belge ETL, yapısal parçalama, yerel vektörleme, sürüm/silme yönetimi, zamanlayıcı, ACL'li belge araması, tarihsel sürüm seçimi, graf bonusu ve analitik paneli çalışıyor; harici SharePoint/Confluence ve Neo4j adaptörleri ileri ölçek adımıdır |
| Faz 12 | Veri Gizliliği ve Analitik Kayıt Yönetimi | Tamamlandı; PII maskeleme, otomatik veri temizliği, yönetici gizlilik kontrolü |
| Faz 13 | Gelişmiş Kurumsal Yetenekler (RBAC, Fallback, Niyet Sınıflandırma) | Tamamlandı; rol bazlı arama filtresi, çevrimdışı yedekleme modu, niyet tabanlı aksiyon butonları |
| Faz 14 | Otomatik e-posta raporlama | Tamamlandı; haftalık HTML ve düz metin istatistik raporu, STARTTLS ve zamanlayıcı |

## Veri Gizliliği

UYDS Excel dosyaları, soru-cevap içerikleri, SQLite veritabanları, vektör kayıtları, günlükler, yedekler ve proje çıktıları özel kurumsal veridir. Bu dosyalar GitHub, kişisel bulut depolama, e-posta veya harici dosya paylaşım servislerine aktarılmamalıdır.

`veriler/`, `yedekler/` ve `modeller/` dizinleri sürüm kontrolünden çıkarılmıştır. Kurum içi terim haritasının gerçek içeriği de yalnızca `veriler/es_anlamlilar.json` dosyasında yerel olarak tutulur. Depodaki `es_anlamlilar.example.json` sadece kurumsal veri içermeyen bir şablondur. Gerçek veri yalnızca yetkili yerel çalışma ortamında tutulmalıdır. UYDS metinleri vektör üretimi sırasında dış servislere gönderilmez.

Faz 6 canlı yanıt üretimi etkinleştirildiğinde yalnızca güven eşiğini geçen ilk kaynak parçaları, kullanıcı sorusu ve sınırlı oturum geçmişi yapılandırılmış DeepSeek API adresine gönderilir. Üretim profilinde hedef alan adı ayrıca `DEEPSEEK_IZINLI_ALAN_ADLARI` listesinde bulunmak zorundadır. Bu özellik kurumun veri işleme ve dış servis politikası onaylanmadan etkinleştirilmemelidir. `DEEPSEEK_API_ANAHTARI` boş bırakıldığında dış çağrı yapılamaz; düşük güvenli sorularda anahtar bulunsa bile DeepSeek çağrısı yapılmaz ve kaynak kimlikleri istemciye açıklanmaz.

Şifreli veritabanı yalnızca oluşturulurken kullanılan `VERITABANI_SIFRELEME_ANAHTARI` ile açılabilir. Mevcut bir `.db.enc` dosyası varken yeni anahtar üretmek veriyi kurtarmaz. Anahtar değişikliği veya veritabanı yeniden oluşturma öncesinde `.env`, `.db.enc`, kaynak Excel ve kurum içi terim haritası birlikte erişimi kısıtlı yerel bir kurtarma yedeğine alınmalıdır. `yedekler/` altında tutulan kurtarma kopyaları sır ve kurumsal veri içerir; Git'e eklenmemeli veya paylaşılmamalıdır.

## Faz 13 Yeni Özellikler

### RBAC Rol Bazlı Arama Filtreleme

Arama motoru seviyesinde veri sızıntısı koruması. `sss_kayitlari` tablosundaki `kullanici_rolu` alanı, FTS5 ve vektör arama sorgularına `WHERE` koşulu olarak eklenir. Yönetici olmayan kullanıcılar yalnızca kendi yetki seviyelerine uygun veya rol belirtilmemiş SSS kayıtlarını görebilir. Yöneticiler tüm kayıtlara erişebilir.

### Çevrimdışı Yedekleme Modu (Offline Fallback)

DeepSeek API bağlantısı koptuğunda veya zaman aşımına uğradığında, sistem 500 hatası yerine en yüksek skorlu kaynakları doğrudan kullanıcıya listeleyen bir yedekleme modu sunar. `YEDEK_KAYNAK_SAYISI` (varsayılan: 3) kadar kaynak `yedek` SSE olayıyla iletilir. Ön yüzde "Yapay zeka şu anda yanıt veremiyor, işte en alakalı kaynaklar" mesajı gösterilir.

### Niyet Sınıflandırma ve Aksiyon Butonları

Anahtar kelime ve regex tabanlı hafif niyet tespit motoru (`uygulama/servisler/niyet_siniflandirici.py`). "Şifremi sıfırla", "Destek bileti aç" gibi kilit sorgular tespit edildiğinde, SSE `eylem` olayı ile aksiyon butonları ön yüze iletilir. Niyet eylemleri `veriler/niyet_eylemleri.json` dosyasından yapılandırılır. Örnek şablon `veriler/niyet_eylemleri.example.json` olarak depoda bulunur. Özellik varsayılan olarak kapalıdır; şablondaki hedefler kurumun gerçek ve erişilebilir rotalarıyla değiştirildikten sonra etkinleştirilmelidir. Etkin durumda eksik, sembolik bağlantı olan veya boyut sınırını aşan yapılandırma uygulama başlangıcında reddedilir.

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `YEDEK_KAYNAK_SAYISI` | Yedekleme modunda gösterilecek kaynak sayısı | `3` |
| `NIYET_SINIFLANDIRMA_AKTIF` | Geçerli eylem dosyası hazırlandıktan sonra niyet sınıflandırmayı etkinleştirir | `false` |
| `NIYET_GUVEN_ESIGI` | Niyet eşleşmesi için asgari güven skoru | `0.80` |
| `NIYET_EYLEMLERI_YOLU` | Niyet eylem yapılandırma dosyası | `veriler/niyet_eylemleri.json` |

## Planlanan Özellikler

- En az 50 uzman etiketli Türkçe arama senaryosunun hazırlanması; Top-1, Top-3, MRR@10, nDCG@10, p95 gecikme ve kaynak gösterme kabulünün çalıştırılması
- Türkçe arama karşılaştırması sonrasında Cross-Encoder üretim aktivasyonu ve aday sayısı ayarı
- **Faz 11 ileri ölçek adaptörleri:** Kurumsal kimlik doğrulamalı SharePoint/Confluence bağlayıcıları ile 10.000 graf düğümü veya karmaşık graf sorgusu eşiğinde Neo4j adaptörü. Yerel dosya ETL, ACL'li belge RAG ve hafif graf katkısı hazırdır. Detaylar için `FAZ11_MIMARI_VIZYON.md`.

## Son İyileştirmeler (Hotfix ve Ince Ayarlar)
- TensorFlow ve Keras 3 uyumluluk sorunlarını gidermek için `tf-keras` ve `protobuf` bağımlılıkları ortamda güncellendi.
- Geçerli ancak kısa soruların reddedilmesini önlemek amacıyla `GUVEN_ESIGI` (Kosinüs Benzerliği) değeri `0.70` seviyesinden `0.50` seviyesine optimize edildi ve bu değişiklik `hata_duzeltme_kaydi.md` kütüğüne işlendi.
- Faz 13 eklendi: RBAC rol bazlı arama filtreleme, DeepSeek API çökme durumunda çevrimdışı yedekleme modu, niyet sınıflandırma tabanlı aksiyon butonları.
- `pyproject.toml` güncellendi: pytest önbellek sağlayıcısı devre dışı bırakıldı (Windows `Erişim engellendi` uyarısı giderildi).

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
| Yeniden sıralama | Sentence-Transformers Cross-Encoder | Güvenli yerel entegrasyon hazır; üretim aktivasyonu karşılaştırma ölçümünü bekliyor |
| LLM istemcisi | HTTPX ve DeepSeek Chat Completions API | Aktif; sentetik ve kurum onaylı gerçek kaynaklarla canlı bağlantı doğrulandı |
| Web arayüzü | Jinja2, HTML, CSS ve JavaScript | Aktif |

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
copy veriler\niyet_eylemleri.example.json veriler\niyet_eylemleri.json
```

Linux veya macOS:

```text
cp .env.example .env
mkdir -p veriler
cp es_anlamlilar.example.json veriler/es_anlamlilar.json
cp veriler/niyet_eylemleri.example.json veriler/niyet_eylemleri.json
```

`.env` içinde en az şu üç değeri güçlü ve benzersiz değerlerle değiştirin:

- `VERITABANI_SIFRELEME_ANAHTARI`
- `JWT_GIZLI_ANAHTARI`
- `VARSAYILAN_YONETICI_SIFRESI`

DeepSeek anahtarı doğrudan ortam değişkeni yerine salt okunur dosyadan verilecekse anahtarı Git tarafından dışlanan `sirlar/` dizininde tutun, `DEEPSEEK_API_ANAHTAR_DOSYASI=/run/secrets/deepseek_api_anahtari` değerini ayarlayın ve `DEEPSEEK_API_ANAHTARI` değerini boş bırakın. Docker Compose, `sirlar/` dizinini konteynere `/run/secrets` konumunda salt okunur bağlar. Anahtar dosyası sembolik bağlantı olamaz ve 4096 baytı aşamaz.

Orijinal çalışma kitabını aşağıdaki konuma yerleştirin:

```text
veriler/UYDS_SSS_Listesi.xlsx
```

Gerçek Excel dosyasını Git'e eklemeyin.

`veriler/es_anlamlilar.json` içeriğini yalnızca yetkili yerel ortamda kurum terimleriyle düzenleyin. Uygulama bu dosya eksikse örnek veya varsayılan kurumsal içerik kullanmaz ve açık hata verir. Niyet sınıflandırma varsayılan olarak kapalıdır. Etkinleştirilmeden önce `veriler/niyet_eylemleri.json` oluşturulmalı, şablondaki örnek hedefler gerçek kurum rotalarıyla değiştirilmeli ve her hedefin erişilebilir olduğu doğrulanmalıdır.

## Yapılandırma

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `ORTAM_PROFILI` | Etkin ortam profili | `prod` |
| `DEEPSEEK_API_ANAHTARI` | Canlı DeepSeek yanıtı için kurum onaylı anahtar | Boş |
| `DEEPSEEK_API_ANAHTAR_DOSYASI` | Yeniden başlatmasız rotasyon için salt okunur anahtar dosyası | Boş |
| `DEEPSEEK_API_ADRESI` | HTTPS Chat Completions uç noktası | `https://api.deepseek.com/chat/completions` |
| `DEEPSEEK_MODEL_ADI` | Kullanılacak DeepSeek model kimliği | `deepseek-v4-pro` |
| `DEEPSEEK_ZAMAN_ASIMI_SANIYE` | Dış API istek zaman aşımı | `120` |
| `DEEPSEEK_YENIDEN_DENEME_SAYISI` | Geçici hata sonrası ek deneme sayısı | `2` |
| `DEEPSEEK_YENIDEN_DENEME_TABAN_SANIYE` | Üstel beklemenin başlangıç süresi | `0.5` |
| `DEEPSEEK_KAYNAK_SAYISI` | Yanıt üretimine gönderilecek azami kaynak | `5` |
| `DEEPSEEK_KAYNAK_MAKS_KARAKTER` | Kaynak başına bağlam karakter sınırı | `6000` |
| `DEEPSEEK_IZINLI_ALAN_ADLARI` | Üretimde kullanılabilecek virgülle ayrılmış API alan adları | `api.deepseek.com` |
| `DEEPSEEK_YANIT_MAKS_KARAKTER` | Tek yanıtta alınabilecek azami toplam karakter | `32768` |
| `DEEPSEEK_AKIS_MAKS_SANIYE` | Tek canlı akışın azami toplam süresi | `180` |
| `DEEPSEEK_AKIS_PARCA_ASGARI_KARAKTER` | SSE'ye aktarılmadan önce birleştirilecek asgari DeepSeek karakter sayısı | `24` |
| `VERITABANI_YOLU` | SQLite dosya yolu | `veriler/veri_deposu.db` |
| `VERITABANI_SIFRELEME_ANAHTARI` | En az 32 karakterli şifreleme anahtarı | Zorunlu |
| `GUVEN_ESIGI` | DeepSeek çağrısı için `0.0`–`1.0` arası asgari kosinüs benzerliği | `0.70` |
| `VEKTOR_MODEL_ADI` | Veritabanında saklanan model kimliği | `paraphrase-multilingual-MiniLM-L12-v2` |
| `VEKTOR_MODEL_YOLU` | Doğrulanmış yerel model dizini | `modeller/paraphrase-multilingual-MiniLM-L12-v2` |
| `VEKTOR_BOYUTU` | Beklenen embedding boyutu | `384` |
| `VEKTOR_TOPLU_ISLEM_BOYUTU` | Tek model çağrısında işlenen parça sayısı | `32` |
| `ES_ANLAMLILAR_YOLU` | Kuruma özel terim haritası | `veriler/es_anlamlilar.json` |
| `JWT_GIZLI_ANAHTARI` | En az 32 karakterli JWT anahtarı | Zorunlu |
| `JWT_ALGORITMASI` | JWT imza algoritması | `HS256` |
| `JWT_OMRU_DAKIKA` | Erişim belirteci ömrü | `30` |
| `JWT_YENILEME_OMRU_GUN` | Yenileme belirteci ömrü | `7` |
| `JWT_ANAHTAR_KIMLIGI` | Etkin JWT imza anahtarı kimliği | `ana-1` |
| `JWT_ONCEKI_GIZLI_ANAHTAR` | Rotasyon sırasında doğrulanacak önceki JWT anahtarı | Boş |
| `JWT_ONCEKI_ANAHTAR_KIMLIGI` | Önceki JWT anahtarı kimliği | Boş |
| `YONETICI_ISTEK_IMZA_ANAHTARI` | Kritik yönetici isteklerinin HMAC anahtarı; boşsa JWT anahtarı kullanılır | Boş |
| `YONETICI_IMZA_ZAMAN_PENCERESI_SANIYE` | Yönetici imzası zaman toleransı | `300` |
| `VARSAYILAN_YONETICI_SIFRESI` | En az 12 karakterli yönetici parolası | Zorunlu |
| `ISTEK_SINIRI` | Pencere başına istek sayısı | `100` |
| `ISTEK_PENCERESI_SANIYE` | İstek sınırı penceresi | `60` |
| `UYGULAMA_PORT` | Dış HTTP portu | `8000` |
| `MESAJ_MAKS_KARAKTER` | Kullanıcı mesajı karakter sınırı | `2000` |
| `DEEPSEEK_MAKS_TOKEN` | LLM çıktı token sınırı | `4096` |
| `GUNLUK_MESAJ_KOTASI` | Kullanıcı başına günlük arama kotası | `500` |
| `OTURUM_MAKS_MESAJ` | Oturum başına saklanan mesaj sınırı | `50` |
| `OTURUM_TTL_DAKIKA` | Hareketsiz oturum yaşam süresi | `30` |
| `OTURUM_MAKS_SAYI` | Bellekte tutulacak toplam oturum sınırı | `1000` |
| `ESZAMANLI_AKIS_MAKS_SAYI` | Aynı anda işlenebilecek SSE akış sayısı | `10` |
| `UYGULAMA_WORKER_SAYISI` | Bellek içi oturum sahipliği için zorunlu worker sayısı | `1` |
| `GUVENLIK_BAKIM_ARALIGI_SAAT` | Süresi dolmuş güvenlik kayıtlarının bakım aralığı | `6` |
| `ISTEK_GOVDE_MAKS_BOYUT` | Genel istek gövdesi sınırı | `1048576` |
| `DOSYA_YUKLEME_MAKS_BOYUT` | Excel yükleme sınırı | `52428800` |
| `LOG_SEVIYESI` | Günlük seviyesi | `INFO` |
| `API_DOKUMANTASYONU_AKTIF` | Swagger, ReDoc ve HTTP OpenAPI şemasını yayımlar; üretimde varsayılan kapalıdır | `false` |
| `RRF_K` | Reciprocal Rank Fusion sabiti | `60` |
| `FTS_ADAY_SAYISI` | FTS5 tarafından alınacak azami aday | `50` |
| `VEKTOR_ADAY_SAYISI` | Vektör aramasından alınacak azami aday | `50` |
| `RRF_ADAY_SAYISI` | Harmanlama sonrasında korunacak azami aday | `20` |
| `ALTERNATIF_SORU_ADAY_SAYISI` | Alternatif soru kanalından alınacak azami aday | `5` |
| `ALTERNATIF_SORU_BENZERLIK_ESIGI` | Alternatif sorunun RRF birleştirmesine katılacağı en düşük kosinüs benzerliği | `0.70` |
| `YENIDEN_SIRALAMA_ETKIN` | Cross-Encoder yeniden sıralamayı etkinleştirir | `false` |
| `YENIDEN_SIRALAMA_MODEL_YOLU` | Doğrulanmış yerel Cross-Encoder model dizini | `modeller/mmarco-mMiniLMv2-L12-H384-v1` |
| `YENIDEN_SIRALAMA_ADAY_SAYISI` | Cross-Encoder ile skorlanacak ilk RRF adayı sayısı | `10` |
| `YENIDEN_SIRALAMA_TOPLU_ISLEM_BOYUTU` | Tek Cross-Encoder çağrısındaki sorgu-aday çifti sayısı | `8` |
| `YENIDEN_SIRALAMA_MAKS_TOKEN` | Cross-Encoder sorgu-aday çifti token sınırı | `512` |
| `FTS_SORU_AGIRLIGI` | BM25 soru alanı ağırlığı | `1.0` |
| `FTS_CEVAP_AGIRLIGI` | BM25 cevap alanı ağırlığı | `1.0` |
| `FTS_KATEGORI_AGIRLIGI` | BM25 kategori alanı ağırlığı | `1.0` |
| `FTS_HARICI_KOD_AGIRLIGI` | BM25 harici kod alanı ağırlığı | `1.0` |
| `FTS_MODUL_AGIRLIGI` | BM25 modül alanı ağırlığı | `1.0` |
| `FTS_ARAMA_METNI_AGIRLIGI` | BM25 birleşik arama metni ağırlığı | `1.0` |
| `YEDEK_KAYNAK_SAYISI` | Yedekleme modunda gösterilecek azami kaynak sayısı | `3` |
| `NIYET_SINIFLANDIRMA_AKTIF` | Geçerli ve kurum rotalarına uyarlanmış eylem dosyasıyla niyet motorunu etkinleştirir | `false` |
| `NIYET_GUVEN_ESIGI` | Niyet eşleşmesi için asgari güven skoru | `0.80` |
| `NIYET_EYLEMLERI_YOLU` | Niyet eylem yapılandırma dosyası | `veriler/niyet_eylemleri.json` |
| `MAKSIMUM_YEDEK_SAYISI` | Saklanacak yedek sayısı | `10` |
| `YEDEKLEME_ARALIGI_SAAT` | Zamanlanmış yedek aralığı | `24` |

Tablodaki değerler uygulama ve Docker Compose varsayılanlarını gösterir. Geliştirme için sunulan `.env.example`, `ORTAM_PROFILI=dev` ve `LOG_SEVIYESI=DEBUG` değerleriyle bu iki varsayılanı bilinçli olarak geçersiz kılar.

`.env.dev`, `.env.test` ve `.env.prod` dosyaları uygulamanın otomatik yüklediği, Git tarafından takip edilen ve yalnızca gizli olmayan profil değerlerini taşıyan dosyalardır; bu dosyalara hiçbir zaman API anahtarı, parola veya şifreleme anahtarı yazılmamalıdır. Gizli değerler Git dışında tutulan `.env`, salt okunur `sirlar/` dosyaları veya kurumun yetkili secret sağlayıcısı üzerinden verilmelidir. `.env` ignore edilirken `.env.example` güvenli kurulum şablonu olarak sürüm kontrolünde tutulur.

Her yapılandırma anahtarı `.env` içinde yalnızca bir kez tanımlanmalıdır. Özellikle `ORTAM_PROFILI`, `VERITABANI_YOLU` ve `VERITABANI_SIFRELEME_ANAHTARI` için yinelenen tanımlar profil dosyalarının beklenmeyen sırayla uygulanmasına veya yanlış şifreli veritabanının seçilmesine neden olabilir. Mevcut şifreli veritabanı taşınırken standart yol `veriler/veri_deposu.db` olarak korunmalı ve aynı şifreleme anahtarı kullanılmalıdır.

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

Model ve vektör komutlarını proje sanal ortamında veya Docker imajında çalıştırmak önerilir. Paylaşımlı bir Python ortamındaki ilgisiz TensorFlow/protobuf paketleri `transformers` yüklemesini bozarsa temiz proje ortamı kullanılmalıdır. Yalnızca PyTorch tabanlı tek seferlik yerel üretimde `USE_TF=0` ve `TRANSFORMERS_NO_TF=1` ortam değişkenleriyle TensorFlow entegrasyonu kapatılabilir; bu değerler üretim yapılandırmasının zorunlu parçası değildir.

## Yerel Cross-Encoder Yeniden Sıralama

Cross-Encoder varsayılan olarak kapalıdır. Sabit revizyonlu ve SHA-256 doğrulamalı model dosyalarını kurum verisi okumadan yerel dizine hazırlayın:

```text
python yeniden_siralama_modelini_hazirla.py
```

Türkçe arama karşılaştırması doğruluk, p50/p95 gecikme ve tepe bellek açısından kabul edilebilir sonuç verirse `.env` içinde etkinleştirin:

```text
YENIDEN_SIRALAMA_ETKIN=true
```

Uygulama yalnızca ilk `YENIDEN_SIRALAMA_ADAY_SAYISI` RRF adayını yeniden skorlar. Model bulunamaz, bütünlük denetiminden geçemez veya geçersiz skor üretirse istek başarısız edilmez; özgün RRF sırası korunur ve yeniden sıralamanın uygulanmadığı sonuç teşhisine yazılır. Model yükleme çalışma zamanında çevrimdışıdır, uzaktan model koduna izin verilmez ve pickle ağırlıkları kabul edilmez.

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

İki konteyner aynı `hadesbot-uygulama:yerel` imajından oluşturulur ancak farklı komutlarla ayrı süreçler olarak çalışır. Aynı Compose ağına ve ana makinedeki `veriler/` dizinine bağlanırlar. Uygulama konteyneri ayrıca `modeller/` dizinini salt-okunur bağlar. Docker Desktop'ta `hadesbot` satırının solundaki ok kullanılarak iki konteyner ayrı ayrı görüntülenebilir.

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

- Sohbet arayüzü: `http://localhost:8000/`
- Yönetici merkezi: `http://localhost:8000/yonetici`
- Analitik görünümü: `http://localhost:8000/analitik`
- Sağlık kontrolü: `http://localhost:8000/api/saglik`
- Hazırlık kontrolü: `http://localhost:8000/api/hazirlik`
- Swagger arayüzü: geliştirme ve test profilinde `http://localhost:8000/docs`
- OpenAPI şeması: geliştirme ve test profilinde `http://localhost:8000/openapi.json`

Üretim profilinde Swagger, ReDoc ve HTTP OpenAPI şeması anonim saldırı yüzeyini azaltmak için varsayılan olarak yayımlanmaz. Gerektiğinde `API_DOKUMANTASYONU_AKTIF=true` yalnızca erişimi sınırlı bir yönetim ortamında kullanılmalıdır.

Web arayüzü açıldığında kimlik doğrulama penceresi gösterilir. Kullanıcı rolü sohbet ekranına; `YONETICI` rolü ayrıca yönetici ve analitik panellerine erişir. Erişim ve yenileme belirteçleri yalnızca geçerli tarayıcı sekmesi oturumunda tutulur.

Yönetici merkezi; geri bildirim onaylama/reddetme, doğru SSS kaydı seçme, SSS kataloğunda arama ve sayfalama, cevapsız sorgu sayfalama, FTS/vektör yeniden indeksleme, tam veya artımlı belge senkronizasyonu, haftalık e-posta raporu gönderimi ve tüm otomasyonların gizli değer açıklamayan durum envanterini sunar. Excel içe aktarma, veri sürümü geri alma ve şifreli yedek geri yükleme canlı SQLite bağlantılarıyla yarışmaması için ekranda bakım aracı olarak gösterilir ve uygulama süreci içinden tetiklenmez.

## API Durumu

### Uygulanan rotalar

| Yöntem | Rota | Açıklama | Yetki |
|---|---|---|---|
| `GET` | `/api/saglik` | Uygulama süreci liveness durumu | Herkese açık |
| `GET` | `/api/hazirlik` | Veritabanı, şema ve FTS5 readiness durumu | Herkese açık |
| `POST` | `/api/v1/kimlik-dogrulama/giris` | Erişim ve yenileme belirteci üretir | Herkese açık |
| `POST` | `/api/v1/kimlik-dogrulama/yenile` | Refresh token rotasyonu yapar | Geçerli refresh token |
| `POST` | `/api/v1/kimlik-dogrulama/cikis` | Token ailesini ve oturumları iptal eder | Kullanıcı |
| `POST` | `/api/v1/arama` | Hibrit arama ve kaynak kontrollü SSE yanıtı | Kullanıcı |
| `GET` | `/api/v1/sss` | Aktif SSS özetlerini sayfalar | Kullanıcı |
| `POST` | `/api/v1/geri-bildirim` | Puan ve yorum kaydeder | Kullanıcı |
| `GET` | `/api/v1/yonetici/geri-bildirimler` | Bekleyen geri bildirimleri listeler | Yönetici |
| `GET` | `/api/v1/yonetici/cevapsiz-sorgular` | Cevapsız veya düşük güvenli sorguları sayfalı listeler | Yönetici |
| `POST` | `/api/v1/yonetici/geri-bildirim/onay` | Geri bildirimi onaylar veya reddeder; yönetici doğru SSS seçimini değiştirebilir | Yönetici ve HMAC |
| `POST` | `/api/v1/yonetici/yeniden-indeksle` | FTS ve vektör indekslerini yeniler | Yönetici ve HMAC |
| `POST` | `/api/v1/yonetici/islem-imzasi` | İzinli tarayıcı yönetici işlemi için tek kullanımlı imza üretir | Yönetici |
| `GET` | `/api/v1/yonetici/isletim-durumu` | Arama, belge, veri yönetimi ve otomasyon durumunu gizli değerler olmadan döndürür | Yönetici |
| `POST` | `/api/v1/yonetici/olcum/arama` | Altın veri seti ölçümü için LLM çağırmadan ilk 10 sıralı SSS kimliğini döndürür | Yönetici |
| `POST` | `/api/v1/yonetici/senkronizasyon` | Tam veya artımlı belge senkronizasyonu başlatır | Yönetici ve HMAC |
| `POST` | `/api/v1/yonetici/eposta-raporu/gonder` | Yapılandırılmış haftalık raporu gönderir | Yönetici ve HMAC |
| `GET` | `/api/v1/analitik` | Kullanım istatistiklerini döndürür | Yönetici |
| `GET` | `/api/v1/analitik/belge-surumleri` | Belge sürüm zincirini listeler | Yönetici |
| `GET` | `/api/v1/analitik/parca-istatistikleri` | Yapısal parça ve token istatistiklerini döndürür | Yönetici |
| `GET` | `/api/v1/analitik/sorgu-trendi` | Son 30 günlük sorgu ve cevaplanma trendini döndürür | Yönetici |
| `GET` | `/api/v1/analitik/yetim-kavramlar` | Bağlantısız graf kavramlarını listeler | Yönetici |
| `GET` | `/api/v1/analitik/rapor/dokuman` | Birleşik doküman analitik raporunu döndürür | Yönetici |

### Yönetici istek imzası

Kritik yönetici POST isteklerinde geçerli yönetici JWT'sine ek olarak `X-UYDS-Zaman`, `X-UYDS-Nonce` ve `X-UYDS-Imza` başlıkları zorunludur. Zaman değeri Unix saniyesidir. Nonce 32-128 karakter uzunluğunda ve her istek için benzersiz olmalıdır. İmza, aşağıdaki beş değerin satır sonuyla birleştirilmiş UTF-8 metni üzerinde HMAC-SHA256 olarak hesaplanır:

```text
X-UYDS-Zaman
X-UYDS-Nonce
HTTP_YONTEMI
/api/v1/hedef-yol
ISTEK_GOVDESI_SHA256
```

İmza anahtarı `YONETICI_ISTEK_IMZA_ANAHTARI` değeridir; bu değer boşsa `JWT_GIZLI_ANAHTARI` kullanılır. Süresi geçen zaman damgaları reddedilir ve kabul edilen nonce özetleri SQLite üzerinde saklanarak tekrar kullanım `409` yanıtıyla engellenir.

Tarayıcı arayüzü gizli HMAC anahtarını almaz. Geçerli yönetici JWT'siyle yalnızca sunucu izin listesindeki hedef yol ve bire bir istek gövdesi için kısa ömürlü, tek kullanımlı imza ister; dönen nonce kritik işlemde tüketilir.

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
python -m compileall -q uygulama excel_ice_aktar.py yedekle.py vektorleri_olustur.py vektor_modelini_hazirla.py yeniden_siralama_modelini_hazirla.py
```

Docker Compose yapılandırması:

```text
docker compose config --quiet
```

Geliştirme bağımlılıklarını ve kalıcı doğrulamaları çalıştırma:

```text
python -m pip install -r requirements-dev.txt
python -m pytest -q
ruff check uygulama testler
bandit -r uygulama -q
python -m pip_audit
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
- Konteyner bağımlılık taramasında düzeltmesi bulunan kritik veya yüksek güvenlik açığı bulunmadı; yerel `torch==2.13.0+cpu` sürüm eki PyPI çözümlemesi dışında kaldı.
- Uygulama ve yedekleyici salt-okunur kök dosya sistemiyle çalıştırıldı.
- Açık bağlantı sırasında şifreleme denemesi özel kilidin serbest kalmasını bekledi ve veri yarışı oluşmadı.

Son yerel işletim doğrulamasında:

- Yinelenen `.env` tanımları kaldırıldı; etkin profil `prod`, standart veritabanı yolu `veriler/veri_deposu.db` olarak doğrulandı.
- Açılabilir şifreli veritabanının SQLite bütünlük kontrolü `ok` verdi ve kurtarma kopyaları alınmadan hiçbir mevcut dosyanın üzerine yazılmadı.
- Gerçek çalışma kitabından 2.398 benzersiz SSS ve 4.075 aktif metin parçası yeniden oluşturuldu.
- Yerel MiniLM modeliyle 4.075 parçanın tamamı vektörleştirildi; eksik, geçersiz veya pasif vektör kalmadı.
- Uygulama gerçek şifreli veritabanıyla başlatıldı; liveness, readiness, ön yüz ve yönetici girişi başarıyla doğrulandı.
- DeepSeek anahtarı devre dışı bırakılarak sentetik bir SSE sohbet akışı uçtan uca tamamlandı; bu doğrulamada kurumsal içerik dış servise gönderilmedi.
- Kapanış sonrasında düz metin SQLite dosyası bırakılmadı ve kalıcı durum yalnızca şifreli `.db.enc` dosyasında tutuldu.

Canlı DeepSeek doğrulamasında:

- `deepseek-v4-pro` modeli sentetik soru ve kaynakla gerçek API üzerinde yanıt ve kaynak atfı üretti.
- Kurum sahibinin açık veri işleme onayıyla gerçek bilgi tabanında güven skoru `0,894982` olan sorgu güven kapısını geçti.
- Yapılandırılmış 5 kaynakla yapılan kimliği doğrulanmış chatbot isteği `HTTP 200` döndürdü.
- Yanıt 29 SSE `parca` olayıyla aktı, 11,64 saniyede `tamamlandi` olayına ulaştı ve `cevaplandi=true` sonucu verdi.
- API anahtarı, gerçek soru ve kaynak içerikleri doğrulama raporuna veya sürüm kontrolüne eklenmedi.
- Bu teknik sorgunun gerçek veri yanıtında `[Kaynak N]` etiketi bulunmadı. Temsili gerçek soru setinde yüzde 100 kaynak gösterme oranı Faz 10 kabul ölçümü olarak korunmaktadır.

Faz 1-14 için kalıcı pytest paketi mevcuttur; canlı Chromium E2E testi yalnızca ayrılmış CI işinde etkinleştirilir. Ruff, Bandit, Python derleme ve `git diff --check` denetimleri kalite kapısı olarak kullanılır. Faz 9 arayüzü gerçek şifreli veritabanı ve Docker süreciyle; masaüstü, 390 piksel mobil kırılım, JWT yönetici girişi, SSS kataloğu, işletim durumu, gelişmiş analitik veri yükleme, statik dosya sunumu ve tarayıcı konsolu bakımından doğrulanmıştır. Python 3.11 kalite işi `pip check`, `pip-audit`, sır kalıbı, test ve statik analiz denetimlerini; Docker işi Compose doğrulaması, üretim imajı oluşturma, liveness ve readiness duman testlerini tekrarlar. Ayrı CodeQL iş akışı Python ve JavaScript kaynaklarını push, pull request ve haftalık zamanlamada analiz eder. İş akışları Node.js 24 tabanlı güncel `actions/checkout@v7`, `actions/setup-python@v7` ve desteklenen `github/codeql-action@v4` ana sürümleriyle yapılandırılmıştır. Faz 10 güvenlik doğrulamaları ile arama karşılaştırma altyapısı tamamlanmıştır; arama kabulü uzman etiketli en az 50 senaryonun hazırlanmasını beklemektedir.

Faz 10 doğrulamalarında (Kurumsal Güvenlik ve RAG Benchmark):

- Gelişmiş siber güvenlik (Red Team) testleri ve RAG Zehirleme (Document Poisoning) senaryoları, sektör standartlarını belirleyen ve AI manipülasyonlarına karşı acımasız bir stres testi sunan [Yargu Security Framework](https://github.com/mecik-arda/Yargu-Framework) kullanılarak icra edilmiştir. HadesBot, Yargu'nun AI-vs-AI manipülasyonlarına, Token Splitting ve Unicode Homoglyph saldırılarına karşı devrilmez bir kale olduğunu kanıtlamıştır.
- Yggdrasil-Security altyapısından alınan WAF-Evader payload'ları (XSS, SQLi, RCE) ve Loki mutasyon teknikleri (Unicode bypass, SQL comment injection, çift URL encoding, boşluk manipülasyonu, case randomization), Pydantic ve HTTP katmanlarında %100 başarıyla (182/182 test, 0 500 hatası) filtrelenmiştir. TestClient rate-limiter GitHub Actions kararsızlıkları izole edilmiş ve pipeline istikrarı sağlanmıştır.
- SQLite üzerinde oluşturulan yapay eşzamanlı yazma (Concurrent Write / DoS) bombardımanları, WAL mimarisi sayesinde sıfır kilitlenme (0 lock) ile atlatılmıştır.
- Mevcut 25 senaryo, HTTP/SSE davranışını, güven eşiği reddini ve saldırı girdilerine karşı kontrollü yanıtı doğrular. Bu senaryolar uzman doğrulamalı beklenen SSS kimlikleri taşımadığı için hibrit aramanın arama doğruluğu hakkında yüzde değer üretmez.
- Benchmark motoru `beklenen_sss_id` veya `beklenen_sss_idler` alanlarıyla etiketlenen senaryolarda Top-1, Top-3, MRR@10 ve nDCG@10; tüm senaryolarda cevap vermeme, kaynak gösterme ve p50/p95 gecikme metriklerini hesaplar. HTML, JSON ve CSV raporları üretir ve kabul eşikleri karşılanmadığında başarısız çıkış kodu döndürür.

Faz 13 doğrulamalarında:

- RBAC rol bazlı arama filtresi FTS5 ve vektör sorgularına başarıyla entegre edildi. 168 birim test hatasız geçti.
- DeepSeek API çökme durumunda `yedek` SSE olayı ile en iyi 3 kaynak başarıyla iletiliyor.
- Niyet sınıflandırma motoru anahtar kelime ve regex tabanlı eşleştirme ile `eylem` SSE olayı üretiyor.
- Tüm yeni değişkenler `.env.example` şablonuna ve `konfigurasyon.py`'ye eklendi.

## Proje Yapısı

Başlıca Git takipli proje dosyaları aşağıdadır:

```text
HadesBot/
├── .github/
│   ├── workflows/
│   │   ├── codeql.yml
│   │   └── faz1-14-dogrulama.yml
│   └── dependabot.yml
├── uygulama/
│   ├── ana.py
│   ├── api/
│   │   ├── bagimliliklar.py
│   │   └── rotalar/
│   │       ├── analitik.py
│   │       ├── arama.py
│   │       ├── geri_bildirim.py
│   │       ├── kimlik_dogrulama.py
│   │       ├── on_yuz.py
│   │       ├── sss.py
│   │       └── yonetici.py
│   ├── sablonlar/
│   │   ├── temel.html
│   │   ├── indeks.html
│   │   ├── yonetici.html
│   │   └── analitik.html
│   ├── statik/
│   │   ├── css/stil.css
│   │   ├── js/uygulama.js
│   │   ├── js/yonetici.js
│   │   └── js/analitik.js
│   ├── cekirdek/
│   │   ├── gunlukleyici.py
│   │   ├── guvenlik.py
│   │   ├── guvenlik_basliklari.py
│   │   ├── dagitim_guvenligi.py
│   │   ├── istek_boyutu.py
│   │   ├── istek_sinirlayici.py
│   │   ├── konfigurasyon.py
│   │   ├── onbellek.py
│   │   ├── dosya_kilidi.py
│   │   └── veritabani.py
│   ├── modeller/
│   │   ├── semalar.py
│   │   └── veritabani_modelleri.py
│   └── servisler/
│       ├── akis_servisi.py
│       ├── api_servisi.py
│       ├── arama_servisi.py
│       ├── deepseek_servisi.py
│       ├── excel_yukleyici.py
│       ├── hibrit_arama.py
│       ├── metin_parcalayici.py
│       ├── model_guvenligi.py
│       ├── niyet_siniflandirici.py
│       ├── oturum_hafizasi.py
│       ├── oturum_sahipligi.py
│       ├── sorgu_genisletici.py
│       ├── terim_haritasi.py
│       ├── vektor_servisi.py
│       └── yeniden_siralayici.py
├── testler/
│   ├── conftest.py
│   ├── test_akis_servisi.py
│   ├── test_arama_servisi.py
│   ├── test_deepseek_servisi.py
│   ├── test_faz7_api.py
│   ├── test_faz9_on_yuz.py
│   ├── test_faz9_tarayici.py
│   ├── test_geri_bildirim_servisi.py
│   ├── test_guvenlik_bakimi.py
│   ├── test_guvenlik_header_ve_cors_izolasyon.py
│   ├── test_hibrit_arama.py
│   ├── test_istek_boyutu.py
│   ├── test_konfigurasyon.py
│   ├── test_llm_api_cokme_ve_yedekleme.py
│   ├── test_markdown_donusturme.py
│   ├── test_openapi_sozlesmesi.py
│   ├── test_oturum_hafizasi.py
│   ├── test_oturum_lru_tahliye_ve_bellek_sizintisi.py
│   ├── test_pii_maskeleme_stress_ve_redos.py
│   ├── test_prompt_markdown_kalitesi.py
│   ├── test_sizma_testi.py
│   ├── test_sorgu_genisletici.py
│   ├── test_sqlite_eszamanlilik_ve_wal_lock.py
│   ├── test_veri_temizligi_zamanlama_mock.py
│   ├── test_yeniden_siralayici.py
│   ├── karsilastirma/
│   │   ├── degerlendirme.py
│   │   └── test_senaryolari.json
├── veriler/
│   ├── niyet_eylemleri.example.json
├── excel_ice_aktar.py
├── es_anlamlilar.example.json
├── vektor_modelini_hazirla.py
├── yeniden_siralama_modelini_hazirla.py
├── vektorleri_olustur.py
├── yedekle.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├── .env.dev
├── .env.test
├── .env.prod
└── README.md
```

`uygulama/api/` kimlik doğrulama, arama, geri bildirim, yönetici, analitik, SSS ve ön yüz rotalarını içerir. `uygulama/sablonlar/` Jinja2 sayfalarını, `uygulama/statik/` ise kurumsal stil ve tarayıcı istemcisini içerir.

## Bilinen Sınırlamalar

- Cross-Encoder güvenli yerel entegrasyonu hazırdır ve varsayılan olarak kapalıdır; üretim aktivasyonu Türkçe arama karşılaştırması, p50/p95 gecikme ve tepe bellek ölçümü sonrasına bırakılmıştır.
- DeepSeek sağlayıcı bağlantısı sentetik ve kurum sahibinin açıkça onayladığı gerçek UYDS kaynaklarıyla doğrulanmıştır. Üretim kullanımı kurumun veri işleme politikası ve etkin API anahtarı gerektirir.
- Desteklenen varsayılan dağıtım tek Uvicorn worker kullanır.
- Bellek içi oturum sahipliği tek worker dağıtımı içindir; standart ortam değişkenleriyle çok worker başlatma girişimi reddedilir. Gerçek çok-worker desteği kalıcı paylaşımlı oturum deposu gerektirir.
- Veritabanı çalışma sırasında düz metin SQLite olarak açıktır ve temiz kapanışta şifrelenir.
- Mantıksal anahtarı birden fazla aktif kayda karşılık gelen belirsiz gruplar otomatik revizyon zincirine bağlanmaz; yanlış eşleşmeyi önlemek için ekleme ve arşivleme olarak işlenir.

## Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Ayrıntılar `LICENSE` dosyasındadır.
