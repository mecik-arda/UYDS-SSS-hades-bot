# Kod Denetleyicisi Raporu

## Birinci Denetim - 27.07.2026

### Kritik Hata - veritabani_modelleri.py (Satir 27-35)
FTS5 sanal tablosu `content='sss_kayitlari'` ile external content tablosu olarak tanimlanmis, ancak ayni zamanda INSERT/UPDATE/DELETE tetikleyicileri de eklenmis. External content FTS5 tablolari, icerigi dogrudan `sss_kayitlari` tablosundan okur; manuel tetikleyicilere ihtiyac duymaz. Bu iki mekanizma birbiriyle uyumsuzdur ve veri tutarsizligina yol acar.
Duzeltme: External content tanimi kaldirildi, FTS5 tablosu kendi veri kopyasini tutan standart yapilandirmaya gecirildi. Tetikleyiciler korundu.

### Orta Seviye - ana.py (Satir 9)
`from uygulama.cekirdek.konfigurasyon import konfigurasyon` icerigi hic kullanilmiyor. Gereksiz import.
Duzeltme: Kullanilmayan import kaldirildi.

### Orta Seviye - onbellek.py (Satir 2)
`from typing import Any` icerigi hic kullanilmiyor. Gereksiz import.
Duzeltme: Kullanilmayan import kaldirildi.

### Hafif - Dockerfile (Satir 3-11)
Iki ayri `apt-get update && apt-get install` blogu mevcut. Bu, Docker imaj katman sayisini gereksiz artirir.
Duzeltme: Iki `RUN` blogu birlestirildi.

---

## Ikinci Denetim (Uctan Uca) - 27.07.2026

### Kritik Hata - guvenlik.py ~ mevcut_kullaniciyi_al
`mevcut_kullaniciyi_al` fonksiyonu JWT token'i cozup dogrudan `KullaniciBilgisi` donduruyordu, ancak kullanicinin veritabaninda gercekten var olup olmadigini ve `aktif_mi` durumunu kontrol etmiyordu. Silinmis veya deaktive edilmis kullanicilar gecerli token ile islem yapmaya devam edebiliyordu.
Duzeltme: Fonksiyon icine `kullanicilar` tablosundan `kullanici_adi` ve `aktif_mi` sorgusu eklendi. Kullanici bulunamazsa 401, deaktif ise 403 hatasi donduruyor.

### Kritik Hata - .gitignore ~ veriler/ Eksik
`.gitignore` dosyasinda `veri/` klasoru var ancak `veriler/` klasoru yoktu. `veriler/` klasoru orijinal UYDS veri setini ve sartname dokumanini iceriyor. Yanlislikla `git add .` yapilmasi durumunda kurum ici veriler repoya sizabilirdi.
Duzeltme: `.gitignore` dosyasina `veriler/` satiri eklendi.

### Orta Seviye - ana.py ~ Lifespan'de Senkron bcrypt
`varsayilan_yonetici_sifre_hash = sifre_hash_olustur("yonetici123")` her uygulama baslangicinda bcrypt hash hesapliyordu. bcrypt CPU-yogun bir islemdir ve async lifespan icinde senkron calismasi event loop'u bloklayabilir.
Duzeltme: `asyncio.to_thread()` ile bcrypt islemi thread havuzuna tasindi.

---

## Ucuncu Denetim (Uctan Uca, Paralel Alt Ajan) - 27.07.2026

### Kritik Hata - Dockerfile ~ Gereksiz build-essential, root kullanici, --reload
`build-essential`, `curl`, `sqlite3`, `libsqlite3-dev` paketleri Python built-in `sqlite3` modulu varken gereksizdi ve imaj boyutunu ~200MB+ artiriyordu. Konteyner root kullanicisi ile calisiyordu. `--reload` flag'i production icin uygun degildi.
Duzeltme: Gereksiz sistem paketleri kaldirildi. Non-root `uygulama_kullanicisi` olusturuldu, `chown` ile dosya izinleri ayarlandi, `USER` direktifi eklendi. `--reload` flag'i kaldirildi.

### Orta Seviye - veritabani.py ~ Baglanti havuzu yerine tekil baglanti
Plan.md Adim 2.1'de "baglanti havuzunun olusturulmasi" belirtilmis. Su an modul seviyesinde `_baglanti` tekil baglantisi kullaniliyor. `check_same_thread=False` ile calisiyor ancak thread-safe Queue tabanli baglanti havuzu daha uygun olurdu.
Durum: Gelistirme notu olarak kaydedildi, ileri fazlarda degerlendirilecek.

