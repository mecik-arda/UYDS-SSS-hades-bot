#!/usr/bin/env python3
# ============================================================
# classify_relevance.py — Belgeleri UYDS ilgililiğine göre sınıflandırır
# ============================================================
"""
Envanterdeki 113 belgeyi UYDS ile ilgililiğine göre sınıflandırır:
- dogrudan_ilgili: Yapı denetimi, 4708, laboratuvar, UYDS modülleri
- dolayli_ilgili: İmar, afet, ihale mevzuatı (arka plan)
- alakasiz: Sokak sağlıklaştırma, yöresel mimari, enerji verimliliği
- manuel_inceleme: Numaralı genelgeler, belirsiz başlıklar
"""
import os
import csv
import re

PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_KOKU = os.path.join(PROJE_KOKU, "google_collab_egitim", "data", "output_v4")
ENVANTER_YOLU = os.path.join(OUTPUT_KOKU, "kaynak_envanteri.csv")
ENVANTER_YENI_YOLU = os.path.join(OUTPUT_KOKU, "kaynak_envanteri_siniflandirilmis.csv")

# UYDS ile doğrudan ilgili anahtar kelimeler
DOGUDAN_ILGILI_KELIMELER = [
    "yapi denetim", "yapı denetim", "4708", "yapi denetim kurulus", "yapı denetim kuruluş",
    "laboratuvar", "laboratuvarlari", "laboratuvarlar", "beton", "numune", "karot",
    "yapi denetimi hakkinda kanun", "yapı denetimi hakkında kanun",
    "yapi denetimi uygulama yonetmelik", "yapı denetimi uygulama yönetmelik",
    "izin belgesi", "hizmet sozlesmesi", "hizmet sözleşmesi",
    "yapi malzemeleri", "yapı malzemeleri", "zemin laboratuvar",
    "denetim hizmetleri yonetmelik", "denetim hizmetleri yönetmelik",
    "ebis", "yapi isleri", "yapı işleri",
    "yapi kayit", "yapı kayıt", "ruhsat",
    "yapi sagligi", "yapı sağlığı",
    "seviye tespit", "hakedis", "hakediş",
    "yapi denetim kurulu", "yapı denetim kurulu",
    "fiiat farki", "fiyat farkı", "sure uzatimi", "süre uzatımı",
    "ilave is", "ilave iş", "benzer is grup", "benzer iş grup",
    "cadd", "cad", "bilgisayar destekli tasarim",
]

# Dolaylı ilgili (arka plan mevzuatı)
DOLAYLI_KELIMELER = [
    "afet", "iskan", "iskân", "6306", "7269", "4123", "5902",
    "deprem", "yapi deprem", "bina deprem",
    "onarim", "onarım", "guclendirme", "güçlendirme",
    "hasar tespit", "afet mudahale", "afet koordinasyon",
    "kamu ihale", "4734", "4735", "5018", "ihale",
    "imar", "3194", "kamulastirma", "kamulaştırma",
    "yapi isleri genel mudurlugu", "yapı işleri genel müdürlüğü",
    "bakanligi", "bakanlığı",
    "genelge", "teblig", "tebliğ", "yonerge", "yönerge",
    "yapi", "yapı", "inşaat", "insaat",
    "denetim", "ruhsat", "iskan",
]

# Kesinlikle alakasız
ALAKASIZ_KELIMELER = [
    "sokak sagliklastirma", "sokak sağlıklaştırma",
    "yoresel mimari", "yöresel mimari", "mugla",
    "enerji verimlilik", "enerji verimliliği",
    "tasarruf hedefi", "kamu binalarindatasarruf",
    "tarihten referans", "kamu binalari tasarim rehberi",
    "afet lojistik", "lojistik bolge",
    "engelli", "ozurlu", "özürlü",
    "bodrum katta su yalitim", "su yalıtım",
    "vaziyet plani", "vaziyet planı",
    "meteorolojik veri",
    "afet konut kitapcig", "afet konut kitapçığ",
    "yatirim takip", "yatırım takip",
    "iskan tanitim", "iskân tanıtım",
    "iskan mevzuati", "iskân mevzuatı",
    "borclandirma", "borçlandırma",
    "devlet eliyle iskan", "devlet eliyle iskân",
    "fiziksel yerlesim", "fiziksel yerleşim",
    "konut edindirme",
    "sokak",
]


