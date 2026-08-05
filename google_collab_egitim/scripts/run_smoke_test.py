#!/usr/bin/env python3
# ============================================================
# run_smoke_test.py — Mock model ile 20 kayıtlık uçtan uca test
# ============================================================
"""
Gerçek GPU/LLM olmadan mock model ile tüm pipeline'ı test eder.

Aşamalar:
  1. Kaynak yükleme testi (en az 1 chunk)
  2. Embedding boyut doğrulama
  3. 5 kayıt retrieval testi
  4. 5 kayıt mock Qwen structured-output testi
  5. 20 kayıt smoke test
  6. Benzersiz _kayit_no kontrolü
  7. İşlem hatası oranı kontrolü (<%5)
  8. Kaynak kullanım oranı kontrolü (>1 ortalama)
  9. Tahmini tam çalışma süresi

Kullanım:
  python scripts/run_smoke_test.py
"""

import json
import os
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import (
    KAYNAK_DIZINI, CKPT_DIZINI, CIKTI_DIZINI,
    EMBEDDING_MODEL, EMBEDDING_BATCH, SORU_EMB_BATCH,
    CHUNK_BOYUT_TOKEN, CHUNK_OVERLAP_TOKEN,
    RAG_TOP_K, RAG_SON_K, RAG_MIN_SKOR,
    GUVEN_ESIK, PROMPT_TOKEN_LIMIT,
    dizinleri_hazirla, dizin_hashi, config_ozeti,
)
from src.document_loader import tum_kaynaklari_yukle
from src.chunking import belgeyi_chunkla, chunk_istatistikleri
from src.embeddings import (
    embedding_modeli_yukle, kaynak_embedding_olustur,
    soru_embedding_olustur, embedding_checkpoint_kaydet,
)
from src.retrieval import dense_kaynak_ara
from src.prompt_builder import kanit_yetersiz_yanit, cevap_bos_yanit
from src.validator import ham_metinden_json_cikar
from src.utils import Zamanlayici


# ============================================================
# Mock vLLM çıktıları (gerçek model çağrılmaz)
# ============================================================
_MOCK_CIKTILAR = [
    # dogru
    '{"karar":"dogru","guven":0.95,"kaynak_idleri":[0],"dayanak":"Kaynak birebir örtüşüyor.","eksik_veya_hata":"","duzeltilmis_cevap":""}',
    # kismen_dogru
    '{"karar":"kismen_dogru","guven":0.72,"kaynak_idleri":[1],"dayanak":"Kısmen doğru.","eksik_veya_hata":"Detay eksik.","duzeltilmis_cevap":"Eklenmiş cevap."}',
    # kanit_yetersiz
    '{"karar":"kanit_yetersiz","guven":0.0,"kaynak_idleri":[],"dayanak":"Yetersiz kaynak.","eksik_veya_hata":"","duzeltilmis_cevap":""}',
    # yanlis
    '{"karar":"yanlis","guven":0.85,"kaynak_idleri":[2],"dayanak":"Çelişkili.","eksik_veya_hata":"Hatalı.","duzeltilmis_cevap":"Doğru cevap."}',
    # dogru
    '{"karar":"dogru","guven":0.91,"kaynak_idleri":[0,1],"dayanak":"İki kaynak da doğruluyor.","eksik_veya_hata":"","duzeltilmis_cevap":""}',
]


def mock_model_cagir(promptlar):
    """Mock model: her prompt için döngüsel mock çıktı döndürür."""
    class MockCikti:
        def __init__(self, text):
            self.outputs = [type("obj", (), {"text": text})()]
    return [MockCikti(_MOCK_CIKTILAR[i % len(_MOCK_CIKTILAR)]) for i in range(len(promptlar))]


def mock_tokenizer():
    """Basit bir mock tokenizer."""
    return None  # Kelime bazlı fallback kullan


