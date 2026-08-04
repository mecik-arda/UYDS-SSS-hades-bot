# ============================================================
# v4.1 Document Loader — Çok formatlı belge okuyucu
# ============================================================
"""
PDF, DOCX, TXT, MD, XLSX, CSV, JSON, JSONL formatlarını destekleyen
birleşik belge yükleme modülü.

PDF'ler sayfa sayfa okunur. Her sayfa/belge için metadata çıkarılır.
Desteklenen formatlar:
  - PDF  → sayfa listesi [(sayfa_no, metin)]
  - DOCX → paragraf bazlı tek metin
  - TXT  → ham metin
  - MD   → ham metin (Markdown işaretleme temizlenir)
  - XLSX → hücre tabanlı düz metin
  - CSV  → satır-sütun metin
  - JSON → anahtar-değer düz metin
  - JSONL → satır bazlı JSON
"""

import csv
import json
import os
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# PDF Okuyucu
# ============================================================
def _pdf_oku(dosya_yolu: str) -> List[Tuple[Optional[int], str]]:
    """PDF dosyasını sayfa sayfa okur. [(sayfa_no|None, metin)] döner."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf kurulu değil. `pip install pypdf`")

    reader = PdfReader(dosya_yolu)
    sayfalar = []
    for i, sayfa in enumerate(reader.pages):
        metin = sayfa.extract_text()
        if metin and metin.strip():
            sayfalar.append((i + 1, metin.strip()))
    return sayfalar


# ============================================================
# DOCX Okuyucu
# ============================================================
def _docx_oku(dosya_yolu: str) -> List[Tuple[None, str]]:
    """DOCX dosyasını paragraf bazlı okur."""
    try:
        import docx
    except ImportError:
        raise ImportError("python-docx kurulu değil. `pip install python-docx`")

    doc = docx.Document(dosya_yolu)
    paragraflar = [p.text for p in doc.paragraphs if p.text.strip()]
    if not paragraflar:
        return []
    return [(None, "\n".join(paragraflar))]


# ============================================================
# TXT / MD Okuyucu
# ============================================================
def _txt_oku(dosya_yolu: str) -> List[Tuple[None, str]]:
    """Düz metin/TXT dosyasını okur."""
    with open(dosya_yolu, "r", encoding="utf-8") as f:
        metin = f.read().strip()
    return [(None, metin)] if metin else []


def _md_oku(dosya_yolu: str) -> List[Tuple[None, str]]:
    """
    Markdown dosyasını okur, temel markdown işaretlemelerini temizler.
    Başlıklar ve liste işaretleri korunur, bağlantı/görsel sözdizimi temizlenir.
    """
    import re

    with open(dosya_yolu, "r", encoding="utf-8") as f:
        metin = f.read()

    # Görsel bağlantılarını temizle: ![alt](url)
    metin = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", metin)
    # Linkleri temizle: [text](url) → text
    metin = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", metin)
    # HTML yorumlarını kaldır
    metin = re.sub(r"<!--.*?-->", "", metin, flags=re.DOTALL)
    # Satır içi kod işaretlerini kaldır: `kod`
    metin = re.sub(r"`([^`]+)`", r"\1", metin)
    # Kalın/italik işaretleri
    metin = re.sub(r"\*{1,3}([^\*]+)\*{1,3}", r"\1", metin)
    metin = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", metin)

    metin = metin.strip()
    return [(None, metin)] if metin else []


# ============================================================
# XLSX / CSV Okuyucu
# ============================================================
def _xlsx_oku(dosya_yolu: str) -> List[Tuple[None, str]]:
    """Excel dosyasını hücre bazlı düz metne dönüştürür."""
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl kurulu değil. `pip install openpyxl`")

    wb = openpyxl.load_workbook(dosya_yolu, read_only=True, data_only=True)
    tum_metinler = []
    for sheet_adi in wb.sheetnames:
        ws = wb[sheet_adi]
        satir_metinleri = []
        for row in ws.iter_rows(values_only=True):
            hucreler = [str(c) for c in row if c is not None]
            if hucreler:
                satir_metinleri.append(" | ".join(hucreler))
        if satir_metinleri:
            tum_metinler.append(f"[Sayfa: {sheet_adi}]\n" + "\n".join(satir_metinleri))
    wb.close()
    metin = "\n\n".join(tum_metinleri)
    return [(None, metin)] if metin.strip() else []


def _csv_oku(dosya_yolu: str) -> List[Tuple[None, str]]:
    """CSV dosyasını satır-sütun bazlı okur."""
    with open(dosya_yolu, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        satirlar = [" | ".join(row) for row in reader if any(cell.strip() for cell in row)]
    metin = "\n".join(satirlar)
    return [(None, metin)] if metin.strip() else []


# ============================================================
# JSON / JSONL Okuyucu
# ============================================================
def _json_oku(dosya_yolu: str) -> List[Tuple[None, str]]:
    """JSON dosyasını anahtar-değer bazlı düz metne dönüştürür."""
    with open(dosya_yolu, "r", encoding="utf-8") as f:
        veri = json.load(f)

    def _duzlestir(obj, on_ek=""):
        if isinstance(obj, dict):
            parcalar = []
            for k, v in obj.items():
                parcalar.append(_duzlestir(v, f"{on_ek}{k}: "))
            return "\n".join(parcalar)
        elif isinstance(obj, list):
            parcalar = []
            for i, item in enumerate(obj):
                parcalar.append(_duzlestir(item, f"{on_ek}[{i}] "))
            return "\n".join(parcalar)
        else:
            return f"{on_ek}{obj}"

    metin = _duzlestir(veri)
    return [(None, metin)] if metin.strip() else []


def _jsonl_oku(dosya_yolu: str) -> List[Tuple[None, str]]:
    """JSONL dosyasını satır bazlı okur."""
    satirlar = []
    with open(dosya_yolu, "r", encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if not satir:
                continue
            try:
                obj = json.loads(satir)
                satirlar.append(json.dumps(obj, ensure_ascii=False, indent=1))
            except json.JSONDecodeError:
                satirlar.append(satir)
    metin = "\n".join(satirlar)
    return [(None, metin)] if metin.strip() else []


# ============================================================
# Format → Okuyucu Eşlemesi
# ============================================================
_OKUYUCULAR = {
    ".pdf": _pdf_oku,
    ".docx": _docx_oku,
    ".txt": _txt_oku,
    ".md": _md_oku,
    ".xlsx": _xlsx_oku,
    ".csv": _csv_oku,
    ".json": _json_oku,
    ".jsonl": _jsonl_oku,
}

DESTEKLENEN_FORMATLAR = set(_OKUYUCULAR.keys())


# ============================================================
# Ana API
# ============================================================
def belge_oku(
    dosya_yolu: str,
    meta: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Bir belge dosyasını okur, sayfa sayfa veya bütün olarak döner.

    Dönüş:
        [
          {
            "dosya": "belge.pdf",
            "dosya_yolu": "/tam/yol/belge.pdf",
            "sayfa": 1,                  # PDF için sayfa no, diğer formatlarda None
            "metin": "...",
            "meta": { ... }              # Kullanıcı tarafından verilen meta
          },
          ...
        ]

    Raises:
        ValueError: Desteklenmeyen format
        FileNotFoundError: Dosya bulunamazsa
        ImportError: Gerekli kütüphane eksikse
    """
    if not os.path.isfile(dosya_yolu):
        raise FileNotFoundError(f"Belge bulunamadı: {dosya_yolu}")

    ext = os.path.splitext(dosya_yolu)[1].lower()
    if ext not in _OKUYUCULAR:
        raise ValueError(
            f"Desteklenmeyen format: {ext}. "
            f"Desteklenenler: {sorted(DESTEKLENEN_FORMATLAR)}"
        )

    okuyucu = _OKUYUCULAR[ext]
    try:
        sayfalar = okuyucu(dosya_yolu)
    except Exception as e:
        raise RuntimeError(
            f"Belge okunamadı: {dosya_yolu} ({type(e).__name__}: {e})"
        )

    dosya_adi = os.path.basename(dosya_yolu)
    meta = meta or {}

    sonuc = []
    for sayfa_no, metin in sayfalar:
        if not metin.strip():
            continue
        sonuc.append({
            "dosya": dosya_adi,
            "dosya_yolu": os.path.abspath(dosya_yolu),
            "sayfa": sayfa_no,
            "metin": metin,
            "meta": dict(meta),
        })

    return sonuc


def kaynak_dizinini_tara(kaynak_dizini: str) -> List[str]:
    """
    Kaynak dizinindeki tüm desteklenen belgeleri tarar, dosya yolları listesi döner.
    Alt dizinleri de tarar.
    """
    dosyalar = []
    if not os.path.isdir(kaynak_dizini):
        return dosyalar

    for kok, _, ds in os.walk(kaynak_dizini):
        for d in ds:
            if d.startswith("."):
                continue
            ext = os.path.splitext(d)[1].lower()
            if ext in DESTEKLENEN_FORMATLAR:
                dosyalar.append(os.path.join(kok, d))

    return sorted(dosyalar)


def tum_kaynaklari_yukle(kaynak_dizini: str) -> List[Dict[str, Any]]:
    """
    Kaynak dizinindeki tüm belgeleri okur, birleşik liste döner.

    Her kayıt:
      {
        "dosya": "belge.pdf",
        "dosya_yolu": "/tam/yol",
        "sayfa": 12,
        "metin": "...",
        "meta": {
          "kaynak_tipi": "resmi_kilavuz",  # dizin adından çıkarılır
          "kaynak_dizini": "02_resmi_uyds_kilavuzlari",
        }
      }
    """
    dosyalar = kaynak_dizinini_tara(kaynak_dizini)
    tum_belgeler = []
    for df in dosyalar:
        # Dizin adından kaynak tipi çıkar
        rel_yol = os.path.relpath(df, kaynak_dizini)
        dizin_adi = os.path.dirname(rel_yol).replace(os.sep, "/")
        if dizin_adi in (".", ""):
            dizin_adi = os.path.basename(kaynak_dizini)

        meta = {
            "kaynak_dizini": dizin_adi,
            "kaynak_tipi": _dizinden_tip_cikar(dizin_adi),
        }
        try:
            belgeler = belge_oku(df, meta=meta)
            tum_belgeler.extend(belgeler)
        except Exception as e:
            print(f"   ⚠️ {os.path.basename(df)} okunamadı: {e}")

    return tum_belgeler


def _dizinden_tip_cikar(dizin_adi: str) -> str:
    """Dizin adından kaynak tipi etiketini çıkarır."""
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