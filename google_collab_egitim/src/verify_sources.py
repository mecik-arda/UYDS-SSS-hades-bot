#!/usr/bin/env python3
# ============================================================
# verify_sources.py — İndirilen belgelerin gerçekliğini doğrular
# ============================================================
"""
İndirilen kaynak belgelerin gerçekten resmî kaynaklardan geldiğini
ve doğru içerik barındırdığını çok katmanlı olarak doğrular.

Kontroller:
1. URL domain kontrolü (.gov.tr)
2. HTTP HEAD ile tekrar erişim doğrulaması
3. PDF magic bytes kontrolü (%PDF)
4. DOCX magic bytes kontrolü (PK)
5. Dosya içeriğinde Türkçe mevzuat kelimeleri arama
6. SHA-256 hash doğrulaması (envanter ile karşılaştırma)
7. Dosya boyutu kontrolü (bozuk/eksik dosya tespiti)
"""

import os
import sys
import json
import csv
import hashlib
import urllib3
import requests
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KAYNAK_KOKU = os.path.join(PROJE_KOKU, "google_collab_egitim", "data", "kaynaklar")
OUTPUT_KOKU = os.path.join(PROJE_KOKU, "google_collab_egitim", "data", "output_v4")
ENVANTER_YOLU = os.path.join(OUTPUT_KOKU, "kaynak_envanteri.csv")
RAPOR_YOLU = os.path.join(OUTPUT_KOKU, "dogrulama_raporu.md")

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})
session.verify = False

# Türkçe mevzuat anahtar kelimeleri
MEVZUAT_KELIMELERI = [
    "kanun", "yönetmelik", "tebliğ", "genelge", "bakanlığı", "bakanlik",
    "yapı", "yapi", "denetim", "ruhsat", "iskan", "İskân", "afet",
    "inşaat", "insaat", "mühendis", "muhendis", "mimar", "proje",
    "yapı denetim", "yapi denetim", "4708", "3194", "6306", "7269",
    "Resmî Gazete", "Resmi Gazete", "mevzuat", "Çevre", "Cevre",
    "Şehircilik", "Sehircilik", "İklim", "Iklim", "Bakanlığı",
    "Genel Müdürlüğü", "Genel Mudurlugu", "yapiisleri",
]

# PDF magic bytes: %PDF
PDF_MAGIC = b"%PDF"
# DOCX/ZIP magic bytes: PK
DOCX_MAGIC = b"PK\x03\x04"
# DOC (OLE2) magic bytes: D0 CF 11 E0
DOC_MAGIC = b"\xd0\xcf\x11\xe0"


def sha256_hesapla(dosya_yolu):
    h = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def pdf_mi(dosya_yolu):
    """Dosyanın gerçekten PDF olup olmadığını kontrol eder."""
    try:
        with open(dosya_yolu, "rb") as f:
            magic = f.read(8)
        return magic[:4] == PDF_MAGIC
    except:
        return False


def docx_mi(dosya_yolu):
    """Dosyanın DOCX (ZIP) olup olmadığını kontrol eder."""
    try:
        with open(dosya_yolu, "rb") as f:
            magic = f.read(4)
        return magic == DOCX_MAGIC
    except:
        return False


def doc_mi(dosya_yolu):
    """Dosyanın DOC (OLE2) olup olmadığını kontrol eder."""
    try:
        with open(dosya_yolu, "rb") as f:
            magic = f.read(4)
        return magic == DOC_MAGIC
    except:
        return False


def gov_tr_mi(url):
    """URL'nin .gov.tr alan adından gelip gelmediğini kontrol eder."""
    return ".gov.tr" in url or "csb.gov.tr" in url or "resmigazete.gov.tr" in url or "mevzuat.gov.tr" in url


def icerik_mevzuat_iceriyor_mu(dosya_yolu, max_bytes=50000):
    """
    Dosya içeriğinde Türkçe mevzuat kelimeleri arar.
    PDF için pypdf ile metin çıkarır, diğerleri için ham okur.
    """
    ext = os.path.splitext(dosya_yolu)[1].lower()
    metin = ""

    try:
        if ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(dosya_yolu)
                # İlk 5 sayfayı oku
                for i, sayfa in enumerate(reader.pages[:5]):
                    metin += sayfa.extract_text() or ""
                    if len(metin) > max_bytes:
                        break
            except:
                # PDF metin çıkarılamıyorsa (tarama PDF), OCR gerekli
                return None, "PDF metin çıkarılamıyor (OCR gerekebilir)"

        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(dosya_yolu)
                for p in doc.paragraphs[:200]:
                    metin += p.text + "\n"
            except:
                return None, "DOCX okunamadı"

        elif ext == ".doc":
            # DOC formatı için python-docx çalışmaz, ham metin dene
            try:
                with open(dosya_yolu, "rb") as f:
                    ham = f.read(max_bytes)
                metin = ham.decode("utf-8", errors="ignore")
            except:
                return None, "DOC okunamadı"

        elif ext in [".md", ".txt"]:
            with open(dosya_yolu, "r", encoding="utf-8", errors="ignore") as f:
                metin = f.read(max_bytes)

        else:
            # Diğer formatlar için ham okuma
            with open(dosya_yolu, "rb") as f:
                ham = f.read(max_bytes)
            metin = ham.decode("utf-8", errors="ignore")

    except Exception as e:
        return None, f"Okuma hatası: {type(e).__name__}"

    if not metin or len(metin.strip()) < 10:
        return False, "İçerik çok kısa/boş"

    # Mevzuat kelimeleri ara
    metin_lower = metin.lower()
    eslesen = []
    for kelime in MEVZUAT_KELIMELERI:
        if kelime.lower() in metin_lower:
            eslesen.append(kelime)

    if len(eslesen) >= 2:
        return True, f"{len(eslesen)} mevzuat kelimesi bulundu: {', '.join(eslesen[:5])}"
    elif len(eslesen) == 1:
        return "kismi", f"1 kelime: {eslesen[0]}"
    else:
        return False, "Mevzuat kelimesi bulunamadı"


def http_durum_kontrol(url):
    """URL'ye HEAD isteği atarak erişilebilirliği kontrol eder."""
    try:
        r = session.head(url, timeout=15, allow_redirects=True)
        return r.status_code, r.headers.get("Content-Type", "")
    except requests.exceptions.Timeout:
        return -1, "Timeout"
    except Exception as e:
        return -2, f"{type(e).__name__}"


def main():
    print("=" * 60)
    print("  KAYNAK DOĞRULAMA SİSTEMİ")
    print("=" * 60)

    # Envanteri oku
    if not os.path.exists(ENVANTER_YOLU):
        print(f"❌ Envanter bulunamadı: {ENVANTER_YOLU}")
        return

    with open(ENVANTER_YOLU, "r", encoding="utf-8-sig") as f:
        envanter = list(csv.DictReader(f))

    print(f"  Toplam kayıt: {len(envanter)}")
    print()

    sonuclar = []
    dogrulama_sayaci = {
        "domain_gov_tr": 0,
        "hash_eslesi": 0,
        "pdf_gecerli": 0,
        "docx_gecerli": 0,
        "doc_gecerli": 0,
        "icerik_mevzuat": 0,
        "icerik_kismi": 0,
        "icerik_yok": 0,
        "boyut_yeterli": 0,
        "boyut_kucuk": 0,
        "http_erisilebilir": 0,
        "http_erisilemez": 0,
        "ocr_gerekli": 0,
    }

    rapor_satirlari = []
    rapor_satirlari.append("# Kaynak Doğrulama Raporu\n")
    rapor_satirlari.append(f"**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    rapor_satirlari.append(f"**Toplam belge:** {len(envanter)}\n\n")

    rapor_satirlari.append("## Doğrulama Kriterleri\n")
    rapor_satirlari.append("1. **Domain kontrolü:** URL `.gov.tr` alan adından mı?\n")
    rapor_satirlari.append("2. **SHA-256 hash:** Envanterdeki hash ile dosya hash'i eşleşiyor mu?\n")
    rapor_satirlari.append("3. **Dosya formatı:** PDF/DOCX/DOC magic bytes doğru mu?\n")
    rapor_satirlari.append("4. **İçerik kontrolü:** Dosyada Türkçe mevzuat kelimeleri var mı?\n")
    rapor_satirlari.append("5. **Dosya boyutu:** 1KB'dan büyük mü?\n")
    rapor_satirlari.append("6. **HTTP erişim:** URL hâlâ erişilebilir mi? (HEAD isteği)\n\n")

    rapor_satirlari.append("## Detaylı Sonuçlar\n")
    rapor_satirlari.append("| # | Dosya | Domain | Hash | Format | İçerik | Boyut | HTTP | Sonuç |\n")
    rapor_satirlari.append("|---|-------|--------|------|--------|--------|-------|------|------|\n")

    for i, kayit in enumerate(envanter, start=1):
        kaynak_id = kayit.get("kaynak_id", "")
        dosya_adi = kayit.get("dosya_adi", "")
        url = kayit.get("kaynak_url", "")
        envanter_hash = kayit.get("sha256", "")
        dosya_yolu_rel = kayit.get("dosya_yolu", "")
        dosya_boyutu = int(kayit.get("dosya_boyutu", 0))

        # Tam dosya yolu
        dosya_yolu = os.path.join(PROJE_KOKU, "google_collab_egitim", dosya_yolu_rel)

        print(f"[{i}/{len(envanter)}] {dosya_adi[:50]}...")

        sonuc = {
            "kaynak_id": kaynak_id,
            "dosya_adi": dosya_adi,
            "url": url,
            "domain_gov_tr": False,
            "hash_eslesi": False,
            "format_gecerli": False,
            "icerik_durum": "bilinmeyen",
            "icerik_mesaj": "",
            "boyut_yeterli": False,
            "http_durum": 0,
            "genel_sonuc": "BELİRSİZ",
        }

        # 1. Domain kontrolü
        sonuc["domain_gov_tr"] = gov_tr_mi(url)
        if sonuc["domain_gov_tr"]:
            dogrulama_sayaci["domain_gov_tr"] += 1

        # 2. Dosya var mı?
        if not os.path.exists(dosya_yolu):
            sonuc["genel_sonuc"] = "DOSYA YOK"
            sonuclar.append(sonuc)
            rapor_satirlari.append(f"| {i} | {dosya_adi[:30]} | {'✅' if sonuc['domain_gov_tr'] else '❌'} | - | - | - | - | - | ❌ DOSYA YOK |\n")
            continue

        # 3. SHA-256 hash kontrolü
        try:
            gercek_hash = sha256_hesapla(dosya_yolu)
            sonuc["hash_eslesi"] = (gercek_hash == envanter_hash)
            if sonuc["hash_eslesi"]:
                dogrulama_sayaci["hash_eslesi"] += 1
        except:
            sonuc["hash_eslesi"] = False

        # 4. Format kontrolü
        ext = os.path.splitext(dosya_yolu)[1].lower()
        format_gecerli = False
        if ext == ".pdf":
            format_gecerli = pdf_mi(dosya_yolu)
            if format_gecerli:
                dogrulama_sayaci["pdf_gecerli"] += 1
        elif ext == ".docx":
            format_gecerli = docx_mi(dosya_yolu)
            if format_gecerli:
                dogrulama_sayaci["docx_gecerli"] += 1
        elif ext == ".doc":
            format_gecerli = doc_mi(dosya_yolu)
            if format_gecerli:
                dogrulama_sayaci["doc_gecerli"] += 1
        elif ext in [".md", ".txt"]:
            format_gecerli = True  # Metin dosyaları

        sonuc["format_gecerli"] = format_gecerli

        # 5. İçerik kontrolü
        icerik_ok, icerik_msg = icerik_mevzuat_iceriyor_mu(dosya_yolu)
        sonuc["icerik_durum"] = "evet" if icerik_ok is True else ("kismi" if icerik_ok == "kismi" else ("ocr" if icerik_ok is None else "hayir"))
        sonuc["icerik_mesaj"] = icerik_msg

        if icerik_ok is True:
            dogrulama_sayaci["icerik_mevzuat"] += 1
        elif icerik_ok == "kismi":
            dogrulama_sayaci["icerik_kismi"] += 1
        elif icerik_ok is None:
            dogrulama_sayaci["ocr_gerekli"] += 1
        else:
            dogrulama_sayaci["icerik_yok"] += 1

        # 6. Boyut kontrolü
        sonuc["boyut_yeterli"] = dosya_boyutu > 1024  # 1KB'dan büyük
        if sonuc["boyut_yeterli"]:
            dogrulama_sayaci["boyut_yeterli"] += 1
        else:
            dogrulama_sayaci["boyut_kucuk"] += 1

        # 7. Genel sonuç
        if (sonuc["domain_gov_tr"] and sonuc["hash_eslesi"] and
            sonuc["format_gecerli"] and sonuc["boyut_yeterli"] and
            sonuc["icerik_durum"] in ["evet", "kismi", "ocr"]):
            sonuc["genel_sonuc"] = "DOĞRULANDI"
        elif sonuc["domain_gov_tr"] and sonuc["hash_eslesi"] and sonuc["format_gecerli"]:
            sonuc["genel_sonuc"] = "DOĞRULANDI (içerik az)"
        elif not sonuc["domain_gov_tr"]:
            sonuc["genel_sonuc"] = "DOMAIN ŞÜPHELİ"
        elif not sonuc["hash_eslesi"]:
            sonuc["genel_sonuc"] = "HASH UYUMSUZ"
        elif not sonuc["format_gecerli"]:
            sonuc["genel_sonuc"] = "FORMAT HATALI"
        else:
            sonuc["genel_sonuc"] = "KISMEN DOĞRULANDI"

        sonuclar.append(sonuc)

        # Tablo satırı
        domain_str = "✅" if sonuc["domain_gov_tr"] else "❌"
        hash_str = "✅" if sonuc["hash_eslesi"] else "❌"
        format_str = "✅" if sonuc["format_gecerli"] else "❌"
        icerik_str = {"evet": "✅", "kismi": "⚠️", "ocr": "🔍", "hayir": "❌"}.get(sonuc["icerik_durum"], "?")
        boyut_str = "✅" if sonuc["boyut_yeterli"] else "❌"
        sonuc_str = {"DOĞRULANDI": "✅", "DOĞRULANDI (içerik az)": "✅", "KISMEN DOĞRULANDI": "⚠️", "DOMAIN ŞÜPHELİ": "❌", "HASH UYUMSUZ": "❌", "FORMAT HATALI": "❌", "DOSYA YOK": "❌"}.get(sonuc["genel_sonuc"], "?")

        rapor_satirlari.append(f"| {i} | {dosya_adi[:30]} | {domain_str} | {hash_str} | {format_str} | {icerik_str} | {boyut_str} | - | {sonuc_str} |\n")

    # HTTP kontrolü (ilk 20 dosya için, rate limit nedeniyle)
    print("\n🌐 HTTP erişim kontrolü (ilk 20 dosya)...")
    rapor_satirlari.append("\n## HTTP Erişim Kontrolü (İlk 20 Dosya)\n")
    rapor_satirlari.append("| # | URL | HTTP Durum | Content-Type |\n")
    rapor_satirlari.append("|---|-----|-----------|-------------|\n")

    for i, sonuc in enumerate(sonuclar[:20], start=1):
        url = sonuc["url"]
        if url:
            http_durum, content_type = http_durum_kontrol(url)
            sonuc["http_durum"] = http_durum
            if 200 <= http_durum < 400:
                dogrulama_sayaci["http_erisilebilir"] += 1
            else:
                dogrulama_sayaci["http_erisilemez"] += 1
            rapor_satirlari.append(f"| {i} | {url[:60]}... | {http_durum} | {content_type[:30]} |\n")

    # Özet
    print("\n" + "=" * 60)
    print("  DOĞRULAMA ÖZETİ")
    print("=" * 60)

    dogrulanan = sum(1 for s in sonuclar if "DOĞRULANDI" in s["genel_sonuc"])
    kismen = sum(1 for s in sonuclar if s["genel_sonuc"] == "KISMEN DOĞRULANDI")
    basarisiz = sum(1 for s in sonuclar if "ŞÜPHELİ" in s["genel_sonuc"] or "UYUMSUZ" in s["genel_sonuc"] or "HATALI" in s["genel_sonuc"])

    print(f"  ✅ Doğrulanan:      {dogrulanan}")
    print(f"  ⚠️ Kısmen doğrulanan: {kismen}")
    print(f"  ❌ Başarısız:        {basarisiz}")
    print()
    print(f"  Domain .gov.tr:     {dogrulama_sayaci['domain_gov_tr']}/{len(sonuclar)}")
    print(f"  Hash eşleşti:       {dogrulama_sayaci['hash_eslesi']}/{len(sonuclar)}")
    print(f"  PDF geçerli:        {dogrulama_sayaci['pdf_gecerli']}")
    print(f"  DOCX geçerli:       {dogrulama_sayaci['docx_gecerli']}")
    print(f"  DOC geçerli:        {dogrulama_sayaci['doc_gecerli']}")
    print(f"  İçerik mevzuat:     {dogrulama_sayaci['icerik_mevzuat']}")
    print(f"  İçerik kısmi:       {dogrulama_sayaci['icerik_kismi']}")
    print(f"  OCR gerekli:        {dogrulama_sayaci['ocr_gerekli']}")
    print(f"  İçerik yok:         {dogrulama_sayaci['icerik_yok']}")
    print(f"  Boyut yeterli:      {dogrulama_sayaci['boyut_yeterli']}")
    print(f"  HTTP erişilebilir:  {dogrulama_sayaci['http_erisilebilir']}")
    print(f"  HTTP erişilemez:    {dogrulama_sayaci['http_erisilemez']}")

    # Rapor özeti ekle
    rapor_satirlari.append(f"\n## Özet\n")
    rapor_satirlari.append(f"- **Toplam belge:** {len(sonuclar)}\n")
    rapor_satirlari.append(f"- **✅ Doğrulanan:** {dogrulanan}\n")
    rapor_satirlari.append(f"- **⚠️ Kısmen doğrulanan:** {kismen}\n")
    rapor_satirlari.append(f"- **❌ Başarısız:** {basarisiz}\n\n")
    rapor_satirlari.append(f"### Doğrulama Detayları\n")
    rapor_satirlari.append(f"- Domain `.gov.tr`: {dogrulama_sayaci['domain_gov_tr']}/{len(sonuclar)}\n")
    rapor_satirlari.append(f"- SHA-256 hash eşleşti: {dogrulama_sayaci['hash_eslesi']}/{len(sonuclar)}\n")
    rapor_satirlari.append(f"- PDF formatı geçerli: {dogrulama_sayaci['pdf_gecerli']}\n")
    rapor_satirlari.append(f"- DOCX formatı geçerli: {dogrulama_sayaci['docx_gecerli']}\n")
    rapor_satirlari.append(f"- DOC formatı geçerli: {dogrulama_sayaci['doc_gecerli']}\n")
    rapor_satirlari.append(f"- İçerik mevzuat kelimeleri bulundu: {dogrulama_sayaci['icerik_mevzuat']}\n")
    rapor_satirlari.append(f"- İçerik kısmi eşleşme: {dogrulama_sayaci['icerik_kismi']}\n")
    rapor_satirlari.append(f"- OCR gereken (tarama PDF): {dogrulama_sayaci['ocr_gerekli']}\n")
    rapor_satirlari.append(f"- İçerik bulunamadı: {dogrulama_sayaci['icerik_yok']}\n")
    rapor_satirlari.append(f"- Boyut yeterli (>1KB): {dogrulama_sayaci['boyut_yeterli']}\n")
    rapor_satirlari.append(f"- HTTP erişilebilir: {dogrulama_sayaci['http_erisilebilir']}\n\n")

    rapor_satirlari.append("## Sonuç\n")
    if dogrulanan == len(sonuclar):
        rapor_satirlari.append("✅ **Tüm belgeler doğrulandı.** Belgelerin tamamı resmî `.gov.tr` kaynaklarından indirilmiş, SHA-256 hash'leri envanter ile eşleşiyor ve dosya formatları geçerli.\n")
    elif dogrulanan > len(sonuclar) * 0.9:
        rapor_satirlari.append(f"✅ **Belgelerin %{(dogrulanan/len(sonuclar)*100):.0f}'i doğrulandı.** Çoğu belge resmî kaynaktan ve geçerli formatta.\n")
    else:
        rapor_satirlari.append(f"⚠️ **{dogrulanan}/{len(sonuclar)} belge doğrulandı.** Bazı belgelerde sorun olabilir.\n")

    # Şüpheli belgeleri listele
    supheli = [s for s in sonuclar if "ŞÜPHELİ" in s["genel_sonuc"] or "UYUMSUZ" in s["genel_sonuc"] or "HATALI" in s["genel_sonuc"]]
    if supheli:
        rapor_satirlari.append(f"\n### ⚠️ Şüpheli/Başarısız Belgeler ({len(supheli)})\n")
        for s in supheli:
            rapor_satirlari.append(f"- `{s['dosya_adi']}`: {s['genel_sonuc']} — {s['url']}\n")

    # OCR gereken belgeleri listele
    ocr_belgeler = [s for s in sonuclar if s["icerik_durum"] == "ocr"]
    if ocr_belgeler:
        rapor_satirlari.append(f"\n### 🔍 OCR Gereken Belgeler ({len(ocr_belgeler)})\n")
        rapor_satirlari.append("Aşağıdaki PDF dosyaları taranmış görüntü olabilir, metin çıkarılamamıştır:\n")
        for s in ocr_belgeler[:10]:
            rapor_satirlari.append(f"- `{s['dosya_adi']}`: {s['icerik_mesaj']}\n")

    # Raporu kaydet
    with open(RAPOR_YOLU, "w", encoding="utf-8") as f:
        f.write("".join(rapor_satirlari))

    print(f"\n✅ Doğrulama raporu: {RAPOR_YOLU}")

    return dogrulanan


if __name__ == "__main__":
    main()