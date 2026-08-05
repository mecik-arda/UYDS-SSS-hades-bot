#!/usr/bin/env python3
# ============================================================
# build_source_corpus.py — Kaynak belge havuzunu oluşturur
# ============================================================
"""
Tüm kaynak belgeleri tarar, chunk'lar, embedding oluşturur,
kaynak envanteri üretir.

Kullanım (Colab):
  !python scripts/build_source_corpus.py --kaynak data/kaynaklar

Kullanım (Lokal test):
  python scripts/build_source_corpus.py --kaynak data/kaynaklar --cpu
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import (
    KAYNAK_DIZINI, CKPT_DIZINI, CIKTI_DIZINI, EMBEDDING_MODEL,
    EMBEDDING_BATCH, CHUNK_BOYUT_TOKEN, CHUNK_OVERLAP_TOKEN,
    CHUNK_ALGORITMA_SURUMU, dizin_hashi, dizinleri_hazirla, config_ozeti,
)
from src.document_loader import tum_kaynaklari_yukle
from src.chunking import belgeyi_chunkla, chunk_istatistikleri
from src.source_inventory import envanter_olustur, envanter_ozeti
from src.embeddings import (
    embedding_modeli_yukle, kaynak_embedding_olustur,
    embedding_checkpoint_kaydet, embedding_checkpoint_yukle,
)
from src.utils import Zamanlayici, gpu_bellek_durumu


def main():
    parser = argparse.ArgumentParser(description="Kaynak belge havuzu oluştur")
    parser.add_argument("--kaynak", default=None, help="Kaynak dizini")
    parser.add_argument("--cpu", action="store_true", help="CPU modu (GPU yoksa)")
    parser.add_argument("--force", action="store_true", help="Embedding checkpoint'i yok say")
    args = parser.parse_args()

    kaynak = args.kaynak or KAYNAK_DIZINI
    dizinleri_hazirla()
    print(config_ozeti())

    z = Zamanlayici()
    cihaz = "cpu" if args.cpu else "cuda"

    # 1. Kaynak envanteri
    print(f"\n📋 Kaynak envanteri taranıyor: {kaynak}")
    envanter = envanter_olustur(
        kaynak, cikti_yolu=os.path.join(CIKTI_DIZINI, "kaynak_envanteri.csv")
    )
    if not envanter:
        raise RuntimeError(f"Hiç kaynak belge bulunamadı: {kaynak}")
    ozet = envanter_ozeti(envanter)
    print(f"   {ozet['benzersiz_kaynak']} benzersiz kaynak (toplam {ozet['toplam_kaynak']})")
    if ozet["kopya"]:
        print(f"   ⚠️ {ozet['kopya']} kopya tespit edildi")
    z.kontrol("envanter")

    # 2. Belgeleri oku (envanter metadata + ilgililik filtresi ile)
    print("\n📄 Belgeler okunuyor (UYDS ilgililik filtresi: dogrudan + dolayli)...")
    # Envanter root output_v4 seviyesinde (timestamp'li alt klasörde değil)
    envanter_csv = os.path.join(
        os.path.dirname(CIKTI_DIZINI),  # output_v4 root
        "kaynak_envanteri_siniflandirilmis.csv"
    )
    if not os.path.exists(envanter_csv):
        envanter_csv = os.path.join(
            os.path.dirname(os.path.dirname(CIKTI_DIZINI)),  # data/
            "output_v4",
            "kaynak_envanteri_siniflandirilmis.csv"
        )
    print(f"   📂 Envanter yolu: {envanter_csv}")
    belgeler = tum_kaynaklari_yukle(
        kaynak,
        envanter_yolu=envanter_csv,
        ilgililik_filtresi=["dogrudan_ilgili", "dolayli_ilgili"],
    )
    if not belgeler:
        raise RuntimeError("Hiç belge okunamadı! İlgililik filtresi çok sıkı olabilir.")
    print(f"   {len(belgeler)} sayfa/belge metni okundu")
    
    # Metadata kontrolü
    meta_dolu = sum(1 for b in belgeler if b.get("meta", {}).get("kaynak_id"))
    print(f"   📋 {meta_dolu}/{len(belgeler)} belgede kaynak_id metadata'sı var")
    z.kontrol("belge_okuma")

    # 3. Chunk'lama
    print(f"\n✂️ Tokenizer tabanlı chunking (hedef={CHUNK_BOYUT_TOKEN}, overlap={CHUNK_OVERLAP_TOKEN})...")
    try:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL, trust_remote_code=False)
        print(f"   Tokenizer yüklendi: {EMBEDDING_MODEL}")
    except Exception:
        print("   ⚠️ Tokenizer yüklenemedi, kelime bazlı fallback")
        tokenizer = None

    chunklar = belgeyi_chunkla(
        belgeler, tokenizer,
        hedef_token=CHUNK_BOYUT_TOKEN, overlap_token=CHUNK_OVERLAP_TOKEN,
    )
    if not chunklar:
        raise RuntimeError("Hiç chunk üretilemedi!")
    ch_stats = chunk_istatistikleri(chunklar, tokenizer)
    print(f"   {ch_stats['toplam_chunk']} chunk ({ch_stats['dokuman_sayisi']} doküman)")
    print(f"   Ortalama token: {ch_stats['ortalama_token']:.0f} (min={ch_stats['min_token']}, max={ch_stats['maks_token']})")
    z.kontrol("chunking")

    # 4. Embedding
    kaynak_dizin_hash = dizin_hashi(kaynak)
    emb_durum = embedding_checkpoint_yukle(
        CKPT_DIZINI, kaynak_dizin_hash, EMBEDDING_MODEL,
        CHUNK_BOYUT_TOKEN, CHUNK_OVERLAP_TOKEN, CHUNK_ALGORITMA_SURUMU,
    )

    if emb_durum and not args.force:
        kaynak_vektorler, tum_parcalar = emb_durum
    else:
        print(f"\n🔤 Embedding: {EMBEDDING_MODEL} ({cihaz})...")
        model = embedding_modeli_yukle(EMBEDDING_MODEL, cihaz=cihaz)
        chunk_metinleri = [c["metin"] for c in chunklar]
        kaynak_vektorler = kaynak_embedding_olustur(
            chunk_metinleri, model, batch_size=EMBEDDING_BATCH,
        )
        embedding_checkpoint_kaydet(
            CKPT_DIZINI, kaynak_vektorler, chunklar,
            kaynak_dizin_hash, EMBEDDING_MODEL,
            CHUNK_BOYUT_TOKEN, CHUNK_OVERLAP_TOKEN, CHUNK_ALGORITMA_SURUMU,
        )
        print(f"   {kaynak_vektorler.shape[0]} vektör × {kaynak_vektorler.shape[1]}d")
    z.kontrol("embedding")

    # 5. Özet
    bellek = gpu_bellek_durumu()
    print(f"\n✅ Kaynak havuzu hazır! Toplam süre: {z.gecen():.1f}s")
    print(z.ozet())
    if bellek:
        print(f"GPU: {bellek['ayrilan_gb']:.1f}/{bellek['toplam_gb']:.1f} GB kullanılıyor")


if __name__ == "__main__":
    main()