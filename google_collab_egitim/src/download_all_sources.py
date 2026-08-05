#!/usr/bin/env python3
# ============================================================
# download_all_sources.py — Toplanan linklerden tüm belgeleri indirir
# ============================================================
"""
collect_links.py tarafından toplanan link_listesi.json dosyasını okur,
tüm PDF/DOCX/DOC belgelerini indirir, sınıflandırır ve envanter oluşturur.

Çıktılar:
  - data/kaynaklar/ altında sınıflandırılmış belgeler
  - data/output_v4/kaynak_envanteri.csv (güncellenmiş)
  - data/output_v4/kaynak_url_manifestosu.jsonl (güncellenmiş)
"""

import os
import sys
import json
import hashlib
import time
import csv
import urllib3
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, unquote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KAYNAK_KOKU = os.path.join(PROJE_KOKU, "google_collab_egitim", "data", "kaynaklar")
OUTPUT_KOKU = os.path.join(PROJE_KOKU, "google_collab_egitim", "data", "output_v4")
TZ_ISTANBUL = timezone(timedelta(hours=3))

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
})
session.verify = False

# Kategori -> Klasör eşlemesi
KATEGORI_KLASOR_ESLEME = {
    "mevzuat": "01_mevzuat",
    "kanunlar": "01_mevzuat",
    "khk": "01_mevzuat",
    "yonetmelik": "01_mevzuat",
    "genelgeler": "01_mevzuat",
    "teblig": "01_mevzuat",
    "iskan_mevzuati": "01_mevzuat",
    "proje_mevzuati": "01_mevzuat",
    "ihale_mevzuati": "01_mevzuat",
    "dis_kaynakli_mevzuati": "01_mevzuat",
    "afet_mevzuati": "01_mevzuat",
    "egitim_dokumanlari": "02_resmi_uyds_kilavuzlari",
    "sunumlar": "02_resmi_uyds_kilavuzlari",
    "iskan_sunumlari": "02_resmi_uyds_kilavuzlari",
    "hizmet_standartlari": "02_resmi_uyds_kilavuzlari",
    "kapsam": "02_resmi_uyds_kilavuzlari",
    "gorev_tanimi": "02_resmi_uyds_kilavuzlari",
    "calistaylar": "03_modul_dokumanlari",
}

# Kategori -> Güven sınıfı
KATEGORI_GUVEN_ESLEME = {
    "mevzuat": "A",
    "kanunlar": "A",
    "khk": "A",
    "yonetmelik": "A",
    "genelgeler": "A",
    "teblig": "A",
    "iskan_mevzuati": "A",
    "proje_mevzuati": "A",
    "ihale_mevzuati": "A",
    "dis_kaynakli_mevzuati": "A",
    "afet_mevzuati": "A",
    "egitim_dokumanlari": "B",
    "sunumlar": "B",
    "iskan_sunumlari": "B",
    "hizmet_standartlari": "B",
    "kapsam": "B",
    "gorev_tanimi": "B",
    "calistaylar": "C",
}

# Kategori -> Kurum
KATEGORI_KURUM_ESLEME = {
    "mevzuat": "Yapı İşleri Genel Müdürlüğü",
    "kanunlar": "Yapı İşleri Genel Müdürlüğü",
    "khk": "Yapı İşleri Genel Müdürlüğü",
    "yonetmelik": "Yapı İşleri Genel Müdürlüğü",
    "genelgeler": "Yapı İşleri Genel Müdürlüğü",
    "teblig": "Yapı İşleri Genel Müdürlüğü",
    "iskan_mevzuati": "Yapı İşleri Genel Müdürlüğü",
    "proje_mevzuati": "Yapı İşleri Genel Müdürlüğü",
    "ihale_mevzuati": "Yapı İşleri Genel Müdürlüğü",
    "dis_kaynakli_mevzuati": "Yapı İşleri Genel Müdürlüğü",
    "afet_mevzuati": "Yapı İşleri Genel Müdürlüğü",
    "egitim_dokumanlari": "Yapı İşleri Genel Müdürlüğü",
    "sunumlar": "Yapı İşleri Genel Müdürlüğü",
    "iskan_sunumlari": "Yapı İşleri Genel Müdürlüğü",
    "hizmet_standartlari": "Yapı İşleri Genel Müdürlüğü",
    "kapsam": "Yapı İşleri Genel Müdürlüğü",
    "gorev_tanimi": "Yapı İşleri Genel Müdürlüğü",
    "calistaylar": "Yapı İşleri Genel Müdürlüğü",
}


def sha256_hesapla(dosya_yolu):
    h = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def guvenli_dosya_adi(baslik, url):
    """Başlıktan veya URL'den güvenli dosya adı üretir."""
    turkce_haritasi = {
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U",
    }

    # Önce başlığı dene
    if baslik and len(baslik) > 3:
        ad = baslik
        for tr, en in turkce_haritasi.items():
            ad = ad.replace(tr, en)
        ad = ad.replace(" ", "_").replace("-", "_").replace("/", "_").replace("\\", "_")
        ad = ad.replace("(", "").replace(")", "").replace(":", "").replace(",", "")
        ad = ad.replace('"', "").replace("'", "").replace("?", "").replace("!", "")
        ad = "".join(c for c in ad if c.isalnum() or c == "_")
        ad = ad.strip("_")
        if len(ad) > 5:
            return ad.lower()[:80]

    # URL'den dosya adını çıkar
    parsed = urlparse(url)
    path = unquote(parsed.path)
    ad = os.path.basename(path)
    for tr, en in turkce_haritasi.items():
        ad = ad.replace(tr, en)
    ad = ad.replace(" ", "_")
    ad = "".join(c for c in ad if c.isalnum() or c in "._-")
    return ad.lower()[:80] if ad else f"belge_{hashlib.md5(url.encode()).hexdigest()[:8]}"


def belge_indir(url, baslik, kategori):
    """Tek bir belgeyi indirir."""
    # Hedef klasör
    hedef_klasor_adi = KATEGORI_KLASOR_ESLEME.get(kategori, "99_inceleme_bekleyenler")
    hedef_klasor = os.path.join(KAYNAK_KOKU, hedef_klasor_adi)
    os.makedirs(hedef_klasor, exist_ok=True)

    # Dosya adı
    dosya_adi = guvenli_dosya_adi(baslik, url)

    # URL'den uzantıyı belirle
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    if path_lower.endswith(".pdf"):
        dosya_adi += ".pdf"
    elif path_lower.endswith(".docx"):
        dosya_adi += ".docx"
    elif path_lower.endswith(".doc"):
        dosya_adi += ".doc"
    elif path_lower.endswith(".xlsx"):
        dosya_adi += ".xlsx"
    else:
        dosya_adi += ".pdf"  # Varsayılan

    dosya_yolu = os.path.join(hedef_klasor, dosya_adi)

    # Benzersiz dosya adı
    counter = 1
    original_path = dosya_yolu
    while os.path.exists(dosya_yolu):
        name, ext = os.path.splitext(original_path)
        dosya_yolu = f"{name}_{counter}{ext}"
        counter += 1

    try:
        response = session.get(url, timeout=60, stream=True, allow_redirects=True)

        if response.status_code != 200:
            return {
                "basarili": False,
                "url": url,
                "hata": f"HTTP {response.status_code}",
                "kategori": kategori,
                "baslik": baslik,
            }

        content_type = response.headers.get("Content-Type", "").lower()

        # Dosyayı kaydet
        with open(dosya_yolu, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Dosya boyutu kontrolü
        boyut = os.path.getsize(dosya_yolu)
        if boyut < 100:
            os.remove(dosya_yolu)
            return {
                "basarili": False,
                "url": url,
                "hata": f"Dosya çok küçük ({boyut} bytes) — muhtemelen hata sayfası",
                "kategori": kategori,
                "baslik": baslik,
            }

        # HTML hata sayfası kontrolü (PDF/DOC olması gereken yerde HTML ise)
        if "text/html" in content_type and not url.lower().endswith((".pdf", ".docx", ".doc")):
            os.remove(dosya_yolu)
            return {
                "basarili": False,
                "url": url,
                "hata": f"HTML döndü (PDF/DOC bekleniyordu): {content_type}",
                "kategori": kategori,
                "baslik": baslik,
            }

        sha256 = sha256_hesapla(dosya_yolu)

        return {
            "basarili": True,
            "url": url,
            "nihai_url": response.url,
            "http_durumu": response.status_code,
            "dosya_yolu": os.path.relpath(dosya_yolu, os.path.join(PROJE_KOKU, "google_collab_egitim")),
            "dosya_adi": os.path.basename(dosya_yolu),
            "sha256": sha256,
            "boyut": boyut,
            "kategori": kategori,
            "baslik": baslik,
            "content_type": content_type,
            "hedef_klasor": hedef_klasor_adi,
        }

    except requests.exceptions.Timeout:
        return {
            "basarili": False,
            "url": url,
            "hata": "Zaman aşımı (timeout)",
            "kategori": kategori,
            "baslik": baslik,
        }
    except Exception as e:
        return {
            "basarili": False,
            "url": url,
            "hata": f"{type(e).__name__}: {str(e)[:200]}",
            "kategori": kategori,
            "baslik": baslik,
        }


def envanter_guncelle(tum_basari_sonuclari, cikti_yolu):
    """Tüm başarılı indirmeleri envantere yazar."""
    alanlar = [
        "kaynak_id", "dosya_yolu", "dosya_adi", "baslik", "kaynak_tipi",
        "guven_sinifi", "kurum", "domain", "kaynak_url", "modul", "alt_konu",
        "yayin_tarihi", "gecerlilik_baslangici", "gecerlilik_bitis", "surum",
        "durum", "sha256", "dosya_boyutu", "indirme_tarihi",
        "ana_rag_havuzuna_alindi", "not",
    ]

    os.makedirs(os.path.dirname(cikti_yolu), exist_ok=True)

    with open(cikti_yolu, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=alanlar)
        writer.writeheader()

        for i, sonuc in enumerate(tum_basari_sonuclari, start=1):
            kategori = sonuc.get("kategori", "")
            hedef_klasor = sonuc.get("hedef_klasor", "99_inceleme_bekleyenler")

            # Kaynak tipi
            tip_haritasi = {
                "01_mevzuat": "mevzuat",
                "02_resmi_uyds_kilavuzlari": "resmi_kilavuz",
                "03_modul_dokumanlari": "modul_dokumani",
                "04_teknik_cozumler": "teknik_cozum",
                "05_onayli_destek_kayitlari": "onayli_destek",
                "06_surum_notlari": "surum_notu",
                "99_inceleme_bekleyenler": "aday",
            }
            kaynak_tipi = "bilinmeyen"
            for anahtar, tip in tip_haritasi.items():
                if anahtar in hedef_klasor:
                    kaynak_tipi = tip
                    break

            guven = KATEGORI_GUVEN_ESLEME.get(kategori, "E")
            kurum = KATEGORI_KURUM_ESLEME.get(kategori, "Yapı İşleri Genel Müdürlüğü")
            ana_rag = "evet" if guven in ["A", "B", "C", "D"] else "hayir"

            # Domain çıkar
            parsed = urlparse(sonuc.get("url", ""))
            domain = parsed.netloc

            writer.writerow({
                "kaynak_id": f"SRC-{i:06d}",
                "dosya_yolu": sonuc.get("dosya_yolu", ""),
                "dosya_adi": sonuc.get("dosya_adi", ""),
                "baslik": sonuc.get("baslik", ""),
                "kaynak_tipi": kaynak_tipi,
                "guven_sinifi": guven,
                "kurum": kurum,
                "domain": domain,
                "kaynak_url": sonuc.get("url", ""),
                "modul": kategori,
                "alt_konu": sonuc.get("baslik", "")[:50],
                "yayin_tarihi": "",
                "gecerlilik_baslangici": "",
                "gecerlilik_bitis": "",
                "surum": "",
                "durum": "guncel" if guven in ["A", "B", "C"] else "belirsiz",
                "sha256": sonuc.get("sha256", ""),
                "dosya_boyutu": sonuc.get("boyut", 0),
                "indirme_tarihi": datetime.now(TZ_ISTANBUL).strftime("%Y-%m-%d"),
                "ana_rag_havuzuna_alindi": ana_rag,
                "not": f"Content-Type: {sonuc.get('content_type', '')}",
            })

    print(f"📋 Envanter CSV güncellendi: {cikti_yolu}")


def manifest_guncelle(tum_sonuclar, cikti_yolu):
    """URL manifesto JSONL dosyasını oluşturur (başarılı + başarısız)."""
    os.makedirs(os.path.dirname(cikti_yolu), exist_ok=True)

    with open(cikti_yolu, "w", encoding="utf-8") as f:
        for i, sonuc in enumerate(tum_sonuclar, start=1):
            kategori = sonuc.get("kategori", "")
            guven = KATEGORI_GUVEN_ESLEME.get(kategori, "E")
            kayit = {
                "kaynak_id": f"SRC-{i:06d}",
                "url": sonuc.get("url", ""),
                "nihai_url": sonuc.get("nihai_url", sonuc.get("url", "")),
                "http_durumu": sonuc.get("http_durumu", 0),
                "erisim_tarihi": datetime.now(TZ_ISTANBUL).isoformat(),
                "dosya_yolu": sonuc.get("dosya_yolu", ""),
                "sha256": sonuc.get("sha256", ""),
                "guven_sinifi": guven,
                "indirme_durumu": "basarili" if sonuc.get("basarili") else "basarisiz",
                "hata": sonuc.get("hata", "") if not sonuc.get("basarili") else "",
            }
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")

    print(f"📋 URL Manifesto güncellendi: {cikti_yolu}")


def main():
    print("=" * 60)
    print("  Tüm Kaynak Belgeleri İndirme Sistemi")
    print("=" * 60)

    # Link listesini oku
    link_dosyasi = os.path.join(OUTPUT_KOKU, "link_listesi.json")
    if not os.path.exists(link_dosyasi):
        print(f"❌ Link listesi bulunamadı: {link_dosyasi}")
        print("   Önce collect_links.py çalıştırın.")
        return 1

    with open(link_dosyasi, "r", encoding="utf-8") as f:
        link_verisi = json.load(f)

    dosya_linkleri = link_verisi.get("dosya_linkleri", [])
    print(f"  Toplam dosya linki: {len(dosya_linkleri)}")
    print()

    tum_sonuclar = []
    basari_sonuclari = []
    gorulen_hashler = set()
    basarisiz_sayisi = 0

    for i, link in enumerate(dosya_linkleri, start=1):
        url = link["url"]
        baslik = link.get("baslik", "")
        kategori = link.get("kategori", "mevzuat")

        print(f"[{i}/{len(dosya_linkleri)}] {baslik[:50]}")
        print(f"  URL: {url}")

        sonuc = belge_indir(url, baslik, kategori)
        tum_sonuclar.append(sonuc)

        if sonuc["basarili"]:
            sha = sonuc["sha256"]
            if sha in gorulen_hashler:
                print(f"  ⚠️ TEKRAR: Aynı SHA-256 zaten indirilmiş")
                dosya_tam_yol = os.path.join(PROJE_KOKU, "google_collab_egitim", sonuc["dosya_yolu"])
                if os.path.exists(dosya_tam_yol):
                    os.remove(dosya_tam_yol)
                basarisiz_sayisi += 1
            else:
                gorulen_hashler.add(sha)
                basari_sonuclari.append(sonuc)
                kb = sonuc.get("boyut", 0)
                print(f"  ✓ İndirildi: {sonuc['dosya_adi']} ({kb/1024:.1f} KB)")
        else:
            basarisiz_sayisi += 1
            print(f"  ✗ Başarısız: {sonuc.get('hata', 'Bilinmeyen hata')}")

        # Rate limit
        time.sleep(0.3)
        print()

        # Her 10 başarılı indirmede envanteri kaydet
        if len(basari_sonuclari) > 0 and len(basari_sonuclari) % 10 == 0:
            envanter_guncelle(basari_sonuclari, os.path.join(OUTPUT_KOKU, "kaynak_envanteri.csv"))
            print(f"  💾 Ara kayıt: {len(basari_sonuclari)} belge envantere eklendi\n")

    # Özet
    print("=" * 60)
    print("  İNDİRME ÖZETİ")
    print("=" * 60)
    print(f"  Toplam URL denen:     {len(tum_sonuclar)}")
    print(f"  Başarılı indirme:     {len(basari_sonuclari)}")
    print(f"  Başarısız/Tekrar:     {basarisiz_sayisi}")

    # Güven sınıfı dağılımı
    guven_dagilim = {}
    for s in basari_sonuclari:
        g = KATEGORI_GUVEN_ESLEME.get(s.get("kategori", ""), "E")
        guven_dagilim[g] = guven_dagilim.get(g, 0) + 1
    print(f"  Güven sınıfı dağılım: {guven_dagilim}")

    # Kategori dağılımı
    kategori_dagilim = {}
    for s in basari_sonuclari:
        k = s.get("kategori", "bilinmeyen")
        kategori_dagilim[k] = kategori_dagilim.get(k, 0) + 1
    print(f"  Kategori dağılım:     {kategori_dagilim}")

    # Dosya türü dağılımı
    tur_dagilim = {}
    for s in basari_sonuclari:
        fn = s.get("dosya_adi", "")
        ext = os.path.splitext(fn)[1].lower()
        tur_dagilim[ext] = tur_dagilim.get(ext, 0) + 1
    print(f"  Dosya türü dağılım:   {tur_dagilim}")

    # Toplam boyut
    toplam_boyut = sum(s.get("boyut", 0) for s in basari_sonuclari)
    print(f"  Toplam boyut:         {toplam_boyut / (1024*1024):.1f} MB")
    print()

    # Envanter ve manifest güncelle
    envanter_guncelle(basari_sonuclari, os.path.join(OUTPUT_KOKU, "kaynak_envanteri.csv"))
    manifest_guncelle(tum_sonuclar, os.path.join(OUTPUT_KOKU, "kaynak_url_manifestosu.jsonl"))

    print(f"\n✅ İşlem tamam. {len(basari_sonuclari)} belge indirildi.")
    return len(basari_sonuclari)


if __name__ == "__main__":
    sys.exit(0 if main() > 0 else 1)