# ============================================================
# Ana Smoke Test
# ============================================================
def main():
    z = Zamanlayici()
    dizinleri_hazirla()
    print(config_ozeti())
    print(f"\n🧪 SMOKE TEST — Mock Model (20 kayıt)")

    basarisiz = False
    uyarilar = []

    # --- Aşama 1: Kaynak Yükleme ---
    print("\n1️⃣ Kaynak yükleme...")
    belgeler = tum_kaynaklari_yukle(KAYNAK_DIZINI)
    if not belgeler:
        print("   ⚠️ Hiç belge yok. Örnek metinle devam ediliyor.")
        belgeler = [{
            "dosya": "ornek_kilavuz.txt",
            "sayfa": None,
            "metin": "Hakediş onay işlemi için belge kontrolü yapılır. "
                     "Belge eksikse sistem hata verir. "
                     "İhale sürecinde teklif zarfları komisyonca açılır. "
                     "Sözleşme imzalandıktan sonra işe başlama onayı verilir.",
            "meta": {"kaynak_tipi": "resmi_kilavuz", "modul": "Hakediş"},
        }]
    print(f"   ✅ {len(belgeler)} belge/sayfa yüklendi")
    z.kontrol("1_yukleme")

    # --- Aşama 2: Chunking ---
    print("\n2️⃣ Tokenizer tabanlı chunking...")
    chunklar = belgeyi_chunkla(belgeler, None, hedef_token=CHUNK_BOYUT_TOKEN, overlap_token=CHUNK_OVERLAP_TOKEN)
    if not chunklar:
        print("   ❌ Hiç chunk üretilemedi!")
        sys.exit(1)
    ch_stats = chunk_istatistikleri(chunklar, None)
    print(f"   ✅ {ch_stats['toplam_chunk']} chunk, {ch_stats['ortalama_token']:.0f} ortalama token")
    z.kontrol("2_chunking")

    # --- Aşama 3: Embedding ---
    print("\n3️⃣ Embedding (CPU mock)...")
    try:
        model = embedding_modeli_yukle(EMBEDDING_MODEL, cihaz="cpu")
        chunk_metinleri = [c["metin"] for c in chunklar]
        kaynak_vektorler = kaynak_embedding_olustur(chunk_metinleri, model, batch_size=1)
        emb_boyut = kaynak_vektorler.shape[1]
        print(f"   ✅ {kaynak_vektorler.shape[0]} vektör × {emb_boyut}d")
        if emb_boyut < 128:
            basarisiz = True
            print(f"   ❌ Embedding boyutu beklenenden düşük: {emb_boyut}")
    except Exception as e:
        print(f"   ⚠️ Embedding modeli yüklenemedi: {e}")
        print("   🔄 Rastgele embedding ile devam ediliyor...")
        kaynak_vektorler = np.random.randn(len(chunklar), 768).astype(np.float32)
        kaynak_vektorler = kaynak_vektorler / np.linalg.norm(kaynak_vektorler, axis=1, keepdims=True)
        emb_boyut = 768
        print(f"   ✅ {kaynak_vektorler.shape[0]} vektör × {emb_boyut}d (mock)")
    z.kontrol("3_embedding")

    # --- Aşama 4: 5 Kayıt Retrieval ---
    print("\n4️⃣ 5 kayıt retrieval testi...")
    soru_metinleri = [
        "Hakediş onayı nasıl yapılır?",
        "İhale teklif zarfları ne zaman açılır?",
        "Sözleşme sonrası işe başlama onayı nereden alınır?",
        "Belge eksik olursa ne olur?",
        "Hakediş raporu nasıl hazırlanır?",
    ]
    soru_vektorler = np.random.randn(5, emb_boyut).astype(np.float32)
    soru_vektorler = soru_vektorler / np.linalg.norm(soru_vektorler, axis=1, keepdims=True)

    for i, soru in enumerate(soru_metinleri):
        parcalar, skor = dense_kaynak_ara(
            soru_vektorler[i], kaynak_vektorler, chunklar,
            top_k=RAG_TOP_K, son_k=RAG_SON_K, min_skor=0.0,
        )
        print(f"   [{i}] → {len(parcalar)} kaynak, maks_skor={skor:.3f}")

    z.kontrol("4_retrieval")

    # --- Aşama 5: 5 Kayıt Mock Qwen ---
    print("\n5️⃣ 5 kayıt mock Qwen structured-output testi...")
    for i in range(5):
        parcalar, _ = dense_kaynak_ara(
            soru_vektorler[i], kaynak_vektorler, chunklar,
            top_k=RAG_TOP_K, son_k=RAG_SON_K, min_skor=0.0,
        )
        sunulan_idler = {p["chunk_id"] for p in parcalar} if parcalar else set()
        mock_metin = _MOCK_CIKTILAR[i % len(_MOCK_CIKTILAR)]
        sonuc = ham_metinden_json_cikar(mock_metin, sunulan_idler)
        print(f"   [{i}] karar={sonuc['karar']}, guven={sonuc['guven']}, hata={sonuc['_islem_hatasi']}")

    z.kontrol("5_mock_qwen")

    # --- Aşama 6: 20 Kayıt Tam Smoke Test ---
    print("\n6️⃣ 20 kayıt tam smoke test (mock)...")
    TAM_KAYIT = 20
    tum_sonuclar = []

    for i in range(TAM_KAYIT):
        cevap_bos = (i == 5)  # 5. kayıt boş cevap
        kaynaksiz = (i == 10)  # 10. kayıt kaynaksız

        if cevap_bos:
            sonuc = cevap_bos_yanit()
        elif kaynaksiz:
            sonuc = kanit_yetersiz_yanit()
        else:
            parcalar, _ = dense_kaynak_ara(
                np.random.randn(emb_boyut).astype(np.float32),
                kaynak_vektorler, chunklar,
                top_k=RAG_TOP_K, son_k=RAG_SON_K, min_skor=0.0,
            )
            sunulan_idler = {p["chunk_id"] for p in parcalar} if parcalar else set()
            mock_metin = _MOCK_CIKTILAR[i % len(_MOCK_CIKTILAR)]
            sonuc = ham_metinden_json_cikar(mock_metin, sunulan_idler)

        sonuc["_kayit_no"] = i
        sonuc["_veri_indeksi"] = i
        sonuc["_rag_maks_skor"] = 0.5 if not kaynaksiz else 0.0
        tum_sonuclar.append(sonuc)

    # İstatistikler
    kararlar = [s["karar"] for s in tum_sonuclar]
    guvenler = [s["guven"] for s in tum_sonuclar if not s.get("_islem_hatasi")]
    hata_sayisi = sum(1 for s in tum_sonuclar if s.get("_islem_hatasi"))
    kaynak_kullanimi = [len(s.get("kaynak_idleri", [])) for s in tum_sonuclar]

    print(f"   Karar dağılımı: {dict(Counter(kararlar))}")
    print(f"   İşlem hatası: {hata_sayisi}/{TAM_KAYIT}")
    ortalama_kaynak = np.mean(kaynak_kullanimi) if kaynak_kullanimi else 0
    print(f"   Ortalama kaynak: {ortalama_kaynak:.1f}")

    # --- Aşama 7: Benzersiz _kayit_no ---
    print("\n7️⃣ Benzersiz _kayit_no kontrolü...")
    nolar = [s["_kayit_no"] for s in tum_sonuclar]
    if len(nolar) != len(set(nolar)):
        print("   ❌ Mükerrer _kayit_no tespit edildi!")
        basarisiz = True
    else:
        print(f"   ✅ {len(nolar)} benzersiz kayıt")

    # --- Aşama 8: İşlem Hatası Oranı ---
    print("\n8️⃣ İşlem hatası oranı kontrolü...")
    hata_oran = hata_sayisi / TAM_KAYIT
    print(f"   Hata oranı: {hata_oran:.1%}")
    if hata_oran > 0.05:
        print("   ❌ İşlem hatası oranı > %5!")
        basarisiz = True

    # --- Aşama 9: Kaynak Kullanım ---
    print("\n9️⃣ Kaynak kullanım oranı...")
    if ortalama_kaynak < 1.0:
        uyarilar.append(f"Ortalama sunulan kaynak < 1.0 ({ortalama_kaynak:.1f})")
        basarisiz = True

    # Kanıt yetersiz oranı
    ky_oran = kararlar.count("kanit_yetersiz") / TAM_KAYIT
    if ky_oran > 0.80:
        uyarilar.append(f"Kanıt yetersiz oranı > %80 ({ky_oran:.0%}) — Kaynak havuzu yetersiz olabilir")

    # --- Aşama 10: Tahmini Süre ---
    z.kontrol("smoke_test")
    saniye_basi = z.kontrol_noktalari[-1][1] / TAM_KAYIT if z.kontrol_noktalari else 0.5
    tahmini_dk = (saniye_basi * 2400) / 60  # ~2400 kayıt için
    print(f"\n⏱️ Tahmini tam çalışma: ~{tahmini_dk:.0f} dk (mock, gerçek A100'de daha uzun)")

    # --- Sonuç ---
    print(f"\n{'='*50}")
    if basarisiz:
        print("❌ SMOKE TEST BAŞARISIZ — Tam çalışmaya geçilmemeli!")
    else:
        print("✅ SMOKE TEST BAŞARILI — Tam çalışmaya geçilebilir.")

    if uyarilar:
        print("\n⚠️ Uyarılar:")
        for u in uyarilar:
            print(f"   - {u}")

    print(f"\nToplam süre: {z.gecen():.1f}s")
    print(z.ozet())

    # Çıktıyı kaydet
    os.makedirs(CIKTI_DIZINI, exist_ok=True)
    cikti = os.path.join(CIKTI_DIZINI, "smoke_test_sonuclari.json")
    with open(cikti, "w", encoding="utf-8") as f:
        json.dump({
            "basarili": not basarisiz,
            "test_edilen": TAM_KAYIT,
            "islem_hatasi": hata_sayisi,
            "islem_hatasi_oran": hata_oran,
            "ortalama_kaynak": ortalama_kaynak,
            "kanit_yetersiz_oran": ky_oran,
            "karar_dagilimi": dict(Counter(kararlar)),
            "uyarilar": uyarilar,
            "toplam_sure_sn": z.gecen(),
        }, f, ensure_ascii=False, indent=2)
    print(f"📁 Sonuç: {cikti}")

    return 0 if not basarisiz else 1


if __name__ == "__main__":
    sys.exit(main())