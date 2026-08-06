import json
import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.cekirdek.konfigurasyon import konfigurasyon

RAPOR_DIZINI = Path(__file__).resolve().parent.parent / "testler" / "benchmark" / "raporlar"

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


def _sorulari_al(orneklem: int = 0) -> list[dict]:
    with baglam_yoneticisi() as baglanti:
        if orneklem > 0:
            satirlar = baglanti.execute(
                "SELECT id, soru FROM sss_kayitlari WHERE durum='aktif' ORDER BY id LIMIT ?",
                (orneklem,),
            ).fetchall()
        else:
            satirlar = baglanti.execute(
                "SELECT id, soru FROM sss_kayitlari WHERE durum='aktif' ORDER BY id"
            ).fetchall()
    return [dict(s) for s in satirlar]


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


def _guven_skorunu_hesapla(kaynaklar) -> float:
    skorlar = [
        kaynak.vektor_benzerlik_skoru
        for kaynak in kaynaklar
        if kaynak.vektor_benzerlik_skoru is not None
    ]
    if not skorlar:
        return 0.0
    return round(max(0.0, min(1.0, max(skorlar))), 6)


def _tek_bilinmeyen_testi(servis, soru: str, esik: float) -> dict:
    baslangic = time.perf_counter()
    try:
        sonuc = servis.ara(soru)
        gecen_ms = (time.perf_counter() - baslangic) * 1000
        kaynaklar = tuple(sonuc.adaylar[: konfigurasyon.DEEPSEEK_KAYNAK_SAYISI])
        guven = _guven_skorunu_hesapla(kaynaklar)
        yeterli = bool(kaynaklar) and guven >= esik
        return {
            "soru": soru[:120],
            "gecen_ms": round(gecen_ms, 2),
            "guven_skoru": round(guven, 4),
            "yeterli_guven": yeterli,
            "kaynak_sayisi": len(kaynaklar),
            "hata": None,
        }
    except Exception as hata:
        return {
            "soru": soru[:120],
            "gecen_ms": round((time.perf_counter() - baslangic) * 1000, 2),
            "guven_skoru": 0.0,
            "yeterli_guven": False,
            "kaynak_sayisi": 0,
            "hata": str(hata)[:200],
        }


def _tek_bilinen_testi(servis, sss_id: int, soru: str, esik: float) -> dict:
    baslangic = time.perf_counter()
    try:
        sonuc = servis.ara(soru)
        gecen_ms = (time.perf_counter() - baslangic) * 1000
        kaynaklar = tuple(sonuc.adaylar[: konfigurasyon.DEEPSEEK_KAYNAK_SAYISI])
        guven = _guven_skorunu_hesapla(kaynaklar)
        yeterli = bool(kaynaklar) and guven >= esik
        aday_idleri = [int(a.sss_id) for a in sonuc.adaylar[:10] if a.sss_id is not None]
        dogru = sss_id in aday_idleri
        return {
            "sss_id": sss_id,
            "soru": soru[:120],
            "gecen_ms": round(gecen_ms, 2),
            "guven_skoru": round(guven, 4),
            "yeterli_guven": yeterli,
            "dogru_buldu": dogru,
            "hata": None,
        }
    except Exception as hata:
        return {
            "sss_id": sss_id,
            "soru": soru[:120],
            "gecen_ms": round((time.perf_counter() - baslangic) * 1000, 2),
            "guven_skoru": 0.0,
            "yeterli_guven": False,
            "dogru_buldu": False,
            "hata": str(hata)[:200],
        }


