import argparse
import os
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

VERILER_DIZINI = Path("veriler")
YEDEK_DIZINI = VERILER_DIZINI / "yedekler"
VERITABANI_YOLU = VERILER_DIZINI / "veri_deposu.db"
SIFRELI_VERITABANI_YOLU = VERILER_DIZINI / "veri_deposu.db.enc"
MAKSIMUM_YEDEK_SAYISI = int(os.getenv("MAKSIMUM_YEDEK_SAYISI", "10"))
YEDEKLEME_ARALIGI_SAAT = float(os.getenv("YEDEKLEME_ARALIGI_SAAT", "24"))


def veritabani_butunlugunu_dogrula(veritabani_yolu: Path) -> None:
    baglanti = sqlite3.connect(str(veritabani_yolu))
    try:
        sonuc = baglanti.execute("PRAGMA integrity_check").fetchone()
    finally:
        baglanti.close()
    if sonuc is None or sonuc[0] != "ok":
        raise sqlite3.DatabaseError("Veritabani butunluk denetimi basarisiz")


def veritabani_dosyasini_adiyla_yedekle(kaynak: Path, hedef_adi: str) -> None:
    if not kaynak.exists():
        return
    hedef = YEDEK_DIZINI / hedef_adi
    gecici_hedef = YEDEK_DIZINI / f"{hedef_adi}.yaziliyor"
    kaynak_baglanti = sqlite3.connect(str(kaynak))
    yedek_baglanti = sqlite3.connect(str(gecici_hedef))
    try:
        kaynak_baglanti.backup(yedek_baglanti)
    finally:
        yedek_baglanti.close()
        kaynak_baglanti.close()
    veritabani_butunlugunu_dogrula(gecici_hedef)
    os.replace(gecici_hedef, hedef)


def dosya_yedekle(kaynak: Path, hedef_adi: str) -> None:
    if not kaynak.exists():
        return
    hedef = YEDEK_DIZINI / hedef_adi
    gecici_hedef = YEDEK_DIZINI / f"{hedef_adi}.yaziliyor"
    shutil.copy2(kaynak, gecici_hedef)
    os.replace(gecici_hedef, hedef)


def yedek_dosyalari() -> list[Path]:
    kaliplar = (
        "veri_deposu_*.db",
        "veri_deposu_*.db.enc",
        "es_anlamlilar_*.json",
    )
    dosyalar = {
        dosya
        for kalip in kaliplar
        for dosya in YEDEK_DIZINI.glob(kalip)
        if dosya.is_file()
    }
    return sorted(dosyalar, key=lambda dosya: dosya.stat().st_mtime)


def eski_yedekleri_temizle() -> None:
    if MAKSIMUM_YEDEK_SAYISI < 1:
        raise ValueError("MAKSIMUM_YEDEK_SAYISI en az 1 olmalidir")
    mevcut_yedekler = yedek_dosyalari()
    while len(mevcut_yedekler) > MAKSIMUM_YEDEK_SAYISI:
        mevcut_yedekler.pop(0).unlink()


def yedekle() -> list[Path]:
    YEDEK_DIZINI.mkdir(parents=True, exist_ok=True)
    zaman_damgasi = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    olusturulan_yedekler: list[Path] = []

    if VERITABANI_YOLU.exists():
        veritabani_yedek_adi = f"veri_deposu_{zaman_damgasi}.db"
        veritabani_dosyasini_adiyla_yedekle(
            VERITABANI_YOLU,
            veritabani_yedek_adi,
        )
        olusturulan_yedekler.append(YEDEK_DIZINI / veritabani_yedek_adi)
    elif SIFRELI_VERITABANI_YOLU.exists():
        sifreli_yedek_adi = f"veri_deposu_{zaman_damgasi}.db.enc"
        dosya_yedekle(SIFRELI_VERITABANI_YOLU, sifreli_yedek_adi)
        olusturulan_yedekler.append(YEDEK_DIZINI / sifreli_yedek_adi)

    es_anlamlilar_yolu = VERILER_DIZINI / "es_anlamlilar.json"
    if es_anlamlilar_yolu.exists():
        es_anlamlilar_yedek_adi = f"es_anlamlilar_{zaman_damgasi}.json"
        dosya_yedekle(es_anlamlilar_yolu, es_anlamlilar_yedek_adi)
        olusturulan_yedekler.append(YEDEK_DIZINI / es_anlamlilar_yedek_adi)

    eski_yedekleri_temizle()
    return olusturulan_yedekler


