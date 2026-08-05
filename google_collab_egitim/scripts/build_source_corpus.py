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

import csv
import hashlib

from src.config import (
    KAYNAK_DIZINI, CIKTI_KOK_DIZINI, CIKTI_DIZINI, CKPT_DIZINI,
    EMBEDDING_MODEL, EMBEDDING_BATCH, CHUNK_BOYUT_TOKEN, CHUNK_OVERLAP_TOKEN,
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
        kaynak,
        cikti_yolu=os.path.join(CIKTI_KOK_DIZINI, "kaynak_envanteri.csv"),
        mevcut_envanter_yolu=os.path.join(CIKTI_KOK_DIZINI, "kaynak_envanteri.csv"),
    )
    if not envanter:
        raise RuntimeError(f"Hiç kaynak belge bulunamadı: {kaynak}")
    ozet = envanter_ozeti(envanter)
    print(f"   {ozet['benzersiz_kaynak']} benzersiz kaynak (toplam {ozet['toplam_kaynak']})")
    if ozet["kopya"]:
        print(f"   ⚠️ {ozet['kopya']} kopya tespit edildi")

    # Desteklenmeyen dosyaları raporla
    doc_dosyalari = []
    for kok, _, ds in os.walk(kaynak):
        for d in ds:
            if d.lower().endswith(".doc") and not d.lower().endswith(".docx"):
                doc_dosyalari.append(os.path.join(kok, d))
    if doc_dosyalari:
        print(f"   ⚠️ {len(doc_dosyalari)} .doc dosyası desteklenmiyor (DOCX'e dönüştürülmeli):")
        for dd in doc_dosyalari:
            print(f"      - {os.path.basename(dd)}")
    z.kontrol("envanter")

    # 2. Belgeleri oku (envanter metadata + ilgililik filtresi ile)
    ILGILILIK_FILTRESI = ["dogrudan_ilgili", "dolayli_ilgili"]
    print(f"\n📄 Belgeler okunuyor (UYDS ilgililik filtresi: {' + '.join(ILGILILIK_FILTRESI)})...")
    # Envanter root output_v4 seviyesinde
    envanter_csv = os.path.join(
        CIKTI_KOK_DIZINI, "kaynak_envanteri_siniflandirilmis.csv"
    )
    print(f"   📂 Envanter yolu: {envanter_csv}")

    # Envanter hash hesapla
    siniflandirilmis_envanter_hash = ""
    if os.path.exists(envanter_csv):
        with open(envanter_csv, "rb") as f:
            siniflandirilmis_envanter_hash = hashlib.sha256(f.read()).hexdigest()
        print(f"   🔐 Envanter SHA-256: {siniflandirilmis_envanter_hash[:16]}...")

    okunan_belgeler = []
    okunamayan_belgeler = []
    belgeler = tum_kaynaklari_yukle(
        kaynak,
        envanter_yolu=envanter_csv,
        ilgililik_filtresi=ILGILILIK_FILTRESI,
    )
    if not belgeler:
        raise RuntimeError("Hiç belge okunamadı! İlgililik filtresi çok sıkı olabilir.")
    print(f"   {len(belgeler)} sayfa/belge metni okundu")
    
    # Metadata kontrolü
    meta_dolu = sum(1 for b in belgeler if b.get("meta", {}).get("kaynak_id"))
    print(f"   📋 {meta_dolu}/{len(belgeler)} belge/sayfa kaydında kaynak_id metadata'sı var")
    
    # Okunan/okunamayan belge raporlaması için benzersiz belgeleri tara
    okunan_dosyalar = set()
    for b in belgeler:
        okunan_dosyalar.add(b.get("dosya", ""))

    # Envanterdeki tüm uygun belgeleri kontrol et
    if os.path.exists(envanter_csv):
        with open(envanter_csv, "r", encoding="utf-8-sig") as f:
            envanter_kayitlari = list(csv.DictReader(f))
        for ek in envanter_kayitlari:
            dosya_adi = ek.get("dosya_adi", "")
            ilgililik = ek.get("uyds_ilgililik", "")
            kaynak_id = ek.get("kaynak_id", "")
            dosya_turu = os.path.splitext(dosya_adi)[1].lower() if dosya_adi else ""
            
            if ilgililik not in ILGILILIK_FILTRESI:
                continue
            
            if dosya_adi in okunan_dosyalar:
                okunan_belgeler.append({
                    "dosya_adi": dosya_adi,
                    "kaynak_id": kaynak_id,
                    "dosya_turu": dosya_turu,
                    "uyds_ilgililik": ilgililik,
                    "durum": "okundu",
                    "hata_tipi": "",
                    "hata_mesaji": "",
                })
            else:
                hata_tipi = _hata_tipini_belirle(dosya_turu)
                okunamayan_belgeler.append({
                    "dosya_adi": dosya_adi,
                    "kaynak_id": kaynak_id,
                    "dosya_turu": dosya_turu,
                    "uyds_ilgililik": ilgililik,
                    "durum": "okunamadi",
                    "hata_tipi": hata_tipi,
                    "hata_mesaji": _hata_mesaji_uret(hata_tipi, dosya_turu),
                })
                
                # Doğrudan ilgili belge okunamazsa alarm ver
                if ilgililik == "dogrudan_ilgili":
                    print(f"\n   🚨 ALARM: Doğrudan ilgili belge okunamadı!")
                    print(f"      Dosya: {dosya_adi} ({kaynak_id})")
                    print(f"      Hata: {hata_tipi}")

    # Okunamayan raporunu kaydet
    if okunamayan_belgeler:
        _csv_kaydet(okunamayan_belgeler, os.path.join(CIKTI_DIZINI, "okunamayan_belgeler.csv"))
        print(f"\n   ⚠️ {len(okunamayan_belgeler)} belge okunamadı (rapor: okunamayan_belgeler.csv)")
        
        dogrudan_okunamayan = [b for b in okunamayan_belgeler if b["uyds_ilgililik"] == "dogrudan_ilgili"]
        if dogrudan_okunamayan:
            raise RuntimeError(
                f"{len(dogrudan_okunamayan)} doğrudan ilgili belge okunamadı! "
                f"İşlem durduruldu. Dosyalar: {[b['dosya_adi'] for b in dogrudan_okunamayan]}"
            )

    if okunan_belgeler:
        _csv_kaydet(okunan_belgeler, os.path.join(CIKTI_DIZINI, "okunan_belgeler.csv"))

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
    SINIFLANDIRMA_SURUMU = "2.0"
    emb_durum = embedding_checkpoint_yukle(
        CKPT_DIZINI, kaynak_dizin_hash, EMBEDDING_MODEL,
        CHUNK_BOYUT_TOKEN, CHUNK_OVERLAP_TOKEN, CHUNK_ALGORITMA_SURUMU,
        siniflandirilmis_envanter_hash=siniflandirilmis_envanter_hash,
        ilgililik_filtresi=ILGILILIK_FILTRESI,
        siniflandirma_surumu=SINIFLANDIRMA_SURUMU,
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
            siniflandirilmis_envanter_hash=siniflandirilmis_envanter_hash,
            ilgililik_filtresi=ILGILILIK_FILTRESI,
            siniflandirma_surumu=SINIFLANDIRMA_SURUMU,
        )
        print(f"   {kaynak_vektorler.shape[0]} vektör × {kaynak_vektorler.shape[1]}d")
    z.kontrol("embedding")

    # 5. Özet
    bellek = gpu_bellek_durumu()
    print(f"\n✅ Kaynak havuzu hazır! Toplam süre: {z.gecen():.1f}s")
    print(z.ozet())
    if bellek:
        print(f"GPU: {bellek['ayrilan_gb']:.1f}/{bellek['toplam_gb']:.1f} GB kullanılıyor")


