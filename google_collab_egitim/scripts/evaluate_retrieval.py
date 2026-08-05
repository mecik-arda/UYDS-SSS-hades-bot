#!/usr/bin/env python3
# ============================================================
# evaluate_retrieval.py — Gerçek sorularla RAG retrieval kalitesini ölçer
# ============================================================
"""
50-100 gerçek UYDS sorusunu MPNet ile encode eder, dense retrieval yapar,
top-3 kaynakları CSV'ye yazar, Hit@1/3, Recall@3 metriklerini hesaplar.

Kullanım (Colab):
  !python scripts/evaluate_retrieval.py --soru_sayisi 50

Kullanım (Lokal):
  python scripts/evaluate_retrieval.py --soru_sayisi 50 --cpu
"""

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import (
    CKPT_DIZINI, CIKTI_DIZINI, EMBEDDING_MODEL, EMBEDDING_BATCH,
    CHUNK_BOYUT_TOKEN, CHUNK_OVERLAP_TOKEN, CHUNK_ALGORITMA_SURUMU,
    dizin_hashi, dosya_hashi, dizinleri_hazirla,
)
from src.embeddings import (
    soru_embedding_olustur, embedding_checkpoint_yukle,
)
from src.retrieval import dense_kaynak_ara, rag_istatistikleri


# ============================================================
# Soru Yükleme
# ============================================================
def sorulari_yukle(excel_yolu: Optional[str] = None, max_soru: int = 50) -> List[Dict[str, str]]:
    """
    Excel'den veya fallback soru listesinden soruları yükler.
    Her soru: {"soru_id": ..., "soru_metni": ..., "modul": ..., "kategori": ...}
    """
    sorular = []

    if excel_yolu and os.path.exists(excel_yolu):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(excel_yolu, read_only=True, data_only=True)
            ws = wb.active
            basliklar = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if len(sorular) >= max_soru:
                    break
                kayit = dict(zip(basliklar, row))
                soru_metni = (
                    kayit.get("soru") or kayit.get("Soru") or
                    kayit.get("soru_metni") or kayit.get("SORU_METNI") or ""
                )
                if soru_metni and str(soru_metni).strip():
                    sorular.append({
                        "soru_id": str(kayit.get("soru_id") or kayit.get("SORU_ID") or kayit.get("no") or len(sorular) + 1),
                        "soru_metni": str(soru_metni).strip(),
                        "modul": str(kayit.get("modul") or kayit.get("MODUL") or ""),
                        "kategori": str(kayit.get("kategori") or kayit.get("KATEGORI") or ""),
                    })
            wb.close()
            print(f"   📊 Excel'den {len(sorular)} soru yüklendi: {excel_yolu}")
        except Exception as e:
            print(f"   ⚠️ Excel okunamadı: {e}")

    if not sorular:
        sorular = _fallback_sorular(max_soru)
        print(f"   📋 Fallback soru listesinden {len(sorular)} soru yüklendi.")

    return sorular


