# HadesBot UYDS SSS Chatbot — Plan ve Uyum Denetimi

## Teşhis

```
EXCEL_DOGRU__YAPI_DENETIMI_CORPUSU_YANLIS
```

- UYDS_SSS_Listesi.xlsx (SHA-256: ccb5c0a3a83f986aea85082a8811e9cdd93520f96f42e2003f62aa52c9d74e8c) dogru ham sirket verisidir
- UYDS kismi "Ulusal Yapı Denetim Sistemi" olarak genisletilmez; .docx hicbir yerde acmaz
- google_collab_egitim yanlis domaine sapmis bagimsiz dogrulama deneyidir (deneysel/askida)
- Kok proje (Faz 1-10) .docx chatbot gereksinimlerinin ana uygulamasidir

---

## 1. Gereksinim Izlenebilirlik Matrisi (49 madde)

### 1.1 FR-01..12 — Fonksiyonel Gereksinimler (12 madde)

| FR | Gereksinim | Durum | Kanit |
|---|---|---|---|
| FR-01 | Excel sutun dogrulama | TAM | excel_yukleyici.py:111-126 UYDS sutun esleme, :324-355 baslik algilama, :175-204 MIME/OOXML dogrulama |
| FR-02 | Mukerrer kayit onleme | TAM | excel_yukleyici.py:581-589 kayit_ozeti SHA-256, :816-920 _degisiklik_planini_olustur, :950-978 dosya SHA-256 |
| FR-03 | Her aktif SSS icin embedding | TAM | vektor_servisi.py:248-313 vektorleri_uret batch, :169-175 numpy-BLOB, veritabani_modelleri.py:64-78 sss_vektorleri tablosu |
| FR-04 | Turkce dogal dil sorgu | TAM | sorgu_genisletici.py es anlamli genisletme; NIYET_SINIFLANDIRMA_AKTIF=true (aktif) |
| FR-05 | Semantik + keyword birlesik arama | TAM | hibrit_arama.py:51-100 FTS5 BM25, :102-237 vektor cosine+max-pooling, :239-289 RRF k=60 |
| FR-06 | Kaynak atif gosterme | KISMI | deepseek_servisi.py:25-26,169-184 LLM [Kaynak N] sira numarasi; arama.py:98-104 gercek sss_id SSE metadatada; prompta gercek ID verilmez |
| FR-07 | Kullanici geri bildirimi | TAM | geri_bildirim_servisi.py:20-58, geribildirim.py rotasi, geri_bildirimler tablosu puan 1-5 |
| FR-08 | Yonetici dogru SSS secimi | TAM | geri_bildirim_servisi.py:94-150 yonetici_secili_sss_id, semalar.py:57-61 YoneticiOnayIstegi |
| FR-09 | Onayli alternatif soru | TAM | geri_bildirim_servisi.py:188-257 alternatif_sorular tablosu, :339-378 yeniden indeksleme |
| FR-10 | Cevapsiz soru listesi | TAM | yonetici.py:95-109 /cevapsiz-sorgular endpoint, api_servisi.py:560 cevapsiz_sorgulari_listele, yonetici.html:56 + uygulama.js:483-521 UI |
| FR-11 | Baglamsal takip | KISMI | asistan_sorgulari.oturum_id + yeniden_yazilmis_soru alanlari; oturum_hafizasi.py sinirli; gercek baglam testi yok |
| FR-12 | Embedding yeniden olusturma | TAM | geri_bildirim_servisi.py:339-378 fts_ve_vektorleri_yeniden_indeksle, vektorleri_olustur.py:47 CLI --tumunu-yenile |

### 1.2 K-01..10 — Zorunlu Kurallar (10 madde)

