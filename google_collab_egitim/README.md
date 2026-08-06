# UYDS SSS Cevap Doğrulama Pipeline v4.1.0

**Qwen3-32B-AWQ · vLLM Structured Output · Tokenizer Chunking · Modüler Mimari**

---

## Sistem Ne Yapıyor?

UYDS (Ulusal Yapı Denetim Sistemi) SSS Excel'indeki soru-cevap çiftlerini, **bağımsız ve güvenilir kaynak belgelere** (mevzuat, resmî kılavuz, modül dokümanları) dayanarak Qwen3-32B-AWQ ile doğrular.

Model eğitilmez; hazır Qwen3-32B-AWQ modeli yalnızca inference (çıkarım) için kullanılır.

**GPU gereksinimi:** NVIDIA A100 40 GB veya 80 GB (vLLM + 32B model).

---

## Klasör Yapısı

```
google_collab_egitim/
├── veri_ayiklama_v4.1.ipynb       ← Ana notebook (Colab A100)
├── README.md
├── requirements.txt
├── .gitignore
├── config/
│   └── config_v4.yaml             ← Tüm eşikler burada
├── src/                           ← Modüler Python kütüphanesi (22 modül)
│   ├── config.py                  ← YAML config, dizin keşfi, hash
│   ├── document_loader.py         ← PDF/DOCX/TXT/MD/XLSX/CSV/JSON/JSONL
│   ├── chunking.py                ← Tokenizer tabanlı chunking (256/50)
│   ├── source_inventory.py        ← SHA-256 envanter, kopya tespiti
│   ├── utils.py                   ← Metin temizleme, GPU bellek, zamanlayıcı
│   ├── embeddings.py              ← SentenceTransformer + checkpoint
│   ├── retrieval.py               ← Dense cosine RAG
│   ├── prompt_builder.py          ← Chat template token kontrolü
│   ├── validator.py               ← JSON çıktı doğrulama (6 kural)
│   ├── checkpoint.py              ← JSONL checkpoint yönetimi
│   ├── reporting.py               ← Excel/JSON/grafik çıktıları
│   ├── excel_format.py            ← Excel başlık algılama, UYDS eşleme
│   ├── ocr_helpers.py             ← Taranmış PDF OCR pipeline
│   ├── source_validation.py       ← Kaynak güvenlik kapısı
│   ├── classify_relevance.py      ← Kaynak ilgililik sınıflandırma
│   ├── gap_analysis.py            ← Kaynak kapsama analizi
│   ├── verify_sources.py          ← Kaynak bütünlük doğrulama
│   ├── download_sources.py        ← Mevzuat kaynak indirme
│   ├── download_all_sources.py    ← Toplu kaynak indirme
│   ├── collect_links.py           ← Kaynak bağlantı toplama
│   ├── final_report.py            ← Nihai rapor çıktısı
│   ├── web_scraper.py             ← Web kazıma
│   └── source_inventory.py        ← Dosya envanter yönetimi
├── tests/                         ← 107 birim test (pytest, 7 dosya)
│   ├── test_excel_format.py       ← Başlık algılama, UYDS eşleme
│   ├── test_chunking.py           ← Cümle ayırma, tokenizer chunking
│   ├── test_retrieval.py          ← Dense RAG, min_skor, aynı doküman limiti
│   ├── test_json_validation.py    ← JSON parse, 6 doğrulama kuralı
│   ├── test_checkpoint.py         ← Kaydet/yükle, eksik kayıt
│   ├── test_prompt_token_limit.py ← Token sayımı, kısaltma stratejisi
│   └── test_output_integrity.py   ← Doğrulanan maskesi, smoke test eşikleri
├── scripts/
│   ├── build_source_corpus.py     ← Kaynak havuzu inşa betiği
│   ├── run_smoke_test.py          ← Mock model ile 20 kayıt uçtan uca test
│   ├── validate_outputs.py        ← Çıktı bütünlüğü kontrol aracı
│   ├── evaluate_retrieval.py      ← Retrieval değerlendirmesi (Hit@k)
│   ├── prepare_colab.py           ← Colab ortam hazırlık
│   └── validate_notebook.py       ← Notebook yapısal doğrulama
└── data/
    ├── input/                     ← UYDS Excel'i buraya (.gitignore korumalı)
    └── kaynaklar/                 ← Referans belgeler (.gitignore korumalı)
        ├── 01_mevzuat/
        ├── 02_resmi_uyds_kilavuzlari/
        ├── 03_modul_dokumanlari/
        ├── 04_teknik_cozumler/
        ├── 05_onayli_destek_kayitlari/
        └── 06_surum_notlari/
```

