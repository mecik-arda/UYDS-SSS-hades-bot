import argparse
import csv
import html
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

TEST_SENARYOLARI_YOLU = Path("testler/karsilastirma/test_senaryolari.json")
RAPOR_DIZINI = Path("testler/karsilastirma/raporlar")


def _senaryolari_yukle() -> dict:
    with TEST_SENARYOLARI_YOLU.open(encoding="utf-8") as dosya:
        return json.load(dosya)


def _sse_olaylarini_ayrikla(ham: str) -> list[dict]:
    olaylar = []
    simdiki_olay = None
    for satir in ham.splitlines():
        if satir.startswith("event:"):
            simdiki_olay = satir.removeprefix("event:").strip()
        elif satir.startswith("data:"):
            try:
                veri = json.loads(satir.removeprefix("data:").strip())
            except json.JSONDecodeError:
                continue
            veri["olay"] = simdiki_olay
            olaylar.append(veri)
    return olaylar


def _olayi_bul(olaylar: list[dict], olay_adi: str) -> dict | None:
    return next((olay for olay in olaylar if olay.get("olay") == olay_adi), None)


def _tek_senaryo_calistir(
    istemci: httpx.Client,
    senaryo: dict,
    erisim_belirteci: str,
) -> dict:
    baslangic = time.perf_counter()
    try:
        yanit = istemci.post(
            "/api/v1/arama",
            json={"soru": senaryo["soru"]},
            headers={"Authorization": f"Bearer {erisim_belirteci}"},
            timeout=30,
        )
        gecen_sure = (time.perf_counter() - baslangic) * 1000
        if yanit.status_code == 422:
            return {
                "senaryo_id": senaryo["id"],
                "test_gecerli": True,
                "sonuc": "HTTP_422",
                "gecen_sure_ms": round(gecen_sure, 2),
                "kaynak_idleri": [],
                "cevaplandi": False,
            }
        if yanit.status_code != 200:
            return {
                "senaryo_id": senaryo["id"],
                "test_gecerli": False,
                "sonuc": f"HTTP_{yanit.status_code}",
                "gecen_sure_ms": round(gecen_sure, 2),
                "hata_mesaji": yanit.text[:500],
                "kaynak_idleri": [],
                "cevaplandi": False,
            }
        olaylar = _sse_olaylarini_ayrikla(yanit.text)
        meta = _olayi_bul(olaylar, "meta") or {}
        tamamlandi = _olayi_bul(olaylar, "tamamlandi") or {}
        kaynak_idleri = [
            int(kaynak["sss_id"])
            for kaynak in meta.get("kaynaklar", [])
            if isinstance(kaynak, dict) and isinstance(kaynak.get("sss_id"), int)
        ]
        return {
            "senaryo_id": senaryo["id"],
            "test_gecerli": bool(tamamlandi),
            "http_durum": yanit.status_code,
            "guven_skoru": float(meta.get("guven_skoru", 0.0)),
            "yeterli_guven": bool(meta.get("yeterli_guven", False)),
            "cevaplandi": bool(tamamlandi.get("cevaplandi", False)),
            "gecen_sure_ms": round(gecen_sure, 2),
            "kaynak_idleri": kaynak_idleri,
            "kaynak_sayisi": len(kaynak_idleri),
        }
    except httpx.TimeoutException:
        gecen_sure = (time.perf_counter() - baslangic) * 1000
        return {
            "senaryo_id": senaryo["id"],
            "test_gecerli": False,
            "sonuc": "ZAMAN_ASIMI",
            "gecen_sure_ms": round(gecen_sure, 2),
            "kaynak_idleri": [],
            "cevaplandi": False,
        }
    except httpx.RequestError as hata:
        gecen_sure = (time.perf_counter() - baslangic) * 1000
        return {
            "senaryo_id": senaryo["id"],
            "test_gecerli": False,
            "sonuc": f"BAGLANTI_HATASI: {type(hata).__name__}",
            "gecen_sure_ms": round(gecen_sure, 2),
            "kaynak_idleri": [],
            "cevaplandi": False,
        }


def _giris_yap(istemci: httpx.Client, kullanici_adi: str, sifre: str) -> str | None:
    yanit = istemci.post(
        "/api/v1/kimlik-dogrulama/giris",
        json={"kullanici_adi": kullanici_adi, "sifre": sifre},
    )
    if yanit.status_code != 200:
        return None
    return yanit.json().get("erisim_belirteci")


def _arama_siralamasini_al(
    istemci: httpx.Client,
    soru: str,
    erisim_belirteci: str,
) -> list[int]:
    yanit = istemci.post(
        "/api/v1/yonetici/olcum/arama",
        json={"soru": soru},
        headers={"Authorization": f"Bearer {erisim_belirteci}"},
        timeout=30,
    )
    yanit.raise_for_status()
    return [
        int(kimlik)
        for kimlik in yanit.json().get("sirali_sss_idleri", [])[:10]
        if isinstance(kimlik, int)
    ]


def beklenen_kaynaklari_al(senaryo: dict) -> set[int]:
    kimlikler = senaryo.get("beklenen_sss_idler")
    if isinstance(kimlikler, list):
        return {int(kimlik) for kimlik in kimlikler if isinstance(kimlik, int)}
    kimlik = senaryo.get("beklenen_sss_id")
    return {int(kimlik)} if isinstance(kimlik, int) else set()


def davranis_basarili_mi(sonuc: dict) -> bool:
    beklenen = sonuc.get("beklenen_davranis")
    if beklenen == "BASARILI_CEVAP":
        return (
            sonuc.get("test_gecerli", False)
            and sonuc.get("cevaplandi", False)
            and sonuc.get("yeterli_guven", False)
            and bool(sonuc.get("kaynak_idleri"))
        )
    if beklenen == "GUVEN_ESIK_ALTI":
        return (
            sonuc.get("test_gecerli", False)
            and not sonuc.get("cevaplandi", False)
            and not sonuc.get("yeterli_guven", False)
            and not sonuc.get("kaynak_idleri")
        )
    if beklenen == "HTTP_422":
        return sonuc.get("sonuc") == "HTTP_422"
    return False


def _yuzdelik(degerler: list[float], yuzde: float) -> float:
    if not degerler:
        return 0.0
    sirali = sorted(degerler)
    konum = (len(sirali) - 1) * yuzde
    alt = math.floor(konum)
    ust = math.ceil(konum)
    if alt == ust:
        return float(sirali[alt])
    return float(sirali[alt] + (sirali[ust] - sirali[alt]) * (konum - alt))


def _arama_metriklerini_hesapla(sonuclar: list[dict]) -> dict:
    etiketli = [sonuc for sonuc in sonuclar if sonuc["beklenen_kaynak_idleri"]]
    if not etiketli:
        return {
            "etiketli_senaryo": 0,
            "top_1_dogruluk": None,
            "top_3_dogruluk": None,
            "mrr_10": None,
            "ndcg_10": None,
        }
    top_1 = 0
    top_3 = 0
    ters_siralar = []
    ndcg_degerleri = []
    for sonuc in etiketli:
        beklenen = set(sonuc["beklenen_kaynak_idleri"])
        donen = sonuc.get("kaynak_idleri", [])[:10]
        top_1 += bool(donen and donen[0] in beklenen)
        top_3 += bool(set(donen[:3]) & beklenen)
        ilk_sira = next(
            (sira for sira, kimlik in enumerate(donen, start=1) if kimlik in beklenen),
            None,
        )
        ters_siralar.append(1.0 / ilk_sira if ilk_sira else 0.0)
        dcg = sum(
            1.0 / math.log2(sira + 1)
            for sira, kimlik in enumerate(donen, start=1)
            if kimlik in beklenen
        )
        ideal_eslesme = min(len(beklenen), 10)
        ideal_dcg = sum(1.0 / math.log2(sira + 1) for sira in range(1, ideal_eslesme + 1))
        ndcg_degerleri.append(dcg / ideal_dcg if ideal_dcg else 0.0)
    toplam = len(etiketli)
    return {
        "etiketli_senaryo": toplam,
        "top_1_dogruluk": round(top_1 / toplam * 100, 2),
        "top_3_dogruluk": round(top_3 / toplam * 100, 2),
        "mrr_10": round(statistics.fmean(ters_siralar), 4),
        "ndcg_10": round(statistics.fmean(ndcg_degerleri), 4),
    }


