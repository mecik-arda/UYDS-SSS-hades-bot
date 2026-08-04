# UYDS SSS Cevap Doğrulama Pipeline v4.0.2

**Qwen3-32B-AWQ · vLLM Structured Output · Batch Inference · Checkpoint**

---

## 📦 Klasör İçeriği

```
google_collab_egitim/
├── veri_ayiklama_v4.0.ipynb       ← **ANA DOSYA (v4.0.2)**
├── veri_ayiklama_v3.1.ipynb       ← v3.1 ayıklama (yedek)
├── veri_ayiklama_v3.0.ipynb       ← v3.0 (yedek)
├── veri_ayiklama_v2.1.ipynb       ← v2.1 (yedek)
├── veri_ayiklama.ipynb            ← v1 (referans)
├── README.md                      ← Bu dosya
├── requirements.txt               ← v4.0 bağımlılıkları
├── .gitignore                     ← Çıktı/checkpoint dışlama
├── config/
│   ├── config_v4.yaml             ← v4.0 doğrulama eşikleri
│   └── config.yaml                ← v3.x ayıklama eşikleri (yedek)
├── data/
│   ├── kaynaklar/                 ← Referans dokümanları buraya koyun (.txt/.pdf/.docx/.md)
│   └── input/                     ← SSS Excel'i buraya koyun
└── checkpoints_v4/                ← Çalışma sırasında otomatik oluşur
```

---

## 🚀 Hızlı Başlangıç

### 1. Drive'a Yükle
`google_collab_egitim/` klasörünü Google Drive → MyDrive'a yükle.

### 2. Kaynakları ve Excel'i Yerleştir
- Referans dokümanları (mevzuat, yönetmelik, kılavuz) `data/kaynaklar/` içine koy.
- `UYDS_SSS_Listesi.xlsx`'i `data/input/` içine koy.

### 3. Colab'da Aç
`veri_ayiklama_v4.0.ipynb` → Google Colab → **A100 GPU** seç → `Run All`.

### 4. Çıktıları Al
`data/output_v4/YYYY-MM-DD_HHMM/` içinde:
- `tum_sonuclar.xlsx` — Tüm kayıtlar + doğrulama sonuçları
- `dogrulanan.xlsx` — `karar == "dogru" and guven >= 0.85`
- `supheli.xlsx` — Şüpheli kayıtlar (elle incelenmeli)
- `ozet.json` — Sayısal özet (karar dağılımı, güven istatistikleri)
- `dogrulama_grafik.png` — Pasta grafik + bar chart
- `guven_dagilimi.png` — Güven skoru histogramı

---

## 🆚 Sürüm Karşılaştırması

| Özellik | v3.1 | v4.0.2 |
|---|---|---|
| Görev | Yinelenen ayıklama | **Cevap doğrulama** |
| LLM | Yok | Qwen3-32B-AWQ (vLLM) |
| Yöntem | Embedding + DBSCAN + IsoForest | RAG + LLM + structured JSON |
| Kaynak | SSS Excel'in kendisi | **Bağımsız mevzuat/kılavuz** |
| GPU | CPU/T4 yeterli | **A100 40 GB+ zorunlu** |
| Checkpoint | .pkl + .npy | JSONL + meta hash doğrulama |
| Batch | Yok | 8-16 kayıt batch inference |

---

## ⚙️ config_v4.yaml ile Özelleştirme

Tüm eşikleri `config/config_v4.yaml`'dan değiştirebilirsiniz:

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `v4.model.birincil` | Qwen/Qwen3-32B-AWQ | Birincil LLM |
| `v4.model.yedek` | Qwen/Qwen2.5-32B-Instruct-AWQ | Yedek LLM |
| `v4.vllm.batch_size` | 8 | Batch büyüklüğü |
| `v4.vllm.max_model_len` | 8192 | Maksimum bağlam uzunluğu |
| `v4.vllm.gpu_memory_utilization` | 0.88 | GPU bellek kullanımı |
| `v4.rag.top_k` | 10 | Dense retrieval aday sayısı |
| `v4.rag.son_k` | 5 | Modele gönderilen kaynak sayısı |
| `v4.rag.min_skor` | 0.3 | Minimum cosine eşiği |
| `v4.chunk.boyut` | 400 | Chunk token sayısı |
| `v4.chunk.overlap` | 80 | Chunk örtüşme |
| `v4.guven.esik` | 0.85 | **KALİBRE EDİLMEMİŞ** |
| `v4.checkpoint.aralik` | 100 | Her N kayıtta checkpoint |

---

## 🧠 Modeller

- **LLM:** `Qwen/Qwen3-32B-AWQ` (birincil) / `Qwen/Qwen2.5-32B-Instruct-AWQ` (yedek)
- **Embedding:** `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768d)
- **Inference:** vLLM (offline batch, structured JSON output, enable_thinking=False)

---

## ❓ Sorun Giderme

| Sorun | Çözüm |
|---|---|
| GPU yetersiz | Runtime → A100 40 GB veya 80 GB seçin |
| Kaynak bulunamadı | `data/kaynaklar/` içine en az bir .txt/.pdf/.docx koyun |
| Excel bulunamadı | `data/input/UYDS_SSS_Listesi.xlsx` yolunu kontrol et |
| vLLM yüklenemedi | İnternet bağlantısını kontrol et; yedek model otomatik denenir |
| CUDA OOM | `config_v4.yaml` → `v4.vllm.gpu_memory_utilization: 0.80` |
| Checkpoint geçersiz | Excel/config/model değişmişse otomatik sıfırlanır |

---

## ⚠️ Önemli Not

**Güven eşiği (0.85) kalibre edilmemiştir.** İlk 200-300 kaydı elle etiketleyip precision/recall ölçtükten sonra nihai eşik belirlenmelidir.

---

**HadesBot · v4.0.2 · 2026**