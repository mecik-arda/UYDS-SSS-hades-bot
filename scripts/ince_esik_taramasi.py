import json
import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uygulama.cekirdek.konfigurasyon import konfigurasyon

BENCHMARK_KOKU = Path(__file__).resolve().parent.parent / "testler" / "benchmark"
RAPOR_DIZINI = BENCHMARK_KOKU / "raporlar"
FINAL_YOLU = BENCHMARK_KOKU / "final_test_seti.json"
KALIBRASYON_YOLU = BENCHMARK_KOKU / "kalibrasyon_seti.json"

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


def _guven_ve_marj(servis, soru: str) -> dict:
    try:
        sonuc = servis.ara(soru)
        adaylar = list(sonuc.adaylar[:konfigurasyon.DEEPSEEK_KAYNAK_SAYISI])
    except Exception:
        return {"guven": 0.0, "top1_rrf": 0.0, "top2_rrf": 0.0, "marj": 0.0, "top1_siralama": 0.0, "hata": True}

    skorlar = [a.vektor_benzerlik_skoru for a in adaylar if a.vektor_benzerlik_skoru is not None]
    guven = max(skorlar) if skorlar else 0.0

    top1_rrf = adaylar[0].rrf_skoru if adaylar else 0.0
    top2_rrf = adaylar[1].rrf_skoru if len(adaylar) > 1 else 0.0
    marj = round(top1_rrf - top2_rrf, 6)

    top1_siralama = adaylar[0].yeniden_siralama_skoru if sonuc.yeniden_siralama_etkin and adaylar else 0.0

    return {
        "guven": round(guven, 6),
        "top1_rrf": round(top1_rrf, 6),
        "top2_rrf": round(top2_rrf, 6),
        "marj": marj,
        "top1_siralama": round(top1_siralama, 6) if isinstance(top1_siralama, (int, float)) and top1_siralama else 0.0,
        "hata": False,
    }


def _birlestik_kontrol(guven_skoru: float, marj: float, min_guven: float, min_marj: float, min_siralama: float, siralama_skoru: float) -> bool:
    if guven_skoru < min_guven:
        return False
    if marj <= min_marj and siralama_skoru > 0 and siralama_skoru < min_siralama:
        return False
    return True


def _yuzdelik(degerler: list[float], p: float) -> float:
    if not degerler:
        return 0
    s = sorted(degerler)
    pos = (p / 100) * (len(s) - 1)
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (pos - lo)


def main() -> None:
    RAPOR_DIZINI.mkdir(parents=True, exist_ok=True)

    print("Arama servisi olusturuluyor...")
    servis = _arama_servisini_olustur()

    kalibrasyon = _set_yukle(KALIBRASYON_YOLU)
    final = _set_yukle(FINAL_YOLU)
    print(f"Kalibrasyon: {len(kalibrasyon)}, Final: {len(final)}")

    print("\n=== Ince Esik Taramasi (0.50-0.56, 0.01 adim) ===")
    esikler = [round(x, 2) for x in [0.50 + i * 0.01 for i in range(7)]]
    en_iyi_sonuc = None

    for esik in esikler:
        bilinmeyen_skorlar = [_guven_ve_marj(servis, s) for s in BILINMEYEN_SORULAR]
        kal_skorlar = [_guven_ve_marj(servis, s["soru"]) for s in kalibrasyon]

        b_toplam = len(bilinmeyen_skorlar)
        b_sustu = sum(1 for s in bilinmeyen_skorlar if s["guven"] < esik)
        susma = round(b_sustu / b_toplam * 100, 2)

        k_toplam = len(kal_skorlar)
        k_kayip = sum(1 for s in kal_skorlar if s["guven"] < esik)
        kayip = round(k_kayip / k_toplam * 100, 2)

        gecti = susma >= 85.0

        print(f"  esik={esik:.2f} | susma=%{susma:.1f} ({b_sustu}/{b_toplam}) | kayip=%{kayip:.1f} ({k_kayip}/{k_toplam}) | {'GECTI' if gecti else 'BASARISIZ'}")

        if gecti and (en_iyi_sonuc is None or kayip < en_iyi_sonuc["kayip_pct"]):
            en_iyi_sonuc = {"esik": esik, "susma_pct": susma, "kayip_pct": kayip}

    print(f"\n=== Marj Tabanli Yaklasim ===")
    marj_esikleri = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030]
    min_siralama = 0.5

    for guven_esik in [0.50, 0.52, 0.55]:
        for marj_esik in marj_esikleri:
            b_sustu = 0
            for s in [_guven_ve_marj(servis, soru) for soru in BILINMEYEN_SORULAR]:
                if not _birlestik_kontrol(s["guven"], s["marj"], guven_esik, marj_esik, min_siralama, s["top1_siralama"]):
                    b_sustu += 1
            susma = round(b_sustu / len(BILINMEYEN_SORULAR) * 100, 2)

            k_kayip = 0
            for s in [_guven_ve_marj(servis, soru["soru"]) for soru in kalibrasyon]:
                if not _birlestik_kontrol(s["guven"], s["marj"], guven_esik, marj_esik, min_siralama, s["top1_siralama"]):
                    k_kayip += 1
            kayip = round(k_kayip / len(kalibrasyon) * 100, 2)

            if susma >= 85.0:
                print(f"  guven={guven_esik} marj={marj_esik} | susma=%{susma} | kayip=%{kayip} | GECTI")
                if en_iyi_sonuc is None or kayip < (en_iyi_sonuc.get("marj_kayip_pct", 999)):
                    en_iyi_sonuc["marj_guven"] = guven_esik
                    en_iyi_sonuc["marj_degeri"] = marj_esik
                    en_iyi_sonuc["marj_susma_pct"] = susma
                    en_iyi_sonuc["marj_kayip_pct"] = kayip

    print(f"\n=== Final Set Dogrulamasi ===")
    if en_iyi_sonuc:
        secili_esik = en_iyi_sonuc["esik"]
        f_bilinmeyen = [_guven_ve_marj(servis, s) for s in BILINMEYEN_SORULAR]
        f_bilinen = [_guven_ve_marj(servis, s["soru"]) for s in final]
        f_susma = round(sum(1 for s in f_bilinmeyen if s["guven"] < secili_esik) / len(f_bilinmeyen) * 100, 2)
        f_kayip = round(sum(1 for s in f_bilinen if s["guven"] < secili_esik) / len(f_bilinen) * 100, 2)
        print(f"  Esik={secili_esik}: final susma=%{f_susma}, final kayip=%{f_kayip}")

    cikti = {
        "ince_tarama": {
            "esik_araligi": "0.50-0.56",
            "en_iyi_sonuc": en_iyi_sonuc,
            "final_dogrulama": {
                "susma_pct": f_susma if 'f_susma' in dir() else None,
                "kayip_pct": f_kayip if 'f_kayip' in dir() else None,
            },
        },
    }
    json_yolu = RAPOR_DIZINI / "ince_esik_taramasi.json"
    json_yolu.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON: {json_yolu}")


if __name__ == "__main__":
    main()
