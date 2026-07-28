import argparse
import hashlib
import json
import math
import os
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from uygulama.cekirdek.dosya_kilidi import surecler_arasi_veritabani_kilidi

VERILER_DIZINI = Path("veriler")
YEDEK_DIZINI = VERILER_DIZINI / "yedekler"
VERITABANI_YOLU = Path(
    os.getenv("VERITABANI_YOLU", str(VERILER_DIZINI / "veri_deposu.db"))
)
SIFRELI_VERITABANI_YOLU = (
    VERITABANI_YOLU.parent / f"{VERITABANI_YOLU.name}.enc"
)
ES_ANLAMLILAR_YOLU = Path(
    os.getenv("ES_ANLAMLILAR_YOLU", str(VERILER_DIZINI / "es_anlamlilar.json"))
)


def pozitif_tamsayi_ortam_degiskenini_oku(
    degisken_adi: str,
    varsayilan_deger: int,
) -> int:
    ham_deger = os.getenv(degisken_adi)
    if ham_deger is None:
        return varsayilan_deger
    try:
        deger = int(ham_deger)
    except ValueError as hata:
        raise ValueError(f"{degisken_adi} pozitif bir tam sayi olmalidir") from hata
    if deger < 1:
        raise ValueError(f"{degisken_adi} en az 1 olmalidir")
    return deger


def pozitif_ondalik_ortam_degiskenini_oku(
    degisken_adi: str,
    varsayilan_deger: float,
) -> float:
    ham_deger = os.getenv(degisken_adi)
    if ham_deger is None:
        return varsayilan_deger
    try:
        deger = float(ham_deger)
    except ValueError as hata:
        raise ValueError(f"{degisken_adi} pozitif bir sayi olmalidir") from hata
    if not math.isfinite(deger) or deger <= 0:
        raise ValueError(f"{degisken_adi} sifirdan buyuk olmalidir")
    return deger


def veritabani_butunlugunu_dogrula(veritabani_yolu: Path) -> None:
    baglanti = sqlite3.connect(str(veritabani_yolu))
    try:
        sonuc = baglanti.execute("PRAGMA integrity_check").fetchone()
    finally:
        baglanti.close()
    if sonuc is None or sonuc[0] != "ok":
        raise sqlite3.DatabaseError("Veritabani butunluk denetimi basarisiz")


def dosya_ozetini_hesapla(dosya_yolu: Path) -> str:
    ozetleyici = hashlib.sha256()
    with dosya_yolu.open("rb") as dosya:
        for parca in iter(lambda: dosya.read(1024 * 1024), b""):
            ozetleyici.update(parca)
    return ozetleyici.hexdigest()


def manifest_yolunu_al(yedek_yolu: Path) -> Path:
    return Path(f"{yedek_yolu}.manifest.json")


def veritabani_manifest_bilgilerini_al(
    veritabani_yolu: Path,
) -> dict[str, int | str | None]:
    baglanti = sqlite3.connect(str(veritabani_yolu))
    try:
        tablo_adlari = {
            satir[0]
            for satir in baglanti.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }
        aktif_kayit_sayisi = (
            baglanti.execute(
                """
                SELECT COUNT(*)
                FROM sss_kayitlari
                WHERE durum = 'aktif'
                """
            ).fetchone()[0]
            if "sss_kayitlari" in tablo_adlari
            else None
        )
        fts_kayit_sayisi = (
            baglanti.execute("SELECT COUNT(*) FROM sss_fts").fetchone()[0]
            if "sss_fts" in tablo_adlari
            else None
        )
        veri_surumu = (
            baglanti.execute(
                "SELECT MAX(surum_numarasi) FROM veri_surumleri"
            ).fetchone()[0]
            if "veri_surumleri" in tablo_adlari
            else None
        )
        butunluk = baglanti.execute("PRAGMA quick_check").fetchone()[0]
    finally:
        baglanti.close()
    return {
        "aktif_kayit_sayisi": aktif_kayit_sayisi,
        "fts_kayit_sayisi": fts_kayit_sayisi,
        "veri_surumu": veri_surumu,
        "butunluk": butunluk,
    }


