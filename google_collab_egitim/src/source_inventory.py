# ============================================================
# v4.1 Source Inventory — Kaynak Envanteri Yönetimi
# ============================================================
"""
Kaynak belgelerin envanterini oluşturur, SHA-256 hash hesaplar,
tekrarları tespit eder, kaynak_envanteri.csv üretir.

NOT: Envanter CSV'si kaynak dizini DIŞINA (data/output_v4/) yazılır,
böylece RAG tarafından kaynak belge olarak taranmaz.
"""

import csv
import hashlib
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

# Kendi modüllerimizden import
try:
    from .document_loader import kaynak_dizinini_tara, DESTEKLENEN_FORMATLAR
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from src.document_loader import kaynak_dizinini_tara, DESTEKLENEN_FORMATLAR  # noqa

# ============================================================
# Sabitler
# ============================================================
ENVANTER_DOSYASI = "kaynak_envanteri.csv"
ENVANTER_ALANLARI = [
    "kaynak_id",
    "dosya_yolu",
    "dosya_adi",
    "baslik",
    "kaynak_tipi",
    "guven_sinifi",
    "kurum",
    "domain",
    "kaynak_url",
    "modul",
    "alt_konu",
    "yayin_tarihi",
    "gecerlilik_baslangici",
    "gecerlilik_bitis",
    "surum",
    "resmiyet_seviyesi",
    "sha256",
    "dosya_boyutu",
    "durum",
    "not",
]

# Envanter kendisi kaynak olarak taranmasın diye hariç tutulan dosyalar
URETILEN_DOSYALAR = {
    "kaynak_envanteri.csv",
    ".gitkeep",
}


# ============================================================
# Hash Hesaplama
# ============================================================
def sha256_dosya(dosya_yolu: str) -> str:
    """Dosyanın SHA-256 hash'ini hesaplar."""
    h = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


# ============================================================
# Tarih Çıkarma
# ============================================================
_TARIH_KALIPLARI = [
    re.compile(r"(\d{4})[-/](\d{2})[-/](\d{2})"),
    re.compile(r"(\d{1,2})[./\s](Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)[.\s](\d{4})", re.IGNORECASE),
    re.compile(r"(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(\d{4})", re.IGNORECASE),
]

_AY_HARITASI = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}


def _metinden_tarih_cikar(metin: str) -> Optional[str]:
    if not metin:
        return None
    for kalip in _TARIH_KALIPLARI:
        eslesme = kalip.search(metin)
        if eslesme:
            gruplar = eslesme.groups()
            if len(gruplar) == 3:
                if gruplar[0].isdigit() and len(gruplar[0]) == 4:
                    yil, ay, gun = int(gruplar[0]), _ay_cevir(gruplar[1]), int(gruplar[2])
                else:
                    gun, ay, yil = int(gruplar[0]), _ay_cevir(gruplar[1]), int(gruplar[2])
                try:
                    return f"{yil:04d}-{ay:02d}-{gun:02d}"
                except (ValueError, TypeError):
                    continue
            elif len(gruplar) == 2:
                ay = _ay_cevir(gruplar[0])
                yil = int(gruplar[1])
                return f"{yil:04d}-{ay:02d}-01"
    return None


def _ay_cevir(ay_metni: str) -> int:
    if ay_metni.isdigit():
        return int(ay_metni)
    return _AY_HARITASI.get(ay_metni.lower(), 1)


def _kaynak_id_ata(sira: int) -> str:
    return f"SRC-{sira:05d}"


_SURUM_KALIPLARI = [
    re.compile(r"[vV](\d+[\.\d]*)"),
    re.compile(r"sürüm\s*[:#]?\s*(\d+[\.\d]*)", re.IGNORECASE),
    re.compile(r"versiyon\s*[:#]?\s*(\d+[\.\d]*)", re.IGNORECASE),
    re.compile(r"version\s*[:#]?\s*(\d+[\.\d]*)", re.IGNORECASE),
]


def _metinden_surum_cikar(metin: str) -> str:
    if not metin:
        return ""
    for kalip in _SURUM_KALIPLARI:
        eslesme = kalip.search(metin)
        if eslesme:
            return eslesme.group(1)
    return ""


_KAYNAK_TIPI_RESMIYET = {
    "mevzuat": "resmi",
    "resmi_kilavuz": "resmi",
    "modul_dokumani": "resmi",
    "teknik_cozum": "kurum_ici",
    "onayli_destek": "uzman_onayli",
    "surum_notu": "resmi",
    "bilinmeyen": "belirsiz",
}


def _dizinden_tip_cikar(dizin_adi: str) -> str:
    tip_haritasi = {
        "01_mevzuat": "mevzuat",
        "02_resmi_uyds_kilavuzlari": "resmi_kilavuz",
        "03_modul_dokumanlari": "modul_dokumani",
        "04_teknik_cozumler": "teknik_cozum",
        "05_onayli_destek_kayitlari": "onayli_destek",
        "06_surum_notlari": "surum_notu",
    }
    for anahtar, tip in tip_haritasi.items():
        if anahtar in dizin_adi:
            return tip
    return "bilinmeyen"


# ============================================================
# Başlık Çıkarma (Dosya Adından)
# ============================================================
def _dosya_adindan_baslik(dosya_adi: str) -> str:
    ad = os.path.splitext(dosya_adi)[0]
    ad = re.sub(r"[_\-]+", " ", ad)
    ad = re.sub(r"\s+", " ", ad).strip()
    if not ad:
        return dosya_adi
    return ad[0].upper() + ad[1:] if len(ad) > 1 else ad.upper()


# ============================================================
# Mevcut Envanter Yükleme (Merge için)
# ============================================================
_METADATA_ALANLARI = [
    "baslik", "guven_sinifi", "kurum", "domain",
    "kaynak_url", "modul", "alt_konu", "durum", "not",
]


def _mevcut_envanteri_yukle(yol: str) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
    sha256_harita = {}
    ad_harita = {}
    if not yol or not os.path.exists(yol):
        return sha256_harita, ad_harita
    with open(yol, "r", encoding="utf-8-sig") as f:
        for kayit in csv.DictReader(f):
            sha = kayit.get("sha256", "")
            ad = kayit.get("dosya_adi", "")
            if sha:
                sha256_harita[sha] = kayit
            if ad:
                ad_harita[ad] = kayit
    return sha256_harita, ad_harita


# ============================================================
# Ana Envanter Oluşturma
# ============================================================
def envanter_olustur(
    kaynak_dizini: str,
    cikti_yolu: Optional[str] = None,
    mevcut_envanter_yolu: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Kaynak dizinini tarar, her dosya için envanter kaydı oluşturur.

    mevcut_envanter_yolu verilirse SHA-256 ve dosya adı üzerinden
    merge yapılır: eski kayıtlardaki baslik, guven_sinifi, kurum,
    domain, kaynak_url, modul, alt_konu gibi zengin metadata korunur.
    """
    sha256_harita, ad_harita = _mevcut_envanteri_yukle(mevcut_envanter_yolu)
    if sha256_harita:
        print(f"   [MERGE] Mevcut envanter yüklendi: {len(sha256_harita)} kayıt")

    dosyalar = kaynak_dizinini_tara(kaynak_dizini)
    if not dosyalar:
        print("⚠️ Hiç kaynak belge bulunamadı.")
        return []

    kayitlar = []
    gorulen_hashler = {}
    korunan_meta = 0
    yeni_kayit = 0

    for i, df in enumerate(dosyalar, start=1):
        dosya_adi = os.path.basename(df)

        if dosya_adi in URETILEN_DOSYALAR:
            continue

        try:
            dosya_hash = sha256_dosya(df)
        except Exception as e:
            print(f"   ⚠️ Hash alınamadı: {dosya_adi} ({e})")
            continue

        dosya_boyut = os.path.getsize(df)
        rel_yol = os.path.relpath(df, kaynak_dizini)
        dizin_adi = os.path.dirname(rel_yol).replace(os.sep, "/")
        if dizin_adi in (".", ""):
            dizin_adi = os.path.basename(kaynak_dizini)

        kaynak_tipi = _dizinden_tip_cikar(dizin_adi)
        resmiyet = _KAYNAK_TIPI_RESMIYET.get(kaynak_tipi, "belirsiz")

        metin_ornek = ""
        try:
            with open(df, "r", encoding="utf-8", errors="replace") as f:
                metin_ornek = f.read(10240)
        except Exception:
            try:
                from pypdf import PdfReader
                reader = PdfReader(df)
                if reader.pages:
                    metin_ornek = reader.pages[0].extract_text() or ""
            except Exception:
                pass

        tarih = _metinden_tarih_cikar(metin_ornek)
        surum = _metinden_surum_cikar(metin_ornek)
        baslik = _dosya_adindan_baslik(dosya_adi)

        durum = "aktif"
        if tarih:
            try:
                t = datetime.strptime(tarih, "%Y-%m-%d")
                yil_farki = datetime.now().year - t.year
                if yil_farki > 10:
                    durum = "eski"
                elif yil_farki > 5:
                    durum = "belirsiz"
            except ValueError:
                durum = "belirsiz"
        else:
            durum = "belirsiz"

        kaynak_id = _kaynak_id_ata(i)
        kopya_mi = False
        if dosya_hash in gorulen_hashler:
            kaynak_id = gorulen_hashler[dosya_hash]
            durum = "kopya"
            kopya_mi = True

        if not kopya_mi:
            gorulen_hashler[dosya_hash] = kaynak_id

        not_metni = f"Kopya — orijinal: {gorulen_hashler[dosya_hash]}" if kopya_mi else ""

        kayit = {
            "kaynak_id": kaynak_id,
            "dosya_yolu": rel_yol,
            "dosya_adi": dosya_adi,
            "baslik": baslik,
            "kaynak_tipi": kaynak_tipi,
            "guven_sinifi": "",
            "kurum": "",
            "domain": "",
            "kaynak_url": "",
            "modul": "",
            "alt_konu": "",
            "yayin_tarihi": tarih or "",
            "gecerlilik_baslangici": tarih or "",
            "gecerlilik_bitis": "",
            "surum": surum,
            "resmiyet_seviyesi": resmiyet,
            "sha256": dosya_hash,
            "dosya_boyutu": str(dosya_boyut),
            "durum": durum,
            "not": not_metni,
        }

        mevcut = sha256_harita.get(dosya_hash) or ad_harita.get(dosya_adi)
        if mevcut and not kopya_mi:
            for alan in _METADATA_ALANLARI:
                deger = mevcut.get(alan, "")
                if deger:
                    kayit[alan] = deger
            korunan_meta += 1
        elif not kopya_mi:
            yeni_kayit += 1

        kayitlar.append(kayit)

    if mevcut_envanter_yolu and sha256_harita:
        print(f"   [KORUNDU] Metadata: {korunan_meta} kayıt")
        if yeni_kayit:
            print(f"   [YENI] Yeni kayıt: {yeni_kayit} (metadata manuel doldurulmalı)")

    if cikti_yolu and kayitlar:
        os.makedirs(os.path.dirname(cikti_yolu), exist_ok=True)
        with open(cikti_yolu, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=ENVANTER_ALANLARI)
            writer.writeheader()
            writer.writerows(kayitlar)
        print(f"[ENVANTER] Kaynak envanteri: {cikti_yolu} ({len(kayitlar)} kayıt)")

    return kayitlar


def envanter_ozeti(kayitlar: List[Dict[str, str]]) -> Dict[str, Any]:
    if not kayitlar:
        return {"toplam_kaynak": 0}

    tipler = {}
    durumlar = {}
    kopyalar = 0
    eski = 0
    belirsiz = 0

    for k in kayitlar:
        tip = k["kaynak_tipi"]
        tipler[tip] = tipler.get(tip, 0) + 1
        durum = k["durum"]
        durumlar[durum] = durumlar.get(durum, 0) + 1
        if durum == "kopya":
            kopyalar += 1
        elif durum == "eski":
            eski += 1
        elif durum == "belirsiz":
            belirsiz += 1

    return {
        "toplam_kaynak": len(kayitlar),
        "benzersiz_kaynak": len(kayitlar) - kopyalar,
        "kopya": kopyalar,
        "eski": eski,
        "belirsiz": belirsiz,
        "tiplere_gore": tipler,
        "durumlara_gore": durumlar,
    }