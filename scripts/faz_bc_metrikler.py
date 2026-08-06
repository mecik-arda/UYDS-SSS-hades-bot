import asyncio
import hashlib
import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.servisler.deepseek_servisi import PROMPT_SURUMU

BENCHMARK_KOKU = Path(__file__).resolve().parent.parent / "testler" / "benchmark"
RAPOR_DIZINI = BENCHMARK_KOKU / "raporlar"
KALIBRASYON_YOLU = BENCHMARK_KOKU / "kalibrasyon_seti.json"
FINAL_YOLU = BENCHMARK_KOKU / "final_test_seti.json"
ESIK_TARAMA_JSON = RAPOR_DIZINI / "esik_taramasi.json"
METRIK_RAPORU_JSON = RAPOR_DIZINI / "metrik_raporu.json"
METRIK_RAPORU_MD = RAPOR_DIZINI / "metrik_raporu.md"
METRIK_RAPORU_HTML = RAPOR_DIZINI / "metrik_raporu.html"

BILINMEYEN_SORULAR = [
    "Mars yuzeyinde tarim yapmak icin hangi gubre kullanilir",
    "Kuantum bilgisayarda Python kodumu nasil debug ederim",
    "Fuzelerde yakit olarak zeytinyagi kullanilir mi",
    "1842 Londra kopru ihalesi sartnamesi nedir",
    "Transistorun icinde kaybolan elektron nasil bulunur",
    "Mikroservis mimaride pasta tarifi nasil yazilir",
    "Plastik cerrahide yapay zeka ile dogal secilim iliskisi",
    "Otoyol projesinde toprak kaymasi raporu nasil hazirlanir",
    "Eski Misir'da hiyeroglif ile fatura kesme yontemi",
    "Denizaltida wifi sinyali nasil guclendirilir",
    "Sut urunleri uretiminde blockchain kullanimi zorunlu mu",
    "Gemide calisan yazilimcilar icin is hukuku maddeleri",
    "Kaplumbaga bakiminda ag tikisikligi sorunu cozumu",
    "Ruzgar turbini kanatlarinda buzlanma onleme teknigi",
    "Jenerator yagi degisiminde kac numara zimpara kullanilir",
    "Muhasebe kaydinda Picasso tablosu nasil amortisman ayirilir",
    "Apartman yonetiminde drone ile baca temizligi yonetmeligi",
    "Sera gazlarinin muhasebe kaydinda kdv orani kactir",
    "Yeni dogan bebeklerde kripto para vergilendirmesi",
    "Gunes tutulmasi sirasinda enerji santrali bakim formu",
    "Antarktika seferi icin personel maas bordrosu nasil hazirlanir",
    "Okul kantininde acilan tezgah icin ruhsat nereden alinir",
    "Kedi mamasi iceriginde gluten tespiti icin hangi laboratuvar",
    "Otomatik portakal sikma makinasi bakim sozlesmesi",
    "Halida leke cikarma kimyasallarinin ithalat mevzuati",
    "Dijital piyano akordu icin ses frekansi analizi",
    "Vinil plak temizleme solusyonu uretim ruhsati",
    "Cimento fabrikasi atik su aritma tesisinde balik olur mu",
    "Elektrikli scooter bataryasi geri donusum kriterleri",
    "Fotograf makinesi lens temizliginde hangi bez kullanilmali",
    "Uzay istasyonunda gorevli astronotlarin yillik izin hakki",
    "Spor salonunda kullanilan matlarin antibakteriyel standardi",
    "Telefon kulubesinden yapilan aramalarin kayit suresi",
    "Bisiklet yolu cizgisinde kullanilan boyanin parlama katsayisi",
    "Yagmur suyu hasadi sisteminde filtre degisim periyodu",
]


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


def _set_yukle(yol: Path) -> list[dict]:
    with yol.open(encoding="utf-8") as f:
        return json.load(f)["sorgular"]