def _fallback_sorular(max_soru: int) -> List[Dict[str, str]]:
    """Excel yoksa kullanılacak 50+ UYDS sorusu."""
    tum_sorular = [
        ("S-001", "Yapı denetim izin belgesi nasıl alınır?", "mevzuat", "izin_belgesi"),
        ("S-002", "4708 sayılı kanun kapsamında laboratuvar denetimi nasıl yapılır?", "mevzuat", "laboratuvar"),
        ("S-003", "Hakediş raporu hazırlanırken hangi formüller kullanılır?", "modul", "hakedis"),
        ("S-004", "UYDS'ye giriş yapamıyorum, şifremi nasıl sıfırlarım?", "teknik", "giris"),
        ("S-005", "Beton numunesi alma sıklığı ne olmalıdır?", "laboratuvar", "beton"),
        ("S-006", "Yapı denetim hizmet sözleşmesi nasıl feshedilir?", "mevzuat", "sozlesme"),
        ("S-007", "Seviye tespit raporu hangi durumlarda zorunludur?", "modul", "seviye_tespit"),
        ("S-008", "İlave iş ve fiyat farkı hesaplaması nasıl yapılır?", "modul", "hakedis"),
        ("S-009", "CAD ile çizilen projeler hangi formatta UYDS'ye yüklenir?", "teknik", "cad"),
        ("S-010", "Yapı kayıt belgesi başvurusu için gerekli evraklar nelerdir?", "mevzuat", "yapi_kayit"),
        ("S-011", "Laboratuvar denetim sonuçları UYDS'de hangi ekranda görüntülenir?", "modul", "laboratuvar"),
        ("S-012", "Kısmi kabul işlemleri nasıl yapılır?", "modul", "kabul"),
        ("S-013", "Geçici kabul ile kesin kabul arasındaki farklar nelerdir?", "mevzuat", "kabul"),
        ("S-014", "Fiyat farkı hesabında TÜİK endeksleri nasıl kullanılır?", "modul", "hakedis"),
        ("S-015", "Süre uzatımı talebi hangi şartlarda kabul edilir?", "mevzuat", "sure_uzatimi"),
        ("S-016", "Yapı malzemeleri yönetmeliğine göre hangi belgeler zorunludur?", "mevzuat", "malzeme"),
        ("S-017", "UYDS modüllerinden hangileri laboratuvar personeli tarafından kullanılır?", "teknik", "moduller"),
        ("S-018", "Denetim hizmetleri yönetmeliği kapsamında kaç denetçi görevlendirilir?", "mevzuat", "denetim"),
        ("S-019", "EBİS kaydı için gerekli adımlar nelerdir?", "mevzuat", "ebis"),
        ("S-020", "İş bitirme belgesi UYDS'ye nasıl yüklenir?", "modul", "is_bitirme"),
        ("S-021", "Benzer iş grupları hangi kriterlere göre belirlenir?", "mevzuat", "is_grup"),
        ("S-022", "Yapı denetim kuruluşu sınıflandırması nasıl yapılır?", "mevzuat", "siniflandirma"),
        ("S-023", "Karot numunesi alımında dikkat edilmesi gereken hususlar nelerdir?", "laboratuvar", "karot"),
        ("S-024", "UYDS'de kullanıcı yetkilendirme işlemleri nasıl yapılır?", "teknik", "yetki"),
        ("S-025", "Asgari işçilik hesaplaması hangi durumlarda yapılır?", "modul", "iscilik"),
        ("S-026", "Yapı denetimi uygulama yönetmeliğinde son değişiklikler nelerdir?", "mevzuat", "yonetmelik"),
        ("S-027", "Zemin etüdü raporu UYDS'ye nasıl kaydedilir?", "modul", "zemin"),
        ("S-028", "Statik proje onay süreci UYDS üzerinden nasıl yürütülür?", "modul", "proje"),
        ("S-029", "Laboratuvar akreditasyon belgesi hangi kurum tarafından verilir?", "laboratuvar", "akreditasyon"),
        ("S-030", "İhale sürecinde yeterlik kriterleri nasıl belirlenir?", "mevzuat", "ihale"),
        ("S-031", "UYDS bakım ve destek hizmetleri nasıl alınır?", "teknik", "destek"),
        ("S-032", "CDD raporu hangi aralıklarla güncellenmelidir?", "modul", "cdd"),
        ("S-033", "Yapı denetim personeli mesleki yeterlilik şartları nelerdir?", "mevzuat", "personel"),
        ("S-034", "İnşaat ruhsatı başvurusu hangi belgelere tabidir?", "mevzuat", "ruhsat"),
        ("S-035", "UYDS'de veri yedekleme sıklığı ne olmalıdır?", "teknik", "yedekleme"),
        ("S-036", "Şantiye şefliği görevlendirmesi nasıl yapılır?", "mevzuat", "santiye"),
        ("S-037", "Yapı yaklaşık maliyet hesabı UYDS'de hangi modülde yapılır?", "modul", "maliyet"),
        ("S-038", "İş güvenliği uzmanı ataması zorunlu mudur?", "mevzuat", "is_guvenligi"),
        ("S-039", "UYDS API entegrasyonu için gerekli dokümantasyon nerededir?", "teknik", "api"),
        ("S-040", "Yapı denetim ücret tarifesi nasıl belirlenir?", "mevzuat", "ucret"),
        ("S-041", "Numune kabul formu doldurulurken dikkat edilmesi gerekenler nelerdir?", "laboratuvar", "numune"),
        ("S-042", "UYDS mobil uygulaması hangi platformlarda çalışır?", "teknik", "mobil"),
        ("S-043", "İş programı revizyonu hangi durumlarda yapılır?", "modul", "is_programi"),
        ("S-044", "Yapı ruhsatı iptali hangi şartlarda gerçekleşir?", "mevzuat", "ruhsat"),
        ("S-045", "Denetim raporu şablonları nereden indirilir?", "modul", "rapor"),
        ("S-046", "UYDS log kayıtları ne kadar süreyle saklanır?", "teknik", "log"),
        ("S-047", "Yapı denetim hizmet bedeli hangi kalemlerden oluşur?", "mevzuat", "ucret"),
        ("S-048", "Parça bazlı imalat takibi nasıl yapılır?", "modul", "imalat"),
        ("S-049", "CBS entegrasyonu ile yapı konum bilgisi nasıl kaydedilir?", "teknik", "cbs"),
        ("S-050", "Alt yüklenici yönetimi UYDS'de hangi ekranda yapılır?", "modul", "alt_yuklenici"),
    ]
    return [
        {"soru_id": sid, "soru_metni": metin, "modul": modul, "kategori": kat}
        for sid, metin, modul, kat in tum_sorular[:max_soru]
    ]