def metrikleri_hesapla(sonuclar: list[dict]) -> dict:
    gecikmeler = [float(sonuc["gecen_sure_ms"]) for sonuc in sonuclar]
    davranis_basarilari = [davranis_basarili_mi(sonuc) for sonuc in sonuclar]
    cevaplanmasi_beklenen = [
        sonuc for sonuc in sonuclar if sonuc.get("beklenen_davranis") == "BASARILI_CEVAP"
    ]
    cevapsiz_beklenen = [
        sonuc for sonuc in sonuclar if sonuc.get("beklenen_davranis") == "GUVEN_ESIK_ALTI"
    ]
    kaynakli_cevaplar = [
        sonuc
        for sonuc in cevaplanmasi_beklenen
        if sonuc.get("cevaplandi") and sonuc.get("kaynak_idleri")
    ]
    arama_metrikleri = _arama_metriklerini_hesapla(sonuclar)
    return {
        "toplam_senaryo": len(sonuclar),
        "davranis_basarisi": round(sum(davranis_basarilari) / len(sonuclar) * 100, 2)
        if sonuclar
        else 0.0,
        "cevap_vermeme_basarisi": round(
            sum(davranis_basarili_mi(sonuc) for sonuc in cevapsiz_beklenen)
            / len(cevapsiz_beklenen)
            * 100,
            2,
        )
        if cevapsiz_beklenen
        else None,
        "kaynak_gosterme_orani": round(
            len(kaynakli_cevaplar) / len(cevaplanmasi_beklenen) * 100,
            2,
        )
        if cevaplanmasi_beklenen
        else None,
        "ortalama_gecikme_ms": round(statistics.fmean(gecikmeler), 2)
        if gecikmeler
        else 0.0,
        "p50_gecikme_ms": round(_yuzdelik(gecikmeler, 0.50), 2),
        "p95_gecikme_ms": round(_yuzdelik(gecikmeler, 0.95), 2),
        **arama_metrikleri,
    }


def kabul_durumunu_hesapla(metrikler: dict, asgari_etiketli_senaryo: int = 50) -> dict:
    kontroller = {
        "asgari_etiketli_senaryo": metrikler["etiketli_senaryo"] >= asgari_etiketli_senaryo,
        "top_1": metrikler["top_1_dogruluk"] is not None
        and metrikler["top_1_dogruluk"] >= 80,
        "top_3": metrikler["top_3_dogruluk"] is not None
        and metrikler["top_3_dogruluk"] >= 92,
        "cevap_vermeme": metrikler["cevap_vermeme_basarisi"] is not None
        and metrikler["cevap_vermeme_basarisi"] >= 85,
        "kaynak_gosterme": metrikler["kaynak_gosterme_orani"] == 100,
    }
    return {"basarili": all(kontroller.values()), "kontroller": kontroller}


def degerlendir(temel_url: str, zehirleme_testi: bool = False) -> dict:
    veri = _senaryolari_yukle()
    senaryolar = veri["senaryolar"]
    with httpx.Client(base_url=temel_url, timeout=30) as istemci:
        yonetici_sifresi = os.getenv(
            "VARSAYILAN_YONETICI_SIFRESI",
            "test_sifresi_12_karakter_minimum",
        )
        try:
            belirtec = _giris_yap(istemci, "yonetici", yonetici_sifresi)
        except httpx.RequestError:
            return {"hata": f"Uygulamaya baglanilamadi: {temel_url}"}
        if belirtec is None:
            return {"hata": "Giris yapilamadi. Test kullanicilari olusturulmamis."}
        sonuclar = []
        for senaryo in senaryolar:
            if senaryo["zorluk"] == "zehirlenmis" and not zehirleme_testi:
                continue
            sonuc = _tek_senaryo_calistir(istemci, senaryo, belirtec)
            beklenen_kaynaklar = sorted(beklenen_kaynaklari_al(senaryo))
            if beklenen_kaynaklar and sonuc.get("test_gecerli"):
                try:
                    sonuc["kaynak_idleri"] = _arama_siralamasini_al(
                        istemci,
                        senaryo["soru"],
                        belirtec,
                    )
                except httpx.HTTPError as hata:
                    sonuc["test_gecerli"] = False
                    sonuc["sonuc"] = f"RETRIEVAL_HATASI: {type(hata).__name__}"
            sonuclar.append(
                {
                    **sonuc,
                    "zorluk": senaryo["zorluk"],
                    "kategori": senaryo.get("kategori", ""),
                    "beklenen_davranis": senaryo["beklenen_davranis"],
                    "beklenen_kaynak_idleri": beklenen_kaynaklar,
                    "soru": senaryo["soru"],
                }
            )
    metrikler = metrikleri_hesapla(sonuclar)
    return {
        "veri_seti_surumu": veri.get("surum"),
        "metrikler": metrikler,
        "kabul": kabul_durumunu_hesapla(metrikler),
        "sonuclar": sonuclar,
    }


def _metrik_degeri(deger: object) -> str:
    return "Olculmedi" if deger is None else str(deger)


def html_raporu_uret(sonuc: dict, rapor_yolu: Path) -> Path:
    metrikler = sonuc.get("metrikler", {})
    kabul = sonuc.get("kabul", {})
    satirlar = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<title>HadesBot Faz 10 Benchmark Raporu</title>",
        "<style>body{font-family:Arial,sans-serif;margin:2em}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:8px;text-align:left}th{background-color:#e9edf2}.basarili{color:green}.basarisiz{color:red}</style></head><body>",
        "<h1>HadesBot Faz 10 Benchmark Raporu</h1>",
        f"<p><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        f"<p><strong>Kabul:</strong> {'Başarılı' if kabul.get('basarili') else 'Başarısız'}</p>",
        "<h2>Metrikler</h2><table><tr><th>Metrik</th><th>Değer</th></tr>",
    ]
    for ad, deger in metrikler.items():
        satirlar.append(
            f"<tr><td>{html.escape(str(ad))}</td><td>{html.escape(_metrik_degeri(deger))}</td></tr>"
        )
    satirlar.append("</table><h2>Senaryo Detayları</h2>")
    satirlar.append(
        "<table><tr><th>ID</th><th>Zorluk</th><th>Soru</th><th>Beklenen</th><th>Dönen</th><th>Süre</th><th>Sonuç</th></tr>"
    )
    for senaryo in sonuc.get("sonuclar", []):
        basarili = davranis_basarili_mi(senaryo)
        sinif = "basarili" if basarili else "basarisiz"
        alanlar = [
            senaryo.get("senaryo_id", ""),
            senaryo.get("zorluk", ""),
            senaryo.get("soru", ""),
            senaryo.get("beklenen_kaynak_idleri", []),
            senaryo.get("kaynak_idleri", []),
            senaryo.get("gecen_sure_ms", ""),
            "Başarılı" if basarili else "Başarısız",
        ]
        hucreler = "".join(f"<td>{html.escape(str(alan))}</td>" for alan in alanlar)
        satirlar.append(f"<tr class='{sinif}'>{hucreler}</tr>")
    satirlar.append("</table></body></html>")
    rapor_yolu.write_text("\n".join(satirlar), encoding="utf-8")
    return rapor_yolu


def json_raporu_uret(sonuc: dict, rapor_yolu: Path) -> Path:
    rapor_yolu.write_text(
        json.dumps(sonuc, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return rapor_yolu


def csv_raporu_uret(sonuc: dict, rapor_yolu: Path) -> Path:
    alanlar = [
        "senaryo_id",
        "zorluk",
        "kategori",
        "beklenen_davranis",
        "beklenen_kaynak_idleri",
        "kaynak_idleri",
        "guven_skoru",
        "cevaplandi",
        "gecen_sure_ms",
        "davranis_basarili",
    ]
    with rapor_yolu.open("w", encoding="utf-8-sig", newline="") as dosya:
        yazici = csv.DictWriter(dosya, fieldnames=alanlar)
        yazici.writeheader()
        for senaryo in sonuc.get("sonuclar", []):
            satir = {alan: senaryo.get(alan) for alan in alanlar}
            satir["davranis_basarili"] = davranis_basarili_mi(senaryo)
            satir["beklenen_kaynak_idleri"] = json.dumps(
                satir["beklenen_kaynak_idleri"]
            )
            satir["kaynak_idleri"] = json.dumps(satir["kaynak_idleri"])
            yazici.writerow(satir)
    return rapor_yolu


def main() -> None:
    ayrıştirici = argparse.ArgumentParser(description="HadesBot Faz 10 Benchmark")
    ayrıştirici.add_argument("--temel-url", default="http://127.0.0.1:8000")
    ayrıştirici.add_argument("--zehirleme-testi", action="store_true")
    ayrıştirici.add_argument("--yonetici-sifresi", default=None)
    args = ayrıştirici.parse_args()
    if args.yonetici_sifresi:
        os.environ["VARSAYILAN_YONETICI_SIFRESI"] = args.yonetici_sifresi
    sonuc = degerlendir(args.temel_url, args.zehirleme_testi)
    if "hata" in sonuc:
        print(f"HATA: {sonuc['hata']}")
        raise SystemExit(2)
    RAPOR_DIZINI.mkdir(parents=True, exist_ok=True)
    zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
    kok = RAPOR_DIZINI / f"karsilastirma_{zaman_damgasi}"
    yollar = [
        html_raporu_uret(sonuc, kok.with_suffix(".html")),
        json_raporu_uret(sonuc, kok.with_suffix(".json")),
        csv_raporu_uret(sonuc, kok.with_suffix(".csv")),
    ]
    print(json.dumps(sonuc["metrikler"], indent=2, ensure_ascii=False))
    print("Raporlar: " + ", ".join(str(yol) for yol in yollar))
    if not sonuc["kabul"]["basarili"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