def _top_1_accurcy(sonuclar: list[dict]) -> float:
    n = len(sonuclar)
    return round(sum(1 for s in sonuclar if s["isabet_sirasi"] == 1) / n * 100, 2) if n else 0


def _top_3_accurcy(sonuclar: list[dict]) -> float:
    n = len(sonuclar)
    return round(sum(1 for s in sonuclar if 0 < s["isabet_sirasi"] <= 3) / n * 100, 2) if n else 0


def _mrr(sonuclar: list[dict]) -> float:
    vals = [1.0 / s["isabet_sirasi"] if s["isabet_sirasi"] > 0 else 0.0 for s in sonuclar]
    return round(statistics.fmean(vals), 4) if vals else 0


def _ndcg(sonuclar: list[dict]) -> float:
    vals = [
        (1.0 / math.log2(s["isabet_sirasi"] + 1)) if s["isabet_sirasi"] > 0 else 0.0
        for s in sonuclar
    ]
    return round(statistics.fmean(vals), 4) if vals else 0


def _tek_sorgu(servis, soru: str, beklenen_id: int) -> dict:
    t0 = time.perf_counter()
    try:
        sonuc = servis.ara(soru)
    except Exception as e:
        return {"isabet_sirasi": 0, "hata": str(e)[:200], "gecen_ms": 0}
    ms = round((time.perf_counter() - t0) * 1000, 2)
    ids = [int(a.sss_id) for a in sonuc.adaylar[:10] if a.sss_id is not None]
    sira = ids.index(beklenen_id) + 1 if beklenen_id in ids else 0
    return {
        "isabet_sirasi": sira,
        "top_1_id": ids[0] if ids else None,
        "top_3_ids": ids[:3],
        "gecen_ms": ms,
        "aday_sayisi": len(sonuc.adaylar),
        "yeniden_siralama_etkin": sonuc.yeniden_siralama_etkin,
        "hata": None,
    }


def _guven_skorunu_hesapla(kaynaklar) -> float:
    skorlar = [k.vektor_benzerlik_skoru for k in kaynaklar if k.vektor_benzerlik_skoru is not None]
    return round(max(skorlar), 6) if skorlar else 0.0


def _bilinmeyen_testi(servis, soru: str, esik: float) -> dict:
    t0 = time.perf_counter()
    try:
        sonuc = servis.ara(soru)
        ms = round((time.perf_counter() - t0) * 1000, 2)
        kaynaklar = tuple(sonuc.adaylar[:konfigurasyon.DEEPSEEK_KAYNAK_SAYISI])
        guven = _guven_skorunu_hesapla(kaynaklar)
        return {"yeterli": bool(kaynaklar) and guven >= esik, "guven": guven, "gecen_ms": ms, "hata": None}
    except Exception as e:
        return {"yeterli": False, "guven": 0, "gecen_ms": 0, "hata": str(e)[:200]}


def _bilinen_testi(servis, soru: str, beklenen_id: int, esik: float) -> dict:
    t0 = time.perf_counter()
    try:
        sonuc = servis.ara(soru)
        ms = round((time.perf_counter() - t0) * 1000, 2)
        kaynaklar = tuple(sonuc.adaylar[:konfigurasyon.DEEPSEEK_KAYNAK_SAYISI])
        guven = _guven_skorunu_hesapla(kaynaklar)
        yeterli = bool(kaynaklar) and guven >= esik
        ids = [int(a.sss_id) for a in sonuc.adaylar[:10] if a.sss_id is not None]
        dogru = beklenen_id in ids
        return {"yeterli": yeterli, "guven": guven, "dogru_buldu": dogru, "gecen_ms": ms, "hata": None}
    except Exception as e:
        return {"yeterli": False, "guven": 0, "dogru_buldu": False, "gecen_ms": 0, "hata": str(e)[:200]}