---

## Hızlı Başlangıç

Ayrıntılı adım adım talimatlar ve komutlar için **[COLAB_KULLANIM.md](COLAB_KULLANIM.md)** dosyasına bakın. Aşağıda özet çalışma sırası verilmiştir:

### 1. Kaynak Belgeleri Ekle

`data/kaynaklar/` alt klasörlerine referans belgeleri (PDF, DOCX, TXT, MD) koyun.

**Önemli:** Sistem yalnızca verdiğiniz belgelere dayanır. Kaynak yoksa tüm cevaplar `kanit_yetersiz` çıkar.

**UYARI:** Doğrulanmamış SSS cevaplarını kaynak olarak kullanmayın — döngüsel doğrulamaya neden olur.

### 2. Excel'i Yerleştir

`data/input/` içine `UYDS_SSS_Listesi.xlsx` dosyasını koyun.

### 3. Drive'a Yükle

`google_collab_egitim/` klasörünün tamamını Google Drive → MyDrive'a yükleyin.

### 4. Ön Hazırlık (Colab veya Lokal)

```bash
# Kaynak ilgililik sınıflandırması
python src/classify_relevance.py

# Corpus ve embedding üretimi
python scripts/build_source_corpus.py --cpu --force

# Retrieval değerlendirmesi (örnek 50 soru)
python scripts/evaluate_retrieval.py --soru_sayisi 50 --cpu
```

### 5. Smoke Test (GPU Gerektirmez)

20 kayıt mock model ile uçtan uca test; kalite kapıları:
- İşlem hatası < %5 (zorunlu)
- Ortalama kaynak kullanımı > 1 (zorunlu)

```bash
python scripts/run_smoke_test.py
```

### 6. Colab'da Çalıştır

1. `veri_ayiklama_v4.1.ipynb` → Google Colab'da aç
2. Runtime → Change runtime type → **A100 GPU**
3. `Disconnect and delete runtime` ile temiz başlangıç
4. Hücreleri sırayla çalıştır (Hücre 0-8)
5. Benchmark (Hücre 5) kalite kapıları geçmeden tam çalışmaya geçilmez

### 7. Çıktıları Al

`data/output_v4/YYYY-MM-DD_HHMM/` içinde:

| Dosya | Açıklama |
|---|---|
| `tum_sonuclar.xlsx` | Tüm kayıtlar + doğrulama sonuçları |
| `dogrulanan.xlsx` | `karar=dogru AND guven>=0.85` |
| `supheli.xlsx` | Diğer tüm kayıtlar (elle incelenmeli) |
| `islem_hatalari.xlsx` | Yeniden denemeye rağmen hatalı kalanlar |
| `kaynak_kapsama_raporu.xlsx` | Modül ve kaynak bazlı kapsama |
| `ozet.json` | Sayısal özet |
| `benchmark.json` | Benchmark performans metrikleri |
| `grafikler/karar_dagilimi.png` | Pasta grafik + güven histogramı |

---

## Smoke Test (GPU Gerektirmez)

Lokal bilgisayarda mock model ile 20 kayıtlık uçtan uca test:

```bash
cd google_collab_egitim
pip install -r requirements.txt
python scripts/run_smoke_test.py
```

Aşamalar: kaynak yükleme → chunking → embedding → retrieval → mock Qwen → 20 kayıt doğrulama → bütünlük kontrolleri.

