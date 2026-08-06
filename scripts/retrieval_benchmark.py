import argparse
import html as html_mod
import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uygulama.cekirdek.veritabani import baglam_yoneticisi


BENCHMARK_KOKU = Path(__file__).resolve().parent.parent / "testler" / "benchmark"
RAPOR_DIZINI = BENCHMARK_KOKU / "raporlar"
SEMANTIK_TEST_YOLU = Path(__file__).resolve().parent.parent / "testler" / "karsilastirma" / "semantik_test_seti.json"

HEDEF_METRIKLER = {
    "top_1_dogruluk": 80.0,
    "top_3_dogruluk": 92.0,
    "kaynaksiz_cevap_orani": 0.0,
    "bilinmeyende_susma_basarisi": 85.0,
    "kaynak_gosterme_orani": 100.0,
}


def _sorulari_veritabanindan_al(orneklem: int = 0) -> list[dict]:
    with baglam_yoneticisi() as baglanti:
        if orneklem > 0:
            satirlar = baglanti.execute(
                """
                SELECT id, kategori, soru, cevap, modul
                FROM sss_kayitlari WHERE durum='aktif'
                ORDER BY id LIMIT ?
                """,
                (orneklem,),
            ).fetchall()
        else:
            satirlar = baglanti.execute(
                """
                SELECT id, kategori, soru, cevap, modul
                FROM sss_kayitlari WHERE durum='aktif'
                ORDER BY id
                """
            ).fetchall()
    return [dict(s) for s in satirlar]


def _semantik_test_setini_yukle() -> list[dict]:
    if not SEMANTIK_TEST_YOLU.is_file():
        return []
    with SEMANTIK_TEST_YOLU.open(encoding="utf-8") as dosya:
        return json.load(dosya)


def _arama_servisini_olustur():
    from uygulama.servisler.arama_servisi import AramaServisi
    from uygulama.servisler.terim_haritasi import TerimHaritasi
    from uygulama.servisler.vektor_servisi import VektorServisi
    from uygulama.servisler.yeniden_siralayici import CrossEncoderYenidenSiralayici

    vektor = VektorServisi()
    terim = TerimHaritasi()
    try:
        yeniden_siralayici = CrossEncoderYenidenSiralayici()
    except Exception:
        yeniden_siralayici = None
    return AramaServisi(vektor, terim, yeniden_siralayici)


def _tek_sorgu_testi(
    servis,
    soru_id: int,
    soru_metni: str,
) -> dict:
    baslangic = time.perf_counter()
    try:
        sonuc = servis.ara(soru_metni)
        gecen_ms = (time.perf_counter() - baslangic) * 1000
    except Exception as hata:
        return {
            "sss_id": soru_id,
            "soru": soru_metni[:200],
            "hata": str(hata)[:200],
            "aday_sayisi": 0,
            "gecen_ms": round((time.perf_counter() - baslangic) * 1000, 2),
            "isabet": False,
            "top_1_id": None,
            "top_3_idleri": [],
            "top_10_idleri": [],
            "maks_rrf": 0.0,
            "guven_skoru": 0.0,
            "yeniden_siralama_etkin": False,
        }
    adaylar = sonuc.adaylar
    aday_idleri = [int(a.sss_id) for a in adaylar[:10] if a.sss_id is not None]
    isabet = soru_id in aday_idleri
    isabet_sirasi = aday_idleri.index(soru_id) + 1 if isabet else 0
    max_rrf = max((a.rrf_skoru for a in adaylar), default=0.0)
    aday_sayisi = len(adaylar)
    guven = min(aday_sayisi / 10.0, 1.0) * 0.6 + min(max_rrf * 0.4, 0.4)
    if sonuc.yeniden_siralama_etkin:
        guven = min(guven * 1.15, 1.0)
    return {
        "sss_id": soru_id,
        "soru": soru_metni[:200],
        "gecen_ms": round(sonuc.gecen_sure_ms, 2),
        "aday_sayisi": aday_sayisi,
        "isabet": isabet,
        "isabet_sirasi": isabet_sirasi,
        "top_1_id": aday_idleri[0] if aday_idleri else None,
        "top_3_idleri": aday_idleri[:3],
        "top_10_idleri": aday_idleri,
        "maks_rrf": round(max_rrf, 4),
        "guven_skoru": round(guven, 4),
        "yeniden_siralama_etkin": sonuc.yeniden_siralama_etkin,
    }