def _retrieval_benchmark(servis, sorgular: list[dict]) -> dict:
    sonuclar = []
    for s in sorgular:
        r = _tek_sorgu(servis, s["soru"], s["beklenen_sss_id"])
        r["soru"] = s["soru"][:120]
        r["beklenen_id"] = s["beklenen_sss_id"]
        sonuclar.append(r)

    hatali = [s for s in sonuclar if s.get("hata")]
    gecmli = [s for s in sonuclar if not s.get("hata")]
    gecikmeler = [s["gecen_ms"] for s in gecmli]

    kategoriler = {"kisa_sorgu": 0, "belirsiz_sorgu": 0, "mukerrer_kayit": 0, "diger": 0}
    basarisiz_detay = []
    for s in sonuclar:
        if s["isabet_sirasi"] == 0 and not s.get("hata"):
            soru = s.get("soru", "")
            if len(soru) < 25:
                kat = "kisa_sorgu"
            elif len(soru.split()) < 6:
                kat = "belirsiz_sorgu"
            else:
                kat = "diger"
            kategoriler[kat] += 1
            basarisiz_detay.append({"soru": soru, "beklenen_id": s.get("beklenen_id"), "kategori": kat})

    return {
        "sorgu_sayisi": len(sonuclar),
        "hata": len(hatali),
        "top_1_accurcy_pct": _top_1_accurcy(sonuclar),
        "top_3_accurcy_pct": _top_3_accurcy(sonuclar),
        "mrr_10": _mrr(sonuclar),
        "ndcg_10": _ndcg(sonuclar),
        "ortalama_gecikme_ms": round(statistics.fmean(gecikmeler), 2) if gecikmeler else 0,
        "p95_gecikme_ms": round(_yuzdelik(gecikmeler, 95), 2) if gecikmeler else 0,
        "basarisiz_kategorileri": kategoriler,
        "basarisiz_detay": basarisiz_detay[:20],
    }


def _yuzdelik(degerler: list[float], p: float) -> float:
    if not degerler:
        return 0
    s = sorted(degerler)
    pos = (p / 100) * (len(s) - 1)
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _esik_taramasi(servis, kalibrasyon: list[dict]) -> list[dict]:
    esikler = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
    sonuclar = []
    for esik in esikler:
        bilinmeyen = [_bilinmeyen_testi(servis, s, esik) for s in BILINMEYEN_SORULAR]
        bilinen = [_bilinen_testi(servis, s["soru"], s["beklenen_sss_id"], esik) for s in kalibrasyon]

        b_toplam = len(bilinmeyen)
        b_sustu = sum(1 for s in bilinmeyen if not s["yeterli"])
        k_toplam = len(bilinen)
        k_kayip = sum(1 for s in bilinen if not s["yeterli"])

        susma_orani = round(b_sustu / b_toplam * 100, 2)
        kayip_orani = round(k_kayip / k_toplam * 100, 2)

        sonuclar.append({
            "esik": esik,
            "bilinmeyen_susma_orani_pct": susma_orani,
            "bilinmeyen_sustu": b_sustu,
            "bilinmeyen_toplam": b_toplam,
            "bilinen_kayip_orani_pct": kayip_orani,
            "bilinen_kayip": k_kayip,
            "bilinen_toplam": k_toplam,
            "hedef_gecti": susma_orani >= 85.0,
        })
    return sonuclar


def _en_iyi_esigi_sec(esik_sonuclari: list[dict]) -> float:
    gecenler = [e for e in esik_sonuclari if e["hedef_gecti"]]
    if not gecenler:
        return 0.70
    return min(gecenler, key=lambda e: e["bilinen_kayip_orani_pct"])["esik"]