def _hata_tipini_belirle(dosya_turu: str) -> str:
    """Dosya türüne göre olası hata tipini belirler."""
    if dosya_turu == ".doc":
        return "desteklenmeyen_format"
    elif dosya_turu in (".pdf", ".docx"):
        return "okuma_hatasi"
    elif dosya_turu:
        return "bilinmeyen"
    return "dosya_bulunamadi"


def _hata_mesaji_uret(hata_tipi: str, dosya_turu: str) -> str:
    """Hata tipine göre açıklayıcı mesaj üretir."""
    if hata_tipi == "desteklenmeyen_format":
        return f"{dosya_turu} formatı desteklenmiyor. DOCX/TXT'ye dönüştürülmeli."
    elif hata_tipi == "okuma_hatasi":
        return "PDF/DOCX okunamadı. Dosya bozuk veya şifreli olabilir."
    elif hata_tipi == "bilinmeyen":
        return f"{dosya_turu} formatı için okuyucu bulunamadı."
    return "Dosya bulunamadı."


def _csv_kaydet(kayitlar: list, yol: str) -> None:
    """Dict listesini CSV'ye kaydeder."""
    if not kayitlar:
        return
    alanlar = list(kayitlar[0].keys())
    with open(yol, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=alanlar)
        writer.writeheader()
        writer.writerows(kayitlar)
    print(f"   📊 Kaydedildi: {yol} ({len(kayitlar)} kayıt)")


if __name__ == "__main__":
    main()
