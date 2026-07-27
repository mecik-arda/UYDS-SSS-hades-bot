# UYDS Akıllı SSS Chatbot (HadesBot)

UYDS Sık Sorulan Sorular verilerini kullanarak anlamsal arama tabanlı, kaynak kontrollü ve akıllı cevap üreten kurumsal destek asistanı.

## Veri Gizliliği ve Kurumsal Güvenlik Bildirimi

Proje kapsamında kullanılacak UYDS verileri özel ve kurum içi niteliktedir. Bu nedenle Excel dosyaları, SQLite veritabanı, embedding kayıtları, loglar, ekran görüntüleri ve proje çıktıları hiçbir şekilde GitHub, GitLab, kişisel bulut hesapları, e-posta veya harici dosya paylaşım servislerine yüklenmeyecektir. Tüm geliştirme, konteynerizasyon ve test süreçleri yalnızca tahsis edilen yerel iş bilgisayarlarında yürütülecektir. `veriler/` klasörü `.gitignore` ile korunmakta olup orijinal UYDS veri seti ve teknik şartname dokümanı kesinlikle sürüm kontrolüne dahil edilmemiştir.

## Proje Hakkında

Bu proje, UYDS bünyesindeki 2.403 adet SSS kaydını kullanarak kullanıcıların sorularına anlamsal olarak en uygun cevapları bulan, dış API (DeepSeek) entegrasyonu ile kaynak kontrollü yanıt üreten ve kullanıcı geri bildirimleriyle sürekli iyileşen bir akıllı sohbet botudur.

## Özellikler

- SQLite FTS5 ve Vektör Gömmeleri tabanlı hibrit arama
- Reciprocal Rank Fusion (RRF) ve Cross-Encoder ile yeniden sıralama
- DeepSeek API ile kaynak kontrollü RAG yanıt üretimi
- Server-Sent Events (SSE) ile canlı akışlı yanıt
- Rol Tabanlı Erişim Kontrolü (RBAC) ve JWT kimlik doğrulama
- IP ve kullanıcı bazlı istek sınırlama (Rate Limiting)
- Kullanıcı geri bildirim mekanizması ve yönetici onay süreci
- Yönetici analitik paneli
- Docker konteyner tabanlı yalıtılmış çalışma ortamı
- Tüm kod, değişken ve arayüz bileşenleri Türkçe

## Teknoloji Yığını

- Python 3.11 ve FastAPI
- SQLite3 (FTS5 tam metin arama)
- Sentence-Transformers (yerel Türkçe vektör gömme modelleri)
- DeepSeek API (dış LLM entegrasyonu)
- Docker ve Docker Compose
- Pydantic, Jinja2, SlowAPI, JWT

## Kurulum

### Ön Koşullar

- Docker ve Docker Compose
- DeepSeek API anahtarı

### Hızlı Başlangıç

1.  Depoyu klonlayın:
    ```
    git clone <depo-adresi>
    cd HadesBot
    ```

2.  Ortam değişkenlerini yapılandırın:
    ```
    copy .env.example .env
    ```
    `.env` dosyasını açıp `DEEPSEEK_API_ANAHTARI` ve `JWT_GIZLI_ANAHTARI` değerlerini güncelleyin.

3.  Uygulamayı başlatın:
    ```
    docker-compose up --build
    ```

4.  Tarayıcıdan erişin:
    ```
    http://localhost:8000
    ```

### Varsayılan Yönetici Hesabı

- Kullanıcı adı: `yonetici`
- Şifre: `yonetici123`
- İlk giriş sonrası şifreyi değiştirmeniz önerilir.

## API Uç Noktaları

- `GET /api/saglik` - Sistem sağlık kontrolü
- `POST /api/v1/arama` - SSS araması ve cevap üretimi
- `POST /api/v1/geri-bildirim` - Kullanıcı geri bildirimi
- `GET /api/v1/yonetici/bekleyen-bildirimler` - Bekleyen onay listesi
- `POST /api/v1/yonetici/onay` - Geri bildirim onayı
- `GET /api/v1/analitik` - Sistem analitik verileri
- `POST /api/v1/kimlik-dogrulama/giris` - Kullanıcı girişi ve JWT

## Proje Yapısı

- `uygulama/cekirdek/` - Konfigürasyon, veritabanı, güvenlik, loglama, önbellek
- `uygulama/modeller/` - Veritabanı modelleri ve Pydantic şemaları
- `uygulama/servisler/` - İş mantığı servisleri (arama, vektör, DeepSeek, vb.)
- `uygulama/api/` - API rotaları
- `uygulama/sablonlar/` - Jinja2 HTML şablonları
- `uygulama/statik/` - CSS ve JavaScript dosyaları
- `veriler/` - Orijinal UYDS SSS veri seti, şartname, veritabanı, eş anlamlı haritası, günlükler
- `testler/` - Birim ve entegrasyon testleri

## Güvenlik ve Gizlilik

- `veriler/` klasörü orijinal UYDS verilerini içerir ve `.gitignore` ile korunmaktadır
- Vektör gömme işlemleri tamamen yerel modda çalışır, dış ağa veri göndermez
- Tüm API uç noktaları JWT ve RBAC ile korunmaktadır

## Lisans

MIT License - detaylar için `LICENSE` dosyasına bakın.