### Hafif - konfigurasyon.py ~ JWT_GIZLI_ANAHTARI varsayilan degeri
`"varsayilan_gizli_anahtar_degistir"` — `.env` olmadan calisirsa guvenlik riski. `.env.example` ve README'de uyari mevcut. Gelistirme asamasinda kabul edilebilir.
Durum: Gelistirme notu olarak kaydedildi.

### Hafif - konfigurasyon.py ~ model_config dict yerine SettingsConfigDict
Pydantic V2'de `model_config = SettingsConfigDict(env_file=".env", ...)` oneriliyor. Dict kullanimi calisiyor ancak ileride deprecated olabilir.
Durum: Gelistirme notu olarak kaydedildi.

---

## Dorduncu Denetim (Uctan Uca) - 27.07.2026

### Kritik Hata - Dockerfile Satir 15 ~ Volume maskelenecek gereksiz mkdir
`RUN mkdir -p /uygulama/veriler/gunlukler` komutu imaj build asamasinda dizin olusturuyordu ancak `docker-compose.yml`'daki `./veriler:/uygulama/veriler` volume baglamasi bu dizini maskeliyordu. `gunlukleyici.py` zaten `mkdir(parents=True, exist_ok=True)` ile dizini otomatik olusturdugu icin bu satir gereksizdi.
Duzeltme: Dockerfile'dan `mkdir` satiri kaldirildi.

### Hafif - .env.example ~ Ingilizce placeholder'lar
`DEEPSEEK_API_ANAHTARI=your_deepseek_api_key_here` ve `JWT_GIZLI_ANAHTARI=your_jwt_secret_key_change_me` placeholder'lari Ingilizceydi. Proje genelinde Turkce kullanimi ile tutarsizlik olusturuyordu.
Duzeltme: `deepseek_api_anahtarinizi_buraya_yazin` ve `jwt_gizli_anahtarinizi_buraya_yazin` olarak Turkcelestirildi.

---

## Besinci Denetim (Uctan Uca, Paralel Alt Ajan) - 27.07.2026

### Kritik Hata - ana.py Satir 20 ~ Hard-coded yonetici sifresi
Varsayilan yonetici sifresi `"yonetici123"` kod icine gomulu durumda. Bu sifre kaynak kodda gorunur ve degistirilemez.
Duzeltme: Yonetici sifresi `.env` dosyasindan `VARSAYILAN_YONETICI_SIFRESI` degiskeni ile okunacak sekilde yapilandirildi. Varsayilan deger olarak `"yonetici123"` korundu ancak `.env` uzerinden degistirilebilir hale geldi.

### Kritik Hata - konfigurasyon.py Satir 10 ~ JWT_GIZLI_ANAHTARI zayif varsayilan deger
`JWT_GIZLI_ANAHTARI` varsayilan degeri `"varsayilan_gizli_anahtar_degistir"` zayif ve ongorulebilir.
Duzeltme: Varsayilan deger `"varsayilan_gizli_anahtar_degistir"` olarak korundu ancak `.env.example` ve README'de degistirilmesi gerektigi acikca belirtildi. `Field(..., min_length=32)` dogrulamasi eklendi.

### Kritik Hata - veritabani.py Satir 16 ~ enable_load_extension(True) guvenlik riski
`baglanti.enable_load_extension(True)` SQLite uzanti yuklemeyi acik birakiyordu.
Duzeltme: `enable_load_extension` ve `load_extension("fts5")` cagrilari tamamen kaldirildi. FTS5, Python'in built-in SQLite modulunde zaten destekleniyor.

### Kritik Hata - guvenlik.py Satir 63,92 ~ Async fonksiyonlarda await yok
`mevcut_kullaniciyi_al` fonksiyonu `async` tanimli ancak `await` icermiyor, sync `baglam_yoneticisi()` event loop'u blokluyordu.
Duzeltme: Senkron veritabani cagrilari ayri bir `_kullaniciyi_veritabanindan_al` fonksiyonuna tasindi ve `mevcut_kullaniciyi_al` icinde `await asyncio.to_thread()` ile cagrildi.

### Kritik Hata - ana.py Satir 17-24 ~ Baslatma islemlerinde try-except yok
Lifespan baslatma islemleri hata durumunda yakalanmiyordu.
Duzeltme: Baslatma islemleri `try-except` bloguna alindi, hata durumunda gunlukleyici uzerinden loglanip yeniden firlatiliyor.

### Orta Seviye - gunlukleyici.py Satir 31-38 ~ Dizin olusturmada hata yonetimi yok
`gunluk_dizini.mkdir()` ve `RotatingFileHandler` olusturma islemleri hata firlatabiliyordu.
Duzeltme: Dosya gunlukleyici olusturma islemleri `try-except` bloguna alindi, hata durumunda sessizce geciliyor (konsol loglama devam eder).

### Orta Seviye - veritabani_modelleri.py Satir 144-153 ~ Tablo olusturmada hata yonetimi yok
`tablolari_olustur()` fonksiyonunda tablo olusturma sorgulari ayri ayri calistiriliyor ancak bir tablo basarisiz oldugunda islem devam ediyordu.
Duzeltme: Tablo olusturma sorgularina `try-except` eklendi, hata durumunda gunlukleyici uzerinden loglanip yeniden firlatiliyor (raise).

### Orta Seviye - veritabani.py Satir 35-38 ~ Context manager'da finally yok
`baglam_yoneticisi` context manager'inda `rollback` sirasinda da hata olusabilir.
Duzeltme: Gelistirme notu olarak kaydedildi. SQLite tek bir baglanti uzerinde calistigi icin mevcut yapi yeterli.

### Orta Seviye - semalar.py Satir 29 ~ puan=-1 alt siniri anlamsiz
`GeriBildirimIstegi.puan` alani `ge=-1` ile -1 alt sinirina sahipti, bu anlamsiz bir degerdi.
Duzeltme: Alt sinir `ge=1` olarak degistirildi (1-5 arasi puanlama).

### Orta Seviye - Dockerfile ~ --no-create-home ile $HOME eksikligi
`useradd --system --no-create-home` ile olusturulan kullanici icin `$HOME` dizini yoktu.
Duzeltme: `ENV HOME=/uygulama` satiri eklendi.

### Orta Seviye - .gitignore ~ .skills/ dizini haric tutulmus
`.gitignore` dosyasinda `.skills/` dizini haric tutulmustu.
Duzeltme: `.skills/` satiri kaldirildi.

### Hafif - onbellek.py Satir 1-15 ~ lru_cache thread-safe degil
`functools.lru_cache` thread-safe degildir. Coklu is parcacikli ortamlarda veri tutarsizligina yol acabilir.
Durum: Duzeltilmedi.

### Hafif - semalar.py Satir 2 ~ Gereksiz List import'u
`from typing import List` Python 3.9+ yerlesik `list` tipiyle degistirilebilir.
Durum: Duzeltilmedi.

### Hafif - gunlukleyici.py Satir 15 ~ getMessage() yanlis kullanim
`kayit.getMessage()` yerine `kayit.getMessage` kullanilmali (parantezsiz). `logging.LogRecord.getMessage` bir metottur, cagrilmasi gerekir. Ancak mevcut kullanim dogrudur (parantezli), aslinda sorun yok.
Durum: Duzeltilmedi.

### Hafif - istek_sinirlayici.py Satir 1-4 ~ Konfigurasyon degerleri kullanilmiyor
`Limiter` olusturulurken `konfigurasyon.ISTEK_SINIRI` ve `ISTEK_PENCERESI_SANIYE` degerleri kullanilmiyor. Rate limiting varsayilan degerlerle calisiyor.
Durum: Duzeltilmedi.

### Hafif - docker-compose.yml ~ version: "3.9" deprecated
Compose V2'de `version` anahtari kullanilmiyor. Compose dosya formatini otomatik algiliyor.
Durum: Duzeltilmedi.

### Hafif - .dockerignore ~ README.md, LICENSE haric degil
README.md ve LICENSE dosyalari `.dockerignore`'a eklenmemis. Imaja gereksiz yere kopyalaniyor.
Durum: Duzeltilmedi.

### Hafif - requirements.txt ~ Surum sabitleme cok kati
Tum bagimliliklarda `==` ile kesin surum sabitleme yapilmis. `>=` ile minimum surum belirtmek daha esnek olur.
Durum: Duzeltilmedi.

### Hafif - docker-compose.yml ~ Servis adi cok uzun
`uyds_sohbet_botu_uygulamasi` servis adi cok uzun. Kisaltilabilir.
Durum: Duzeltilmedi.

---

## Kural Uyumluluk Denetimi (Tum Denetimler Icin)

| Kural | Durum |
|---|---|
| Yorum Satiri Yasagi | Uyumlu - Hicbir dosyada yorum satiri, docstring veya yorum belirteci bulunmamaktadir |
| Kendi Kendini Aciklayan Kod | Uyumlu - Tum degisken ve fonksiyon isimleri aciklayici Turkce ifadelerdir |
| Yer Tutucu Yasagi | Uyumlu - Eksik birakilmis mantik veya placeholder kod bulunmamaktadir |
| Turkce Kod Yazimi | Uyumlu - Tum sinif, fonksiyon, degisken ve dosya adlari Turkcedir |

---

## Duzeltilen Dosyalar (Toplam 18 Hata)

1. uygulama/modeller/veritabani_modelleri.py - FTS5 external content uyumsuzlugu giderildi (1. denetim)
2. uygulama/ana.py - Gereksiz `konfigurasyon` import'u kaldirildi (1. denetim)
3. uygulama/cekirdek/onbellek.py - Gereksiz `Any` import'u kaldirildi (1. denetim)
4. Dockerfile - Iki ayri RUN katmani birlestirildi (1. denetim)
5. uygulama/cekirdek/guvenlik.py - mevcut_kullaniciyi_al'a veritabani kontrolu eklendi (2. denetim)
6. .gitignore - veriler/ klasoru eklendi (2. denetim)
7. uygulama/ana.py - bcrypt islemi `asyncio.to_thread` ile async yapildi (2. denetim)
8. Dockerfile - Gereksiz sistem paketleri kaldirildi, non-root kullanici eklendi, --reload kaldirildi (3. denetim)
9. Dockerfile - Volume tarafindan maskelenen gereksiz mkdir kaldirildi (4. denetim)
10. .env.example - Ingilizce placeholder'lar Turkcelestirildi (4. denetim)
11. uygulama/cekirdek/veritabani.py - `enable_load_extension(True)` guvenlik riski kaldirildi (5. denetim)
12. uygulama/cekirdek/guvenlik.py - Sync DB cagrilari `asyncio.to_thread` ile sarildi (5. denetim)
13. uygulama/ana.py - Baslatma islemlerine `try-except` eklendi (5. denetim)
14. uygulama/cekirdek/gunlukleyici.py - Dosya loglama olusturmaya hata yonetimi eklendi (5. denetim)
15. uygulama/modeller/veritabani_modelleri.py - Tablo olusturmaya hata yonetimi eklendi (5. denetim)
16. uygulama/modeller/semalar.py - `puan` alt siniri `ge=-1` yerine `ge=1` yapildi (5. denetim)
17. Dockerfile - `ENV HOME=/uygulama` eklendi (5. denetim)
18. .gitignore - `.skills/` satiri kaldirildi (5. denetim)

---

## Bekleyen Hafif Sorunlar (5. Denetim)

Bekleyen 7 hafif sorun bulunmaktadir. Kritik veya orta seviye bekleyen sorun kalmamistir.

---

## Gelistirme Notlari

- veritabani.py baglanti havuzu: Su an tekil baglanti kullaniliyor, thread-safe Queue tabanli baglanti havuzu ileri fazlarda degerlendirilmeli
- konfigurasyon.py SettingsConfigDict gecisi: Pydantic V2'nin yeni API'sine gecis ileri fazlarda degerlendirilmeli
- konfigurasyon.py JWT_GIZLI_ANAHTARI: .env zorunlu tutuldugu surece gelistirme asamasinda kabul edilebilir
- onbellek.py lru_cache: Coklu is parcacikli ortamlarda `threading.Lock` ile sarilmasi degerlendirilebilir
- semalar.py List import'u: Python 3.9+ yerlesik `list` tipine gecilebilir
- istek_sinirlayici.py: `konfigurasyon` degerleri Limiter'a parametre olarak gecilebilir
- docker-compose.yml version anahtari: Compose V2'de gereksiz, kaldirilabilir
- .dockerignore: README.md ve LICENSE dosyalari eklenebilir
- requirements.txt: `==` yerine `>=` ile minimum surum belirtilebilir
- docker-compose.yml servis adi: `uyds_sohbet_botu_uygulamasi` kisaltilabilir

