# Colab Kullanım Kılavuzu — UYDS SSS Doğrulama Pipeline v4.1.0

Bu kılavuz, Google Colab A100 ortamında pipeline'ı baştan sona çalıştırmak için adım adım talimatlar içerir.

---

## 1. ZIP'i Drive'a Yükleme ve Çıkarma

1. `google_collab_egitim.zip` dosyasını Google Drive → MyDrive kök dizinine yükleyin
2. Drive'da ZIP'e sağ tık → "Bir Klasöre Çıkart" → `MyDrive/google_collab_egitim/` olarak çıkartın
3. Çıkarma sonrası yapı:

```
MyDrive/
└── google_collab_egitim/
    ├── veri_ayiklama_v4.1.ipynb
    ├── README.md
    ├── COLAB_KULLANIM.md
    ├── requirements.txt
    ├── .gitignore
    ├── config/
    │   └── config_v4.yaml
    ├── src/               (12 modül)
    ├── scripts/
    ├── tests/
    └── data/
        ├── input/         (.gitkeep — Excel'i buraya koy)
        └── kaynaklar/     (.gitkeep — Kaynak belgeleri buraya koy)
            ├── 01_mevzuat/
            ├── 02_resmi_uyds_kilavuzlari/
            ├── 03_modul_dokumanlari/
            ├── 04_teknik_cozumler/
            ├── 05_onayli_destek_kayitlari/
            └── 06_surum_notlari/
```

---

## 2. Gerçek Excel'i Yerleştirme

`UYDS_SSS_Listesi.xlsx` dosyasını `data/input/` klasörüne koyun.

```bash
# Drive üzerinden kopyala (Colab'da):
!cp "/content/drive/MyDrive/UYDS_SSS_Listesi.xlsx" \
   "/content/drive/MyDrive/google_collab_egitim/data/input/"
```

**Format:** UYDS Excel'inde başlık 4. satırdadır:
- `Modül`, `Konu`, `Açıklama`, `Yapılacak` → soru metni
- `Yapılan İşlem` → cevap metni

---

## 3. Kaynak Belgeleri Yerleştirme

Kaynak PDF/DOCX/TXT/MD dosyalarını `data/kaynaklar/` alt klasörlerine koyun:

| Klasör | İçerik |
|---|---|
| `01_mevzuat/` | Kanun, yönetmelik, tebliğ (4708, ihale, afet) |
| `02_resmi_uyds_kilavuzlari/` | UYDS resmi kullanım kılavuzları |
| `03_modul_dokumanlari/` | Modül dokümanları (hakediş, kabul, vb.) |
| `04_teknik_cozumler/` | Teknik çözüm notları |
| `05_onayli_destek_kayitlari/` | Onaylı destek kayıtları |
| `06_surum_notlari/` | Sürüm notları |

**Önemli:** `.doc` dosyaları desteklenmez. Önce DOCX'e dönüştürün.

---

## 4. Sınıflandırılmış Envanter Oluşturma

Kaynakları UYDS ilgililiğine göre sınıflandırın:

```bash
%cd /content/drive/MyDrive/google_collab_egitim
!python src/classify_relevance.py
```

Bu, `data/output_v4/kaynak_envanteri_siniflandirilmis.csv` üretir.

**Sınıflar:**
- `dogrudan_ilgili` (puan ≥ 4.0): 4708, UYDS, yapı denetim, laboratuvar
- `dolayli_ilgili` (puan ≥ 2.0): Afet, ihale, imar mevzuatı
- `alakasiz` (negatif): Alakasız belgeler
- `manuel_inceleme` (puan < 2.0): Belirsiz başlıklar

---

## 5. Corpus ve Embedding Üretme

```bash
!python scripts/build_source_corpus.py --cpu --force
```

Bu adım:
- Sınıflandırılmış envanteri yükler (hash kontrolü ile)
- Sadece `dogrudan_ilgili` + `dolayli_ilgili` belgeleri okur
- Tokenizer tabanlı chunking (110 token, 25 overlap)
- MPNet embedding üretir
- `checkpoints_v4/latest/kaynak_embedding/` kaydeder

**Eski checkpoint'i silmek için:**
```bash
!rm -rf checkpoints_v4/latest/kaynak_embedding
```

---

## 6. Gerçek Excel ile Retrieval Değerlendirmesi

Corpus kalitesini gerçek sorularla ölçün:

```bash
!python scripts/evaluate_retrieval.py \
    --soru_sayisi 50 \
    --excel data/input/UYDS_SSS_Listesi.xlsx \
    --ilk_havuz dogrudan_ilgili \
    --cpu
```

Çıktılar:
- `retrieval_degerlendirme.csv` — Her soru için top-3 kaynak + `etiket` sütunu (insan değerlendirmesi)
- `retrieval_metrikleri.json` — Hit@1, Hit@3, ortalama skor

**İnsan değerlendirmesi:** CSV'deki `etiket` sütununu `ilgili` / `kismen_ilgili` / `alakasiz` olarak doldurun.

---

## 7. 20 Kayıtlık Qwen Smoke Testi

İlk 20 kayıt üzerinde gerçek Qwen3-32B-AWQ modeli ile uçtan uca test:

Notebook Hücre 0-5'i çalıştırın. Hücre 5 benchmark için `BENCHMARK_KAYIT` değerini değiştirin:

```python
BENCHMARK_KAYIT = min(20, len(veri))  # 100 yerine 20
```

**Kalite kapıları:**
- İşlem hatası < %5
- Kanıt yetersiz < %80

Geçemezse tam çalıştırmaya geçmeyin.

---

## 8. Tam Doğrulama

Tüm kayıtlar için: Notebook Hücre 0-8'i sırayla çalıştırın (`Run All`).

- Benchmark (Hücre 5) sonuçları otomatik yüklenir
- Kalan kayıtlar batch halinde işlenir
- Her 100 kayıtta bir checkpoint yazılır
- Bağlantı kesilse bile kaldığı yerden devam eder

---

## 9. Checkpoint'ten Devam

Aynı config/model/excel ile tekrar çalıştırırsanız otomatik devam eder.

**Tamamen sıfırdan başlamak için:**
```bash
!rm -rf checkpoints_v4/latest/dogrulama_sonuclari.jsonl
!rm -f checkpoints_v4/latest/meta.json
```

---

## 10. Çıktıları Bulma ve İndirme

Çıktılar: `data/output_v4/YYYY-MM-DD_HHMM/`

| Dosya | Açıklama |
|---|---|
| `tum_sonuclar.xlsx` | Tüm kayıtlar + doğrulama sonuçları |
| `dogrulanan.xlsx` | `karar=dogru AND guven>=0.85` |
| `supheli.xlsx` | Elle incelenmesi gereken kayıtlar |
| `ozet.json` | Sayısal özet |
| `grafikler/karar_dagilimi.png` | Görsel özet |

**İndirme:** Drive üzerinden doğrudan erişilebilir.

---

## 11. Sorun Giderme

### OOM (Out of Memory)

```
RuntimeError: CUDA out of memory
```

**Çözüm:**
- `config_v4.yaml` → `gpu_memory_utilization: 0.70`
- `max_model_len: 3072`
- Runtime → Restart session

### Token Aşımı

Sistem otomatik kısaltır. Daha fazla bağlam için:
- `config_v4.yaml` → `max_model_len: 6144` (A100 80GB)

### Kaynak Yetersizliği (%80+ kanit_yetersiz)

- Daha fazla kaynak belge ekle
- `dogrudan_ilgili` belgelerinin sayısını artır
- `.doc` dosyalarını DOCX'e dönüştür

### Eski Checkpoint Hatası

Metadata eksik (`guven_sinifi`, `uyds_ilgililik` boş):
```bash
!rm -rf checkpoints_v4/latest/kaynak_embedding
!python scripts/build_source_corpus.py --cpu --force
```

### vLLM Yüklenemedi

```bash
!pip install vllm==0.12.0 --extra-index-url https://download.pytorch.org/whl/cu128
# Runtime → Restart session
```

### Config Bulunamadı

`config/config_v4.yaml` dosyasının proje kökünde olduğundan emin olun.

---

## Hızlı Başlatma Kontrol Listesi

- [ ] ZIP Drive'a yüklendi ve çıkarıldı
- [ ] Excel `data/input/` içinde
- [ ] Kaynak belgeler `data/kaynaklar/` alt klasörlerinde
- [ ] `python src/classify_relevance.py` çalıştırıldı
- [ ] `python scripts/build_source_corpus.py --cpu --force` çalıştırıldı
- [ ] Notebook açıldı, Runtime → A100 GPU
- [ ] Hücre 0-8 sırayla çalıştırıldı
- [ ] Kalite kapıları geçildi
- [ ] Çıktılar Drive'dan indirildi

---

**Soru?** `README.md` ve notebook içindeki Markdown hücrelerini inceleyin.