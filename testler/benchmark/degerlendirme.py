import argparse
import json
import os
import time
from datetime import datetime

import httpx

TEST_SENARYOLARI_YOLU = "testler/benchmark/test_senaryolari.json"
RAPOR_DIZINI = "testler/benchmark/raporlar"


def _senaryolari_yukle() -> dict:
    with open(TEST_SENARYOLARI_YOLU, encoding="utf-8") as dosya:
        return json.load(dosya)


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
        http_durum = yanit.status_code
        if http_durum == 422:
            return {
                "senaryo_id": senaryo["id"],
                "test_gecerli": False,
                "sonuc": "HTTP_422",
                "gecen_sure_ms": round(gecen_sure, 2),
                "hata_mesaji": "Pydantic dogrulama reddetti",
            }
        if http_durum != 200:
            return {
                "senaryo_id": senaryo["id"],
                "test_gecerli": False,
                "sonuc": f"HTTP_{http_durum}",
                "gecen_sure_ms": round(gecen_sure, 2),
                "hata_mesaji": yanit.text[:500],
            }
        sse_olaylari = _sse_olaylarini_ayrikla(yanit.text)
        meta = _meta_olayini_bul(sse_olaylari)
        guven_skoru = meta.get("guven_skoru", -1) if meta else -1
        tamamlandi_olayi = any(o.get("olay") == "tamamlandi" for o in sse_olaylari)
        return {
            "senaryo_id": senaryo["id"],
            "test_gecerli": True,
            "http_durum": http_durum,
            "guven_skoru": guven_skoru,
            "tamamlandi": tamamlandi_olayi,
            "gecen_sure_ms": round(gecen_sure, 2),
        }
    except httpx.TimeoutException:
        gecen_sure = (time.perf_counter() - baslangic) * 1000
        return {
            "senaryo_id": senaryo["id"],
            "test_gecerli": False,
            "sonuc": "ZAMAN_ASIMI",
            "gecen_sure_ms": round(gecen_sure, 2),
        }
    except httpx.RequestError as hata:
        gecen_sure = (time.perf_counter() - baslangic) * 1000
        return {
            "senaryo_id": senaryo["id"],
            "test_gecerli": False,
            "sonuc": f"BAGLANTI_HATASI: {hata}",
            "gecen_sure_ms": round(gecen_sure, 2),
        }


def _sse_olaylarini_ayrikla(ham: str) -> list[dict]:
    olaylar = []
    simdiki_olay = None
    for satir in ham.split("\n"):
        if satir.startswith("event:"):
            simdiki_olay = satir[len("event:"):].strip()
        elif satir.startswith("data:"):
            try:
                veri = json.loads(satir[len("data:"):].strip())
                veri["olay"] = simdiki_olay
                olaylar.append(veri)
            except json.JSONDecodeError:
                continue
    return olaylar


def _meta_olayini_bul(olaylar: list[dict]) -> dict | None:
    for olay in olaylar:
        if olay.get("olay") == "meta":
            return olay
    return None


def _giris_yap(istemci: httpx.Client, kullanici_adi: str, sifre: str) -> str | None:
    yanit = istemci.post(
        "/api/v1/kimlik-dogrulama/giris",
        json={"kullanici_adi": kullanici_adi, "sifre": sifre},
    )
    if yanit.status_code != 200:
        return None
    return yanit.json().get("erisim_belirteci")


def karsilastir(beklenen: str, sonuc: dict) -> bool:
    if beklenen == "BASARILI_CEVAP":
        return sonuc.get("guven_skoru", -1) >= 0.0 and sonuc.get(
            "tamamlandi", False
        )
    if beklenen == "GUVEN_ESIK_ALTI":
        guven = sonuc.get("guven_skoru", -1)
        return guven < 0.70 and not sonuc.get("tamamlandi", False)
    if beklenen == "HTTP_422":
        return sonuc.get("sonuc") == "HTTP_422"
    return False


def degerlendir(temel_url: str, zehirleme_testi: bool = False) -> dict:
    veri = _senaryolari_yukle()
    senaryolar = veri["senaryolar"]
    istemci = httpx.Client(base_url=temel_url, timeout=30)
    try:
        yonetici_sifresi = os.getenv(
            "VARSAYILAN_YONETICI_SIFRESI",
            "test_sifresi_12_karakter_minimum",
        )
        belirtec = _giris_yap(istemci, "yonetici", yonetici_sifresi)
        if belirtec is None:
            return {"hata": "Giris yapilamadi. Test kullanicilari olusturulmamis."}
    except httpx.RequestError:
        return {"hata": f"Uygulamaya baglanilamadi: {temel_url}"}
    sonuclar = []
    for senaryo in senaryolar:
        if senaryo["zorluk"] == "zehirlenmis" and not zehirleme_testi:
            continue
        sonuc = _tek_senaryo_calistir(istemci, senaryo, belirtec)
        sonuclar.append(
            {
                **sonuc,
                "zorluk": senaryo["zorluk"],
                "kategori": senaryo.get("kategori", ""),
                "beklenen_davranis": senaryo["beklenen_davranis"],
                "soru": senaryo["soru"],
            }
        )
    metrikler = _metrikleri_hesapla(sonuclar)
    return {"metrikler": metrikler, "sonuclar": sonuclar}


