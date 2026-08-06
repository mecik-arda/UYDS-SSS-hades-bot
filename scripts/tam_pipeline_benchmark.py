import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.cekirdek.konfigurasyon import konfigurasyon

RAPOR_DIZINI = Path(__file__).resolve().parent.parent / "testler" / "benchmark" / "raporlar"


def _sorulari_al(orneklem: int = 0) -> list[dict]:
    with baglam_yoneticisi() as baglanti:
        if orneklem > 0:
            satirlar = baglanti.execute(
                "SELECT id, soru, cevap, kategori FROM sss_kayitlari WHERE durum='aktif' ORDER BY id LIMIT ?",
                (orneklem,),
            ).fetchall()
        else:
            satirlar = baglanti.execute(
                "SELECT id, soru, cevap, kategori FROM sss_kayitlari WHERE durum='aktif' ORDER BY id"
            ).fetchall()
    return [dict(s) for s in satirlar]


def _bos_soru_uret() -> str:
    return "xylophone_quadratic_nonexistent_xyzzy_42"


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


async def _tam_pipeline_test(soru: str, arama_servisi) -> dict:
    t0 = time.perf_counter()
    try:
        from uygulama.servisler.akis_servisi import AkisServisi
        from uygulama.servisler.deepseek_servisi import DeepSeekServisi
        from uygulama.servisler.oturum_hafizasi import OturumHafizasi
        akis = AkisServisi(arama_servisi, DeepSeekServisi(), OturumHafizasi())
        parcalar = []
        guven_skoru = 0.0
        kaynaklar = []
        cevaplandi = False
        async for sse_metni in akis.yanit_akisini_uret(soru, "benchmark_test"):
            for sse_parcasi in sse_metni.strip().split("\n\n"):
                satirlar = sse_parcasi.strip().split("\n")
                olay_adi = None
                veri_metni = None
                for satir in satirlar:
                    satir = satir.strip()
                    if satir.startswith("event: "):
                        olay_adi = satir.removeprefix("event: ").strip()
                    elif satir.startswith("data: "):
                        veri_metni = satir.removeprefix("data: ").strip()
                if olay_adi is None or veri_metni is None:
                    continue
                try:
                    veri = json.loads(veri_metni)
                except json.JSONDecodeError:
                    continue
                if olay_adi == "meta":
                    guven_skoru = float(veri.get("guven_skoru", 0.0))
                    kaynaklar = veri.get("kaynaklar", [])
                elif olay_adi == "parca":
                    parcalar.append(str(veri.get("metin", "")))
                elif olay_adi == "tamamlandi":
                    cevaplandi = bool(veri.get("cevaplandi", False))
        gecen = (time.perf_counter() - t0) * 1000
        cevap_metni = "".join(parcalar)
        kaynak_sayisi = len(kaynaklar)
        kaynak_atifli = "[Kaynak" in cevap_metni if cevaplandi else True
        return {
            "gecen_ms": round(gecen, 2),
            "cevaplandi": cevaplandi,
            "guven_skoru": round(guven_skoru, 4),
            "kaynak_sayisi": kaynak_sayisi,
            "cevap_uzunlugu": len(cevap_metni),
            "kaynak_atifli": kaynak_atifli,
            "hata": None,
        }
    except Exception as hata:
        gecen = (time.perf_counter() - t0) * 1000
        return {
            "gecen_ms": round(gecen, 2),
            "cevaplandi": False,
            "guven_skoru": 0.0,
            "kaynak_sayisi": 0,
            "cevap_uzunlugu": 0,
            "kaynak_atifli": False,
            "hata": str(hata)[:300],
        }


def _metrikleri_hesapla(sonuclar: list[dict]) -> dict:
    toplam = len(sonuclar)
    if toplam == 0:
        return {}
    hatali = [s for s in sonuclar if s.get("hata")]
    cevaplanan = [s for s in sonuclar if s["cevaplandi"]]
    cevaplanmayan = [s for s in sonuclar if not s["cevaplandi"]]
    cevaplanan_atifli = [s for s in cevaplanan if s["kaynak_atifli"]]
    cevaplanan_atifsiz = [s for s in cevaplanan if not s["kaynak_atifli"]]

    bilinmeyen_testi = [s for s in sonuclar if s.get("guven_skoru", 0) < konfigurasyon.GUVEN_ESIGI or not s["cevaplandi"]]

    return {
        "test_edilen": toplam,
        "hata_sayisi": len(hatali),
        "hata_orani_pct": round(len(hatali) / toplam * 100, 2),
        "cevaplanan": len(cevaplanan),
        "cevaplanma_orani_pct": round(len(cevaplanan) / toplam * 100, 2),
        "kaynak_atifli": len(cevaplanan_atifli),
        "kaynak_atifsiz": len(cevaplanan_atifsiz),
        "kaynaksiz_cevap_orani_pct": round(len(cevaplanan_atifsiz) / len(cevaplanan) * 100, 2) if cevaplanan else 0,
        "kaynak_atif_orani_pct": round(len(cevaplanan_atifli) / len(cevaplanan) * 100, 2) if cevaplanan else 0,
        "cevaplanmayan": len(cevaplanmayan),
        "ortalama_guven": round(statistics.fmean([s["guven_skoru"] for s in sonuclar if not s.get("hata")]), 4) if sonuclar else 0,
    }