def _celiski_tespit_et(servis, en_iyi_adaylar: list) -> dict:
    if len(en_iyi_adaylar) < 2:
        return {"celiski_var": False, "ilgili_sss_idler": [], "aciklama": ""}

    moduller = {}
    for aday in en_iyi_adaylar[:8]:
        modul = aday.kaynak_dokuman or ""
        if modul not in moduller:
            moduller[modul] = []
        moduller[modul].append(aday)

    celiskiler = []
    for modul, adaylar in moduller.items():
        if len(adaylar) < 2:
            continue
        skorlar = [a.rrf_skoru for a in adaylar]
        skor_araligi = max(skorlar) - min(skorlar)
        if skor_araligi > 0.15:
            continue
        metin_uzunluklari = [len(a.aday_metni) for a in adaylar]
        if max(metin_uzunluklari) > 0 and min(metin_uzunluklari) / max(metin_uzunluklari) < 0.3:
            continue
        celiski_adaylari = [a for a in adaylar if a.sss_id is not None]
        if len(celiski_adaylari) >= 2:
            celiskiler.append({
                "modul": modul,
                "ilgili_sss_idler": [a.sss_id for a in celiski_adaylari],
                "skor_benzerligi": round(skor_araligi, 4),
            })

    if celiskiler:
        tum_idler = []
        for c in celiskiler:
            tum_idler.extend(c["ilgili_sss_idler"])
        return {
            "celiski_var": True,
            "ilgili_sss_idler": list(dict.fromkeys(tum_idler)),
            "aciklama": f"{len(celiskiler)} modülde benzer skorlu farklı SSS kaydı tespit edildi",
            "detay": celiskiler,
        }
    return {"celiski_var": False, "ilgili_sss_idler": [], "aciklama": ""}


def _deepseek_metrikleri(servis, sorular: list[dict]) -> dict:
    async def _tek_test(soru: str):
        try:
            from uygulama.servisler.akis_servisi import AkisServisi
            from uygulama.servisler.deepseek_servisi import DeepSeekServisi
            from uygulama.servisler.oturum_hafizasi import OturumHafizasi
            akis = AkisServisi(servis, DeepSeekServisi(), OturumHafizasi())
            cevap_parcalari = []
            kaynak_sayisi = 0
            cevaplandi = False
            guven = 0.0
            celiski_tespit_edildi = False
            async for sse_metni in akis.yanit_akisini_uret(soru, "bench_deepseek"):
                for sse_parcasi in sse_metni.strip().split("\n\n"):
                    satirlar = sse_parcasi.strip().split("\n")
                    olay_adi = veri_metni = None
                    for satir in satirlar:
                        satir = satir.strip()
                        if satir.startswith("event: "):
                            olay_adi = satir.removeprefix("event: ").strip()
                        elif satir.startswith("data: "):
                            veri_metni = satir.removeprefix("data: ").strip()
                    if olay_adi and veri_metni:
                        try:
                            veri = json.loads(veri_metni)
                        except json.JSONDecodeError:
                            continue
                        if olay_adi == "meta":
                            guven = float(veri.get("guven_skoru", 0))
                            kaynak_sayisi = len(veri.get("kaynaklar", []))
                        elif olay_adi == "parca":
                            cevap_parcalari.append(str(veri.get("metin", "")))
                        elif olay_adi == "tamamlandi":
                            cevaplandi = bool(veri.get("cevaplandi", False))
                        elif olay_adi == "celiski":
                            celiski_tespit_edildi = True
            tam_cevap = "".join(cevap_parcalari)
            kaynak_atifli = "[Kaynak" in tam_cevap if cevaplandi else True
            kaynaksiz = cevaplandi and not kaynak_atifli
            return {
                "cevaplandi": cevaplandi,
                "guven": round(guven, 4),
                "kaynak_sayisi": kaynak_sayisi,
                "kaynak_atifli": kaynak_atifli,
                "kaynaksiz": kaynaksiz,
                "celiski_tespit_edildi": celiski_tespit_edildi,
                "hata": None,
            }
        except Exception as e:
            return {"cevaplandi": False, "guven": 0, "kaynak_sayisi": 0, "kaynak_atifli": False, "kaynaksiz": False, "celiski_tespit_edildi": False, "hata": str(e)[:300]}

    async def _tumunu_calistir():
        gorevler = [_tek_test(s["soru"]) for s in sorular]
        return await asyncio.gather(*gorevler)

    sonuclar = asyncio.run(_tumunu_calistir())
    cevaplanan = [s for s in sonuclar if s["cevaplandi"]]
    return {
        "test_edilen": len(sonuclar),
        "hata": sum(1 for s in sonuclar if s["hata"]),
        "cevaplanan": len(cevaplanan),
        "cevaplanma_orani_pct": round(len(cevaplanan) / len(sonuclar) * 100, 2) if sonuclar else 0,
        "kaynak_atifli": sum(1 for s in cevaplanan if s["kaynak_atifli"]),
        "kaynak_atifsiz": sum(1 for s in cevaplanan if s["kaynaksiz"]),
        "kaynaksiz_cevap_orani_pct": round(sum(1 for s in cevaplanan if s["kaynaksiz"]) / len(cevaplanan) * 100, 2) if cevaplanan else 0,
        "kaynak_gosterme_orani_pct": round(sum(1 for s in cevaplanan if s["kaynak_atifli"]) / len(cevaplanan) * 100, 2) if cevaplanan else 0,
        "ortalama_guven": round(statistics.fmean([s["guven"] for s in sonuclar if not s["hata"]]), 4) if sonuclar else 0,
        "celiski_tespit_edilen": sum(1 for s in sonuclar if s["celiski_tespit_edildi"]),
    }


