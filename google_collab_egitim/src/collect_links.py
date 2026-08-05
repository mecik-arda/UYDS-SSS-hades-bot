#!/usr/bin/env python3
"""
yapiisleri.csb.gov.tr sitesindeki önemli sayfaları tarar ve
PDF/DOCX/DOC linklerini toplar. Çıktı: link_listesi.json
"""
import os
import sys
import json
import time
import urllib3
import requests
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
})
session.verify = False

# Taranacak önemli sayfalar
SAYFALAR = [
    ("https://yapiisleri.csb.gov.tr/mevzuat-i-506", "mevzuat"),
    ("https://yapiisleri.csb.gov.tr/kanunlar-i-507", "kanunlar"),
    ("https://yapiisleri.csb.gov.tr/khk-i-509", "khk"),
    ("https://yapiisleri.csb.gov.tr/genelgeler-i-6255", "genelgeler"),
    ("https://yapiisleri.csb.gov.tr/teblig-i-90234", "teblig"),
    ("https://yapiisleri.csb.gov.tr/egitim-dokumanlari-i-6088", "egitim_dokumanlari"),
    ("https://yapiisleri.csb.gov.tr/sunumlar-i-6289", "sunumlar"),
    ("https://yapiisleri.csb.gov.tr/calistaylar-i-6082", "calistaylar"),
    ("https://yapiisleri.csb.gov.tr/kapsam-i-6090", "kapsam"),
    ("https://yapiisleri.csb.gov.tr/gorev-tanimi-i-3", "gorev_tanimi"),
    ("https://yapiisleri.csb.gov.tr/hizmet-standartlari-i-360", "hizmet_standartlari"),
    ("https://yapiisleri.csb.gov.tr/iskan-daire-baskanligi-mevzuati-i-91329", "iskan_mevzuati"),
    ("https://yapiisleri.csb.gov.tr/iskan-sunumlari-i-91330", "iskan_sunumlari"),
    ("https://yapiisleri.csb.gov.tr/proje-daire-baskanligi-mevzuati-i-102050", "proje_mevzuati"),
    ("https://yapiisleri.csb.gov.tr/ihale-dairesi-baskanligi-mevzuati-i-102053", "ihale_mevzuati"),
    ("https://yapiisleri.csb.gov.tr/dis-kaynakli-yatirimlar-daire-baskanligi-mevzuati-i-102052", "dis_kaynakli_mevzuati"),
    ("https://yapiisleri.csb.gov.tr/afet-koordinasyon-dairesi-ve-afet-hasarlari-tespiti-dairesi-mevzuati-i-102056", "afet_mevzuati"),
]

DOSYA_UZANTILARI = [".pdf", ".docx", ".doc", ".xlsx", ".xls"]


def sayfa_tara(url, kategori_etiketi):
    """Bir sayfadaki tüm dosya linklerini çıkarır."""
    try:
        r = session.get(url, timeout=30)
        if r.status_code != 200:
            print(f"  ✗ {url}: HTTP {r.status_code}")
            return [], []

        
        soup = BeautifulSoup(r.text, "html.parser")
        
        dosya_linkleri = []
        sayfa_linkleri = []
        
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True) or ""
            
            # Mutlak URL'ye çevir
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://yapiisleri.csb.gov.tr" + href
            
            # Dosya linkleri
            href_lower = href.lower()
            if any(href_lower.endswith(ext) for ext in DOSYA_UZANTILARI):
                dosya_linkleri.append({"url": href, "baslik": text, "kategori": kategori_etiketi})
            
            # Sayfa linkleri (alt sayfalar)
            elif "yapiisleri.csb.gov.tr" in href and "-i-" in href and href != url:
                sayfa_linkleri.append({"url": href, "baslik": text, "kategori": kategori_etiketi})
        
        return dosya_linkleri, sayfa_linkleri
        
    except Exception as e:
        print(f"  ✗ {url}: {type(e).__name__}: {e}")
        return [], []


def main():
    print("=" * 60)
    print("  Link Toplama Sistemi — yapiisleri.csb.gov.tr")
    print("=" * 60)
    
    tum_dosya_linkleri = []
    tum_sayfa_linkleri = []
    gorulen_url = set()
    
    for i, (url, etiket) in enumerate(SAYFALAR, start=1):
        print(f"\n[{i}/{len(SAYFALAR)}] {etiket}: {url}")
        
        dosyalar, sayfalar = sayfa_tara(url, etiket)
        
        for d in dosyalar:
            if d["url"] not in gorulen_url:
                gorulen_url.add(d["url"])
                tum_dosya_linkleri.append(d)
                print(f"  📄 {d['baslik'][:50]}: {d['url']}")
        
        for s in sayfalar:
            if s["url"] not in gorulen_url:
                gorulen_url.add(s["url"])
                tum_sayfa_linkleri.append(s)
        
        print(f"  → {len(dosyalar)} dosya, {len(sayfalar)} alt sayfa bulundu")
        time.sleep(0.5)
    
    # Alt sayfaları da tara (bir seviye derinlik)
    print(f"\n\n📋 Alt sayfalar taranıyor ({len(tum_sayfa_linkleri)} sayfa)...")
    for i, s in enumerate(tum_sayfa_linkleri[:30], start=1):  # İlk 30 alt sayfa
        print(f"[{i}/30] {s['baslik'][:50]}: {s['url']}")
        
        dosyalar, _ = sayfa_tara(s["url"], s["kategori"])
        
        for d in dosyalar:
            if d["url"] not in gorulen_url:
                gorulen_url.add(d["url"])
                tum_dosya_linkleri.append(d)
                print(f"  📄 {d['baslik'][:50]}: {d['url']}")
        
        time.sleep(0.5)
    
    # Sonuçları kaydet
    output = {
        "dosya_linkleri": tum_dosya_linkleri,
        "toplam_dosya": len(tum_dosya_linkleri),
        "tarih": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    output_yolu = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "output_v4", "link_listesi.json"
    )
    os.makedirs(os.path.dirname(output_yolu), exist_ok=True)
    
    with open(output_yolu, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"  TOPLAM {len(tum_dosya_linkleri)} DOSYA LİNKİ BULUNDU")
    print(f"  Kayıt: {output_yolu}")
    print(f"{'='*60}")
    
    # Kategori bazında özet
    kategori_sayac = {}
    for d in tum_dosya_linkleri:
        k = d["kategori"]
        kategori_sayac[k] = kategori_sayac.get(k, 0) + 1
    print("\nKategori dağılımı:")
    for k, v in sorted(kategori_sayac.items()):
        print(f"  {k}: {v}")
    
    return tum_dosya_linkleri


if __name__ == "__main__":
    main()