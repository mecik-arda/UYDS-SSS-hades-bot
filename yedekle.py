import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

VERILER_DIZINI = Path("veriler")
YEDEK_DIZINI = VERILER_DIZINI / "yedekler"
MAKSIMUM_YEDEK_SAYISI = 10


def veritabani_dosyasini_adiyla_yedekle(kaynak: Path, hedef_adi: str) -> None:
    if not kaynak.exists():
        return
    hedef = YEDEK_DIZINI / hedef_adi
    with sqlite3.connect(str(kaynak)) as kaynak_baglanti:
        yedek_baglanti = sqlite3.connect(str(hedef))
        kaynak_baglanti.backup(yedek_baglanti)
        yedek_baglanti.close()


def dosya_yedekle(kaynak: Path, hedef_adi: str) -> None:
    if not kaynak.exists():
        return
    hedef = YEDEK_DIZINI / hedef_adi
    shutil.copy2(str(kaynak), str(hedef))


def eski_yedekleri_temizle() -> None:
    yedek_dosyalari = sorted(YEDEK_DIZINI.glob("*"), key=lambda p: p.stat().st_mtime)
    while len(yedek_dosyalari) > MAKSIMUM_YEDEK_SAYISI:
        en_eski = yedek_dosyalari.pop(0)
        en_eski.unlink()


def yedekle() -> None:
    YEDEK_DIZINI.mkdir(parents=True, exist_ok=True)
    zaman_damgasi = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    veritabani_yolu = VERILER_DIZINI / "veri_deposu.db"
    veritabani_dosyasini_adiyla_yedekle(veritabani_yolu, f"veri_deposu_{zaman_damgasi}.db")

    es_anlamlilar_yolu = VERILER_DIZINI / "es_anlamlilar.json"
    dosya_yedekle(es_anlamlilar_yolu, f"es_anlamlilar_{zaman_damgasi}.json")

    eski_yedekleri_temizle()
    print(f"Yedekleme tamamlandi: {zaman_damgasi}")


if __name__ == "__main__":
    yedekle()