def _html_raporu(metrikler: dict, esik: dict, config_ozeti: dict, deepseek_m: dict) -> str:
    s = metrikler
    e = esik
    c = config_ozeti
    d = deepseek_m or {}
    top1_gecti = s["final"]["top_1_accurcy_pct"] >= 80
    top3_gecti = s["final"]["top_3_accurcy_pct"] >= 92
    return f"""<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8"><title>HadesBot Faz B+C Metrik Raporu</title>
<style>body{{font-family:system-ui,sans-serif;max-width:1000px;margin:0 auto;padding:24px;background:#f8fafc;color:#1e293b}}
h1{{font-size:1.4rem}}h2{{font-size:1.1rem;margin-top:24px;border-bottom:1px solid #e2e8f0;padding-bottom:4px}}
.kart{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}}
.k{{background:white;border:1px solid #e2e8f0;border-radius:8px;padding:14px}}
.k .d{{font-size:1.5rem;font-weight:700}}.k .l{{font-size:0.8rem;color:#64748b}}
.gecti{{color:#22c55e;font-weight:bold}}.basari{{color:#ef4444;font-weight:bold}}
table{{width:100%;border-collapse:collapse;background:white;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin:8px 0}}
th,td{{padding:6px 10px;text-align:left;font-size:0.85rem}}th{{background:#f1f5f9;font-weight:600}}
</style></head><body>
<h1>HadesBot UYDS SSS — Faz B+C Metrik Raporu</h1>
<p>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | Prompt: {c['prompt_surumu'][:12]}</p>
<h2>Retrieval Metrikleri (Final Test Seti)</h2>
<div class="kart">
<div class="k"><div class="d">%{s['final']['top_1_accurcy_pct']}</div><div class="l">Top-1 Accuracy {'GECTI' if top1_gecti else 'BASARISIZ'}</div></div>
<div class="k"><div class="d">%{s['final']['top_3_accurcy_pct']}</div><div class="l">Top-3 Accuracy {'GECTI' if top3_gecti else 'BASARISIZ'}</div></div>
<div class="k"><div class="d">{s['final']['mrr_10']}</div><div class="l">MRR@10</div></div>
<div class="k"><div class="d">{s['final']['ndcg_10']}</div><div class="l">NDCG@10</div></div>
<div class="k"><div class="d">{s['final']['p95_gecikme_ms']}ms</div><div class="l">P95 Gecikme</div></div>
</div>
<h2>Esik Taramasi</h2>
<p>Secilen esik: <b>{e['secili_esik']}</b></p>
<table><tr><th>Esik</th><th>Susma %</th><th>Susma N</th><th>Bilinen Kayip %</th><th>Kayip N</th><th>Hedef</th></tr>
{"".join(f'<tr><td>{r["esik"]}</td><td>%{r["bilinmeyen_susma_orani_pct"]}</td><td>{r["bilinmeyen_sustu"]}/{r["bilinmeyen_toplam"]}</td><td>%{r["bilinen_kayip_orani_pct"]}</td><td>{r["bilinen_kayip"]}/{r["bilinen_toplam"]}</td><td class="{"gecti" if r["hedef_gecti"] else "basari"}">{"GECTI" if r["hedef_gecti"] else "BASARISIZ"}</td></tr>' for r in e['tarama_sonuclari'])}
</table>
<h2>Basarisiz Hata Analizi</h2>
{"".join(f'<p><b>{k}</b>: {v} sorgu</p>' for k,v in s['final']['basarisiz_kategorileri'].items())}
<h2>Effective Runtime Config</h2>
<table><tr><th>Parametre</th><th>Deger</th></tr>
{"".join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k,v in c.items())}
</table>
<h2>DeepSeek Pipeline Metrikleri</h2>
{"<p>DeepSeek API cagrisi yapilmadi</p>" if not d else f'''
<div class="kart">
<div class="k"><div class="d">%{d.get("kaynak_gosterme_orani_pct",0)}</div><div class="l">Kaynak Gosterme</div></div>
<div class="k"><div class="d">%{d.get("kaynaksiz_cevap_orani_pct",0)}</div><div class="l">Kaynaksiz Cevap</div></div>
<div class="k"><div class="d">{d.get("cevaplanan",0)}/{d.get("test_edilen",0)}</div><div class="l">Cevaplanma</div></div>
<div class="k"><div class="d">{d.get("celiski_tespit_edilen",0)}</div><div class="l">Celiski Tespit</div></div>
</div>'''}
</body></html>"""