def yedek_manifesti_olustur(yedek_yolu: Path) -> Path:
    manifest = {
        "manifest_surumu": 1,
        "dosya_adi": yedek_yolu.name,
        "dosya_boyutu": yedek_yolu.stat().st_size,
        "sha256": dosya_ozetini_hesapla(yedek_yolu),
        "olusturulma_tarihi": datetime.now(timezone.utc).isoformat(),
        "veritabani": (
            veritabani_manifest_bilgilerini_al(yedek_yolu)
            if yedek_yolu.suffix == ".db"
            else None
        ),
    }
    manifest_yolu = manifest_yolunu_al(yedek_yolu)
    gecici_manifest_yolu = Path(f"{manifest_yolu}.yaziliyor")
    gecici_manifest_yolu.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    os.replace(gecici_manifest_yolu, manifest_yolu)
    return manifest_yolu


def yedek_manifestini_dogrula(yedek_yolu: Path) -> None:
    manifest_yolu = manifest_yolunu_al(yedek_yolu)
    if not manifest_yolu.exists():
        return
    try:
        manifest = json.loads(manifest_yolu.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as hata:
        raise ValueError("Yedek manifesti gecerli JSON icermiyor") from hata
    if not isinstance(manifest, dict):
        raise ValueError("Yedek manifesti JSON nesnesi olmalidir")
    if manifest.get("manifest_surumu") != 1:
        raise ValueError("Yedek manifest surumu desteklenmiyor")
    if manifest.get("dosya_adi") != yedek_yolu.name:
        raise ValueError("Yedek manifest dosya adi eslesmiyor")
    if manifest.get("dosya_boyutu") != yedek_yolu.stat().st_size:
        raise ValueError("Yedek dosya boyutu manifest ile eslesmiyor")
    if manifest.get("sha256") != dosya_ozetini_hesapla(yedek_yolu):
        raise ValueError("Yedek dosya ozeti manifest ile eslesmiyor")


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
    maksimum_yedek_sayisi = pozitif_tamsayi_ortam_degiskenini_oku(
        "MAKSIMUM_YEDEK_SAYISI",
        10,
    )
    mevcut_yedekler = yedek_dosyalari()
    while len(mevcut_yedekler) > maksimum_yedek_sayisi:
        eski_yedek = mevcut_yedekler.pop(0)
        eski_yedek.unlink()
        eski_manifest = manifest_yolunu_al(eski_yedek)
        if eski_manifest.exists():
            eski_manifest.unlink()


def yedekle() -> list[Path]:
    YEDEK_DIZINI.mkdir(parents=True, exist_ok=True)
    zaman_damgasi = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    olusturulan_yedekler: list[Path] = []

    with surecler_arasi_veritabani_kilidi(
        VERITABANI_YOLU,
        paylasimli=True,
    ):
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
        else:
            raise FileNotFoundError(
                f"Yedeklenecek veritabani bulunamadi: {VERITABANI_YOLU}"
            )

    if ES_ANLAMLILAR_YOLU.exists():
        es_anlamlilar_yedek_adi = f"es_anlamlilar_{zaman_damgasi}.json"
        dosya_yedekle(ES_ANLAMLILAR_YOLU, es_anlamlilar_yedek_adi)
        olusturulan_yedekler.append(YEDEK_DIZINI / es_anlamlilar_yedek_adi)

    for yedek_yolu in olusturulan_yedekler:
        yedek_manifesti_olustur(yedek_yolu)
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
    yedek_manifestini_dogrula(yedek_yolu)
    VERILER_DIZINI.mkdir(parents=True, exist_ok=True)

    with surecler_arasi_veritabani_kilidi(
        VERITABANI_YOLU,
        paylasimli=False,
    ):
        if yedek_yolu.name.endswith(".db.enc"):
            if VERITABANI_YOLU.exists():
                raise RuntimeError(
                    "Sifreli geri yukleme icin uygulama durdurulmalidir"
                )
            gecici_hedef = Path(f"{SIFRELI_VERITABANI_YOLU}.geri_yukleniyor")
            shutil.copy2(yedek_yolu, gecici_hedef)
            os.replace(gecici_hedef, SIFRELI_VERITABANI_YOLU)
            return SIFRELI_VERITABANI_YOLU

        if yedek_yolu.suffix != ".db":
            raise ValueError(
                "Yalnizca .db veya .db.enc veritabani yedekleri yuklenebilir"
            )

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
    if not math.isfinite(aralik_saat) or aralik_saat <= 0:
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
        default=None,
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
    aralik_saat = (
        argumanlar.aralik_saat
        if argumanlar.aralik_saat is not None
        else pozitif_ondalik_ortam_degiskenini_oku(
            "YEDEKLEME_ARALIGI_SAAT",
            24,
        )
    )
    zamanli_yedeklemeyi_baslat(aralik_saat)


if __name__ == "__main__":
    ana()