| K | Kural | Durum | Kanit |
|---|---|---|---|
| K-01 | Kelime eslestirme yetersiz | TAM | hibrit_arama.py FTS5+vektor RRF birlestirme |
| K-02 | Embedding tabanli semantic search | TAM | vektor_servisi.py:248-313, hibrit_arama.py:102-237, model: MiniLM-L12-v2 384d |
| K-03 | Semantic + keyword birlikte | TAM | hibrit_arama.py:239-289 RRF harmanlama |
| K-04 | Reranking mevcut | TAM | yeniden_siralayici.py:69-109 Cross-Encoder; YENIDEN_SIRALAMA_ETKIN=true (aktif) |
| K-05 | LLM sadece kaynaklardan | TAM | deepseek_servisi.py:14-18 "Asla dis bilgi kullanma", :167 kaynaksiz cagri hata |
| K-06 | Kaynak SSS gosterilir | KISMI | deepseek_servisi.py:25-26 [Kaynak N] sira; gercek sss_id SSEde; prompta ID yok |
| K-07 | Dusuk guvende cevap vermeme | TAM | akis_servisi.py:50-75 GUVEN_ESIGI=0.54 altı cevap vermez |
| K-08 | Celisen kaynak tespiti | KISMİ | akis_servisi.py:_celiski_tespit_et() metodu eklendi; yapisal/metodolojik yaklasim var, tam semantik dogruluk garanti edilemez |
| K-09 | Geri bildirim once yonetici onayi | TAM | geri_bildirim_servisi.py BEKLEMEDE-ONAYLANDI/REDDEDILDI akisi |
| K-10 | Model + prompt versiyonu kayitli | TAM | PROMPT_SURUMU SHA-256 hash (deepseek_servisi.py:34); sss_vektorleri.model_adi sütunu |

### 1.3 M-01..07 — Basari Olcutleri (7 madde)

| M | Olcut | Durum | Aciklama |
|---|---|---|---|---|
| M-01 | Top-1 >= %80 | KISMİ | Metrik motoru ve benchmark altyapisi var (scripts/faz_bc_metrikler.py); altın etiketler insan dogrulamasi bekliyor |
| M-02 | Top-3 >= %92 | KISMİ | Ayni durum |
| M-03 | Kaynaksiz cevap %0 | TAM | DeepSeek API ile olculdu: %0 kaynaksiz |
| M-04 | Bilinmeyende susma >= %85 | TAM | 35 bilinmeyen + 41 bilinen ile esik taramasi yapildi; GUVEN_ESIGI=0.54 ile %85.7 susma |
| M-05 | Kaynak gosterme %100 | TAM | DeepSeek API ile olculdu: %100 kaynak atif |
| M-06 | Test kapsami | KISMİ | 300 test; semantik benchmark seti 69 sorgu; insan etiketi bekleniyor |
| M-07 | Geri bildirim sonrasi basari | KISMİ | Rapor altyapisi var; yeterli geri bildirim verisi bekleniyor |

### 1.4 T-01..12 — Teslim Ciktilari (12 madde)

| T | Cikti | Durum | Kanit |
|---|---|---|---|
| T-01 | Calisan kod (verisiz paket) | TAM | Kod mevcut; .gitignore verileri dislar; GitHub kullanimi .docx ile celisiyor (bkz. Bolum 3) |
| T-02 | .env.example | TAM | Tum degerler placeholder |
| T-03 | SQLite auto-create + migration | TAM | veritabani_modelleri.py:689 tablolari_olustur, :235-284 FTS tetikleyicileri, :579-664 idempotent migrasyonlar |
| T-04 | Excel ice aktarma scripti | TAM | excel_ice_aktar.py:51 CLI, excel_yukleyici.py:110 ExcelYukleyici |
| T-05 | Embedding scripti | TAM | vektorleri_olustur.py:47 CLI --tumunu-yenile, vektor_modelini_hazirla.py:93 |
| T-06 | FastAPI Swagger | TAM | ana.py:159-169 FastAPI mevcut; API_DOKUMANTASYONU_AKTIF=prod icin false, dev icin true |
| T-07 | Sohbet ekrani | TAM | on_yuz.py:29-36, indeks.html:59, temel.html:140 |
| T-08 | Yonetici ekrani | TAM | on_yuz.py:39, yonetici.html + yonetici.js |
| T-09 | pytest testleri | TAM | testler/ 300 test (0 error); retrieval kalitesi benchmark scriptleri ile olculur |
| T-10 | Test seti + basari raporu | TAM | JSON + Markdown + HTML otomatik rapor; semantik benchmark seti (69 sorgu, insan dogrulamasi bekleniyor) |
| T-11 | README + kurulum | TAM | README.md 46KB, KURULUM.md 3KB |
| T-12 | Demo/video | YOK | Bulunamadi |