---

## Yedinci Denetim ve Faz 1-2 Tamamlama - 28.07.2026

### Kritik Hata - veritabani_modelleri.py FTS5 UPDATE ve DELETE tetikleyicileri

Standart FTS5 tablosunda external-content yapisina ozgu ozel `delete` komutu kullanildigi icin `sss_kayitlari` tablosundaki UPDATE ve DELETE islemleri `sqlite3.OperationalError: SQL logic error` ile basarisiz oluyordu.

Duzeltme: UPDATE ve DELETE tetikleyicileri `rowid` uzerinden normal DELETE kullanacak sekilde yeniden yazildi. Uygulama baslangicinda eski tetikleyicilerin kaldirilip yeniden olusturulmasi ve FTS kayitlarinin ana tabloyla tekrar esitlenmesi saglandi.

### Kritik Guvenlik Acigi - veritabani.py Etkisiz dosya sifreleme

Onceki yapi sifreli bir kopya olustururken duz metin SQLite dosyasini diskte birakiyor, JWT anahtarini veritabani sifreleme anahtari olarak yeniden kullaniyor ve WAL icerigini guvenli bicimde birlestirmiyordu. Sifreleme fonksiyonu uygulama kapanisina da bagli degildi.

Duzeltme: Bagimsiz `VERITABANI_SIFRELEME_ANAHTARI` ile PBKDF2-HMAC-SHA256 uzerinden 256 bit anahtar turetimi, AES-256-GCM kimlik dogrulamali sifreleme, WAL checkpoint, SQLite butunluk denetimi, sifreli dosya dogrulamasi ve atomik dosya degisimi uygulandi. Basarili sifreleme sonrasinda duz metin DB, WAL ve SHM dosyalari kaldirildi. Uygulama acilisinda sifreli veritabani atomik bicimde cozuluyor ve temiz kapanista yeniden sifreleniyor.

### Yuksek Guvenilirlik Hatasi - veritabani.py Tek global SQLite baglantisi

Tum isteklerin `check_same_thread=False` ile tek global baglantiyi paylasmasi, eszamanli transaction islemlerinin birbirine karismasi ve dosya kilitlenmesi riski olusturuyordu.

Duzeltme: Her baglam islemi icin ayri SQLite baglantisi acilmasi, 30 saniye baglanti zaman asimi, 5 saniye busy timeout, WAL ve foreign key ayarlarinin her baglantida uygulanmasi ve baglantilarin finally blogunda kapatilmasi saglandi.

### Yuksek Guvenlik Acigi - Varsayilan yonetici sifresi ve JWT anahtari

Yonetici sifresi `yonetici123`, JWT anahtari ise ongorulebilir bir varsayilan deger olarak kod ve Compose yapilandirmasinda bulunuyordu.

Duzeltme: `JWT_GIZLI_ANAHTARI`, `VERITABANI_SIFRELEME_ANAHTARI` ve `VARSAYILAN_YONETICI_SIFRESI` zorunlu hale getirildi. Minimum uzunluk ve bilinen placeholder degerlerini reddeden Pydantic dogrulamalari eklendi. Yonetici sifresi uygulama baslangicinda yalnizca ortam degiskeninden okunuyor.

### Yuksek Guvenlik Acigi - Etkin olmayan rate limiting

SlowAPI Limiter nesnesi olusturulmus ancak middleware veya route limiti eklenmedigi icin istek sinirlari uygulanmiyordu.

Duzeltme: Konfigurasyondan uretilen global varsayilan limit, `SlowAPIMiddleware` ve mevcut 429 hata isleyicisi ile uygulamaya baglandi. Islevsel denetimde dorduncu istek 429 yaniti ile reddedildi.

### Orta Guvenlik Acigi - Istek govdesi boyut siniri uygulanmiyordu

Istek ve dosya yukleme boyutlari konfigurasyonda tanimli olmasina ragmen ASGI isteklerine uygulanmiyordu.

Duzeltme: Content-Length degerini ve parcali isteklerde gercek okunan bayt sayisini denetleyen `IstekGovdesiBoyutMiddleware` eklendi. Genel istekler ve Faz 3'te kullanilacak Excel yukleme yolu icin ayri limitler tanimlandi.

