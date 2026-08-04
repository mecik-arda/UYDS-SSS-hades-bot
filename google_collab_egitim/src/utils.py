# ============================================================
# v4.1 Utilities — Genel yardımcı fonksiyonlar
# ============================================================
"""Metin temizleme, hash hesaplama ve genel yardımcı fonksiyonlar."""

import hashlib
import json
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional


# ============================================================
# Metin Temizleme
# ============================================================
def metin_temizle(metin: str) -> str:
    """Metni normalize eder, fazla boşlukları temizler."""
    if not isinstance(metin, str):
        return ""
    # Unicode normalize (NFKC)
    metin = unicodedata.normalize("NFKC", metin)
    # Satır başı/sonu boşlukları
    metin = metin.strip()
    # 3'ten fazla satır atlamasını 2'ye indir
    metin = re.sub(r"\n{3,}", "\n\n", metin)
    # Gereksiz boşlukları temizle
    metin = re.sub(r"[ \t]+", " ", metin)
    return metin


def guvenli_str(deger: Any, varsayilan: str = "") -> str:
    """Herhangi bir değeri güvenli string'e çevirir."""
    if deger is None:
        return varsayilan
    if isinstance(deger, float) and (deger != deger):  # NaN kontrolü
        return varsayilan
    if isinstance(deger, (int, float)):
        if deger == int(deger):
            return str(int(deger))
        return str(deger)
    return str(deger).strip()


def adi_normalize_et(ad: str) -> str:
    """Sütun adını karşılaştırma için normalize eder."""
    if not isinstance(ad, str):
        return ""
    ad = unicodedata.normalize("NFKC", ad).casefold()
    ad = ad.replace("ı", "i")
    ad = unicodedata.normalize("NFKD", ad)
    ad = "".join(
        karakter for karakter in ad if not unicodedata.combining(karakter)
    )
    return ad.strip()


# ============================================================
# JSON Yardımcıları
# ============================================================
def json_guvenli_yukle(metin: str) -> Optional[Dict]:
    """JSON metnini güvenli şekilde parse eder. Başarısızsa None döner."""
    if not isinstance(metin, str) or not metin.strip():
        return None

    metin = metin.strip()
    # Markdown kod bloğu temizleme
    metin = re.sub(r"```(?:json)?\s*", "", metin).replace("```", "").strip()

    # JSON başlangıç/bitiş bul
    basla = metin.find("{")
    bitir = metin.rfind("}")
    if basla >= 0 and bitir > basla:
        metin = metin[basla : bitir + 1]

    try:
        return json.loads(metin)
    except json.JSONDecodeError:
        return None


# ============================================================
# Hash Yardımcıları
# ============================================================
def kisa_hash(veri: Any, uzunluk: int = 16) -> str:
    """Herhangi bir veriden kısa hash üretir."""
    if isinstance(veri, dict):
        veri = json.dumps(veri, sort_keys=True)
    elif not isinstance(veri, (str, bytes)):
        veri = str(veri)
    if isinstance(veri, str):
        veri = veri.encode("utf-8")
    return hashlib.sha256(veri).hexdigest()[:uzunluk]


def checkpoint_kimligi(
    excel_hash: str,
    kaynak_hash: str,
    config_hash: str,
    model: str,
    embedding: str,
    prompt_surumu: str,
    kural_surumu: str,
    chunk_algo: str,
    retrieval_algo: str,
) -> str:
    """Tüm checkpoint bileşenlerinden birleşik kimlik üretir."""
    bilesenler = f"{excel_hash}|{kaynak_hash}|{config_hash}|{model}|{embedding}|{prompt_surumu}|{kural_surumu}|{chunk_algo}|{retrieval_algo}"
    return kisa_hash(bilesenler, 32)


# ============================================================
# Zamanlayıcı
# ============================================================
import time


class Zamanlayici:
    """Basit bir işlem süresi ölçer."""

    def __init__(self):
        self.baslangic = time.time()
        self.kontrol_noktalari = []

    def gecen(self) -> float:
        """Başlangıçtan bu yana geçen süre (saniye)."""
        return time.time() - self.baslangic

    def kontrol(self, etiket: str = "") -> float:
        """Bir kontrol noktası ekle, geçen süreyi döndür."""
        suan = time.time()
        gecen = suan - self.baslangic
        self.kontrol_noktalari.append((etiket, gecen))
        return gecen

    def ozet(self) -> str:
        """Tüm kontrol noktalarının özeti."""
        if not self.kontrol_noktalari:
            return f"Toplam: {self.gecen():.1f}s"
        satirlar = []
        for i, (etiket, gecen) in enumerate(self.kontrol_noktalari):
            satirlar.append(f"  [{i}] {etiket}: {gecen:.1f}s")
        satirlar.append(f"  Toplam: {self.gecen():.1f}s")
        return "\n".join(satirlar)


# ============================================================
# Dict/Dizi Yardımcıları
# ============================================================
def dict_varsayilan(d: Dict, anahtar: str, varsayilan: Any = None) -> Any:
    """Sözlükten güvenli değer okuma."""
    return d.get(anahtar, varsayilan)


def dict_guncelle_derin(hedef: Dict, kaynak: Dict) -> Dict:
    """İç içe sözlükleri derinlemesine günceller."""
    for k, v in kaynak.items():
        if k in hedef and isinstance(hedef[k], dict) and isinstance(v, dict):
            dict_guncelle_derin(hedef[k], v)
        else:
            hedef[k] = v
    return hedef


def benzersiz_sirali(dizi: List[Any]) -> List[Any]:
    """Listedeki benzersiz öğeleri sıralı döndürür."""
    return sorted(set(dizi))


# ============================================================
# GPU Bellek Yardımcısı
# ============================================================
def gpu_bellek_durumu() -> Optional[Dict[str, float]]:
    """GPU bellek durumunu döndürür (GPU yoksa None)."""
    try:
        import torch
        if not torch.cuda.is_available():
            return None
        return {
            "ayrilan_gb": torch.cuda.memory_allocated() / 1e9,
            "rezerve_gb": torch.cuda.memory_reserved() / 1e9,
            "toplam_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
            "bos_gb": (
                torch.cuda.get_device_properties(0).total_memory
                - torch.cuda.memory_allocated()
            )
            / 1e9,
        }
    except Exception:
        return None


def gpu_onbellek_temizle() -> None:
    """GPU belleğini boşaltmaya çalışır."""
    import gc
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass