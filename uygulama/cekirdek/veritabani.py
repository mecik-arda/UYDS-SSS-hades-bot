import sqlite3
from contextlib import contextmanager
from pathlib import Path

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.gunlukleyici import gunlukleyici


def baglanti_olustur() -> sqlite3.Connection:
    veritabani_yolu = Path(konfigurasyon.VERITABANI_YOLU)
    veritabani_yolu.parent.mkdir(parents=True, exist_ok=True)

    baglanti = sqlite3.connect(str(veritabani_yolu), check_same_thread=False)
    baglanti.execute("PRAGMA journal_mode=WAL")
    baglanti.execute("PRAGMA foreign_keys=ON")
    baglanti.row_factory = sqlite3.Row
    return baglanti


_baglanti = baglanti_olustur()


@contextmanager
def baglam_yoneticisi():
    try:
        yield _baglanti
        _baglanti.commit()
    except Exception as hata:
        _baglanti.rollback()
        gunlukleyici.error(f"Veritabani islemi hatasi: {hata}")
        raise