def _md_raporu(metrikler: dict, esik: dict, config_ozeti: dict, deepseek_m: dict) -> str:
    s = metrikler["final"]
    e = esik
    c = config_ozeti
    d = deepseek_m or {}
    lines = [
        "# HadesBot UYDS SSS — Faz B+C Metrik Raporu",
        "",
        f"**Tarih:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | **Prompt:** {c['prompt_surumu'][:12]}",
        "",
        "## Retrieval Metrikleri (Final Test Seti)",
        "",
        f"| Metrik | Olculen | Hedef | Durum |",
        "|---|---|---|---|",
        f"| Top-1 Accuracy | %{s['top_1_accurcy_pct']} | %80 | {'GECTI' if s['top_1_accurcy_pct']>=80 else 'BASARISIZ'} |",
        f"| Top-3 Accuracy | %{s['top_3_accurcy_pct']} | %92 | {'GECTI' if s['top_3_accurcy_pct']>=92 else 'BASARISIZ'} |",
        f"| MRR@10 | {s['mrr_10']} | — | — |",
        f"| NDCG@10 | {s['ndcg_10']} | — | — |",
        f"| P95 Gecikme | {s['p95_gecikme_ms']}ms | — | — |",
        "",
        "## Esik Taramasi",
        "",
        f"Secilen esik: **{e['secili_esik']}**",
        "",
        "| Esik | Susma % | Bilinen Kayip % | Hedef |",
        "|---|---|---|---|",
    ]
    for r in e["tarama_sonuclari"]:
        lines.append(
            f"| {r['esik']} | %{r['bilinmeyen_susma_orani_pct']} "
            f"({r['bilinmeyen_sustu']}/{r['bilinmeyen_toplam']}) | "
            f"%{r['bilinen_kayip_orani_pct']} ({r['bilinen_kayip']}/{r['bilinen_toplam']}) | "
            f"{'GECTI' if r['hedef_gecti'] else 'BASARISIZ'} |"
        )
    lines.append("")
    lines.append("## Basarisiz Hata Analizi")
    for k, v in s["basarisiz_kategorileri"].items():
        lines.append(f"- **{k}**: {v} sorgu")
    lines.append("")
    lines.append("## Effective Runtime Config")
    lines.append("")
    lines.append("| Parametre | Deger |")
    lines.append("|---|---|")
    for k, v in c.items():
        lines.append(f"| {k} | {v} |")
    if d:
        lines.append("")
        lines.append("## DeepSeek Pipeline Metrikleri")
        lines.append("")
        lines.append(f"- Kaynak Gosterme: %{d.get('kaynak_gosterme_orani_pct', 0)}")
        lines.append(f"- Kaynaksiz Cevap: %{d.get('kaynaksiz_cevap_orani_pct', 0)}")
        lines.append(f"- Cevaplanma: {d.get('cevaplanan', 0)}/{d.get('test_edilen', 0)}")
        lines.append(f"- Celiski Tespit: {d.get('celiski_tespit_edilen', 0)}")
    return "\n".join(lines)