def _semantik_test_calistir(servis, test_senaryolari: list[dict]) -> list[dict]:
    sonuclar = []
    for senaryo in test_senaryolari:
        baslangic = time.perf_counter()
        try:
            sonuc = servis.ara(senaryo["soru"])
            gecen_ms = (time.perf_counter() - baslangic) * 1000
        except Exception as hata:
            sonuclar.append({
                "senaryo_id": senaryo["id"],
                "soru": senaryo["soru"][:200],
                "hata": str(hata)[:200],
                "top_1_id": None,
                "top_3_idleri": [],
                "top_10_idleri": [],
                "beklenen_id": senaryo["beklenen_sss_id"],
                "isabet": False,
                "gecen_ms": round((time.perf_counter() - baslangic) * 1000, 2),
            })
            continue
        aday_idleri = [int(a.sss_id) for a in sonuc.adaylar[:10] if a.sss_id is not None]
        beklenen = senaryo["beklenen_sss_id"]
        isabet = beklenen in aday_idleri
        isabet_sirasi = aday_idleri.index(beklenen) + 1 if isabet else 0
        max_rrf = max((a.rrf_skoru for a in sonuc.adaylar), default=0.0)
        guven = min(len(sonuc.adaylar) / 10.0, 1.0) * 0.6 + min(max_rrf * 0.4, 0.4)
        if sonuc.yeniden_siralama_etkin:
            guven = min(guven * 1.15, 1.0)
        sonuclar.append({
            "senaryo_id": senaryo["id"],
            "soru": senaryo["soru"][:200],
            "top_1_id": aday_idleri[0] if aday_idleri else None,
            "top_3_idleri": aday_idleri[:3],
            "top_10_idleri": aday_idleri,
            "beklenen_id": beklenen,
            "isabet": isabet,
            "isabet_sirasi": isabet_sirasi,
            "gecen_ms": round(gecen_ms, 2),
            "maks_rrf": round(max_rrf, 4),
            "guven_skoru": round(guven, 4),
        })
    return sonuclar