async def _test_kumesi_calistir(sorular: list[dict], arama_servisi) -> list[dict]:
    sonuclar = []
    for i, s in enumerate(sorular):
        sonuc = await _tam_pipeline_test(s["soru"], arama_servisi)
        sonuc["sss_id"] = s["id"]
        sonuc["soru"] = s["soru"][:120]
        sonuclar.append(sonuc)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(sorular)} (cevaplanan: {sum(1 for x in sonuclar if x['cevaplandi'])})")
    return sonuclar


async def _bilinmeyen_testi_calistir(arama_servisi, sayi: int = 10) -> list[dict]:
    sonuclar = []
    for i in range(sayi):
        sonuc = await _tam_pipeline_test(_bos_soru_uret(), arama_servisi)
        sonuc["sss_id"] = None
        sonuc["soru"] = f"bilinmeyen_test_{i+1}"
        sonuclar.append(sonuc)
    return sonuclar


def main() -> None:
    ayrıştırıcı = argparse.ArgumentParser(description="Tam pipeline benchmark — DeepSeek API dahil")
    ayrıştırıcı.add_argument("--orneklem", type=int, default=20, help="Test edilecek kayit sayisi")
    ayrıştırıcı.add_argument("--bilinmeyen", type=int, default=5, help="Bilinmeyen test sayisi")
    ayrıştırıcı.add_argument("--json", action="store_true", help="JSON cikti")
    argumanlar = ayrıştırıcı.parse_args()

    sorular = _sorulari_al(argumanlar.orneklem)
    print(f"{len(sorular)} soru yuklendi, arama servisi olusturuluyor...")
    arama = _arama_servisini_olustur()

    print(f"Gercek SSS testi basliyor ({len(sorular)} soru)...")
    t0 = time.perf_counter()
    gercek_sonuclar = asyncio.run(_test_kumesi_calistir(sorular, arama))

    print(f"\nBilinmeyen soru testi basliyor ({argumanlar.bilinmeyen} soru)...")
    bilinmeyen_sonuclar = asyncio.run(_bilinmeyen_testi_calistir(arama, argumanlar.bilinmeyen))
    b_susma = sum(1 for s in bilinmeyen_sonuclar if not s["cevaplandi"])

    gecen = time.perf_counter() - t0
    metrikler = _metrikleri_hesapla(gercek_sonuclar)

    print(f"\nToplam sure: {gecen:.1f}s")
    print(f"Hata: {metrikler['hata_sayisi']}/%{metrikler['hata_orani_pct']}")
    print(f"Cevaplanma: {metrikler['cevaplanan']}/%{metrikler['cevaplanma_orani_pct']}")
    print(f"Kaynak atifli: {metrikler['kaynak_atifli']}/%{metrikler['kaynak_atif_orani_pct']} (hedef: %100)")
    print(f"Kaynaksiz: {metrikler['kaynak_atifsiz']}/%{metrikler['kaynaksiz_cevap_orani_pct']} (hedef: %0)")
    print(f"Bilinmeyen susma: {b_susma}/{argumanlar.bilinmeyen} = %{b_susma/argumanlar.bilinmeyen*100:.0f} (hedef: >=%85)")
    print(f"Ortalama guven: {metrikler['ortalama_guven']}")

    zaman = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    cikti_dizini = RAPOR_DIZINI
    cikti_dizini.mkdir(parents=True, exist_ok=True)

    tum_sonuclar = {
        "metrikler": metrikler,
        "bilinmeyen_test": {
            "test_edilen": argumanlar.bilinmeyen,
            "sustu": b_susma,
            "susma_orani": round(b_susma / argumanlar.bilinmeyen * 100, 2),
        },
        "orneklem": len(sorular),
        "gecen_sure_sn": round(gecen, 2),
        "guven_esigi": konfigurasyon.GUVEN_ESIGI,
    }

    if argumanlar.json:
        json_yolu = cikti_dizini / f"tam_pipeline_{zaman}.json"
        json_yolu.write_text(json.dumps(tum_sonuclar, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON: {json_yolu}")

    md_yolu = cikti_dizini / f"tam_pipeline_{zaman}.md"
    md_satirlar = [
        "# Tam Pipeline Benchmark (DeepSeek API)",
        "",
        f"**Tarih:** {zaman} | **Orneklem:** {len(sorular)} | **Sure:** {gecen:.1f}s",
        f"**Guven esigi:** {konfigurasyon.GUVEN_ESIGI}",
        "",
        "## M-03/M-05: Kaynak Gosterme / Kaynaksiz Cevap",
        "",
        f"| Metrik | Olculen | Hedef |",
        "|---|---|---|",
        f"| Kaynak atif orani | %{metrikler['kaynak_atif_orani_pct']} | %100 |",
        f"| Kaynaksiz cevap orani | %{metrikler['kaynaksiz_cevap_orani_pct']} | %0 |",
        "",
        "## M-04: Bilinmeyen Soruda Susma",
        "",
        f"| Metrik | Olculen | Hedef |",
        "|---|---|---|",
        f"| Bilinmeyen susma | %{b_susma/argumanlar.bilinmeyen*100:.0f} ({b_susma}/{argumanlar.bilinmeyen}) | >=%85 |",
        "",
        f"## Genel",
        "",
        f"- Cevaplanma: %{metrikler['cevaplanma_orani_pct']}",
        f"- Ortalama guven: {metrikler['ortalama_guven']}",
        f"- Hata: {metrikler['hata_sayisi']}/%{metrikler['hata_orani_pct']}",
    ]
    md_yolu.write_text("\n".join(md_satirlar), encoding="utf-8")
    print(f"Markdown: {md_yolu}")


if __name__ == "__main__":
    main()