def siniflandir(baslik, dosya_adi, modul, alt_konu):
    """Belgeyi UYDS ilgililiğine göre sınıflandırır."""
    metin = f"{baslik} {dosya_adi} {modul} {alt_konu}".lower()
    
    # Önce alakasız kontrol et
    for kelime in ALAKASIZ_KELIMELER:
        if kelime.lower() in metin:
            return "alakasiz", f"Alakasız: '{kelime}' eşleşti"
    
    # Doğrudan ilgili kontrol et
    for kelime in DOGUDAN_ILGILI_KELIMELER:
        if kelime.lower() in metin:
            return "dogrudan_ilgili", f"Doğrudan: '{kelime}' eşleşti"
    
    # Dolaylı ilgili kontrol et
    for kelime in DOLAYLI_KELIMELER:
        if kelime.lower() in metin:
            return "dolayli_ilgili", f"Dolaylı: '{kelime}' eşleşti"
    
    # Numaralı genelgeler ve belirsiz başlıklar
    if re.match(r'^\d+\)', baslik) or baslik.strip() == "":
        return "manuel_inceleme", "Numaralı/belirsiz başlık"
    
    return "manuel_inceleme", "Sınıflandırılamadı"


def main():
    print("=" * 60)
    print("  UYDS İlgililik Sınıflandırması")
    print("=" * 60)
    
    with open(ENVANTER_YOLU, "r", encoding="utf-8-sig") as f:
        envanter = list(csv.DictReader(f))
    
    print(f"  Toplam belge: {len(envanter)}")
    
    from collections import Counter
    dagilim = Counter()
    
    for kayit in envanter:
        baslik = kayit.get("baslik", "")
        dosya_adi = kayit.get("dosya_adi", "")
        modul = kayit.get("modul", "")
        alt_konu = kayit.get("alt_konu", "")
        
        sinif, gerekce = siniflandir(baslik, dosya_adi, modul, alt_konu)
        kayit["uyds_ilgililik"] = sinif
        kayit["ilgililik_gerekce"] = gerekce
        dagilim[sinif] += 1
    
    print(f"\n  Sınıflandırma dağılımı:")
    for sinif, sayi in dagilim.most_common():
        yuzde = sayi / len(envanter) * 100
        print(f"    {sinif}: {sayi} ({yuzde:.0f}%)")
    
    # Alakasız belgeleri listele
    alakasiz = [k for k in envanter if k["uyds_ilgililik"] == "alakasiz"]
    if alakasiz:
        print(f"\n  ⚠️ Alakasız belgeler ({len(alakasiz)}):")
        for k in alakasiz:
            print(f"    - {k['dosya_adi']}: {k['ilgililik_gerekce']}")
    
    # Doğrudan ilgili belgeleri listele
    dogrudan = [k for k in envanter if k["uyds_ilgililik"] == "dogrudan_ilgili"]
    if dogrudan:
        print(f"\n  ✅ Doğrudan ilgili belgeler ({len(dogrudan)}):")
        for k in dogrudan:
            print(f"    - {k['dosya_adi']}")
    
    # Ana RAG havuzuna alınacak belgeler
    ana_rag = [k for k in envanter if k["uyds_ilgililik"] in ["dogrudan_ilgili", "dolayli_ilgili"]]
    print(f"\n  📊 Ana RAG havuzuna alınabilecek: {len(ana_rag)} belge")
    print(f"  🗑️ Ayıklanacak (alakasız): {len(alakasiz)} belge")
    
    # Yeni envanteri kaydet
    alanlar = list(envanter[0].keys()) if envanter else []
    with open(ENVANTER_YENI_YOLU, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=alanlar)
        writer.writeheader()
        writer.writerows(envanter)
    
    print(f"\n  ✅ Sınıflandırılmış envanter: {ENVANTER_YENI_YOLU}")
    
    # Özet JSON
    import json
    ozet_yolu = os.path.join(OUTPUT_KOKU, "ilgililik_ozet.json")
    ozet = {
        "toplam_belge": len(envanter),
        "dagilim": dict(dagilim),
        "ana_rag_havuzu": len(ana_rag),
        "alakasiz": len(alakasiz),
        "dogrudan_ilgili_dosyalar": [k["dosya_adi"] for k in dogrudan],
        "alakasiz_dosyalar": [k["dosya_adi"] for k in alakasiz],
    }
    with open(ozet_yolu, "w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Özet: {ozet_yolu}")


if __name__ == "__main__":
    main()