def _metrikleri_hesapla(sonuclar: list[dict]) -> dict:
    basarili = 0
    basarisiz = 0
    zorluk_dagilimi: dict[str, dict] = {}
    for sonuc in sonuclar:
        if sonuc.get("test_gecerli") and not sonuc.get("sonuc"):
            basarili += 1
        else:
            basarisiz += 1
        zorluk = sonuc.get("zorluk", "bilinmeyen")
        if zorluk not in zorluk_dagilimi:
            zorluk_dagilimi[zorluk] = {"toplam": 0, "basarili": 0}
        zorluk_dagilimi[zorluk]["toplam"] += 1
        if karsilastir(
            sonuc.get("beklenen_davranis", ""), sonuc
        ):
            zorluk_dagilimi[zorluk]["basarili"] += 1
    toplam = basarili + basarisiz
    return {
        "toplam_senaryo": toplam,
        "uygulama_yanit_verdi": basarili,
        "uygulama_hatasi": basarisiz,
        "basarili_orani": round(basarili / toplam * 100, 1) if toplam > 0 else 0,
        "zorluk_dagilimi": zorluk_dagilimi,
    }


def html_raporu_uret(sonuc: dict, rapor_yolu: str) -> str:
    metrikler = sonuc.get("metrikler", {})
    satirlar = []
    satirlar.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
    satirlar.append("<title>HadesBot Faz 10 Benchmark Raporu</title>")
    satirlar.append("<style>body{font-family:Arial,sans-serif;margin:2em;}")
    satirlar.append("table{border-collapse:collapse;width:100%}")
    satirlar.append("td,th{border:1px solid #ccc;padding:8px;text-align:left}")
    satirlar.append("th{background-color:#e9edf2}.basarili{color:green}.basarisiz{color:red}")
    satirlar.append("</style></head><body>")
    satirlar.append("<h1>HadesBot Faz 10 Benchmark Raporu</h1>")
    satirlar.append(
        f"<p><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
    )
    satirlar.append("<h2>Genel Metrikler</h2>")
    satirlar.append(
        f"<p>Toplam Senaryo: <strong>{metrikler.get('toplam_senaryo', 0)}</strong></p>"
    )
    satirlar.append(
        f"<p>Uygulama Yanit Verdi: <strong>{metrikler.get('uygulama_yanit_verdi', 0)}</strong></p>"
    )
    satirlar.append(
        f"<p>Uygulama Hatasi: <strong>{metrikler.get('uygulama_hatasi', 0)}</strong></p>"
    )
    zorluk = metrikler.get("zorluk_dagilimi", {})
    if zorluk:
        satirlar.append("<h2>Zorluk Seviyesine Gore Basari</h2>")
        satirlar.append("<table><tr><th>Zorluk</th><th>Toplam</th><th>Basarili</th><th>Oran</th></tr>")
        for ad, dagilim in sorted(zorluk.items()):
            oran = (
                round(dagilim["basarili"] / dagilim["toplam"] * 100, 1)
                if dagilim["toplam"] > 0
                else 0
            )
            satirlar.append(
                f"<tr><td>{ad}</td><td>{dagilim['toplam']}</td>"
                f"<td>{dagilim['basarili']}</td><td>%{oran}</td></tr>"
            )
        satirlar.append("</table>")
    satirlar.append("<h2>Senaryo Detaylari</h2>")
    satirlar.append(
        "<table><tr><th>ID</th><th>Zorluk</th><th>Soru</th><th>Sure(ms)</th><th>Sonuc</th></tr>"
    )
    for s in sonuc.get("sonuclar", []):
        basarili_mi = karsilastir(s.get("beklenen_davranis", ""), s)
        satir_sinifi = "basarili" if basarili_mi else "basarisiz"
        satirlar.append(
            f"<tr class='{satir_sinifi}'>"
            f"<td>{s.get('senaryo_id')}</td>"
            f"<td>{s.get('zorluk')}</td>"
            f"<td>{s.get('soru', '')[:100]}</td>"
            f"<td>{s.get('gecen_sure_ms')}</td>"
            f"<td>{'Basarili' if basarili_mi else 'Basarisiz'}</td>"
            f"</tr>"
        )
    satirlar.append("</table>")
    satirlar.append("</body></html>")
    with open(rapor_yolu, "w", encoding="utf-8") as dosya:
        dosya.write("\n".join(satirlar))
    return rapor_yolu


def main() -> None:
    ayrıştirici = argparse.ArgumentParser(description="HadesBot Faz 10 Benchmark")
    ayrıştirici.add_argument(
        "--temel-url",
        default="http://127.0.0.1:8000",
        help="Uygulama temel URL'si",
    )
    ayrıştirici.add_argument(
        "--zehirleme-testi",
        action="store_true",
        help="RAG zehirleme senaryolarini da calistir",
    )
    ayrıştirici.add_argument(
        "--yonetici-sifresi",
        default=None,
        help="Yonetici sifresi (ortam degiskeni yoksa kullanilir)",
    )
    args = ayrıştirici.parse_args()
    if args.yonetici_sifresi:
        os.environ["VARSAYILAN_YONETICI_SIFRESI"] = args.yonetici_sifresi
    sonuc = degerlendir(args.temel_url, args.zehirleme_testi)
    if "hata" in sonuc:
        print(f"HATA: {sonuc['hata']}")
        return
    zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
    rapor_yolu = f"{RAPOR_DIZINI}/benchmark_{zaman_damgasi}.html"
    html_raporu_uret(sonuc, rapor_yolu)
    print(json.dumps(sonuc["metrikler"], indent=2, ensure_ascii=False))
    print(f"\nHTML raporu: {rapor_yolu}")


if __name__ == "__main__":
    main()