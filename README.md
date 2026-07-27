# UYDS Akıllı SSS Destek Asistanı (HadesBot)

Sürüm 1.0.0 | Geliştirme Aşamasında | MIT Lisansı

---

## Veri Gizliliği ve Kurumsal Güvenlik Bildirimi

Proje kapsamında işlenen UYDS verileri özel ve kurum içi niteliktedir. Bu nedenle Excel dosyaları, SQLite veritabanı, vektör gömme kayıtları, uygulama günlükleri, ekran görüntüleri ve proje çıktıları hiçbir şekilde GitHub, GitLab, kişisel bulut hesapları, e-posta veya harici dosya paylaşım servislerine aktarılmayacaktır. Tüm geliştirme, konteynerizasyon ve test süreçleri yalnızca tahsis edilen yerel iş istasyonlarında yürütülmektedir. `veriler/` dizini `.gitignore` ile korunmakta olup orijinal UYDS SSS veri seti ve teknik şartname dokümanı sürüm kontrolüne dahil edilmemiştir.

---

## Proje Hakkında

HadesBot, UYDS bünyesindeki 2.403 adet Sık Sorulan Soru kaydı üzerinde anlamsal arama yapabilen, kurumsal bir destek asistanıdır. Kullanıcı sorularına yalnızca anahtar kelime eşleşmesi ile değil, anlam tabanlı hibrit arama yöntemleriyle yanıt arar. Bulunan sonuçları DeepSeek geniş dil modeli aracılığıyla kaynak kontrollü olarak yanıtlar. Düşük güven skoruna sahip eşleşmelerde bilgi üretmek yerine kullanıcıyı bilgilendirir.

Sistem, kullanıcı geri bildirimleri ve yönetici onay süreçleri aracılığıyla zaman içinde iyileşmeye açık olarak tasarlanmıştır.

---

## Özellikler

### Arama ve Yanıt Üretimi
- SQLite FTS5 tam metin araması (BM25 algoritması)
- Yerel Türkçe vektör gömme modelleri ile anlamsal benzerlik araması
- Hibrit arama sonuçlarının Reciprocal Rank Fusion (RRF) ile harmanlanması
- Cross-Encoder modeli ile aday yanıtların yeniden sıralanması
- DeepSeek API ile kaynak kontrollü RAG yanıt üretimi
- Güven eşiği kontrolü: skorun altında kalan eşleşmelerde yanıt üretilmez
- Server-Sent Events (SSE) ile canlı akışlı yanıt mekanizması

### Güvenlik
- Rol Tabanlı Erişim Kontrolü (RBAC): Kullanıcı ve Yönetici rolleri
- JWT tabanlı kimlik doğrulama ve oturum yönetimi
- IP bazlı istek sınırlama (Rate Limiting)
- Non-root kullanıcı ile Docker konteyner izolasyonu
- Parametreli SQL sorguları ile SQL injection koruması
- Hassas verilerin (`veriler/`) sürüm kontrolünden tamamen dışlanması

### Veri Yönetimi
- Excel formatındaki SSS verilerinin otomatik içe aktarımı
- Anlamsal metin parçalama (Semantic Chunking)
- Veri sürümleme ve içe aktarım geçmişi takibi
- Kurum içi terim ve eş anlamlı kelime haritası desteği

### Kullanıcı Etkileşimi
- Kullanıcı puanlama ve geri bildirim mekanizması
- Yönetici onay ve içerik yönetim paneli
- Sistem kullanım analitiği ve raporlama

---

## Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Programlama Dili | Python 3.11 |
| Web Çerçevesi | FastAPI |
| ASGI Sunucu | Uvicorn |
| Veritabanı | SQLite3 (FTS5 tam metin arama) |
| Vektör Gömmeleri | Sentence-Transformers (yerel, çevrimdışı) |
| Dış LLM API | DeepSeek API |
| Konteynerizasyon | Docker, Docker Compose |
| Kimlik Doğrulama | JWT (python-jose), bcrypt (passlib) |
| İstek Sınırlama | SlowAPI |
| Veri İşleme | Pandas, OpenPyXL, NumPy |
| HTTP İstemci | HTTPX |
| Şablon Motoru | Jinja2 |
| Veri Doğrulama | Pydantic, Pydantic-Settings |
| Dosya Yükleme | Python-Multipart |