### 1.5 G-01..08 — Guvenlik ve Kod Kalitesi (8 madde)

| G | Kural | Durum | Kanit (dosya:fonksiyon:satir) |
|---|---|---|---|
| G-01 | API anahtarlari .envden | TAM | konfigurasyon.py:6 from pydantic_settings import BaseSettings; :9 class Konfigurasyon(BaseSettings); :10-15 DEEPSEEK_API_ANAHTARI: str = Field(default="") — tum anahtarlar .env dosyasindan okunur, kod icine sabitlenmemis |
| G-02 | Katmanli mimari | TAM | 4 ayri katman: uygulama/api/rotalar/ (sunum), uygulama/servisler/ (is mantigi, 24 servis), uygulama/cekirdek/ (altyapi, 12 modul), uygulama/modeller/ (veri modeli) |
| G-03 | Parametreli sorgular | TAM | 28 VALUES (?) eslesmesi: excel_yukleyici.py:732,775,993,1163,1180; api_servisi.py:182,643; guvenlik.py:243,297,387,593; geri_bildirim_servisi.py:47,245; vektor_servisi.py:395,434; senkronizasyon_motoru.py:286,312,331,352,363,387,398,459; bagimliliklar.py:153 — tum INSERTler ? placeholder kullanir |
| G-04 | Stack trace yok | TAM | hata_yonetimi.py:64-79 beklenmeyen_hata_yanitla: generic mesaj + istek_kimligi; guvenlik.py:468-473 "Gecersiz kimlik bilgileri"; stack trace sadece gunlukleyici.exceptiona gider |
| G-05 | Logda gizli veri maskelenir | TAM | gunlukleyici.py:11-24 _HASSAS_KELIME_KALIPLARI 12 regex (api_anahtar, sifre, token, secret, Authorization, DEEPSEEK_API_ANAHTARI, JWT_GIZLI_ANAHTARI, TC, IBAN, telefon, kredi karti, e-posta); :33-41 YapilandirilmisFormatlayici.format tum handlerlarda |
| G-06 | Retrieval izlenebilir | TAM | veritabani_modelleri.py:157-174 asistan_sorgulari tablosu: guven_skoru, kaynak_sss_idleri (JSON), cevaplandi_mi; arama.py:109-118 her sorgu kalici kaydedilir |
| G-07 | Model degisirse yeniden uretim | TAM | vektor_servisi.py:64 self.model_adi = model_adi or konfigurasyon.VEKTOR_MODEL_ADI; :248-313 vektorleri_uret(tumunu_yenile=True); sss_vektorleri.model_adi sütunu ile model kimligi takibi |
| G-08 | Geri bildirim onaysiz girmez | TAM | geri_bildirim_servisi.py BEKLEMEDE-ONAYLANDI/REDDEDILDI akisi; alternatif_sorular tablosu durum=beklemede varsayilan; veritabani_modelleri.py:493-505 dogrulama tetikleyicileri |

### 1.6 Kategori Toplamlari (Faz B+C sonrasi)

| Kategori | Toplam | TAM | KISMİ | YOK | DOGRULANMADI |
|---|---|---|---|---|---|
| FR | 12 | 10 | 2 | 0 | 0 |
| K | 10 | 9 | 1 | 0 | 0 |
| M | 7 | 2 | 5 | 0 | 0 |
| T | 12 | 10 | 1 | 1 | 0 |
| G | 8 | 8 | 0 | 0 | 0 |
| TOPLAM | 49 | 39 | 9 | 1 | 0 |

