# ============================================================
# v4.1 Reporting — Çıktı ve rapor üretimi
# ============================================================
"""
Doğrulama sonuçlarından Excel, JSON ve grafik çıktıları üretir.

Üretilen dosyalar:
  - tum_sonuclar.xlsx (tüm kayıtlar + doğrulama sonuçları)
  - dogrulanan.xlsx (güvenle doğrulanan kayıtlar)
  - supheli.xlsx (şüpheli kayıtlar)
  - islem_hatalari.xlsx (yeniden denemeye rağmen hatalı kalanlar)
  - kaynak_kapsama_raporu.xlsx (modül ve kaynak bazlı kapsama)
  - retrieval_ornekleri.xlsx (örnek RAG eşleşmeleri)
  - ozet.json (sayısal özet)
  - benchmark.json (benchmark sonuçları)
  - grafikler/ (karar dağılımı, güven histogramı)
"""

import json
import os
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ============================================================
# Excel Çıktıları
# ============================================================
def tum_sonuclari_excel_kaydet(
    df,
    tum_sonuclar: List[Dict[str, Any]],
    cikti_dizini: str,
    guven_esik: float = 0.85,
) -> Tuple[Any, Any, Any, int]:
    """
    Sonuçları DataFrame ile birleştirir, sınıflandırılmış Excel çıktıları üretir.

    Returns:
        (cikti_df, dogrulanan_df, supheli_df, hata_sayisi)
    """
    import json
    import pandas as pd

    cikti_df = df.copy()

    # Sonuçları DataFrame'e işle
    for s in tum_sonuclar:
        idx = int(s["_veri_indeksi"])
        cikti_df.at[idx, "_karar"] = s.get("karar", "?")
        cikti_df.at[idx, "_guven"] = s.get("guven", 0)
        cikti_df.at[idx, "_dayanak"] = s.get("dayanak", "")
        cikti_df.at[idx, "_eksik_hata"] = s.get("eksik_veya_hata", "")
        cikti_df.at[idx, "_duzeltilmis"] = s.get("duzeltilmis_cevap", "")
        cikti_df.at[idx, "_islem_hatasi"] = s.get("_islem_hatasi", False)
        cikti_df.at[idx, "_kaynak_dokumanlari"] = s.get("_kaynak_dokumanlari", "")
        cikti_df.at[idx, "_rag_maks_skor"] = s.get("_rag_maks_skor", 0)
        cikti_df.at[idx, "_model"] = s.get("_model", "")
        cikti_df.at[idx, "_prompt_surumu"] = s.get("_prompt_surumu", "")
        cikti_df.at[idx, "_kural_seti_surumu"] = s.get("_kural_seti_surumu", "")
        # Kaynak ID'lerini JSON string olarak yaz
        cikti_df.at[idx, "_kaynak_idleri"] = json.dumps(
            s.get("kaynak_idleri", []), ensure_ascii=False
        )

    # Doğrulanan / Şüpheli ayrımı
    # Kaynaksız "dogru" kararlarını engelle (kaynak_idleri boş değilse)
    dogrulanan_mask = (
        (cikti_df["_karar"] == "dogru")
        & (cikti_df["_guven"] >= guven_esik)
        & (~cikti_df["_islem_hatasi"].fillna(False))
        & (cikti_df["_kaynak_idleri"] != "[]")
    )
    dogrulanan = cikti_df[dogrulanan_mask].copy()
    supheli = cikti_df[~dogrulanan_mask].copy()
    islem_hatalari = cikti_df[cikti_df["_islem_hatasi"].fillna(False)].copy()

    # Excel'e kaydet
    cikti_df.to_excel(
        os.path.join(cikti_dizini, "tum_sonuclar.xlsx"), index=False
    )
    if len(dogrulanan):
        dogrulanan.to_excel(
            os.path.join(cikti_dizini, "dogrulanan.xlsx"), index=False
        )
    if len(supheli):
        supheli.to_excel(
            os.path.join(cikti_dizini, "supheli.xlsx"), index=False
        )
    if len(islem_hatalari):
        islem_hatalari.to_excel(
            os.path.join(cikti_dizini, "islem_hatalari.xlsx"), index=False
        )

    hata_sayisi = int(cikti_df["_islem_hatasi"].sum())
    return cikti_df, dogrulanan, supheli, hata_sayisi


# ============================================================
# Kaynak Kapsama Raporu
# ============================================================
def kaynak_kapsama_raporu(
    cikti_df,
    tum_parcalar: List[Dict[str, Any]],
    cikti_dizini: str,
) -> Dict[str, Any]:
    """
    Modül bazlı ve kaynak bazlı kapsama raporu üretir.

    Returns:
        Kapsama metrikleri sözlüğü
    """
    import pandas as pd

    # Modül başına chunk sayısı
    modul_chunk = Counter()
    for p in tum_parcalar:
        modul = p.get("modul", "bilinmeyen")
        if modul:
            modul_chunk[modul] += 1
        else:
            modul_chunk["bilinmeyen"] += 1

    # Kaynak tipine göre chunk
    tip_chunk = Counter()
    for p in tum_parcalar:
        tip = p.get("kaynak_tipi", "bilinmeyen")
        tip_chunk[tip] += 1

    # Modül başına kanit_yetersiz oranı
    modul_ky = {}
    if "_karar" in cikti_df.columns and "_modul" in cikti_df.columns:
        for modul in cikti_df["_modul"].unique():
            modul_df = cikti_df[cikti_df["_modul"] == modul]
            if len(modul_df) > 0:
                ky_oran = (modul_df["_karar"] == "kanit_yetersiz").mean()
                modul_ky[str(modul)] = round(ky_oran, 3)

    # Kullanılan / kullanılmayan kaynaklar
    kullanilan_chunk_idler = set()
    for _, row in cikti_df.iterrows():
        if row.get("_karar") == "kanit_yetersiz":
            continue
        # Kaynak dokümanları string olarak tutuluyor, chunk_id'leri
        # sonuçlardan çıkarmak mümkün değil - bu nedenle kullanım sayısı
        # retrieval aşamasından hesaplanır

    # Hiç retrieval alamayan soru sayısı
    kaynaksiz = 0
    if "_rag_maks_skor" in cikti_df.columns:
        kaynaksiz = int((cikti_df["_rag_maks_skor"] <= 0).sum())

    rapor = {
        "toplam_kaynak_dosya": len(
            set(p.get("dokuman", "") for p in tum_parcalar)
        ),
        "toplam_chunk": len(tum_parcalar),
        "modul_basina_chunk": dict(modul_chunk.most_common(20)),
        "kaynak_tipine_gore_chunk": dict(tip_chunk),
        "modul_basina_kanit_yetersiz_oran": modul_ky,
        "kaynaksiz_soru_sayisi": kaynaksiz,
    }

    # Excel'e kaydet
    modul_df = pd.DataFrame(
        [
            {"modul": k, "chunk_sayisi": v}
            for k, v in modul_chunk.most_common()
        ]
    )
    modul_df.to_excel(
        os.path.join(cikti_dizini, "kaynak_kapsama_raporu.xlsx"), index=False
    )

    return rapor


# ============================================================
# Özet JSON
# ============================================================
def ozet_json_uret(
    cikti_df,
    dogrulanan,
    supheli,
    hata_sayisi: int,
    cikti_dizini: str,
    ek_bilgiler: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Kapsamlı bir özet JSON dosyası üretir."""
    karar_sayilari = cikti_df["_karar"].value_counts().to_dict()

    gecerli_guven = cikti_df[
        (cikti_df["_guven"] > 0) & (~cikti_df["_islem_hatasi"].fillna(False))
    ]["_guven"]

    ozet = {
        "olusturma_tarihi": datetime.now().isoformat(),
        "toplam_kayit": int(len(cikti_df)),
        "dogrulanan": int(len(dogrulanan)),
        "supheli": int(len(supheli)),
        "islem_hatasi": int(hata_sayisi),
        "karar_dagilimi": {str(k): int(v) for k, v in karar_sayilari.items()},
        "guven_istatistikleri": {
            "ortalama": round(float(gecerli_guven.mean()), 4) if len(gecerli_guven) > 0 else 0,
            "medyan": round(float(gecerli_guven.median()), 4) if len(gecerli_guven) > 0 else 0,
            "min": round(float(gecerli_guven.min()), 4) if len(gecerli_guven) > 0 else 0,
            "maks": round(float(gecerli_guven.max()), 4) if len(gecerli_guven) > 0 else 0,
        },
        **(ek_bilgiler or {}),
    }

    with open(os.path.join(cikti_dizini, "ozet.json"), "w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=2)

    return ozet


# ============================================================
# Grafikler
# ============================================================
def grafik_uret(
    cikti_df,
    cikti_dizini: str,
    guven_esik: float = 0.85,
    grafik_alt_dizin: str = "",
) -> str:
    """Karar dağılımı ve güven histogramı grafiklerini üretir."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("⚠️ matplotlib kurulu değil, grafik atlanıyor.")
        return ""

    grafik_dizini = os.path.join(cikti_dizini, grafik_alt_dizin or "grafikler")
    os.makedirs(grafik_dizini, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    # Pasta grafiği
    karar_sayilari = cikti_df["_karar"].value_counts()
    renkler = {
        "dogru": "#2ecc71",
        "kismen_dogru": "#f1c40f",
        "yanlis": "#e74c3c",
        "kanit_yetersiz": "#95a5a6",
        "soru_belirsiz": "#9b59b6",
        "error": "#c0392b",
        "cevap_bos": "#7f8c8d",
    }
    etiketler = [k for k in karar_sayilari.index]
    degerler = [karar_sayilari[k] for k in etiketler]
    pasta_renkler = [renkler.get(k, "#bdc3c7") for k in etiketler]
    ax1.pie(
        degerler, labels=etiketler, autopct="%1.1f%%",
        colors=pasta_renkler, startangle=90,
    )
    ax1.set_title(f"Karar Dağılımı (n={len(cikti_df)})")

    # Güven histogramı
    gecerli_guven = cikti_df[
        (cikti_df["_guven"] > 0) & (~cikti_df["_islem_hatasi"].fillna(False))
    ]["_guven"]
    if len(gecerli_guven) > 0:
        ax2.hist(gecerli_guven, bins=20, color="#3498db", edgecolor="white")
        ax2.axvline(
            x=guven_esik, color="red", linestyle="--",
            label=f"Eşik: {guven_esik}",
        )
        ax2.set_xlabel("Güven Skoru")
        ax2.set_ylabel("Kayıt Sayısı")
        ax2.set_title(f"Güven Skoru Dağılımı (n={len(gecerli_guven)})")
        ax2.legend()
    else:
        ax2.text(
            0.5, 0.5, "Güven skoru > 0 yok",
            ha="center", va="center", transform=ax2.transAxes,
        )

    plt.tight_layout()
    grafik_yolu = os.path.join(grafik_dizini, "karar_dagilimi.png")
    plt.savefig(grafik_yolu, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"📈 Grafik kaydedildi: {grafik_yolu}")
    return grafik_dizini


# ============================================================
# Benchmark Özeti
# ============================================================
def benchmark_ozeti_uret(
    benchmark_sonuclari: List[Dict[str, Any]],
    cikti_dizini: str,
    gecen_sure: float,
    toplam_kayit: int = 0,
) -> Dict[str, Any]:
    """Benchmark sonuçlarının özetini üretir ve kaydeder."""
    kararlar = [s.get("karar", "?") for s in benchmark_sonuclari]
    guvenler = [
        s.get("guven", 0)
        for s in benchmark_sonuclari
        if s.get("karar") not in ("error", "cevap_bos")
    ]
    islem_hatalari = sum(
        1 for s in benchmark_sonuclari if s.get("_islem_hatasi")
    )

    saniye_basi = gecen_sure / len(benchmark_sonuclari) if benchmark_sonuclari else 0
    tahmini_toplam_dk = (
        (saniye_basi * toplam_kayit) / 60 if toplam_kayit > 0 else 0
    )

    ozet = {
        "test_edilen": len(benchmark_sonuclari),
        "sure_sn": round(gecen_sure, 1),
        "saniye_basi_kayit": round(saniye_basi, 2),
        "tahmini_toplam_dakika": round(tahmini_toplam_dk, 1),
        "karar_dagilimi": dict(Counter(kararlar)),
        "guven_ortalama": round(float(np.mean(guvenler)), 4) if guvenler else 0,
        "guven_medyan": round(float(np.median(guvenler)), 4) if guvenler else 0,
        "islem_hatasi": islem_hatalari,
        "islem_hatasi_oran": (
            round(islem_hatalari / len(benchmark_sonuclari), 4)
            if benchmark_sonuclari
            else 0
        ),
    }

    with open(
        os.path.join(cikti_dizini, "benchmark.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(ozet, f, ensure_ascii=False, indent=2)

    return ozet