def _metrikleri_hesapla(sonuclar: list[dict], isaretli_sonuclar: list[dict] | None = None) -> dict:
    toplam = len(sonuclar)
    if toplam == 0:
        return {}
    isabetli = [s for s in sonuclar if s.get("isabet")]
    hatali = [s for s in sonuclar if s.get("hata")]
    adayli = [s for s in sonuclar if s.get("aday_sayisi", 0) > 0]
    guven_skorlari = [s.get("guven_skoru", 0) for s in sonuclar if not s.get("hata")]
    gecikmeler = [s.get("gecen_ms", 0) for s in sonuclar if not s.get("hata")]
    top_1 = sum(1 for s in sonuclar if s.get("isabet_sirasi", 0) == 1)
    top_3 = sum(1 for s in sonuclar if 0 < s.get("isabet_sirasi", 0) <= 3)
    ters_siralar = []
    ndcg_degerleri = []
    for s in sonuclar:
        sira = s.get("isabet_sirasi", 0)
        ters_siralar.append(1.0 / sira if sira > 0 else 0.0)
        dcg = 1.0 / math.log2(sira + 1) if sira > 0 else 0.0
        ideal_dcg = 1.0
        ndcg_degerleri.append(dcg / ideal_dcg)
    semantik_metrikleri = {}
    if isaretli_sonuclar:
        s_toplam = len(isaretli_sonuclar)
        s_isabetli = [s for s in isaretli_sonuclar if s.get("isabet")]
        s_top_1 = sum(1 for s in isaretli_sonuclar if s.get("isabet_sirasi", 0) == 1)
        s_top_3 = sum(1 for s in isaretli_sonuclar if 0 < s.get("isabet_sirasi", 0) <= 3)
        s_ters_siralar = []
        for s in isaretli_sonuclar:
            sira = s.get("isabet_sirasi", 0)
            s_ters_siralar.append(1.0 / sira if sira > 0 else 0.0)
        semantik_metrikleri = {
            "semantik_toplam": s_toplam,
            "semantik_isabet": len(s_isabetli),
            "semantik_isabet_orani": round(len(s_isabetli) / s_toplam * 100, 2) if s_toplam else None,
            "semantik_top_1_dogruluk": round(s_top_1 / s_toplam * 100, 2) if s_toplam else None,
            "semantik_top_3_dogruluk": round(s_top_3 / s_toplam * 100, 2) if s_toplam else None,
            "semantik_mrr_10": round(statistics.fmean(s_ters_siralar), 4) if s_ters_siralar else None,
        }
    return {
        "test_edilen_kayit": toplam,
        "hata_sayisi": len(hatali),
        "hata_orani": round(len(hatali) / toplam * 100, 2) if toplam else 0,
        "isabet_sayisi": len(isabetli),
        "aday_bulma_orani": round(len(adayli) / toplam * 100, 2) if toplam else 0,
        "top_1_dogruluk": round(top_1 / toplam * 100, 2) if toplam else 0,
        "top_3_dogruluk": round(top_3 / toplam * 100, 2) if toplam else 0,
        "mrr_10": round(statistics.fmean(ters_siralar), 4) if ters_siralar else 0,
        "ndcg_10": round(statistics.fmean(ndcg_degerleri), 4) if ndcg_degerleri else 0,
        "ortalama_guven": round(statistics.fmean(guven_skorlari), 4) if guven_skorlari else 0,
        "medyan_guven": round(statistics.median(guven_skorlari), 4) if guven_skorlari else 0,
        "ortalama_gecikme_ms": round(statistics.fmean(gecikmeler), 2) if gecikmeler else 0,
        "p50_gecikme_ms": round(_yuzdelik(gecikmeler, 50), 2) if gecikmeler else 0,
        "p95_gecikme_ms": round(_yuzdelik(gecikmeler, 95), 2) if gecikmeler else 0,
        **semantik_metrikleri,
    }


def _yuzdelik(degerler: list[float], yuzdelik: float) -> float:
    if not degerler:
        return 0.0
    sirali = sorted(degerler)
    konum = (yuzdelik / 100.0) * (len(sirali) - 1)
    alt = int(math.floor(konum))
    ust = int(math.ceil(konum))
    if alt == ust:
        return sirali[alt]
    return float(sirali[alt] + (sirali[ust] - sirali[alt]) * (konum - alt))


def _hedef_karsilastirmasi(metrikler: dict) -> list[dict]:
    eslesme = {
        "top_1_dogruluk": "Top-1 dogruluk",
        "top_3_dogruluk": "Top-3 dogruluk",
    }
    satirlar = []
    for anahtar, etiket in eslesme.items():
        deger = metrikler.get(anahtar)
        hedef = HEDEF_METRIKLER.get(anahtar)
        if deger is not None and hedef is not None:
            satirlar.append({
                "metrik": etiket,
                "olculen": deger,
                "hedef": hedef,
                "durum": "GECTI" if deger >= hedef else "BASARISIZ",
            })
    return satirlar


def _html_raporu_olustur(metrikler: dict, sonuclar: list[dict], karsilastirma: list[dict], gecen_sure: float) -> str:
    satirlar_html = []
    for s in sonuclar[:50]:
        isabet_sinifi = "isabetli" if s.get("isabet") else "isabetsiz"
        satirlar_html.append(
            f'<tr class="{isabet_sinifi}">'
            f'<td>{html_mod.escape(str(s.get("sss_id", "?")))}</td>'
            f'<td>{html_mod.escape(str(s.get("soru", ""))[:80])}</td>'
            f'<td>{s.get("isabet_sirasi", "-")}</td>'
            f'<td>{s.get("guven_skoru", 0)}</td>'
            f'<td>{s.get("gecen_ms", 0)}ms</td></tr>'
        )
    karsilastirma_satirlari = ""
    for k in karsilastirma:
        gecti_mi = k["durum"] == "GECTI"
        renk = "#22c55e" if gecti_mi else "#ef4444"
        karsilastirma_satirlari += (
            f'<tr><td>{k["metrik"]}</td>'
            f'<td>{k["olculen"]}</td>'
            f'<td>{k["hedef"]}</td>'
            f'<td style="color:{renk};font-weight:bold">{k["durum"]}</td></tr>'
        )
    zaman = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>Retrieval Benchmark Raporu</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; background: #f8fafc; color: #1e293b; }}
