# ============================================================
# source_validation.py — Kaynak belge güvenlik kapısı
# ============================================================
"""
Sınıflandırılmış kaynak envanteri ile gerçekten okunan belgeleri
karşılaştırır. dogrudan_ilgili bir belge okunamışsa Runtime hatası
fırlatır; dolayli_ilgili eksikler yalnızca raporlanır.

Hem scripts/build_source_corpus.py hem veri_ayiklama_v4.1.ipynb
aynı dogrulama mantığını kullansın diye burada toplanır.
"""

import csv
import os
from typing import Any, Dict, List, Set

DOGUDAN_ILGILI = "dogrudan_ilgili"
DOLAYLI_ILGILI = "dolayli_ilgili"


class EnvanterHatasi(RuntimeError):
    """Envanter dosyası eksik veya okunamıyor."""


class DogrudanKaynakHatasi(RuntimeError):
    """dogrudan_ilgili bir belge okunamadı."""


def envanter_oku(envanter_yolu: str) -> List[Dict[str, str]]:
    """Sınıflandırılmış envanter CSV'sini kayıt listesi olarak döndürür."""
    if not os.path.exists(envanter_yolu):
        raise EnvanterHatasi(
            f"Sınıflandırılmış envanter bulunamadı: {envanter_yolu}"
        )
    with open(envanter_yolu, "r", encoding="utf-8-sig") as f:
        kayitlar = list(csv.DictReader(f))
    if not kayitlar:
        raise EnvanterHatasi(f"Envanter boş: {envanter_yolu}")
    return kayitlar


def ilgililik_kumeleri(
    kayitlar: List[Dict[str, str]],
) -> Dict[str, Set[str]]:
    """Envanter kayıtlarından {ilgililik: {dosya_adi}} haritası üretir."""
    kumeler: Dict[str, Set[str]] = {}
    for kayit in kayitlar:
        dosya = (kayit.get("dosya_adi") or "").strip()
        ilgililik = (kayit.get("uyds_ilgililik") or "").strip()
        if dosya and ilgililik:
            kumeler.setdefault(ilgililik, set()).add(dosya)
    return kumeler


def okunan_dosya_kumesi(belgeler: List[Dict[str, Any]]) -> Set[str]:
    """Belge listesinden başarıyla okunan benzersiz dosya adlarını döndürür."""
    kume: Set[str] = set()
    for belge in belgeler or []:
        if not isinstance(belge, dict):
            continue
        dosya = belge.get("dosya")
        if dosya:
            kume.add(os.path.basename(str(dosya)))
    return kume


def dogrudan_kaynaklari_dogrula(
    envanter_yolu: str,
    belgeler: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Envanterdeki dogrudan_ilgili belgelerin gerçekten okunup okunmadığını
    doğrular.

    Dönüş:
        {
            "dogrudan_okunamayan": [...],   # sıralı dosya listesi
            "dolayli_okunamayan": [...],    # sıralı dosya listesi
            "toplam_dogrudan": int,
            "toplam_dolayli": int,
        }

    Fırlatır:
        EnvanterHatasi: envanter dosyası yoksa/boşsa
        DogrudanKaynakHatasi: en az bir dogrudan_ilgili belge okunamışsa
    """
    kayitlar = envanter_oku(envanter_yolu)
    kumeler = ilgililik_kumeleri(kayitlar)
    dogrudan = kumeler.get(DOGUDAN_ILGILI, set())
    dolayli = kumeler.get(DOLAYLI_ILGILI, set())
    okunan = okunan_dosya_kumesi(belgeler)

    dogrudan_okunamayan = sorted(dogrudan - okunan)
    dolayli_okunamayan = sorted(dolayli - okunan)

    if dogrudan_okunamayan:
        raise DogrudanKaynakHatasi(
            "Doğrudan ilgili belgeler okunamadı:\n- "
            + "\n- ".join(dogrudan_okunamayan)
        )

    return {
        "dogrudan_okunamayan": dogrudan_okunamayan,
        "dolayli_okunamayan": dolayli_okunamayan,
        "toplam_dogrudan": len(dogrudan),
        "toplam_dolayli": len(dolayli),
    }
