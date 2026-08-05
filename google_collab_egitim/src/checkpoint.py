# ============================================================
# v4.1 Checkpoint — JSONL tabanlı sonuç kalıcılığı
# ============================================================
"""
Çalışma sonuçlarını JSONL formatında kaydeder,
_hash doğrulama ile checkpoint geçerliliğini kontrol eder,
yarım kalmış işlemi eksik kayıtlardan devam ettirir.

Özellikler:
  - sonuc_haritasi: _kayit_no → sonuç eşlemesi
  - _islem_hatasi = True olanlar eksik sayılır, tekrar denenir
  - Mükerrer _kayit_no için uyarı + son geçerliyi kullan
  - Benchmark ve ana doğrulama checkpoint'leri ayrı yönetilir
"""

import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple


# ============================================================
# Ana Checkpoint API
# ============================================================
def checkpoint_yukle(
    sonuc_dosyasi: str,
    meta_dosyasi: str,
    beklenen_meta: Dict[str, Any],
) -> Tuple[Dict[int, Dict[str, Any]], bool]:
    """
    Checkpoint dosyalarını yükler, meta uyumluluğunu kontrol eder.

    Args:
        sonuc_dosyasi: dogrulama_sonuclari.jsonl yolu
        meta_dosyasi: meta.json yolu
        beklenen_meta: Beklenen meta alanları (excel_hash, kaynak_dizin_hash, vs.)

    Returns:
        (sonuc_haritasi, gecerli_mi):
          - sonuc_haritasi: {_kayit_no: sonuc_dict}
          - gecerli_mi: Meta uyuşuyorsa True, değilse False (eski sonuçlar silinir)
    """
    sonuc_haritasi: Dict[int, Dict[str, Any]] = {}

    if not os.path.exists(meta_dosyasi) or not os.path.exists(sonuc_dosyasi):
        return sonuc_haritasi, False

    # Meta kontrolü
    try:
        with open(meta_dosyasi, "r", encoding="utf-8") as f:
            mevcut_meta = json.load(f)

        farklar = []
        for anahtar, beklenen_deger in beklenen_meta.items():
            mevcut_deger = mevcut_meta.get(anahtar)
            if mevcut_deger != beklenen_deger:
                farklar.append(anahtar)

        if farklar:
            print(f"\n⚠️ Checkpoint geçersiz ({', '.join(farklar)}). Sıfırdan başlanacak.")
            if os.path.exists(sonuc_dosyasi):
                os.remove(sonuc_dosyasi)
            return sonuc_haritasi, False

    except Exception as e:
        print(f"⚠️ Checkpoint meta okunamadı: {e}")
        return sonuc_haritasi, False

    # Sonuçları yükle
    yuklenen = 0
    mukerer = 0
    with open(sonuc_dosyasi, "r", encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if not satir:
                continue
            try:
                sonuc = json.loads(satir)
                kayit_no = int(sonuc["_kayit_no"])
                if kayit_no in sonuc_haritasi:
                    mukerer += 1
                    # Son geçerliyi kullan (append modunda yazıldığı için en son iyidir)
                sonuc_haritasi[kayit_no] = sonuc
                yuklenen += 1
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    if mukerer:
        print(f"   ⚠️ {mukerer} mükerrer _kayit_no tespit edildi (son geçerli kullanıldı).")
    print(f"🔄 Checkpoint'ten {yuklenen} sonuç yüklendi.")
    return sonuc_haritasi, True


def checkpoint_kaydet(
    meta_dosyasi: str,
    meta: Dict[str, Any],
) -> None:
    """Checkpoint meta dosyasını günceller."""
    os.makedirs(os.path.dirname(meta_dosyasi), exist_ok=True)
    with open(meta_dosyasi, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def sonuc_ekle(
    dosya: Any,  # Dosya handle veya yol
    sonuc: Dict[str, Any],
) -> None:
    """Bir sonucu JSONL dosyasına append eder."""
    satir = json.dumps(sonuc, ensure_ascii=False)
    if isinstance(dosya, str):
        with open(dosya, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    else:
        dosya.write(satir + "\n")


# ============================================================
# Eksik Kayıt Yönetimi
# ============================================================
def eksik_kayitlari_bul(
    sonuc_haritasi: Dict[int, Dict[str, Any]],
    toplam_kayit: int,
    benchmark_kayit: int = 0,
) -> Tuple[Set[int], Set[int], List[int]]:
    """
    Tamamlanan, hatalı ve eksik kayıt numaralarını belirler.

    Args:
        sonuc_haritasi: {_kayit_no: sonuc} haritası
        toplam_kayit: Toplam kayıt sayısı
        benchmark_kayit: Benchmark kapsamındaki kayıt sayısı

    Returns:
        (tamamlanan_nolar, islem_hatasi_nolar, eksik_nolar)
          - tamamlanan_nolar: Başarıyla tamamlanan kayıt numaraları
          - islem_hatasi_nolar: _islem_hatasi=True olanlar (tekrar denenecek)
          - eksik_nolar: Hiç sonucu olmayan kayıt numaraları (sıralı liste)
    """
    tamamlanan = set()
    hatali = set()

    for kayit_no, s in sonuc_haritasi.items():
        if s.get("_islem_hatasi"):
            hatali.add(kayit_no)
        elif s.get("karar") not in ("error",):
            tamamlanan.add(kayit_no)

    # Hatalıları haritadan çıkar (tekrar denenecek)
    for no in hatali:
        if no in sonuc_haritasi:
            del sonuc_haritasi[no]

    # Eksik = hiç sonucu olmayan veya benchmark dışı kalan
    eksik = sorted([
        i for i in range(toplam_kayit)
        if i not in tamamlanan
    ])

    # Benchmark kayıtları tamamlanan sayılır (onlar ayrı checkpoint'te)
    # Benchmark sonuçları sonuc_haritasi'na zaten eklendi

    return tamamlanan, hatali, eksik


# ============================================================
# Sonuç Bütünlük Kontrolü
# ============================================================
def butunluk_kontrolu(
    sonuc_haritasi: Dict[int, Dict[str, Any]],
    toplam_kayit: int,
) -> List[int]:
    """
    Tüm kayıtların işlendiğini doğrular.
    Eksik varsa liste döner, yoksa boş liste.

    Eksik kalan kayıt varsa RuntimeError fırlatılması önerilir.
    """
    eksik = []
    for i in range(toplam_kayit):
        if i not in sonuc_haritasi:
            eksik.append(i)
    return eksik


# ============================================================
# Benchmark Checkpoint
# ============================================================
def benchmark_meta_olustur(
    excel_hash: str,
    kaynak_dizin_hash: str,
    model: str,
    embedding_model: str,
    prompt_surumu: str,
    kural_seti_surumu: str,
    config_hash: str,
) -> Dict[str, Any]:
    """Benchmark checkpoint meta sözlüğü oluşturur."""
    return {
        "excel_hash": excel_hash,
        "kaynak_dizin_hash": kaynak_dizin_hash,
        "model": model,
        "embedding_model": embedding_model,
        "prompt_surumu": prompt_surumu,
        "kural_seti_surumu": kural_seti_surumu,
        "config_hash": config_hash,
    }


def benchmark_checkpoint_kontrol(
    benchmark_meta_yolu: str,
    benchmark_sonuc_yolu: str,
    beklenen_meta: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Benchmark checkpoint'ini kontrol eder, geçerliyse sonuçları yükler.

    Returns:
        (benchmark_sonuclari, gecerli_mi)
    """
    if not os.path.exists(benchmark_meta_yolu) or not os.path.exists(benchmark_sonuc_yolu):
        return [], False

    try:
        with open(benchmark_meta_yolu, "r", encoding="utf-8") as f:
            mevcut_meta = json.load(f)

        for anahtar, deger in beklenen_meta.items():
            if mevcut_meta.get(anahtar) != deger:
                return [], False

        sonuclar = []
        with open(benchmark_sonuc_yolu, "r", encoding="utf-8") as f:
            for satir in f:
                if satir.strip():
                    try:
                        sonuclar.append(json.loads(satir))
                    except json.JSONDecodeError:
                        pass
        print(f"🔄 Uyumlu benchmark checkpoint bulundu ({len(sonuclar)} sonuç).")
        return sonuclar, True
    except Exception:
        return [], False