def _ozet_hesapla(bilinmeyen_sonuclar: list[dict], bilinen_sonuclar: list[dict], esik: float) -> dict:
    b_toplam = len(bilinmeyen_sonuclar)
    b_sustu = sum(1 for s in bilinmeyen_sonuclar if not s["yeterli_guven"])
    b_cevapladi = b_toplam - b_sustu
    b_susma_orani = round(b_sustu / b_toplam * 100, 2) if b_toplam else 0

    k_toplam = len(bilinen_sonuclar)
    k_cevapladi = sum(1 for s in bilinen_sonuclar if s["yeterli_guven"])
    k_cevaplayamadi = k_toplam - k_cevapladi
    k_kayip_orani = round(k_cevaplayamadi / k_toplam * 100, 2) if k_toplam else 0

    return {
        "esik": esik,
        "bilinmeyen_test_sayisi": b_toplam,
        "bilinmeyen_susma": b_sustu,
        "bilinmeyen_cevaplama": b_cevapladi,
        "bilinmeyen_susma_orani_pct": b_susma_orani,
        "bilinen_test_sayisi": k_toplam,
        "bilinen_cevapladi": k_cevapladi,
        "bilinen_cevaplayamadi": k_cevaplayamadi,
        "bilinen_kayip_orani_pct": k_kayip_orani,
    }


def main() -> None:
    print("=== M-04 Esik Taramasi (yerel, API cagrisi YOK) ===\n")
    print(f"Bilinmeyen soru: {len(BILINMEYEN_SORULAR)}")
    RAPOR_DIZINI.mkdir(parents=True, exist_ok=True)

    bilinen_sorular = _sorulari_al(50)
    print(f"Bilinen SSS: {len(bilinen_sorular)}")

    servis = _arama_servisini_olustur()
    print("Arama servisi olusturuldu\n")

    esikler = [0.35, 0.40, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
    tum_ozetler = []

    for esik in esikler:
        t0 = time.perf_counter()
        bilinmeyen = [_tek_bilinmeyen_testi(servis, s, esik) for s in BILINMEYEN_SORULAR]
        bilinen = [_tek_bilinen_testi(servis, s["id"], s["soru"], esik) for s in bilinen_sorular]
        gecen = time.perf_counter() - t0

        ozet = _ozet_hesapla(bilinmeyen, bilinen, esik)
        ozet["gecen_sn"] = round(gecen, 1)
        tum_ozetler.append(ozet)

        durum = "GECTI" if ozet["bilinmeyen_susma_orani_pct"] >= 85.0 else "BASARISIZ"
        print(
            f"esik={esik:.2f} | susma=%{ozet['bilinmeyen_susma_orani_pct']:5.1f} "
            f"({ozet['bilinmeyen_susma']}/{ozet['bilinmeyen_test_sayisi']}) | "
            f"bilinen_kayip=%{ozet['bilinen_kayip_orani_pct']:5.1f} "
            f"({ozet['bilinen_cevaplayamadi']}/{ozet['bilinen_test_sayisi']}) | "
            f"{durum}"
        )

    print(f"\nToplam sure: {sum(o['gecen_sn'] for o in tum_ozetler):.1f}s\n")

    print("=" * 60)
    print(f"{'Esik':<7} {'Susma %':<9} {'Susma':<8} {'B.Kayip %':<10} {'B.Kayip':<9} {'Hedef':<8}")
    print("-" * 60)
    for o in tum_ozetler:
        gecti = "GECTI" if o["bilinmeyen_susma_orani_pct"] >= 85.0 else "BASARISIZ"
        print(
            f'{o["esik"]:<7.2f} {o["bilinmeyen_susma_orani_pct"]:<9.1f} '
            f'{o["bilinmeyen_susma"]}/{o["bilinmeyen_test_sayisi"]:<7} '
            f'{o["bilinen_kayip_orani_pct"]:<10.1f} '
            f'{o["bilinen_cevaplayamadi"]}/{o["bilinen_test_sayisi"]:<8} '
            f'{gecti}'
        )
    print("=" * 60)
    print("\nHedef: >=%85 bilinmeyende susma")

    cikti = {
        "test_tipi": "m04_esik_taramasi",
        "bilinmeyen_soru_sayisi": len(BILINMEYEN_SORULAR),
        "bilinen_soru_sayisi": len(bilinen_sorular),
        "esik_tarama": tum_ozetler,
        "not": "API cagrisi yapilmadi. Yalniz yerel arama servisi kullanildi.",
    }
    json_yolu = RAPOR_DIZINI / "m04_esik_taramasi.json"
    json_yolu.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON rapor: {json_yolu}")


if __name__ == "__main__":
    main()