def guvenli_yedek_yolunu_al(yedek_adi: str) -> Path:
    yedek_koku = YEDEK_DIZINI.resolve()
    yedek_yolu = (YEDEK_DIZINI / yedek_adi).resolve()
    try:
        yedek_yolu.relative_to(yedek_koku)
    except ValueError as hata:
        raise ValueError("Yedek yolu yedek dizini disina cikamaz") from hata
    if not yedek_yolu.is_file():
        raise FileNotFoundError("Yedek dosyasi bulunamadi")
    return yedek_yolu


def veritabanini_geri_yukle(yedek_adi: str) -> Path:
    yedek_yolu = guvenli_yedek_yolunu_al(yedek_adi)
    VERILER_DIZINI.mkdir(parents=True, exist_ok=True)

    if yedek_yolu.name.endswith(".db.enc"):
        if VERITABANI_YOLU.exists():
            raise RuntimeError("Sifreli geri yukleme icin uygulama durdurulmalidir")
        gecici_hedef = Path(f"{SIFRELI_VERITABANI_YOLU}.geri_yukleniyor")
        shutil.copy2(yedek_yolu, gecici_hedef)
        os.replace(gecici_hedef, SIFRELI_VERITABANI_YOLU)
        return SIFRELI_VERITABANI_YOLU

    if yedek_yolu.suffix != ".db":
        raise ValueError("Yalnizca .db veya .db.enc veritabani yedekleri yuklenebilir")

    veritabani_butunlugunu_dogrula(yedek_yolu)
    gecici_hedef = Path(f"{VERITABANI_YOLU}.geri_yukleniyor")
    kaynak_baglanti = sqlite3.connect(str(yedek_yolu))
    hedef_baglanti = sqlite3.connect(str(gecici_hedef))
    try:
        kaynak_baglanti.backup(hedef_baglanti)
    finally:
        hedef_baglanti.close()
        kaynak_baglanti.close()
    veritabani_butunlugunu_dogrula(gecici_hedef)
    os.replace(gecici_hedef, VERITABANI_YOLU)
    if SIFRELI_VERITABANI_YOLU.exists():
        SIFRELI_VERITABANI_YOLU.unlink()
    return VERITABANI_YOLU


def zamanli_yedeklemeyi_baslat(aralik_saat: float) -> None:
    if aralik_saat <= 0:
        raise ValueError("Yedekleme araligi sifirdan buyuk olmalidir")
    bekleme_suresi = aralik_saat * 60 * 60
    while True:
        olusturulan_yedekler = yedekle()
        zaman_damgasi = datetime.now(timezone.utc).isoformat()
        print(f"Yedekleme tamamlandi: {zaman_damgasi}, dosya={len(olusturulan_yedekler)}")
        time.sleep(bekleme_suresi)


def komut_satiri_ayristiricisini_olustur() -> argparse.ArgumentParser:
    ayristirici = argparse.ArgumentParser(prog="yedekle.py")
    alt_komutlar = ayristirici.add_subparsers(dest="komut")
    alt_komutlar.add_parser("yedekle")
    geri_yukle_komutu = alt_komutlar.add_parser("geri-yukle")
    geri_yukle_komutu.add_argument("yedek_adi")
    zamanla_komutu = alt_komutlar.add_parser("zamanla")
    zamanla_komutu.add_argument(
        "--aralik-saat",
        type=float,
        default=YEDEKLEME_ARALIGI_SAAT,
    )
    return ayristirici


def ana() -> None:
    ayristirici = komut_satiri_ayristiricisini_olustur()
    argumanlar = ayristirici.parse_args()
    if argumanlar.komut in (None, "yedekle"):
        olusturulan_yedekler = yedekle()
        print(f"Yedekleme tamamlandi: dosya={len(olusturulan_yedekler)}")
        return
    if argumanlar.komut == "geri-yukle":
        geri_yuklenen_yol = veritabanini_geri_yukle(argumanlar.yedek_adi)
        print(f"Geri yukleme tamamlandi: {geri_yuklenen_yol}")
        return
    zamanli_yedeklemeyi_baslat(argumanlar.aralik_saat)


if __name__ == "__main__":
    ana()
