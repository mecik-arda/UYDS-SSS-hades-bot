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

# ============================================================
# Puan Tabanlı Sınıflandırma (v2.0)
# ============================================================
# Her anahtar kelimenin bir ağırlığı var.
# Doğrudan ilgili kelimeler yüksek puan, genel/zayıf kelimeler düşük puan alır.
# Sınıflandırma:
#   toplam_puan >= 4.0  → dogrudan_ilgili
#   toplam_puan >= 2.0  → dolayli_ilgili
#   toplam_puan <  2.0  → manuel_inceleme

GUCLU_KELIMELER = {
    # Doğrudan UYDS terimleri — her eşleşme yüksek puan
    "uyds": 5.0,
    "ulusal yapı denetim sistemi": 5.0,
    "4708": 4.0,
    "yapı denetim kuruluş": 4.0,
    "yapı denetim kurulus": 4.0,
    "yapı denetimi uygulama yönetmeliği": 4.0,
    "yapı denetimi uygulama yonetmelik": 4.0,
    "denetim hizmetleri yönetmeliği": 3.0,
    "denetim hizmetleri yonetmelik": 3.0,
    "hakediş": 3.0,
    "hakedis": 3.0,
    "yapı denetim": 3.0,
    "yapi denetim": 3.0,
    "yapi denetimi hakkinda kanun": 3.0,
    "yapı denetimi hakkında kanun": 3.0,
    "laboratuvar": 2.0,
    "laboratuvarları": 2.0,
    "beton": 2.0,
    "numune": 2.0,
    "karot": 2.0,
    "izin belgesi": 2.0,
    "hizmet sözleşmesi": 2.0,
    "hizmet sozlesmesi": 2.0,
    "yapı malzemeleri": 2.0,
    "yapi malzemeleri": 2.0,
    "zemin laboratuvar": 2.0,
    "ebis": 2.0,
    "yapı kayıt": 2.0,
    "yapi kayit": 2.0,
    "yapı sağlığı": 2.0,
    "yapi sagligi": 2.0,
    "seviye tespit": 2.0,
    "fiyat farkı": 2.0,
    "fiiat farki": 2.0,
    "süre uzatımı": 2.0,
    "sure uzatimi": 2.0,
    "ilave iş": 2.0,
    "ilave is": 2.0,
    "benzer iş grup": 2.0,
    "benzer is grup": 2.0,
    "cadd": 2.0,
    "cad": 2.0,
    "bilgisayar destekli tasarim": 2.0,
}

ORTA_KELIMELER = {
    # İmar/afet/ihale mevzuatı — orta puan
    "afet": 1.0,
    "6306": 1.5,
    "7269": 1.5,
    "4123": 1.5,
    "5902": 1.5,
    "deprem": 1.0,
    "bina deprem": 1.0,
    "onarım": 1.0,
    "onarim": 1.0,
    "güçlendirme": 1.0,
    "guclendirme": 1.0,
    "hasar tespit": 1.0,
    "4734": 1.5,
    "4735": 1.5,
    "5018": 1.5,
    "kamu ihale": 1.0,
    "imar": 1.0,
    "3194": 1.5,
    "kamulaştırma": 1.0,
    "kamulastirma": 1.0,
    "yapı işleri genel müdürlüğü": 1.0,
    "yapi isleri genel mudurlugu": 1.0,
}

ZAYIF_KELIMELER = {
    # Genel kelimeler — çok düşük puan, tek başına sınıflandırmaya yetmez
    "yapı": 0.5,
    "yapi": 0.5,
    "inşaat": 0.5,
    "insaat": 0.5,
    "denetim": 0.5,
    "ruhsat": 0.5,
    "i̇skan": 0.5,
    "iskan": 0.5,
    "iskân": 0.5,
    "genelge": 0.5,
    "tebliğ": 0.5,
    "teblig": 0.5,
    "yönerge": 0.5,
    "yonerge": 0.5,
    "bakanlığı": 0.0,
    "bakanligi": 0.0,
}

ALAKASIZ_KELIMELER = {
    # Kesinlikle alakasız — negatif puan, eşleşirse doğrudan alakasız
    "sokak sağlıklaştırma": -10.0,
    "sokak sagliklastirma": -10.0,
    "yöresel mimari": -10.0,
    "yoresel mimari": -10.0,
    "mugla": -5.0,
    "enerji verimlilik": -10.0,
    "enerji verimliliği": -10.0,
    "tasarruf hedefi": -10.0,
    "kamu binalarindatasarruf": -10.0,
    "tarihten referans": -10.0,
    "kamu binalari tasarim rehberi": -10.0,
    "afet lojistik": -10.0,
    "lojistik bolge": -10.0,
    "engelli": -10.0,
    "özürlü": -10.0,
    "ozurlu": -10.0,
    "su yalıtım": -10.0,
    "su yalitim": -10.0,
    "vaziyet planı": -10.0,
    "vaziyet plani": -10.0,
    "meteorolojik veri": -10.0,
    "afet konut kitapçığ": -10.0,
    "afet konut kitapcig": -10.0,
    "yatırım takip": -10.0,
    "yatirim takip": -10.0,
    "iskân tanıtım": -10.0,
    "iskan tanitim": -10.0,
    "iskân mevzuatı": -10.0,
    "iskan mevzuati": -10.0,
    "borçlandırma": -10.0,
    "borclandirma": -10.0,
    "devlet eliyle iskan": -10.0,
    "devlet eliyle iskân": -10.0,
    "fiziksel yerleşim": -10.0,
    "fiziksel yerlesim": -10.0,
    "konut edindirme": -10.0,
    "sokak": -5.0,
}


def siniflandir(baslik, dosya_adi, modul, alt_konu):
    """Belgeyi puan tabanlı UYDS ilgililiğine göre sınıflandırır (v2.0)."""
    metin = f"{baslik} {dosya_adi} {modul} {alt_konu}".lower()

    # Negatif puanlı alakasız kelimeleri kontrol et
    for kelime, puan in ALAKASIZ_KELIMELER.items():
        if kelime.lower() in metin:
            return "alakasiz", f"Alakasız: '{kelime}' negatif eşleşti ({puan})"

    # Puan topla
    toplam_puan = 0.0
    eslesenler = []

    for kelime, puan in GUCLU_KELIMELER.items():
        if kelime.lower() in metin:
            toplam_puan += puan
            eslesenler.append(f"{kelime}(+{puan})")

    for kelime, puan in ORTA_KELIMELER.items():
        if kelime.lower() in metin:
            toplam_puan += puan
            eslesenler.append(f"{kelime}(+{puan})")

    for kelime, puan in ZAYIF_KELIMELER.items():
        if kelime.lower() in metin:
            toplam_puan += puan
            eslesenler.append(f"{kelime}(+{puan})")

    # En az 2 anlamlı eşleşme şartı (zayıf kelimeler sayılmaz)
    anlamli_eslesme = [e for e in eslesenler if not e.startswith(("yapı(", "yapi(", "denetim(", "iskan(", "ruhsat(",
        "inşaat(", "insaat(", "genelge(", "tebliğ(", "teblig(", "yönerge(", "yonerge(",
        "bakanlığı(", "bakanligi("))]

    # Sınıflandır
    if toplam_puan >= 4.0:
        return "dogrudan_ilgili", f"Puan: {toplam_puan:.1f} → {' '.join(eslesenler)}"
    elif toplam_puan >= 2.0:
        return "dolayli_ilgili", f"Puan: {toplam_puan:.1f} → {' '.join(eslesenler)}"
    elif len(anlamli_eslesme) >= 1 and toplam_puan >= 1.0:
        # En az 1 anlamlı eşleşme varsa zayıf dolaylı
        return "dolayli_ilgili", f"Puan: {toplam_puan:.1f} (zayıf) → {' '.join(eslesenler)}"

    # Numaralı genelgeler ve belirsiz başlıklar
    if re.match(r'^\d+\)', baslik) or baslik.strip() == "":
        return "manuel_inceleme", f"Numaralı/belirsiz başlık (puan: {toplam_puan:.1f})"

    return "manuel_inceleme", f"Sınıflandırılamadı (puan: {toplam_puan:.1f})"


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
        "siniflandirma_surumu": "2.0",
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