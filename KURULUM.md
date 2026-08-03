# HadesBot - UYDS Akilli SSS Asistani Kurulum Kilavuzu

## Gereksinimler

- Docker ve Docker Compose v2
- Python 3.11 (yerel gelistirme icin)
- Git

## Hizli Kurulum (Docker)

```bash
git clone https://github.com/mecik-arda/UYDS-SSS-hades-bot.git
cd UYDS-SSS-hades-bot
cp .env.example .env
```

`.env` dosyasinda asagidaki zorunlu degiskenleri gercek degerlerinizle guncelleyin:

- `VERITABANI_SIFRELEME_ANAHTARI` (en az 32 karakter)
- `JWT_GIZLI_ANAHTARI` (en az 32 karakter)
- `VARSAYILAN_YONETICI_SIFRESI` (en az 12 karakter)
- `DEEPSEEK_API_ANAHTARI` (DeepSeek API anahtari)

```bash
docker compose build
docker compose up -d
```

Uygulama varsayilan olarak `http://localhost:8000` adresinde calisir.

## Saglik Kontrolu

```bash
curl http://localhost:8000/api/saglik
curl http://localhost:8000/api/hazirlik
```

## Veri Yukleme

Excel dosyasini `veriler/UYDS_SSS_Listesi.xlsx` yoluna kopyalayin. Ardindan:

```bash
python excel_ice_aktar.py
```

Vektor gommelerini olusturmak icin:

```bash
python vektorleri_olustur.py
```

## Eslestirme ve Model Hazirligi

Vektor modelini indirmek icin:

```bash
python vektor_modelini_hazirla.py
```

Cross-Encoder yeniden siralama modelini indirmek icin (istege bagli, varsayilan kapali):

```bash
python yeniden_siralama_modelini_hazirla.py
```

## Ortam Profilleri

Proje uc ortam profilini destekler:

- `.env.dev` - Gelistirme ortami (DEBUG seviyesi loglama, yerel DeepSeek adresi)
- `.env.test` - Test ortami (CI uyumlu sentetik kimlik bilgileri)
- `.env.prod` - Uretim ortami (siki guvenlik ayarlari)

Profil secimi `ORTAM_PROFILI` ortam degiskeni ile yapilir.

## Yonetim

Varsayilan yonetici kullanicisi: `yonetici`
Parola: `.env` dosyasindaki `VARSAYILAN_YONETICI_SIFRESI` degeri

Yonetici islemleri HMAC imza dogrulamasi gerektirir.

## Testler

```bash
pip install -r requirements-dev.txt
python -m pytest testler/ -v
```

Benchmark degerlendirmesi icin:

```bash
python testler/karsilastirma/degerlendirme.py
```

RAG zehirleme testleri dahil:

```bash
python testler/karsilastirma/degerlendirme.py --zehirleme-testi
```

## Yedekleme

Docker Compose yedekleyici servisi otomatik yedekleme yapar. Yapilandirma:

- `YEDEKLEME_ARALIGI_SAAT`: Yedekleme araligi (varsayilan: 24)
- `YEDEKLEME_SAKLAMA_SURESI_SAAT`: Saklama suresi (varsayilan: 168)

Manuel yedekleme icin:

```bash
python yedekle.py
```

## Guvenlik Notlari

- `.env` dosyasi Git'e eklenmez (`.gitignore` ile korunur)
- Gercek UYDS verileri ve model dosyalari Git'e eklenmez
- Uretim ortaminda HTTPS zorunludur
- DeepSeek API anahtari duzenli olarak dondurulmelidir
- Sistem dis aga veri sizintisini onlemek icin egress firewall kurallari ile korunmalidir
- Dolayli prompt enjeksiyonu (out-of-band exfiltration) riski: Teorik olarak mumkundur ancak sistem ag katmaninda disari cikis kurali olmadigi surece etkisizdir. Bu risk guvenlik raporunda belgelenmistir.
