# ============================================================
# ocr_helpers.py — OCR öncesi/sonrası yardımcılar
# ============================================================
"""
Taranan PDF'ler için OCR geçici dosya yönetimi ve hedef dosya
bulma. notebook OCR hücresi ile testler aynı fonksiyonları paylaşır.

Güvenlik: dogrudan_ilgili bir OCR hedefi bulunamazsa süreç durur
(ve bu dosya envantere hiç girmeden kaybolamaz).
"""

import os
from pathlib import Path
from typing import Union

OCR_GECICI_EK = ".ocr_gecici.pdf"
MIN_KARAKTER = 200


class OCRHedefHatasi(RuntimeError):
    """Beklenen OCR hedef dosyası bulunamadı."""


def pdf_metin_uzunlugu(pdf_yolu: Union[str, Path]) -> int:
    """PDF'in tüm sayfalarından çıkarılan toplam metin karakter sayısı."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return 0
    try:
        reader = PdfReader(str(pdf_yolu))
        return sum(len(sayfa.extract_text() or "") for sayfa in reader.pages)
    except Exception:
        return 0


def gecici_temizle(gecici_yolu: Union[str, Path]) -> bool:
    """
    OCR geçici dosyasını varsa siler.

    Dönüş: dosya vardı ve silindiyse True, yoksa False.
    missing_ok=True eşdeğeridir; dosya yoksa hata fırlatmaz.
    """
    yol = Path(gecici_yolu)
    if yol.exists():
        yol.unlink()
        return True
    return False


def hedef_yolu_bul(kaynak_dizini: Union[str, Path], dosya_adi: str) -> Path:
    """
    Kaynak dizininde (alt dizinler dahil) dosyayı arar.

    Dönüş: bulunanan tek dosya yolu.

    Fırlatır:
        OCRHedefHatasi: dosya hiç yoksa
        RuntimeError: aynı isimde birden fazla dosya varsa
    """
    eslesmeler = list(Path(kaynak_dizini).rglob(dosya_adi))
    if not eslesmeler:
        raise OCRHedefHatasi(f"OCR hedef dosyası bulunamadı: {dosya_adi}")
    if len(eslesmeler) > 1:
        raise RuntimeError(
            f"Aynı isimde birden fazla dosya bulundu: {dosya_adi}\n"
            + "\n".join(str(x) for x in eslesmeler)
        )
    return eslesmeler[0]