---

## Kurulum

### Ön Koşullar
- Docker 20.10 veya üzeri
- Docker Compose V2
- DeepSeek API anahtarı

### Hızlı Başlangıç

Depoyu klonlayın ve proje dizinine geçin:
```
git clone <depo-adresi>
cd HadesBot
```

Ortam değişkenleri dosyasını oluşturun:
```
copy .env.example .env
```

`.env` dosyasında aşağıdaki değişkenleri güncelleyin:

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `DEEPSEEK_API_ANAHTARI` | DeepSeek API anahtarı (zorunlu) | - |
| `JWT_GIZLI_ANAHTARI` | JWT imzalama anahtarı (zorunlu) | - |
| `VERITABANI_YOLU` | SQLite veritabanı dosya yolu | `veriler/veri_deposu.db` |
| `GUVEN_ESIGI` | Arama sonucu kabul eşiği | `0.70` |
| `VEKTOR_MODEL_ADI` | Vektör gömme modeli | `paraphrase-multilingual-MiniLM-L12-v2` |
| `JWT_ALGORITMASI` | JWT imza algoritması | `HS256` |
| `JWT_OMRU_DAKIKA` | JWT token geçerlilik süresi | `30` |
| `ISTEK_SINIRI` | Dakika başına istek limiti | `100` |
| `ISTEK_PENCERESI_SANIYE` | İstek sayacı pencere süresi | `60` |
| `UYGULAMA_PORT` | Uygulama port numarası | `8000` |

Uygulamayı başlatın:
```
docker-compose up --build
```

Tarayıcıdan erişin:
```
http://localhost:8000
```

Sağlık kontrolü:
```
GET http://localhost:8000/api/saglik
```

### Varsayılan Yönetici Hesabı

Uygulama ilk başlatıldığında otomatik olarak bir yönetici hesabı oluşturulur. İlk giriş sonrası şifrenin değiştirilmesi önerilir.

- Kullanıcı adı: `yonetici`
- Şifre: `yonetici123`

---

## API Uç Noktaları

| Yöntem | Uç Nokta | Açıklama | Yetki |
|---|---|---|---|
| `GET` | `/api/saglik` | Sistem sağlık kontrolü | Herkese açık |
| `POST` | `/api/v1/kimlik-dogrulama/giris` | Kullanıcı girişi, JWT token alma | Herkese açık |
| `POST` | `/api/v1/arama` | SSS araması ve yanıt üretimi | Kullanıcı |
| `POST` | `/api/v1/geri-bildirim` | Yanıta puan ve yorum ekleme | Kullanıcı |
| `GET` | `/api/v1/yonetici/bekleyen-bildirimler` | Onay bekleyen geri bildirimler | Yönetici |
| `POST` | `/api/v1/yonetici/onay` | Geri bildirim onaylama veya reddetme | Yönetici |
| `POST` | `/api/v1/yonetici/excel-yukle` | Excel veri seti yükleme | Yönetici |
| `GET` | `/api/v1/analitik` | Sistem kullanım istatistikleri | Yönetici |

---

## Güvenlik Mimarisi

Uygulama aşağıdaki güvenlik katmanlarını içermektedir:

- **Kimlik Doğrulama:** Tüm korumalı uç noktalar JWT Bearer token ile erişim gerektirir. Token'lar yapılandırılabilir süre sonuna sahiptir.
- **Yetkilendirme:** Kullanıcı (`KULLANICI`) ve yönetici (`YONETICI`) olmak üzere iki rol seviyesi tanımlanmıştır. Yönetici uç noktaları ek yetki kontrolüne tabidir.
- **Kullanıcı Doğrulama:** Token çözümleme sonrası kullanıcının veritabanında varlığı ve hesap aktifliği kontrol edilir. Silinmiş veya devre dışı bırakılmış hesapların token'ları reddedilir.
- **İstek Sınırlama:** IP tabanlı rate limiting, hizmet reddi (DoS) saldırılarına karşı koruma sağlar. Eşik değerleri `.env` üzerinden yapılandırılabilir.
- **Veritabanı Güvenliği:** Tüm SQL sorguları parametreli olarak çalıştırılır. SQLite uzantı yükleme (`enable_load_extension`) devre dışıdır.
- **Docker İzolasyonu:** Konteyner root kullanıcısı yerine yetkisiz bir sistem kullanıcısı ile çalışır. Dosya sistemi izinleri asgari seviyede tutulur.
- **Vektör İşlemleri:** Tüm vektör gömme işlemleri yerel olarak, çevrimdışı modda gerçekleştirilir. Hiçbir veri dış hizmetlere gönderilmez.
- **Veri Sızıntısı Koruması:** `veriler/` dizini `.gitignore` ve `.dockerignore` ile hem sürüm kontrolünden hem de Docker imajından dışlanmıştır.

---

## Proje Yapısı

```
HadesBot/
├── uygulama/
│   ├── ana.py                    # FastAPI başlangıç ve yaşam döngüsü
│   ├── cekirdek/                 # Çekirdek altyapı modülleri
│   │   ├── konfigurasyon.py      # Ortam değişkenleri yönetimi
│   │   ├── veritabani.py         # SQLite bağlantı ve bağlam yönetimi
│   │   ├── guvenlik.py           # JWT, bcrypt, RBAC kimlik doğrulama
│   │   ├── istek_sinirlayici.py  # Rate limiting yapılandırması
│   │   ├── gunlukleyici.py       # JSON formatlı yapılandırılmış loglama
│   │   └── onbellek.py           # LRU bellek içi önbellek
│   ├── modeller/                 # Veri modelleri ve şemalar
│   │   ├── veritabani_modelleri.py  # 8 tablo + FTS5 + tetikleyiciler
│   │   └── semalar.py            # Pydantic istek/yanıt modelleri
│   ├── servisler/                # İş mantığı servisleri (geliştirme aşamasında)
│   ├── api/                      # API rota tanımları (geliştirme aşamasında)
│   ├── sablonlar/                # Jinja2 HTML şablonları (geliştirme aşamasında)
│   └── statik/                   # CSS ve JavaScript (geliştirme aşamasında)
├── veriler/                      # Kurumsal veri dizini (sürüm kontrolü dışında)
├── testler/                      # Test dosyaları (geliştirme aşamasında)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
└── README.md
```

---

## Geliştirme Durumu

| Faz | Açıklama | Durum |
|---|---|---|
| Faz 1 | Ortam kurulumu, Docker altyapısı, güvenlik, bağımlılıklar | Tamamlandı |
| Faz 2 | SQLite veritabanı, FTS5, veri modelleri, önbellek | Tamamlandı |
| Faz 3 | Excel içe aktarma, metin parçalama, sürümleme | Beklemede |
| Faz 3.5 | Güvenlik sertleştirmesi (input validasyon, JWT refresh, bağımlılık taraması) | Beklemede |
| Faz 4 | Vektör gömmeleri, eş anlamlı terim haritası | Beklemede |
| Faz 5 | Hibrit arama, RRF, Cross-Encoder yeniden sıralama | Beklemede |
| Faz 6 | DeepSeek API, SSE akış, oturum hafızası | Beklemede |
| Faz 7 | API uç noktaları ve iş mantığı servisleri | Beklemede |
| Faz 8 | Kurumsal Kurşuni ön yüz (HTML/CSS/JS) | Beklemede |
| Faz 9 | Geri bildirim döngüsü, yönetici onayı, analitik | Beklemede |
| Faz 10 | Test, sızma testi, güvenlik taraması, dokümantasyon | Beklemede |

---

## Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız.