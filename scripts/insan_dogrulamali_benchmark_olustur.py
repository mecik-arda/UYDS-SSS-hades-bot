import json
from pathlib import Path

BENCHMARK_KOKU = Path(__file__).resolve().parent.parent / "testler" / "benchmark"
CIKTI_YOLU = BENCHMARK_KOKU / "insan_dogrulamali_benchmark.json"

kal = json.loads((BENCHMARK_KOKU / "kalibrasyon_seti.json").read_text(encoding="utf-8"))
fin = json.loads((BENCHMARK_KOKU / "final_test_seti.json").read_text(encoding="utf-8"))

sorgular = []
for item in kal["sorgular"] + fin["sorgular"]:
    sorgular.append({
        "id": item.get("id", ""),
        "soru": item["soru"],
        "aday_sss_idler": [item["beklenen_sss_id"]],
        "dogrulama_notu": item.get("dogrulama", {}),
        "insan_onayli_sss_id": None,
        "insan_notu": "",
    })

veri = {
    "aciklama": "Insan dogrulamasi beklenen semantik benchmark seti. aday_sss_idler retrieval tarafindan onerilmistir, otomatik kabul edilmemistir. insan_onayli_sss_id alani insan tarafindan doldurulmalidir.",
    "durum": "KISMI",
    "neden": "Insan dogrulamasi yapilmadan retrieval metrikleri (C-1, C-6) nihai kabul edilemez.",
    "olusturma_tarihi": "2026-08-06",
    "toplam_sorgu": len(sorgular),
    "insan_onayli_sayisi": 0,
    "belirsiz_sorgular": [],
    "sorgular": sorgular,
}

CIKTI_YOLU.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Uretildi: {CIKTI_YOLU} ({len(sorgular)} sorgu, tumu insan_onayli_sss_id=null)")
