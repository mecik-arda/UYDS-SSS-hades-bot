# UYDS SSS Veri Ayıklama Pipeline v3.1

**config.yaml · Checkpoint · Matplotlib Grafik · Tarihli Çıktı · Hash Doğrulama**

---

## 📦 Klasör İçeriği

```
google_collab_egitim/
├── veri_ayiklama_v3.1.ipynb     ← **ANA DOSYA**
├── veri_ayiklama_v2.1.ipynb     ← v2.1 (yedek)
├── veri_ayiklama.ipynb          ← v1 (referans)
├── README.md                    ← Bu dosya
├── requirements.txt             ← Colab bağımlılıkları
├── .gitignore                   ← Çıktı/checkpoint dışlama
├── config/
│   └── config.yaml              ← Tüm eşikler burada
└── data/
    ├── input/                   ← Excel'i buraya koyun
    └── output/                  ← Tarihli çıktı (örn: 2026-08-04_0830/)
```

---

## 🚀 Hızlı Başlangıç

### 1. Drive'a Yükle
`google_collab_egitim/` klasörünü Drive → MyDrive'a yükle.
`UYDS_SSS_Listesi.xlsx`'i `data/input/` içine koy.

### 2. Colab'da Aç
`veri_ayiklama_v3.1.ipynb` → Colab → A100 GPU → tüm hücreleri sırayla çalıştır.

### 3. Çıktıları Al
`data/output/2026-08-04_0830/` içinde:
- `korunan_veri.xlsx` — HadesBot'a aktarılacak temiz veri
- `otomatik_silinecekler.xlsx` — Kontrol etmeniz gerekenler
- `tum_kayitlar_raporu.xlsx` — Tüm satırlar + hata sınıfları
- `rapor_grafik.png` — Pasta grafik + histogram
- `ozet.json` — Sayısal özet
- `checkpoints/` — Her hücrenin `.pkl` yedeği

### 4. HadesBot'a Aktar
```bash
python excel_ice_aktar.py data/output/2026-08-04_0830/korunan_veri.xlsx
python vektorleri_olustur.py
```

---

## 🆚 Sürüm Karşılaştırması

| Özellik | v1 | v2.1 | v3.1 |
|---|---|---|---|
| Model | 2 model | tek model | tek model |
| Eşik yönetimi | Kod içinde | Kod içinde | **config.yaml** |
| Checkpoint | Yok | Yok | **.pkl yedek** |
| Grafik | Yok | Yok | **Pasta + histogram** |
| Çıktı klasörü | ciktilar/ | ciktilar/ | **data/output/ZAMAN/** |
| Colab/VS Code | Sadece Colab | Sadece Colab | **Her ikisi** |
| requirements.txt | Yok | Yok | **Var** |
| .gitignore | Yok | Yok | **Var** |

---

## ⚙️ config.yaml ile Özelleştirme

Tüm eşikleri `config/config.yaml`'dan değiştirebilirsiniz:

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `benzerlik.guclu_aday_esik` | 0.95 | Cosine > bu → GÜÇLÜ_ADAY |
| `benzerlik.incele_esik` | 0.88 | Cosine > bu → İNCELE |
| `kategori.uyumsuzluk_esik` | 0.25 | Cosine < bu → İNCELE |
| `yapisal.kisa_metin_esik` | 5 | Minimum token |
| `yazim.esik` | 0.35 | Yazım hatası oranı |
| `dogrulama.boyut` | 200 | Kaç satırlık doğrulama seti |

Değiştirip kaydedin, notebook değerleri otomatik okur.

---

## Doğrulama ve benzerlik kapsamı

Doğrulama etiketleri öncelikle `_kayit_hash` alanı üzerinden eşleştirilir. Kaynak Excel satırlarının sırası değişse bile manuel etiket doğru kayda taşınır. Eski doğrulama dosyalarında `_kayit_hash` bulunmuyorsa `_veri_indeksi` alanı geriye dönük uyumluluk için kullanılır.

Doğrulama dosyası kaynak Excel dosyasının SHA-256 özetiyle ilişkilendirilir. Kaynak Excel değiştiğinde mevcut doğrulama dosyası otomatik olarak silinmez veya üzerine yazılmaz; kullanıcıya uyarı gösterilir.

Semantic benzerlik analizi performans amacıyla sınırlı sayıda en yakın komşu üzerinde çalışır ve tüm olası çiftleri karşılaştırmaz. Tam tekrarlar kayıt hash'i ile ayrıca tespit edilir.

## 🧠 Model

`sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768d, 278M param)

---

## ❓ Sorun Giderme

| Sorun | Çözüm |
|---|---|
| GPU bulunamadı | Runtime → A100 (CPU'da da çalışır, yavaş) |
| Excel bulunamadı | `data/input/UYDS_SSS_Listesi.xlsx` yolunu kontrol et |
| CUDA OOM | `config.yaml` → `model.batch_size: 32` |
| config.yaml okunamadı | Varsayılan değerlerle devam eder |
| Checkpoint hatası | `config.yaml` → `cikti.checkpoint: false` |

---

**HadesBot · v3.1 · 2026**