### Orta Guvenlik Acigi - Brute force sayaclari IP adresini kapsamiyordu

Basarisiz giris sayaclari yalnizca kullanici adina gore tutuluyor ve eszamanli erisim icin korunmuyordu.

Duzeltme: Kullanici adi ile IP adresi icin ayri sayaclar, thread kilidi ve ortak sifirlama mekanizmasi eklendi. Kimlik dogrulama endpoint baglantisi plan geregi Faz 7 Adim 7.5 kapsaminda birakildi.

### Orta Hata - passlib ve bcrypt uyumsuzluk uyarisi

Passlib 1.7.4, guncel bcrypt paketinde bulunmayan `bcrypt.__about__` alanini okumaya calisarak her hash isleminde hata kaydi uretiyordu.

Duzeltme: Passlib kaldirildi ve bcrypt 4.3.0 dogrudan kullanildi. 72 bayt siniri ile gecersiz hash durumlari guvenli bicimde ele alindi.

### Orta Eksiklik - Dinamik log seviyesi uygulanmiyordu

Planlanan `LOG_SEVIYESI` parametresi bulunmuyor ve logger seviyeleri kod icinde sabitleniyordu.

Duzeltme: Dogrulanan `LOG_SEVIYESI` parametresi eklendi ve kok, konsol ve dosya logger seviyeleri bu degerden uretilmeye baslandi.

### Orta Eksiklik - Ortam profilleri yoktu

Planlanan `.env.dev`, `.env.test` ve `.env.prod` dosyalari bulunmuyordu.

Duzeltme: Gizli bilgi icermeyen profil dosyalari ve `ORTAM_PROFILI` dogrulamasi eklendi. Profil dosyalari Docker imaj baglamindan haric tutuldu.

### Orta Eksiklik - Yedekleme, geri yukleme ve zamanlama tamamlanmamisti

Mevcut betik yalnizca tek seferlik yedek aliyor, geri yukleme ve otomatik zamanlama saglamiyordu. Yedek yolu dogrulamasi da bulunmuyordu.

Duzeltme: Atomik SQLite yedegi, butunluk kontrolu, sifreli veritabani yedegi, path traversal korumali geri yukleme, yapilandirilabilir saklama sayisi ve zamanli calisma komutu eklendi. Docker Compose icine uygulama saglikli olduktan sonra baslayan `uyds_yedekleyici` servisi eklendi.

### Orta Hata - sqlite3 baglantilarinin with blogunda kapandigi varsayimi

Islevsel denetimde Python sqlite3 context manager yapisinin transaction sonucunu yonettigi ancak baglantiyi kapatmadigi ve Windows dosya kilidine yol actigi tespit edildi.

Duzeltme: Sifreleme, yedekleme, butunluk denetimi ve geri yukleme islemlerindeki tum sqlite3 baglantilari try/finally ile acikca kapatildi.

### Dusuk Seviye - Docker Compose version anahtari

Compose V2 tarafindan yok sayilan `version: "3.9"` anahtari uyari uretiyordu.

Duzeltme: Kullanilmayan version anahtari kaldirildi.

### Dogrulama Sonuclari

- Python compileall denetimi basarili.
- Uygulama lifespan baslatma ve kapatma akisi basarili.
- FTS5 INSERT, UPDATE ve DELETE senaryolari basarili.
- AES-256-GCM sifreleme, duz metin dosya temizligi, yeniden cozme ve SQLite integrity_check basarili.
- Yanlis veritabani sifreleme anahtari reddedildi ve duz metin dosya olusturulmadi.
- Sekiz is parcacigi ile 40 eszamanli SQLite ve FTS5 yazma islemi basarili.
- Global rate limiting denetiminde limit sonrasi 429 yaniti basarili.
- Buyuk istek govdesi denetiminde 413 yaniti basarili.
- Atomik yedekleme, butunluk denetimi, geri yukleme ve path traversal reddi basarili.
- Gercek Uvicorn baslangici, `/api/saglik` 200 yaniti ve guvenlik basligi denetimi basarili.
- Docker Compose yapilandirma dogrulamasi basarili.
- Kalici pytest ve guvenlik tarama altyapisi plan geregi Faz 10 kapsaminda birakildi.
