#!/usr/bin/env python3
# ============================================================
# download_sources.py — Resmî kaynakları doğrudan indirir
# ============================================================
"""
Google scraping yerine bilinen resmî URL'lerden belgeleri indirir.
Mevzuat, Resmî Gazete, Bakanlık kılavuzları ve UYDS dokümanları için
doğrudan URL erişimi kullanır.

Çıktılar:
  - data/kaynaklar/ altında sınıflandırılmış belgeler
  - data/output_v4/kaynak_envanteri.csv
  - data/output_v4/kaynak_url_manifestosu.jsonl
"""

import os
import sys
import json
import hashlib
import time
import urllib3
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Proje kök dizini
PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KAYNAK_KOKU = os.path.join(PROJE_KOKU, "google_collab_egitim", "data", "kaynaklar")
OUTPUT_KOKU = os.path.join(PROJE_KOKU, "google_collab_egitim", "data", "output_v4")

# İstanbul saat dilimi
TZ_ISTANBUL = timezone(timedelta(hours=3))

# Session ayarları
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
})
session.verify = False

# ============================================================
# Bilinen resmî kaynak URL'leri
# ============================================================
KAYNAK_URL_LISTESI = [
    # --- 01_mevzuat: Kanun, Yönetmelik, Tebliğ, Genelge ---
    {
        "url": "https://www.mevzuat.gov.tr/mevzuatmetni/-/mevzuat/view/4708",
        "kategori": "01_mevzuat",
        "baslik": "4708 sayılı Yapı Denetimi Hakkında Kanun",
        "kurum": "Mevzuat Bilgi Sistemi",
        "domain": "mevzuat.gov.tr",
        "guven_sinifi": "A",
        "modul": "genel",
        "alt_konu": "yapı_denetim_kanunu",
        "yayin_tarihi": "2001-07-03",
        "beklenen_format": "html",
    },
    {
        "url": "https://www.mevzuat.gov.tr/mevzuatmetni/-/mevzuat/view/3194",
        "kategori": "01_mevzuat",
        "baslik": "3194 sayılı İmar Kanunu",
        "kurum": "Mevzuat Bilgi Sistemi",
        "domain": "mevzuat.gov.tr",
        "guven_sinifi": "A",
        "modul": "ruhsat",
        "alt_konu": "imar_kanunu",
        "yayin_tarihi": "1985-05-09",
        "beklenen_format": "html",
    },
    {
        "url": "https://www.mevzuat.gov.tr/mevzuatmetni/-/mevzuat/view/7345",
        "kategori": "01_mevzuat",
        "baslik": "Afet Riski Altındaki Alanların Dönüştürülmesi Hakkında Kanun",
        "kurum": "Mevzuat Bilgi Sistemi",
        "domain": "mevzuat.gov.tr",
        "guven_sinifi": "A",
        "modul": "yapi_kayit",
        "alt_konu": "afet_riski_donusum",
        "yayin_tarihi": "2012-05-31",
        "beklenen_format": "html",
    },
    {
        "url": "https://www.mevzuat.gov.tr/mevzuatmetni/-/mevzuat/view/6306",
        "kategori": "01_mevzuat",
        "baslik": "6306 sayılı Afet Riski Altındaki Alanların Dönüştürülmesi Hakkında Kanun",
        "kurum": "Mevzuat Bilgi Sistemi",
        "domain": "mevzuat.gov.tr",
        "guven_sinifi": "A",
        "modul": "yapi_kayit",
        "alt_konu": "afet_riski_kanun",
        "yayin_tarihi": "2012-05-16",
        "beklenen_format": "html",
    },
    # Resmî Gazete - 4708 sayılı Kanun
    {
        "url": "https://www.resmigazete.gov.tr/main.aspx?home=https://www.resmigazete.gov.tr/eskiler/2001/07/20010703.htm&main=https://www.resmigazete.gov.tr/eskiler/2001/07/20010703.htm",
        "kategori": "01_mevzuat",
        "baslik": "4708 sayılı Yapı Denetimi Kanunu - Resmî Gazete",
        "kurum": "Resmî Gazete",
        "domain": "resmigazete.gov.tr",
        "guven_sinifi": "A",
        "modul": "genel",
        "alt_konu": "yapi_denetim_kanunu_rg",
        "yayin_tarihi": "2001-07-03",
        "beklenen_format": "html",
    },
    # Yapı Denetimi Uygulama Yönetmeliği
    {
        "url": "https://www.resmigazete.gov.tr/eskiler/2001/07/20010703.htm",
        "kategori": "01_mevzuat",
        "baslik": "Yapı Denetimi Uygulama Yönetmeliği - Resmî Gazete",
        "kurum": "Resmî Gazete",
        "domain": "resmigazete.gov.tr",
        "guven_sinifi": "A",
        "modul": "genel",
        "alt_konu": "yapi_denetim_yonetmelik",
        "yayin_tarihi": "2001-07-03",
        "beklenen_format": "html",
    },
    # --- 02_resmi_uyds_kilavuzlari ---
    # Çevre, Şehircilik ve İklim Değişikliği Bakanlığı ana sayfa
    {
        "url": "https://csb.gov.tr/yapi-isleri-genel-mudurlugu-istihdam",
        "kategori": "02_resmi_uyds_kilavuzlari",
        "baslik": "Yapı İşleri Genel Müdürlüğü - İstihdam Bilgisi",
        "kurum": "Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
        "domain": "csb.gov.tr",
        "guven_sinifi": "B",
        "modul": "genel",
        "alt_konu": "yapi_isleri_genel_mudurlugu",
        "yayin_tarihi": "",
        "beklenen_format": "html",
    },
    # Yapi İşleri Genel Müdürlüğü ana sayfa
    {
        "url": "https://yapiisleri.csb.gov.tr/",
        "kategori": "02_resmi_uyds_kilavuzlari",
        "baslik": "Yapı İşleri Genel Müdürlüğü Ana Sayfa",
        "kurum": "Yapı İşleri Genel Müdürlüğü",
        "domain": "yapiisleri.csb.gov.tr",
        "guven_sinifi": "B",
        "modul": "genel",
        "alt_konu": "ana_sayfa",
        "yayin_tarihi": "",
        "beklenen_format": "html",
    },
    # Yapı denetimi sayfası
    {
        "url": "https://yapiisleri.csb.gov.tr/yapi-denetimi-h95123432",
        "kategori": "02_resmi_uyds_kilavuzlari",
        "baslik": "Yapı Denetimi - Yapı İşleri GM",
        "kurum": "Yapı İşleri Genel Müdürlüğü",
        "domain": "yapiisleri.csb.gov.tr",
        "guven_sinifi": "B",
        "modul": "denetci",
        "alt_konu": "yapi_denetimi",
        "yayin_tarihi": "",
        "beklenen_format": "html",
    },
    # --- 03_modul_dokumanlari ---
    # Yapı kayıt sistemi
    {
        "url": "https://yapiisleri.csb.gov.tr/yapi-kayit-sistemi-h95123433",
        "kategori": "03_modul_dokumanlari/yapi_kayit",
        "baslik": "Yapı Kayıt Sistemi - Yapı İşleri GM",
        "kurum": "Yapı İşleri Genel Müdürlüğü",
        "domain": "yapiisleri.csb.gov.tr",
        "guven_sinifi": "B",
        "modul": "yapi_kayit",
        "alt_konu": "yapi_kayit_sistemi",
        "yayin_tarihi": "",
        "beklenen_format": "html",
    },
    # Ruhsat ve yapı denetimi
    {
        "url": "https://yapiisleri.csb.gov.tr/ruhsat-ve-yapi-denetimi-h95123435",
        "kategori": "03_modul_dokumanlari/ruhsat",
        "baslik": "Ruhsat ve Yapı Denetimi - Yapı İşleri GM",
        "kurum": "Yapı İşleri Genel Müdürlüğü",
        "domain": "yapiisleri.csb.gov.tr",
        "guven_sinifi": "B",
        "modul": "ruhsat",
        "alt_konu": "ruhsat_yapi_denetimi",
        "yayin_tarihi": "",
        "beklenen_format": "html",
    },
    # --- 06_surum_notlari ---
    # Bakanlık duyurular sayfası
    {
        "url": "https://csb.gov.tr/duyurular",
        "kategori": "06_surum_notlari",
        "baslik": "ÇŞİB Duyurular",
        "kurum": "Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
        "domain": "csb.gov.tr",
        "guven_sinifi": "C",
        "modul": "genel",
        "alt_konu": "duyurular",
        "yayin_tarihi": "",
        "beklenen_format": "html",
    },
    # Yapı İşleri duyurular
    {
        "url": "https://yapiisleri.csb.gov.tr/duyurular",
        "kategori": "06_surum_notlari",
        "baslik": "Yapı İşleri GM Duyurular",
        "kurum": "Yapı İşleri Genel Müdürlüğü",
        "domain": "yapiisleri.csb.gov.tr",
        "guven_sinifi": "C",
        "modul": "genel",
        "alt_konu": "duyurular",
        "yayin_tarihi": "",
        "beklenen_format": "html",
    },
]


def sha256_hesapla(dosya_yolu):
    """Dosyanın SHA-256 hash'ini hesaplar."""
    h = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def guvenli_dosya_adi(baslik):
    """Başlıktan güvenli dosya adı üretir."""
    turkce_haritasi = {
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U",
    }
    ad = baslik
    for tr, en in turkce_haritasi.items():
        ad = ad.replace(tr, en)
    ad = ad.replace(" ", "_").replace("-", "_").replace("/", "_")
    ad = "".join(c for c in ad if c.isalnum() or c == "_")
    return ad.lower()[:80]


def html_temizle(html_metin):
    """HTML'i temiz Markdown'a dönüştürür."""
    soup = BeautifulSoup(html_metin, "html.parser")

    # Script ve style etiketlerini kaldır
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()

    # Ana içerik
    main = soup.find("main") or soup.find("article") or soup.find("div", class_="content") or soup.find("body")
    if main:
        metin = main.get_text(separator="\n", strip=True)
    else:
        metin = soup.get_text(separator="\n", strip=True)

    # Boş satırları temizle
    satirlar = [s.strip() for s in metin.split("\n") if s.strip()]
    return "\n".join(satirlar)


def url_indir(kaynak_bilgisi):
    """
    URL'den belge indirir, uygun klasöre kaydeder.
    Başarı/başarısızlık bilgisi döner.
    """
    url = kaynak_bilgisi["url"]
    kategori = kaynak_bilgisi["kategori"]
    baslik = kaynak_bilgisi["baslik"]
    beklenen_format = kaynak_bilgisi.get("beklenen_format", "html")

    # Hedef klasör
    hedef_klasor = os.path.join(KAYNAK_KOKU, kategori)
    os.makedirs(hedef_klasor, exist_ok=True)

    # Dosya adı
    dosya_adi = guvenli_dosya_adi(baslik)
    if beklenen_format == "pdf":
        dosya_adi += ".pdf"
    else:
        dosya_adi += ".md"
    dosya_yolu = os.path.join(hedef_klasor, dosya_adi)

    try:
        response = session.get(url, timeout=30, allow_redirects=True)

        if response.status_code != 200:
            return {
                "basarili": False,
                "url": url,
                "hata": f"HTTP {response.status_code}",
                "kaynak_bilgisi": kaynak_bilgisi,
            }

        content_type = response.headers.get("Content-Type", "").lower()

        # PDF ise doğrudan kaydet
        if "application/pdf" in content_type or url.lower().endswith(".pdf"):
            with open(dosya_yolu, "wb") as f:
                f.write(response.content)

            sha256 = sha256_hesapla(dosya_yolu)
            boyut = os.path.getsize(dosya_yolu)

            return {
                "basarili": True,
                "url": url,
                "nihai_url": response.url,
                "http_durumu": response.status_code,
                "dosya_yolu": os.path.relpath(dosya_yolu, os.path.join(PROJE_KOKU, "google_collab_egitim")),
                "dosya_adi": dosya_adi,
                "sha256": sha256,
                "boyut": boyut,
                "kaynak_bilgisi": kaynak_bilgisi,
                "content_type": content_type,
            }

        # HTML ise temizle ve Markdown olarak kaydet
        elif "text/html" in content_type or beklenen_format == "html":
            temiz_metin = html_temizle(response.text)

            # Çok kısa içerik kontrolü (HTML hata sayfası olabilir)
            if len(temiz_metin) < 100:
                return {
                    "basarili": False,
                    "url": url,
                    "hata": f"İçerik çok kısa ({len(temiz_metin)} karakter) — muhtemelen hata sayfası",
                    "kaynak_bilgisi": kaynak_bilgisi,
                }

            # Markdown başlığı ekle
            md_icerik = f"# {baslik}\n\n> Kaynak URL: {url}\n> Erişim tarihi: {datetime.now(TZ_ISTANBUL).isoformat()}\n\n---\n\n{temiz_metin}\n"

            with open(dosya_yolu, "w", encoding="utf-8") as f:
                f.write(md_icerik)

            sha256 = sha256_hesapla(dosya_yolu)
            boyut = os.path.getsize(dosya_yolu)

            return {
                "basarili": True,
                "url": url,
                "nihai_url": response.url,
                "http_durumu": response.status_code,
                "dosya_yolu": os.path.relpath(dosya_yolu, os.path.join(PROJE_KOKU, "google_collab_egitim")),
                "dosya_adi": dosya_adi,
                "sha256": sha256,
                "boyut": boyut,
                "kaynak_bilgisi": kaynak_bilgisi,
                "content_type": content_type,
            }
        else:
            return {
                "basarili": False,
                "url": url,
                "hata": f"Bilinmeyen içerik türü: {content_type}",
                "kaynak_bilgisi": kaynak_bilgisi,
            }

    except requests.exceptions.Timeout:
        return {
            "basarili": False,
            "url": url,
            "hata": "Zaman aşımı (timeout)",
            "kaynak_bilgisi": kaynak_bilgisi,
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "basarili": False,
            "url": url,
            "hata": f"Bağlantı hatası: {type(e).__name__}",
            "kaynak_bilgisi": kaynak_bilgisi,
        }
    except Exception as e:
        return {
            "basarili": False,
            "url": url,
            "hata": f"{type(e).__name__}: {str(e)[:200]}",
            "kaynak_bilgisi": kaynak_bilgisi,
        }


def envanter_csv_olustur(basari_sonuclari, cikti_yolu):
    """Kaynak envanteri CSV dosyasını oluşturur."""
    import csv

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

        for i, sonuc in enumerate(basari_sonuclari, start=1):
            kb = sonuc["kaynak_bilgisi"]
            kategori = kb["kategori"]

            # Kategori -> kaynak_tipi
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
                if anahtar in kategori:
                    kaynak_tipi = tip
                    break

            # Ana RAG havuzuna alınabilir mi?
            guven = kb.get("guven_sinifi", "E")
            ana_rag = "evet" if guven in ["A", "B", "C", "D"] else "hayir"

            writer.writerow({
                "kaynak_id": f"SRC-{i:06d}",
                "dosya_yolu": sonuc.get("dosya_yolu", ""),
                "dosya_adi": sonuc.get("dosya_adi", ""),
                "baslik": kb.get("baslik", ""),
                "kaynak_tipi": kaynak_tipi,
                "guven_sinifi": guven,
                "kurum": kb.get("kurum", ""),
                "domain": kb.get("domain", ""),
                "kaynak_url": sonuc.get("url", ""),
                "modul": kb.get("modul", ""),
                "alt_konu": kb.get("alt_konu", ""),
                "yayin_tarihi": kb.get("yayin_tarihi", ""),
                "gecerlilik_baslangici": kb.get("yayin_tarihi", ""),
                "gecerlilik_bitis": "",
                "surum": "",
                "durum": "guncel" if guven in ["A", "B", "C"] else "belirsiz",
                "sha256": sonuc.get("sha256", ""),
                "dosya_boyutu": sonuc.get("boyut", 0),
                "indirme_tarihi": datetime.now(TZ_ISTANBUL).strftime("%Y-%m-%d"),
                "ana_rag_havuzuna_alindi": ana_rag,
                "not": f"Content-Type: {sonuc.get('content_type', '')}",
            })

    print(f"📋 Envanter CSV: {cikti_yolu}")


def manifest_jsonl_olustur(tum_sonuclar, cikti_yolu):
    """URL manifesto JSONL dosyasını oluşturur (başarılı + başarısız)."""
    os.makedirs(os.path.dirname(cikti_yolu), exist_ok=True)

    with open(cikti_yolu, "w", encoding="utf-8") as f:
        for i, sonuc in enumerate(tum_sonuclar, start=1):
            kb = sonuc.get("kaynak_bilgisi", {})
            kayit = {
                "kaynak_id": f"SRC-{i:06d}",
                "url": sonuc.get("url", ""),
                "nihai_url": sonuc.get("nihai_url", sonuc.get("url", "")),
                "http_durumu": sonuc.get("http_durumu", 0),
                "erisim_tarihi": datetime.now(TZ_ISTANBUL).isoformat(),
                "dosya_yolu": sonuc.get("dosya_yolu", ""),
                "sha256": sonuc.get("sha256", ""),
                "guven_sinifi": kb.get("guven_sinifi", "E"),
                "indirme_durumu": "basarili" if sonuc.get("basarili") else "basarisiz",
                "hata": sonuc.get("hata", "") if not sonuc.get("basarili") else "",
            }
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")

    print(f"📋 URL Manifesto: {cikti_yolu}")


def main():
    print("=" * 60)
    print("  UYDS Kaynak Belge İndirme Sistemi")
    print("=" * 60)
    print(f"  Toplam URL: {len(KAYNAK_URL_LISTESI)}")
    print(f"  Kaynak kökü: {KAYNAK_KOKU}")
    print(f"  Output kökü: {OUTPUT_KOKU}")
    print("=" * 60)
    print()

    tum_sonuclar = []
    basari_sonuclari = []
    basarisiz_sonuclar = []
    gorulen_hashler = set()

    for i, kb in enumerate(KAYNAK_URL_LISTESI, start=1):
        print(f"[{i}/{len(KAYNAK_URL_LISTESI)}] {kb['baslik']}")
        print(f"  URL: {kb['url']}")

        sonuc = url_indir(kb)
        tum_sonuclar.append(sonuc)

        if sonuc["basarili"]:
            # SHA-256 tekrar kontrolü
            sha = sonuc["sha256"]
            if sha in gorulen_hashler:
                print(f"  ⚠️ TEKRAR: Aynı SHA-256 zaten indirilmiş, atlanıyor")
                os.remove(os.path.join(PROJE_KOKU, "google_collab_egitim", sonuc["dosya_yolu"]))
                basarisiz_sonuclar.append({**sonuc, "hata": "Tekrar (SHA-256 duplikası)"})
            else:
                gorulen_hashler.add(sha)
                basari_sonuclari.append(sonuc)
                print(f"  ✓ İndirildi: {sonuc['dosya_adi']} ({sonuc['boyut']} bytes)")
        else:
            basarisiz_sonuclar.append(sonuc)
            print(f"  ✗ Başarısız: {sonuc['hata']}")

        # Rate limit için bekle
        time.sleep(1)
        print()

    # Özet
    print("=" * 60)
    print("  İNDİRME ÖZETİ")
    print("=" * 60)
    print(f"  Toplam URL denen:     {len(tum_sonuclar)}")
    print(f"  Başarılı indirme:     {len(basari_sonuclari)}")
    print(f"  Başarısız indirme:    {len(basarisiz_sonuclar)}")
    print(f"  Tekrar atlanan:       {len(basarisiz_sonuclar) - sum(1 for s in basarisiz_sonuclar if 'Tekrar' not in s.get('hata', ''))}")

    # Güven sınıfı dağılımı
    guven_dagilim = {}
    for s in basari_sonuclari:
        g = s["kaynak_bilgisi"].get("guven_sinifi", "E")
        guven_dagilim[g] = guven_dagilim.get(g, 0) + 1
    print(f"  Güven sınıfı dağılım: {guven_dagilim}")

    # Kategori dağılımı
    kategori_dagilim = {}
    for s in basari_sonuclari:
        k = s["kaynak_bilgisi"]["kategori"].split("/")[0]
        kategori_dagilim[k] = kategori_dagilim.get(k, 0) + 1
    print(f"  Kategori dağılım:     {kategori_dagilim}")
    print()

    # Envanter CSV oluştur
    envanter_csv_yolu = os.path.join(OUTPUT_KOKU, "kaynak_envanteri.csv")
    envanter_csv_olustur(basari_sonuclari, envanter_csv_yolu)

    # Manifest JSONL oluştur (tüm URL'ler — başarılı + başarısız)
    manifest_yolu = os.path.join(OUTPUT_KOKU, "kaynak_url_manifestosu.jsonl")
    manifest_jsonl_olustur(tum_sonuclar, manifest_yolu)

    # Başarısız URL'leri raporla
    if basarisiz_sonuclar:
        print("\n⚠️ Başarısız URL'ler:")
        for s in basarisiz_sonuclar:
            print(f"   - {s['url']}: {s.get('hata', 'Bilinmeyen hata')}")

    print(f"\n✅ İşlem tamam. {len(basari_sonuclari)} belge indirildi.")
    return len(basari_sonuclari)


if __name__ == "__main__":
    sys.exit(0 if main() > 0 else 1)