def main() -> None:
    RAPOR_DIZINI.mkdir(parents=True, exist_ok=True)

    if not FINAL_YOLU.is_file():
        print("Once semantik_benchmark_olustur.py calistirilmali")
        return

    final = _set_yukle(FINAL_YOLU)
    kalibrasyon = _set_yukle(KALIBRASYON_YOLU)
    print(f"Kalibrasyon: {len(kalibrasyon)}, Final: {len(final)}")

    print("Arama servisi olusturuluyor...")
    servis = _arama_servisini_olustur()

    print("\n=== 1. Final Test Setinde Retrieval Metrikleri ===")
    t0 = time.perf_counter()
    final_metrikler = _retrieval_benchmark(servis, final)
    kal_metrikler = _retrieval_benchmark(servis, kalibrasyon)
    gecen = time.perf_counter() - t0
    print(f"Sure: {gecen:.1f}s")
    print(f"Top-1: %{final_metrikler['top_1_accurcy_pct']} (hedef: %80)")
    print(f"Top-3: %{final_metrikler['top_3_accurcy_pct']} (hedef: %92)")
    print(f"MRR@10: {final_metrikler['mrr_10']}")
    print(f"NDCG@10: {final_metrikler['ndcg_10']}")
    print(f"Hata kategorileri: {final_metrikler['basarisiz_kategorileri']}")

    print("\n=== 2. Esik Taramasi (kalibrasyon setinde) ===")
    esik_sonuclari = _esik_taramasi(servis, kalibrasyon)
    en_iyi_esik = _en_iyi_esigi_sec(esik_sonuclari)
    print(f"En iyi esik: {en_iyi_esik}")
    for r in esik_sonuclari:
        print(f"  {r['esik']}: susma=%{r['bilinmeyen_susma_orani_pct']} kayip=%{r['bilinen_kayip_orani_pct']} {'GECTI' if r['hedef_gecti'] else 'BASARISIZ'}")

    print(f"\n=== 3. Final sette dogrulama (esik={en_iyi_esik}) ===")
    f_bilinmeyen = [_bilinmeyen_testi(servis, s, en_iyi_esik) for s in BILINMEYEN_SORULAR]
    f_bilinen = [_bilinen_testi(servis, s["soru"], s["beklenen_sss_id"], en_iyi_esik) for s in final]
    f_susma = round(sum(1 for s in f_bilinmeyen if not s["yeterli"]) / len(f_bilinmeyen) * 100, 2)
    f_kayip = round(sum(1 for s in f_bilinen if not s["yeterli"]) / len(f_bilinen) * 100, 2)
    print(f"Final susma: %{f_susma}, Final kayip: %{f_kayip}")

    print("\n=== 4. Celiski tespiti ===")
    celiski_ornekleri = []
    for s in kalibrasyon[:10]:
        sonuc = servis.ara(s["soru"])
        celiski = _celiski_tespit_et(servis, list(sonuc.adaylar[:8]))
        if celiski["celiski_var"]:
            celiski_ornekleri.append({"soru": s["soru"][:80], "celiski": celiski})
    print(f"Taranan: 10, Celiski bulunan: {len(celiski_ornekleri)}")

    print("\n=== 5. Effective Runtime Config ===")
    config_ozeti = {
        "YENIDEN_SIRALAMA_ETKIN": konfigurasyon.YENIDEN_SIRALAMA_ETKIN,
        "NIYET_SINIFLANDIRMA_AKTIF": konfigurasyon.NIYET_SINIFLANDIRMA_AKTIF,
        "API_DOKUMANTASYONU_AKTIF": konfigurasyon.API_DOKUMANTASYONU_AKTIF,
        "GUVEN_ESIGI_aktif": konfigurasyon.GUVEN_ESIGI,
        "GUVEN_ESIGI_onerilen": en_iyi_esik,
        "DEEPSEEK_MODEL_ADI": konfigurasyon.DEEPSEEK_MODEL_ADI,
        "DEEPSEEK_KAYNAK_SAYISI": konfigurasyon.DEEPSEEK_KAYNAK_SAYISI,
        "VEKTOR_MODEL_ADI": konfigurasyon.VEKTOR_MODEL_ADI,
        "prompt_surumu": PROMPT_SURUMU,
        "yeniden_siralama_modeli": konfigurasyon.YENIDEN_SIRALAMA_MODEL_YOLU if konfigurasyon.YENIDEN_SIRALAMA_ETKIN else "kapali",
    }
    for k, v in config_ozeti.items():
        print(f"  {k}: {v}")

    print("\n=== 6. DeepSeek Pipeline Metrikleri ===")
    try:
        deepseek_m = _deepseek_metrikleri(servis, kalibrasyon[:10])
        print(f"  Cevaplanan: {deepseek_m['cevaplanan']}/{deepseek_m['test_edilen']}")
        print(f"  Kaynak atifli: %{deepseek_m['kaynak_gosterme_orani_pct']}")
        print(f"  Kaynaksiz: %{deepseek_m['kaynaksiz_cevap_orani_pct']}")
        print(f"  Celiski tespit: {deepseek_m['celiski_tespit_edilen']}")
    except Exception as e:
        deepseek_m = {"hata": str(e)[:300]}
        print(f"  DeepSeek API hatasi: {str(e)[:200]}")

    print("\n=== 7. Rapor uretiliyor ===")
    tum_metrikler = {
        "final": final_metrikler,
        "kalibrasyon": kal_metrikler,
    }
    esik_ozeti = {
        "secili_esik": en_iyi_esik,
        "final_susma_pct": f_susma,
        "final_kayip_pct": f_kayip,
        "tarama_sonuclari": esik_sonuclari,
    }
    cikti_json = {
        "metrikler": tum_metrikler,
        "esik_taramasi": esik_ozeti,
        "config_ozeti": config_ozeti,
        "deepseek_metrikleri": deepseek_m,
        "zaman": datetime.now(timezone.utc).isoformat(),
        "celiski_ornekleri": celiski_ornekleri[:5],
    }
    METRIK_RAPORU_JSON.write_text(json.dumps(cikti_json, ensure_ascii=False, indent=2), encoding="utf-8")
    METRIK_RAPORU_MD.write_text(_md_raporu(tum_metrikler, esik_ozeti, config_ozeti, deepseek_m), encoding="utf-8")
    METRIK_RAPORU_HTML.write_text(_html_raporu(tum_metrikler, esik_ozeti, config_ozeti, deepseek_m), encoding="utf-8")
    print(f"JSON: {METRIK_RAPORU_JSON}")
    print(f"Markdown: {METRIK_RAPORU_MD}")
    print(f"HTML: {METRIK_RAPORU_HTML}")

    print("\n=== OZET ===")
    print(f"Top-1: %{final_metrikler['top_1_accurcy_pct']} (%80 hedef)")
    print(f"Top-3: %{final_metrikler['top_3_accurcy_pct']} (%92 hedef)")
    print(f"MRR: {final_metrikler['mrr_10']}, NDCG: {final_metrikler['ndcg_10']}")
    print(f"Esik: {en_iyi_esik} (susma=%{f_susma}, kayip=%{f_kayip})")


if __name__ == "__main__":
    main()
