import base64
import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.gunlukleyici import gunlukleyici


def _sifreleme_anahtari_olustur() -> bytes:
    ham_anahtar = konfigurasyon.JWT_GIZLI_ANAHTARI.encode("utf-8")
    turetilmis = hashlib.sha256(ham_anahtar).digest()
    return base64.urlsafe_b64encode(turetilmis)


_sifreleyici = Fernet(_sifreleme_anahtari_olustur())


def baglanti_olustur() -> sqlite3.Connection:
    veritabani_yolu = Path(konfigurasyon.VERITABANI_YOLU)
    veritabani_yolu.parent.mkdir(parents=True, exist_ok=True)

    sifreli_yol = veritabani_yolu.parent / f"{veritabani_yolu.name}.enc"

    if sifreli_yol.exists():
        try:
            sifreli_veri = sifreli_yol.read_bytes()
            cozulmus_veri = _sifreleyici.decrypt(sifreli_veri)
            veritabani_yolu.write_bytes(cozulmus_veri)
        except Exception as hata:
            gunlukleyici.warning(f"Veritabani cozme hatasi, sifresiz dosya kullaniliyor: {hata}")

    baglanti = sqlite3.connect(str(veritabani_yolu), check_same_thread=False)
    baglanti.execute("PRAGMA journal_mode=WAL")
    baglanti.execute("PRAGMA foreign_keys=ON")
    baglanti.row_factory = sqlite3.Row
    return baglanti


def veritabanini_sifrele() -> None:
    veritabani_yolu = Path(konfigurasyon.VERITABANI_YOLU)
    if not veritabani_yolu.exists():
        return
    sifreli_yol = veritabani_yolu.parent / f"{veritabani_yolu.name}.enc"
    try:
        ham_veri = veritabani_yolu.read_bytes()
        sifreli_veri = _sifreleyici.encrypt(ham_veri)
        sifreli_yol.write_bytes(sifreli_veri)
        gunlukleyici.info("Veritabani basariyla sifrelendi")
    except Exception as hata:
        gunlukleyici.error(f"Veritabani sifreleme hatasi: {hata}")


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