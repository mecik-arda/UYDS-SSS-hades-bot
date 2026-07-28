import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.konfigurasyon import konfigurasyon

_SIFRELI_DOSYA_IMZASI = b"HADESDB2"
_TUZ_BOYUTU = 16
_NONCE_BOYUTU = 12
_ANAHTAR_TURETME_TURU = 600000
_DOSYA_ISLEMI_KILIDI = Lock()


def _veritabani_yollarini_al() -> tuple[Path, Path]:
    veritabani_yolu = Path(konfigurasyon.VERITABANI_YOLU)
    sifreli_yol = veritabani_yolu.parent / f"{veritabani_yolu.name}.enc"
    return veritabani_yolu, sifreli_yol


def _sifreleme_anahtari_olustur(tuz: bytes) -> bytes:
    anahtar_tureteci = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=tuz,
        iterations=_ANAHTAR_TURETME_TURU,
    )
    return anahtar_tureteci.derive(
        konfigurasyon.VERITABANI_SIFRELEME_ANAHTARI.encode("utf-8")
    )


def _sifreli_veritabanini_coz() -> None:
    veritabani_yolu, sifreli_yol = _veritabani_yollarini_al()
    if veritabani_yolu.exists() or not sifreli_yol.exists():
        return

    sifreli_veri = sifreli_yol.read_bytes()
    en_az_boyut = len(_SIFRELI_DOSYA_IMZASI) + _TUZ_BOYUTU + _NONCE_BOYUTU + 16
    if len(sifreli_veri) < en_az_boyut:
        raise ValueError("Sifreli veritabani dosyasi gecersiz")
    if not sifreli_veri.startswith(_SIFRELI_DOSYA_IMZASI):
        raise ValueError("Sifreli veritabani dosya imzasi gecersiz")

    imza_boyutu = len(_SIFRELI_DOSYA_IMZASI)
    tuz = sifreli_veri[imza_boyutu : imza_boyutu + _TUZ_BOYUTU]
    nonce_baslangici = imza_boyutu + _TUZ_BOYUTU
    nonce = sifreli_veri[nonce_baslangici : nonce_baslangici + _NONCE_BOYUTU]
    sifreli_icerik = sifreli_veri[nonce_baslangici + _NONCE_BOYUTU :]
    sifreleyici = AESGCM(_sifreleme_anahtari_olustur(tuz))
    ham_veri = sifreleyici.decrypt(nonce, sifreli_icerik, _SIFRELI_DOSYA_IMZASI)

    veritabani_yolu.parent.mkdir(parents=True, exist_ok=True)
    gecici_yol = veritabani_yolu.parent / f"{veritabani_yolu.name}.cozuluyor"
    gecici_yol.write_bytes(ham_veri)
    os.replace(gecici_yol, veritabani_yolu)
    gunlukleyici.info("Sifreli veritabani kullanima hazirlandi")


def baglanti_olustur() -> sqlite3.Connection:
    with _DOSYA_ISLEMI_KILIDI:
        _sifreli_veritabanini_coz()
    veritabani_yolu, _ = _veritabani_yollarini_al()
    veritabani_yolu.parent.mkdir(parents=True, exist_ok=True)
    baglanti = sqlite3.connect(
        str(veritabani_yolu),
        timeout=30,
        check_same_thread=False,
    )
    baglanti.execute("PRAGMA journal_mode=WAL")
    baglanti.execute("PRAGMA foreign_keys=ON")
    baglanti.execute("PRAGMA busy_timeout=5000")
    baglanti.row_factory = sqlite3.Row
    return baglanti


def veritabanini_sifrele() -> None:
    with _DOSYA_ISLEMI_KILIDI:
        veritabani_yolu, sifreli_yol = _veritabani_yollarini_al()
        if not veritabani_yolu.exists():
            return

        baglanti = sqlite3.connect(str(veritabani_yolu), timeout=30)
        try:
            denetim_sonucu = baglanti.execute("PRAGMA integrity_check").fetchone()
            if denetim_sonucu is None or denetim_sonucu[0] != "ok":
                raise sqlite3.DatabaseError("Veritabani butunluk denetimi basarisiz")
            baglanti.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            baglanti.close()

        ham_veri = veritabani_yolu.read_bytes()
        tuz = os.urandom(_TUZ_BOYUTU)
        nonce = os.urandom(_NONCE_BOYUTU)
        sifreleyici = AESGCM(_sifreleme_anahtari_olustur(tuz))
        sifreli_icerik = sifreleyici.encrypt(
            nonce,
            ham_veri,
            _SIFRELI_DOSYA_IMZASI,
        )
        sifreli_veri = _SIFRELI_DOSYA_IMZASI + tuz + nonce + sifreli_icerik
        gecici_yol = sifreli_yol.parent / f"{sifreli_yol.name}.yaziliyor"
        gecici_yol.write_bytes(sifreli_veri)

        sifreli_veri_dogrulama = gecici_yol.read_bytes()
        dogrulama_tuzu = sifreli_veri_dogrulama[
            len(_SIFRELI_DOSYA_IMZASI) : len(_SIFRELI_DOSYA_IMZASI) + _TUZ_BOYUTU
        ]
        dogrulama_nonce_baslangici = len(_SIFRELI_DOSYA_IMZASI) + _TUZ_BOYUTU
        dogrulama_nonce = sifreli_veri_dogrulama[
            dogrulama_nonce_baslangici : dogrulama_nonce_baslangici + _NONCE_BOYUTU
        ]
        dogrulama_icerigi = sifreli_veri_dogrulama[
            dogrulama_nonce_baslangici + _NONCE_BOYUTU :
        ]
        dogrulama_sifreleyicisi = AESGCM(
            _sifreleme_anahtari_olustur(dogrulama_tuzu)
        )
        dogrulanan_veri = dogrulama_sifreleyicisi.decrypt(
            dogrulama_nonce,
            dogrulama_icerigi,
            _SIFRELI_DOSYA_IMZASI,
        )
        if dogrulanan_veri != ham_veri:
            raise ValueError("Sifreli veritabani dogrulamasi basarisiz")

        os.replace(gecici_yol, sifreli_yol)
        veritabani_yolu.unlink()
        for yan_dosya_eki in ("-wal", "-shm"):
            yan_dosya = Path(f"{veritabani_yolu}{yan_dosya_eki}")
            if yan_dosya.exists():
                yan_dosya.unlink()
        gunlukleyici.info("Veritabani AES-256-GCM ile sifrelendi")


@contextmanager
def baglam_yoneticisi():
    baglanti = baglanti_olustur()
    try:
        yield baglanti
        baglanti.commit()
    except Exception as hata:
        baglanti.rollback()
        gunlukleyici.error(f"Veritabani islemi hatasi: {hata}")
        raise
    finally:
        baglanti.close()