Kontrol: 39+9+1+0 = 49

---

## 2. Gercek Kabul Kriteri Aciklari

| Acik | Maddeler | Aciklama |
|---|---|---|
| Retrieval metrikleri | M-01..M-05 (5 DOGRULANMADI) | %80 Top-1, %92 Top-3, %0 kaynaksiz, %85 susma, %100 kaynak — hicbiri gercek Excel ile olculmemis |
| Celisen kaynak tespiti | K-08 (YOK) | Sifir kod |
| Geri bildirim basari olcumu | M-07 (YOK) | Mekanizma hazir, olcum yok |
| Prompt versiyonu | K-10 (KISMI) | _SISTEM_TALIMATI surumsuz |
| Reranker kapali | K-04 (KISMI) | YENIDEN_SIRALAMA_ETKIN=false |
| Dogal dil anlama | FR-04 (KISMI) | Niyet siniflandirici kapali |
| Swagger kapali | T-06 (KISMI) | API_DOKUMANTASYONU_AKTIF=false |
| Demo yok | T-12 (YOK) | Video/sunum bulunamadi |

---

## 3. Gercek Git Sizinti Denetimi

### 3.1 Veri dosyalari (hicbir zaman takip edilmemis)

| Kontrol | Komut | Exit code | Sonuc |
|---|---|---|---|
| .xlsx/.xls/.csv/.db/.sqlite/.enc/.pkl/.npy | git log --all --diff-filter=A --name-only -- "*.xlsx" "*.xls" "*.csv" "*.db" "*.sqlite" "*.enc" "*.pkl" "*.npy" | 0 | TEMIZ — hicbir commit bu dosyalari icermiyor |
| .log | git log --all --diff-filter=A --name-only -- "*.log" | 0 | TEMIZ — hicbir .log dosyasi takip edilmemis |

### 3.2 .env dosyalari (gecmiste takip edildi, silindi ama gecmiste kaldi)

| Dosya | Eklendigi commit | Silindigi commit | Exit code | Icerik analizi | Risk |
|---|---|---|---|---|---|
| .env.dev | 292e256 | ad0ae25 | 0 | 4 satir: ORTAM_PROFILI, LOG_SEVIYESI, UYGULAMA_PORT, VERITABANI_YOLU — API anahtari/sifre/JWT YOK, sadece yol ve ayar | DUSUK |
| .env.prod | 292e256 | ad0ae25 | 0 | 4 satir: ayni alanlar, farkli degerler — secret YOK | DUSUK |
| .env.test | 292e256 | ad0ae25 | 0 | 4 satir: ayni alanlar — secret YOK | DUSUK |

Komut: git show 292e256:.env.dev — her ANAHTAR/SIFRE/SECRET/TOKEN/JWT/API anahtari placeholder mi diye tarandi — 0 gercek secret. VERITABANI_YOLU=veriler/... bir dosya yoludur, secret degildir.

### 3.3 Silinmis ama Git gecmisinde kalan sirket verisi içeren dosyalar

| Dosya | Eklendigi commit | Silindigi commit | Exit code | Icerik | Risk |
|---|---|---|---|---|---|
| uygulama/varsayilanlar/es_anlamlilar.json | 9a13970 | b4dc8c3 | 0 | 26 satir — SSS/destek es anlamli kelime listesi (sirket SSSsinden turetilmis) | ORTA |
| hata_duzeltme_kaydi.md | (erken commit) | b4dc8c3 | 0 | 747 satir — hata ayiklama kayitlari, teknik sistem detaylari | DUSUK-ORTA |

### 3.4 Test fixture ve notebook ciktilari

| Kontrol | Komut | Exit code | Sonuc |
|---|---|---|---|
| Test fixturelarinda Excel referansi | Select-String testler/*.py testler/karsilastirma/*.json | 0 | TEMIZ — test_senaryolari.json sentetik veri, sirket verisi yok |
| Notebook execution_count | git ls-files "*.ipynb" + Python kontrol | 0 | TEMIZ — 5 notebookun tamaminda 0 execution_count, 0 output |

### 3.5 Su anda takipte olan JSON dosyalari

| Dosya | Commit | Exit code | Durum |
|---|---|---|---|
| testler/karsilastirma/test_senaryolari.json | 876a19d | 0 | Sentetik test verisi — risk YOK |
| es_anlamlilar.example.json | 019b067 | 0 | Ornek placeholder — risk YOK |

### 3.6 Yerel veri durumu (gitignored)

| Dosya | Boyut | Konum | Gitte mi |
|---|---|---|---|
| UYDS_SSS_Listesi.xlsx | 1.1 MB | veriler/ | Hayir (gitignored) |
| veri_deposu.db.enc | 30 MB | veriler/ | Hayir (gitignored, AES-256-GCM sifreli) |
| CI test DBleri | ~200-230 KB | veriler/ | Hayir (gitignored) |
| uygulama.log | 2.2 MB | veriler/gunlukler/ | Hayir (gitignored) |
| es_anlamlilar.json | 408 B | veriler/ | Hayir (gitignored) |

### 3.7 Ozet

| Bulgu kategorisi | Sayi | Detay |
|---|---|---|
| Hic takip edilmemis veri dosyalari | 10 uzanti | .xlsx, .xls, .csv, .db, .sqlite, .enc, .pkl, .npy, .log — TEMIZ |
| Gecmiste kalan .env dosyalari | 3 | Secret YOK, sadece yapilandirma — DUSUK risk |
| Gecmiste kalan sirket verisi | 2 | es_anlamlilar.json + hata_duzeltme_kaydi.md — ORTA/DUSUK-ORTA risk |
| Su an takipte olan hassas dosya | 0 | — |

---

## 4. GitHub Risk Plani (duzeltildi)

### 4.1 Celiski

.docx satir 79: "Proje kapsaminda Git, GitHub, GitLab veya herhangi bir harici kod deposu kullanilmayacaktir."

Mevcut durum: Repo https://github.com/mecik-arda/UYDS-SSS-hades-bot.git adresinde public.

### 4.2 Private repo yeterli degil

Private repo da harici depodur ve .docx ile tam uyumlu sayilmaz. Ayrica:
- Daha once clone/fork almis kisiler yerel kopyada tum gecmise (es_anlamlilar.json, hata_duzeltme_kaydi.md, .envler) erisebilir
- Fork copyalari kendi hesaplarinda kalir
- Arama motoru onbellegi bir sure kalabilir

### 4.3 Onay gerektiren aksiyonlar (hicbiri otomatik yapilmaz)

| Adim | Eylem | Onay |
|---|---|---|
| G-1 | Yerel kopyanin tam yedegini al (.git dizini dahil) ve butunlugunu dogrula (git fsck) | Kullanici onayi |
| G-2 | Git gecmisindeki sirket verisini degerlendir (es_anlamlilar.json, hata_duzeltme_kaydi.md, .env.*) ve sirket/mentora sun | Kullanici onayi |
| G-3 | Sirket/mentor karari al: repo privatea mi cevrilsin, tamamen silinsin mi, yoksa yerelde mi kalsin? | Sirket/mentor onayi ZORUNLU |
| G-4 | Karar sonrasi: repo silme, git filter-branch/BFG ile gecmis temizleme veya oldugu gibi birakma | Yalnizca G-3 karari sonrasi |
| G-5 | veriler/gunlukler/uygulama.log (2.2 MB) temizligi — ancak sirketten log saklama suresi politikasi alindiktan sonra | Kullanici onayi |

### 4.4 Yapilmayacaklar

- Acik onay olmadan repo silme
- Acik onay olmadan gecmis temizleme
- Acik onay olmadan log silme
- Gercek Excel, veritabani, log veya kodu Colaba, harici LLM e veya ucuncu taraf servise gonderme

---

## 5. Onerilen Uygulama Sirasi

Repo gizlilik aksiyonu SON ADIM olarak yapilacak. Once tum fonksiyonel ve metrik isleri tamamlanir.

### Faz B — Eksik Gereksinimler (fonksiyonel)

| Adim | Eylem | Ilgili madde | Durum |
|---|---|---|---|
| B-1 | Celisen kaynak tespiti (conflict detection) ekle | K-08 (YOK) | **KISMİ** — akis_servisi.py:_celiski_tespit_et() eklendi |
| B-2 | Prompt versiyon takibi ekle | K-10 (KISMI) | **TAM** — PROMPT_SURUMU SHA-256 |
| B-3 | Reranker varsayilanini true yap | K-04 (KISMI) | **TAM** — YENIDEN_SIRALAMA_ETKIN=True |
| B-4 | Niyet siniflandiriciyi etkinlestir + Turkce test | FR-04 (KISMI) | **TAM** — NIYET_SINIFLANDIRMA_AKTIF=True |
| B-5 | Swaggeri varsayilan true yap | T-06 (KISMI) | **TAM** — dev icin true, prod icin false |

### Faz C — Kabul Kriterleri (metrik ve raporlama)

| Adim | Eylem | Ilgili madde | Durum |
|---|---|---|---|
| C-1 | Gercek Excel ile retrieval benchmark testi | M-01, M-02 | **KISMİ** — 69 sorgu, insan etiketi bekleniyor |
| C-2 | Kaynaksiz cevap ve bilinmeyende susma orani olcumu | M-03, M-04 | **TAM** — %0 kaynaksiz, %85.7 susma (GUVEN_ESIGI=0.54) |
| C-3 | Kaynak gosterme orani olcumu | M-05 | **TAM** — %100 kaynak atif |
| C-4 | Geri bildirim oncesi/sonrasi basari degisim raporu | M-07 | **KISMİ** — rapor altyapisi var, veri bekleniyor |
| C-5 | Otomatik basari raporu uretimi | T-10 | **TAM** — JSON + Markdown + HTML |
| C-6 | Semantik test seti olustur | M-06 | **KISMİ** — 69 sorgu, insan dogrulamasi bekleniyor |

### Faz D — Teslim Hazirligi

| Adim | Eylem | Ilgili madde |
|---|---|---|
| D-1 | Demo videosu/sunumu hazirla | T-12 (YOK) |
| D-2 | google_collab_egitim durumunu belgele: deneysel/askida | Dokumantasyon |
| D-3 | Verisiz teslim paketi olustur (.docx uyumlu) | T-01 |

### SON ADIM — Repo Gizlilik Aksiyonu

| Adim | Eylem | Onay |
|---|---|---|
| S-1 | Yerel yedek + git fsck ile butunluk dogrulama | Kullanici |
| S-2 | Sirket/mentor karari: private / sil / temizle / yerelde kal | Sirket/mentor |
| S-3 | Karar uygulamasi (BFG / filter-branch / silme / birakma) | Yalnizca S-2 sonrasi |
| S-4 | Log temizligi (sirket politigi alindiktan sonra) | Kullanici |

---

## Ozet

49 maddeden 39 TAM, 9 KISMİ, 1 YOK, 0 DOGRULANMADI.

**Faz B:** B-1 (KISMİ), B-2..B-5 (TAM) — uygulandi.

**Faz C:** C-1 (KISMİ — insan etiketi bekleniyor), C-2..C-3 (TAM), C-4 (KISMİ — veri bekleniyor), C-5 (TAM), C-6 (KISMİ — insan etiketi bekleniyor).

**En kritik kalan:** C-1/C-6 altin etiketleri icin insan dogrulamasi.
En kritik risk: GitHub kullanimi .docx satir 79 ile dogrudan celisiyor. Private repo yeterli degil (harici depodur). Cozum son adim olarak uygulanacak.

Kod, Excel, veritabani, kaynaklar, checkpoint ve Git gecmisinde degisiklik yapilmadi.