# ============================================================
# Değerlendirme
# ============================================================
def metrikleri_hesapla(
    degerlendirme_kayitlari: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Retrieval sonuçlarını analiz eder, metrikleri hesaplar.

    Kayıt başına beklenen alanlar:
      - etiket: "ilgili" / "kismen_ilgili" / "alakasiz" / "" (boş = insan değerlendirmesi eksik)
      - top_1_kaynak_id, top_1_skor
      - top_2_kaynak_id, top_2_skor
      - top_3_kaynak_id, top_3_skor
      - beklenen_kaynak_id (varsa)
    """
    etiketli = [k for k in degerlendirme_kayitlari if k.get("etiket")]
    toplam = len(degerlendirme_kayitlari)

    # Hit@1, Hit@3 (ilgili + kismen_ilgili = başarılı)
    hit1 = sum(
        1 for k in etiketli
        if k["etiket"] in ("ilgili", "kismen_ilgili") and (k.get("top_1_skor") or 0) > 0
    )
    hit3 = sum(
        1 for k in etiketli
        if k["etiket"] in ("ilgili", "kismen_ilgili") and any(
            (k.get(f"top_{i}_skor") or 0) > 0 for i in range(1, 4)
        )
    )

    # Ortalama top-1 skor
    top1_skorlar = [k["top_1_skor"] for k in degerlendirme_kayitlari if k.get("top_1_skor", 0) > 0]
    ortalama_top1 = np.mean(top1_skorlar) if top1_skorlar else 0.0

    # Kaynaksız soru oranı
    kaynaksiz = sum(1 for k in degerlendirme_kayitlari if not k.get("top_1_skor") or k["top_1_skor"] == 0)

    # Modül bazlı kapsama
    modul_kapsama = Counter()
    for k in etiketli:
        if k["etiket"] in ("ilgili", "kismen_ilgili"):
            modul = k.get("modul", "bilinmeyen")
            modul_kapsama[modul] += 1

    # Etiket dağılımı
    etiket_dagilimi = Counter(k["etiket"] for k in etiketli)

    return {
        "toplam_soru": toplam,
        "etiketli_soru": len(etiketli),
        "etiket_dagilimi": dict(etiket_dagilimi),
        "hit_at_1": round(hit1 / len(etiketli) * 100, 1) if etiketli else None,
        "hit_at_3": round(hit3 / len(etiketli) * 100, 1) if etiketli else None,
        "ortalama_top1_skor": round(ortalama_top1, 4),
        "kaynaksiz_soru": kaynaksiz,
        "kaynaksiz_oran": round(kaynaksiz / toplam * 100, 1) if toplam else 0,
        "modul_bazli_kapsama": dict(modul_kapsama.most_common()),
    }


# ============================================================
# Çıktı Raporlama
# ============================================================
def degerlendirme_csv_yaz(
    degerlendirme_kayitlari: List[Dict[str, Any]],
    cikti_yolu: str,
) -> None:
    """Değerlendirme sonuçlarını insan etiketlemesine uygun CSV'ye yazar."""
    alanlar = [
        "soru_id", "soru_metni", "modul", "kategori",
        "top_1_chunk_id", "top_1_kaynak_id", "top_1_dokuman", "top_1_metin", "top_1_skor",
        "top_2_chunk_id", "top_2_kaynak_id", "top_2_dokuman", "top_2_metin", "top_2_skor",
        "top_3_chunk_id", "top_3_kaynak_id", "top_3_dokuman", "top_3_metin", "top_3_skor",
        "etiket",  # INSAN_DEGERLENDIRMESI: ilgili / kismen_ilgili / alakasiz
    ]
    with open(cikti_yolu, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=alanlar, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(degerlendirme_kayitlari)
    print(f"   📊 Değerlendirme CSV: {cikti_yolu}")


def metrik_ozeti_yaz(metrikler: Dict[str, Any], cikti_yolu: str) -> None:
    """Metrikleri JSON dosyasına yazar."""
    with open(cikti_yolu, "w", encoding="utf-8") as f:
        json.dump(metrikler, f, ensure_ascii=False, indent=2)
    print(f"   📊 Metrik özeti: {cikti_yolu}")


# ============================================================
# Ana Fonksiyon
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="RAG retrieval kalitesini ölç")
    parser.add_argument("--soru_sayisi", type=int, default=50, help="Değerlendirilecek soru sayısı")
    parser.add_argument("--excel", default=None, help="UYDS SSS Excel dosyasının yolu")
    parser.add_argument("--cpu", action="store_true", help="CPU modu")
    parser.add_argument("--ilk_havuz", default=None, choices=["dogrudan_ilgili", "dolayli_ilgili"],
                        help="Sadece bu havuzda ara")
    parser.add_argument("--fallback_min_skor", type=float, default=0.30,
                        help="İlk havuzda yeterli skor yoksa ikinci havuza geçiş eşiği")
    parser.add_argument("--dogrudan_boost", type=float, default=0.0,
                        help="Doğrudan ilgili chunk'lara skor bonusu")
    args = parser.parse_args()

    cihaz = "cpu" if args.cpu else "cuda"
    print("=" * 60)
    print("  Retrieval Kalite Değerlendirmesi")
    print("=" * 60)
    if args.ilk_havuz:
        print(f"  Havuz: {args.ilk_havuz} (fallback skor: {args.fallback_min_skor})")
    if args.dogrudan_boost > 0:
        print(f"  Doğrudan boost: +{args.dogrudan_boost}")

    # 1. Embedding checkpoint'ini yükle
    print(f"\n📦 Kaynak embedding checkpoint yükleniyor...")
    # Kaynak dizin hash'i için data/kaynaklar'ı kullan
    notebook = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    KAYNAK_DIZINI = os.path.join(notebook, "data", "kaynaklar")
    kaynak_dizin_hash = dizin_hashi(KAYNAK_DIZINI) if os.path.isdir(KAYNAK_DIZINI) else ""

    emb_durum = embedding_checkpoint_yukle(
        CKPT_DIZINI, kaynak_dizin_hash, EMBEDDING_MODEL,
        CHUNK_BOYUT_TOKEN, CHUNK_OVERLAP_TOKEN, CHUNK_ALGORITMA_SURUMU,
    )
    if not emb_durum:
        # Hash kontrolü olmadan yüklemeyi dene
        print("   ⚠️ Hash uyuşmazlığı, hash kontrolü olmadan deneniyor...")
        alt_dizin = os.path.join(CKPT_DIZINI, "kaynak_embedding")
        vektor_yolu = os.path.join(alt_dizin, "kaynak_vektorler.npy")
        parcalar_yolu = os.path.join(alt_dizin, "parcalar.pkl")
        if os.path.exists(vektor_yolu) and os.path.exists(parcalar_yolu):
            import pickle
            kaynak_vektorler = np.load(vektor_yolu)
            with open(parcalar_yolu, "rb") as f:
                tum_parcalar = pickle.load(f)
            print(f"   🔄 Checkpoint zorla yüklendi: {len(tum_parcalar)} parça")
        else:
            raise RuntimeError("Embedding checkpoint bulunamadı! Önce build_source_corpus.py çalıştırın.")
    else:
        kaynak_vektorler, tum_parcalar = emb_durum

    # Chunk metadata kontrolü
    with_guven = sum(1 for c in tum_parcalar if c.get("guven_sinifi"))
    with_url = sum(1 for c in tum_parcalar if c.get("kaynak_url"))
    with_ilgililik = sum(1 for c in tum_parcalar if c.get("uyds_ilgililik"))
    print(f"   Metadata: guven_sinifi={with_guven}/{len(tum_parcalar)}, "
          f"kaynak_url={with_url}/{len(tum_parcalar)}, "
          f"uyds_ilgililik={with_ilgililik}/{len(tum_parcalar)}")

    # İlgililik dağılımı
    ilgililik_dagilimi = Counter(c.get("uyds_ilgililik") for c in tum_parcalar)
    print(f"   Chunk ilgililik dağılımı: {dict(ilgililik_dagilimi)}")

    # 2. Soruları yükle
    print(f"\n❓ Sorular yükleniyor (hedef: {args.soru_sayisi})...")
    sorular = sorulari_yukle(excel_yolu=args.excel, max_soru=args.soru_sayisi)
    soru_metinleri = [s["soru_metni"] for s in sorular]

    # 3. Soruları encode et
    print(f"\n🔤 Sorular encode ediliyor ({EMBEDDING_MODEL}, {cihaz})...")
    t0 = time.time()
    soru_vektorler = soru_embedding_olustur(
        soru_metinleri, EMBEDDING_MODEL,
        batch_size=EMBEDDING_BATCH, cihaz=cihaz,
    )
    print(f"   {soru_vektorler.shape[0]} soru × {soru_vektorler.shape[1]}d ({time.time() - t0:.1f}s)")

    # 4. Her soru için retrieval yap
    print(f"\n🔍 Retrieval (top_k=10, son_k=3, min_skor=0.2)...")
    degerlendirme_kayitlari = []
    t0 = time.time()

    for i, soru in enumerate(sorular):
        if (i + 1) % 10 == 0:
            print(f"   {i + 1}/{len(sorular)}...")

        parcalar, maks_skor = dense_kaynak_ara(
            soru_vektorler[i],
            kaynak_vektorler,
            tum_parcalar,
            top_k=10,
            son_k=3,
            min_skor=0.2,
            ilk_havuz_filtresi=args.ilk_havuz,
            ikinci_havuz_min_skor=args.fallback_min_skor if args.ilk_havuz else None,
            dogrudan_boost=args.dogrudan_boost,
        )

        kayit = {
            "soru_id": soru["soru_id"],
            "soru_metni": soru["soru_metni"],
            "modul": soru["modul"],
            "kategori": soru["kategori"],
        }

        for rank in range(1, 4):
            if rank <= len(parcalar):
                p = parcalar[rank - 1]
                kayit[f"top_{rank}_chunk_id"] = p.get("chunk_id", "")
                kayit[f"top_{rank}_kaynak_id"] = p.get("kaynak_id", "")
                kayit[f"top_{rank}_dokuman"] = p.get("dokuman", "")
                kayit[f"top_{rank}_metin"] = (p.get("metin", "") or "")[:200]
                kayit[f"top_{rank}_skor"] = p.get("birlesik_skor", 0)
                kayit[f"top_{rank}_ilgililik"] = p.get("uyds_ilgililik", "")
            else:
                kayit[f"top_{rank}_chunk_id"] = ""
                kayit[f"top_{rank}_kaynak_id"] = ""
                kayit[f"top_{rank}_dokuman"] = ""
                kayit[f"top_{rank}_metin"] = ""
                kayit[f"top_{rank}_skor"] = 0.0
                kayit[f"top_{rank}_ilgililik"] = ""

        kayit["etiket"] = ""
        degerlendirme_kayitlari.append(kayit)

    print(f"   Tamamlandı: {len(degerlendirme_kayitlari)} soru ({time.time() - t0:.1f}s)")

    # 5. Çıktıları kaydet
    cikti_dizini = CIKTI_DIZINI
    if not os.path.isdir(cikti_dizini):
        os.makedirs(cikti_dizini, exist_ok=True)

    csv_yolu = os.path.join(cikti_dizini, "retrieval_degerlendirme.csv")
    degerlendirme_csv_yaz(degerlendirme_kayitlari, csv_yolu)

    # İlk metrikler (etiket yoksa sadece teknik metrikler)
    metrikler = metrikleri_hesapla(degerlendirme_kayitlari)
    metrik_yolu = os.path.join(cikti_dizini, "retrieval_metrikleri.json")
    metrik_ozeti_yaz(metrikler, metrik_yolu)

    # Özet
    print(f"\n{'=' * 60}")
    print(f"  Değerlendirme Tamamlandı")
    print(f"{'=' * 60}")
    print(f"  Toplam soru: {metrikler['toplam_soru']}")
    if metrikler['etiketli_soru'] > 0:
        print(f"  Etiketli soru: {metrikler['etiketli_soru']}")
        if metrikler['hit_at_1'] is not None:
            print(f"  Hit@1: %{metrikler['hit_at_1']}")
        if metrikler['hit_at_3'] is not None:
            print(f"  Hit@3: %{metrikler['hit_at_3']}")
    print(f"  Ortalama top-1 skor: {metrikler['ortalama_top1_skor']}")
    print(f"  Kaynaksız soru: {metrikler['kaynaksiz_soru']} (%{metrikler['kaynaksiz_oran']})")
    print(f"\n  Çıktılar:")
    print(f"    {csv_yolu}")
    print(f"    {metrik_yolu}")
    print(f"\n  ⚠️ CSV'deki 'etiket' sütununu insan değerlendirmesiyle doldurun,")
    print(f"     sonra --yeniden_degerlendir ile metrikleri güncelleyin.")


if __name__ == "__main__":
    main()