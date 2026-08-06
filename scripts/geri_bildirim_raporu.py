import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from uygulama.cekirdek.veritabani import baglam_yoneticisi


RAPOR_DIZINI = Path(__file__).resolve().parent.parent / "testler" / "benchmark" / "raporlar"


def _geri_bildirim_etkisini_olc() -> dict:
    with baglam_yoneticisi() as baglanti:
        baglanti.row_factory = None
        onayli_sayisi = baglanti.execute(
            "SELECT COUNT(*) FROM geri_bildirimler WHERE durum='ONAYLANDI'"
        ).fetchone()[0]
        bekleyen_sayisi = baglanti.execute(
            "SELECT COUNT(*) FROM geri_bildirimler WHERE durum='BEKLEMEDE'"
        ).fetchone()[0]
        reddedilen_sayisi = baglanti.execute(
            "SELECT COUNT(*) FROM geri_bildirimler WHERE durum='REDDEDILDI'"
        ).fetchone()[0]
        alternatif_sayisi = baglanti.execute(
            "SELECT COUNT(*) FROM alternatif_sorular WHERE durum='onaylandi'"
        ).fetchone()[0]
        toplam_sorgu = baglanti.execute(
            "SELECT COUNT(*) FROM asistan_sorgulari"
        ).fetchone()[0]
        cevaplanan_sorgu = baglanti.execute(
            "SELECT COUNT(*) FROM asistan_sorgulari WHERE cevaplandi_mi=1"
        ).fetchone()[0]
        ortalama_guven = baglanti.execute(
            "SELECT AVG(guven_skoru) FROM asistan_sorgulari WHERE cevaplandi_mi=1"
        ).fetchone()[0]
        guven_skorlari = baglanti.execute(
            "SELECT guven_skoru FROM asistan_sorgulari WHERE cevaplandi_mi=1"
        ).fetchall()
    guven_listesi = [r[0] for r in guven_skorlari if r[0] is not None]
    return {
        "toplam_sorgu": toplam_sorgu,
        "cevaplanan_sorgu": cevaplanan_sorgu,
        "cevaplanma_orani": round(cevaplanan_sorgu / toplam_sorgu * 100, 2) if toplam_sorgu else 0,
        "ortalama_guven": round(ortalama_guven, 4) if ortalama_guven else 0,
        "medyan_guven": round(statistics.median(guven_listesi), 4) if guven_listesi else 0,
        "onayli_geri_bildirim": onayli_sayisi,
        "bekleyen_geri_bildirim": bekleyen_sayisi,
        "reddedilen_geri_bildirim": reddedilen_sayisi,
        "onayli_alternatif_soru": alternatif_sayisi,
        "geri_bildirim_egilimi": {
            "onayli": onayli_sayisi,
            "bekleyen": bekleyen_sayisi,
            "reddedilen": reddedilen_sayisi,
        },
        "ogrenme_kapasitesi": alternatif_sayisi,
    }


def main() -> None:
    ayrıştırıcı = argparse.ArgumentParser(description="Geri bildirim etki raporu")
    ayrıştırıcı.add_argument("--cikti", type=str, default=None, help="Rapor cikti dizini")
    argumanlar = ayrıştırıcı.parse_args()
    cikti_dizini = Path(argumanlar.cikti) if argumanlar.cikti else RAPOR_DIZINI
    cikti_dizini.mkdir(parents=True, exist_ok=True)
    metrikler = _geri_bildirim_etkisini_olc()
    print(f"Toplam sorgu: {metrikler['toplam_sorgu']}")
    print(f"Cevaplanma orani: %{metrikler['cevaplanma_orani']}")
    print(f"Ortalama guven: {metrikler['ortalama_guven']}")
    print(f"Onayli geri bildirim: {metrikler['onayli_geri_bildirim']}")
    print(f"Bekleyen: {metrikler['bekleyen_geri_bildirim']}")
    print(f"Reddedilen: {metrikler['reddedilen_geri_bildirim']}")
    print(f"Onayli alternatif soru: {metrikler['onayli_alternatif_soru']}")
    if metrikler["onayli_alternatif_soru"] > 0:
        print(f"Ogrenme aktif: {metrikler['onayli_alternatif_soru']} alternatif soru ogrenilmis")
    else:
        print("Ogrenme: henuz alternatif soru ogrenilmemis")
    zaman = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_yolu = cikti_dizini / f"geri_bildirim_etki_{zaman}.json"
    json_yolu.write_text(json.dumps(metrikler, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Cikti: {json_yolu}")


if __name__ == "__main__":
    main()