h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
.ozet {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap: 12px; margin: 16px 0; }}
.kart {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; }}
.kart .deger {{ font-size: 1.5rem; font-weight: 700; }}
.kart .etiket {{ font-size: 0.8rem; color: #64748b; }}
table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }}
th, td {{ padding: 8px 12px; text-align: left; font-size: 0.85rem; }}
th {{ background: #f1f5f9; font-weight: 600; }}
tr.isabetli {{ background: #f0fdf4; }}
tr.isabetsiz {{ background: #fef2f2; }}
</style>
</head>
<body>
<h1>Retrieval Benchmark Raporu</h1>
<p>{zaman} | {metrikler.get("test_edilen_kayit", 0)} kayit | {gecen_sure:.1f}s</p>
<div class="ozet">
<div class="kart"><div class="deger">%{metrikler.get("top_1_dogruluk", 0)}</div><div class="etiket">Top-1 Dogruluk</div></div>
<div class="kart"><div class="deger">%{metrikler.get("top_3_dogruluk", 0)}</div><div class="etiket">Top-3 Dogruluk</div></div>
<div class="kart"><div class="deger">{metrikler.get("mrr_10", 0)}</div><div class="etiket">MRR@10</div></div>
<div class="kart"><div class="deger">{metrikler.get("ndcg_10", 0)}</div><div class="etiket">NDCG@10</div></div>
<div class="kart"><div class="deger">%{metrikler.get("aday_bulma_orani", 0)}</div><div class="etiket">Aday Bulma</div></div>
<div class="kart"><div class="deger">{metrikler.get("p95_gecikme_ms", 0)}ms</div><div class="etiket">P95 Gecikme</div></div>
</div>
<h2>Hedef Karsilastirmasi</h2>
<table><tr><th>Metrik</th><th>Olculen</th><th>Hedef</th><th>Durum</th></tr>
{karsilastirma_satirlari}
</table>
<h2>Ilk 50 Kayit</h2>
<table><tr><th>SSS ID</th><th>Soru</th><th>Si ra</th><th>Guven</th><th>Sure</th></tr>
{''.join(satirlar_html)}
</table>
</body></html>"""


def _markdown_raporu_olustur(metrikler: dict, karsilastirma: list[dict], gecen_sure: float, zaman: str) -> str:
    satirlar = []
    satirlar.append("# Retrieval Benchmark Raporu")
    satirlar.append("")
    satirlar.append(f"**Tarih:** {zaman} | **Kayit:** {metrikler.get('test_edilen_kayit', 0)} | **Sure:** {gecen_sure:.1f}s")
    satirlar.append("")
    satirlar.append("## Metrikler")
    satirlar.append("")
    satirlar.append("| Metrik | Olculen |")
    satirlar.append("|---|---|")
    for anahtar, etiket in [
        ("top_1_dogruluk", "Top-1 Dogruluk"),
        ("top_3_dogruluk", "Top-3 Dogruluk"),
        ("mrr_10", "MRR@10"),
        ("ndcg_10", "NDCG@10"),
        ("aday_bulma_orani", "Aday Bulma Orani"),
        ("isabet_sayisi", "Isabet Sayisi"),
        ("ortalama_guven", "Ortalama Guven"),
        ("ortalama_gecikme_ms", "Ortalama Gecikme (ms)"),
        ("p95_gecikme_ms", "P95 Gecikme (ms)"),
        ("hata_sayisi", "Hata Sayisi"),
    ]:
        deger = metrikler.get(anahtar)
        if deger is not None:
            satirlar.append(f"| {etiket} | {deger} |")
    satirlar.append("")
    satirlar.append("## Hedef Karsilastirmasi")
    satirlar.append("")
    satirlar.append("| Metrik | Olculen | Hedef | Durum |")
    satirlar.append("|---|---|---|---|")
    for k in karsilastirma:
        satirlar.append(f'| {k["metrik"]} | %{k["olculen"]} | %{k["hedef"]} | {k["durum"]} |')
    if metrikler.get("semantik_top_1_dogruluk") is not None:
        satirlar.append("")
        satirlar.append("## Semantik Test")
        satirlar.append("")
        satirlar.append(f'- Top-1: %{metrikler["semantik_top_1_dogruluk"]}')
        satirlar.append(f'- Top-3: %{metrikler["semantik_top_3_dogruluk"]}')
        satirlar.append(f'- MRR@10: {metrikler.get("semantik_mrr_10")}')
    return "\n".join(satirlar)


def main() -> None:
    ayrıştırıcı = argparse.ArgumentParser(description="Retrieval benchmark — gercek Excel ile metrik olcumu")
    ayrıştırıcı.add_argument("--orneklem", type=int, default=100, help="Test edilecek kayit sayisi (0=tumu)")
    ayrıştırıcı.add_argument("--cikti", type=str, default=None, help="Rapor cikti dizini")
    ayrıştırıcı.add_argument("--semantik", action="store_true", help="Semantik test setini de calistir")
    ayrıştırıcı.add_argument("--json", action="store_true", help="JSON ciktisi uret")
    argumanlar = ayrıştırıcı.parse_args()
    cikti_dizini = Path(argumanlar.cikti) if argumanlar.cikti else RAPOR_DIZINI
    cikti_dizini.mkdir(parents=True, exist_ok=True)
    sorular = _sorulari_veritabanindan_al(argumanlar.orneklem)
    if not sorular:
        print("Veritabaninda aktif SSS kaydi bulunamadi.")
        return
    print(f"{len(sorular)} kayit yuklendi, arama servisi olusturuluyor...")
    servis = _arama_servisini_olustur()
    print(f"Test basliyor ({len(sorular)} sorgu)...")
    t0 = time.perf_counter()
    sonuclar = []
    for i, s in enumerate(sorular):
        sonuc = _tek_sorgu_testi(servis, s["id"], s["soru"])
        sonuclar.append(sonuc)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(sorular)}")
    gecen = time.perf_counter() - t0
    semantik_sonuclar = None
    if argumanlar.semantik:
        test_seti = _semantik_test_setini_yukle()
        if test_seti:
            print(f"Semantik test seti calistiriliyor ({len(test_seti)} senaryo)...")
            semantik_sonuclar = _semantik_test_calistir(servis, test_seti)
    metrikler = _metrikleri_hesapla(sonuclar, semantik_sonuclar)
    karsilastirma = _hedef_karsilastirmasi(metrikler)
    print(f"\nToplam sure: {gecen:.1f}s ({gecen/len(sonuclar):.3f}s/kayit)")
    for k in karsilastirma:
        print(f"  {k['metrik']}: %{k['olculen']} (hedef: %{k['hedef']}) -> {k['durum']}")
    if metrikler.get("semantik_top_1_dogruluk") is not None:
        print(f"  Semantik Top-1: %{metrikler['semantik_top_1_dogruluk']}")
        print(f"  Semantik Top-3: %{metrikler['semantik_top_3_dogruluk']}")
    zaman_damgasi = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    html = _html_raporu_olustur(metrikler, sonuclar, karsilastirma, gecen)
    html_yolu = cikti_dizini / f"benchmark_{zaman_damgasi}.html"
    html_yolu.write_text(html, encoding="utf-8")
    print(f"HTML rapor: {html_yolu}")
    md = _markdown_raporu_olustur(metrikler, karsilastirma, gecen, zaman_damgasi)
    md_yolu = cikti_dizini / f"benchmark_{zaman_damgasi}.md"
    md_yolu.write_text(md, encoding="utf-8")
    print(f"Markdown rapor: {md_yolu}")
    if argumanlar.json:
        json_yolu = cikti_dizini / f"benchmark_{zaman_damgasi}.json"
        json_yolu.write_text(json.dumps({
            "metrikler": metrikler,
            "karsilastirma": karsilastirma,
            "orneklem": len(sonuclar),
            "gecen_sure_sn": round(gecen, 2),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON rapor: {json_yolu}")


if __name__ == "__main__":
    main()