---

## Birim Testler

```bash
cd google_collab_egitim
python -m pytest tests/ -v
```

107 test (excel_format, chunking, retrieval, json_validation, checkpoint, prompt_token_limit, output_integrity).

---

## Checkpoint'ten Devam

Yarım kalan çalışma aynı config/model/veri ile devam eder. Checkpoint uyuşmazsa otomatik sıfırlanır.

Yeniden başlatmak için: `checkpoints_v4/latest/` klasörünü silin.

---

## config_v4.yaml ile Özelleştirme

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `v4.model.birincil` | Qwen/Qwen3-32B-AWQ | Birincil LLM |
| `v4.model.yedek` | Qwen/Qwen2.5-32B-Instruct-AWQ | Yedek LLM |
| `v4.chunk.token_boyut` | 256 | Hedef chunk token sayısı |
| `v4.chunk.token_overlap` | 50 | Chunk örtüşme |
| `v4.rag.top_k` | 10 | Dense retrieval aday sayısı |
| `v4.rag.son_k` | 5 | Modele gönderilen kaynak sayısı |
| `v4.rag.min_skor` | 0.25 | Minimum cosine eşiği |
| `v4.vllm.max_model_len` | 4096 | Maksimum bağlam uzunluğu |
| `v4.vllm.gpu_memory_utilization` | 0.75 | GPU bellek kullanımı |
| `v4.vllm.batch_size` | 4 | Batch büyüklüğü |
| `v4.guven.esik` | 0.85 | **KALİBRE EDİLMEMİŞ** |
| `v4.checkpoint.aralik` | 100 | Her N kayıtta checkpoint |

---

## Sık Karşılaşılan Hatalar

| Sorun | Çözüm |
|---|---|
| **GPU yetersiz** | Runtime → A100 40 GB veya 80 GB seçin |
| **OOM (Out of Memory)** | `config_v4.yaml` → `gpu_memory_utilization: 0.70`; `max_model_len: 3072` |
| **Kaynak bulunamadı** | `data/kaynaklar/` içine en az bir belge koyun |
| **Excel bulunamadı** | `data/input/` yolunu kontrol et |
| **>%80 kanit_yetersiz** | Kaynak havuzu yetersiz veya soru-kaynak domain uyumsuzluğu — daha fazla belge ekleyin veya domain'i kontrol edin |
| **vLLM yüklenemedi** | İnternet bağlantısını kontrol et; yedek model otomatik denenir |
| **Prompt token aşımı** | Sistem otomatik kısaltır; `max_model_len` artırılabilir |
| **vLLM sürüm uyumsuzluğu** | `pip install vllm==0.12.0 --extra-index-url https://download.pytorch.org/whl/cu128` |
| **Tokenizer yüklenemedi** | Kelime bazlı fallback kullanılır, doğruluk biraz düşer |

---

## Modeller

- **LLM:** `Qwen/Qwen3-32B-AWQ` (birincil) / `Qwen/Qwen2.5-32B-Instruct-AWQ` (yedek)
- **Embedding:** `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768d, 128 token limit)
- **Inference:** vLLM 0.12.0 (offline batch, structured JSON output, `enable_thinking=False`)

---

## Gizlilik ve Kurumsal Veri Uyarısı

- **Gerçek Excel ve kurum içi kaynak belgeleri Git'e eklenmez** (`.gitignore` korumalı).
- `data/input/*`, `data/kaynaklar/*` GitHub'a push'lanmaz.
- Dağıtım paketi (ZIP) oluştururken `data/input/` ve `data/kaynaklar/` içindeki gerçek dosyaları çıkarın.
- Colab'da çalışırken veriler Google Drive'ınızda kalır.

---

## ⚠️ Önemli Not

**Güven eşiği (0.85) kalibre edilmemiştir.** İlk 200-300 kaydı elle etiketleyip precision/recall ölçtükten sonra nihai eşik belirlenmelidir.

---

**HadesBot · v4.1.0 · 2026**