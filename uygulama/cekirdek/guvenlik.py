import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi

oauth2_semasi = OAuth2PasswordBearer(tokenUrl="/api/v1/kimlik-dogrulama/giris")

_HESAP_KILITLEME_ESIK = 5
_HESAP_KILITLEME_SURE_DAKIKA = 15


class BelirtecVerisi(BaseModel):
    kullanici_adi: str
    rol: str


class KullaniciBilgisi(BaseModel):
    kullanici_adi: str
    rol: str
    aktif_mi: bool = True


def sifre_hash_olustur(duz_metin_sifre: str) -> str:
    sifre_baytlari = duz_metin_sifre.encode("utf-8")
    if len(sifre_baytlari) > 72:
        raise ValueError("Sifre bcrypt icin izin verilen 72 bayti asamaz")
    return bcrypt.hashpw(sifre_baytlari, bcrypt.gensalt(rounds=12)).decode("utf-8")


def sifre_dogrula(duz_metin_sifre: str, hash_degeri: str) -> bool:
    try:
        return bcrypt.checkpw(
            duz_metin_sifre.encode("utf-8"),
            hash_degeri.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def erisim_belirteci_olustur(veri: BelirtecVerisi) -> str:
    sonlanma = datetime.now(timezone.utc) + timedelta(minutes=konfigurasyon.JWT_OMRU_DAKIKA)
    odeme = {
        "sub": veri.kullanici_adi,
        "rol": veri.rol,
        "exp": sonlanma,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(odeme, konfigurasyon.JWT_GIZLI_ANAHTARI, algorithm=konfigurasyon.JWT_ALGORITMASI)


def belirtec_coz(belirtec: str) -> BelirtecVerisi | None:
    try:
        odeme = jwt.decode(
            belirtec,
            konfigurasyon.JWT_GIZLI_ANAHTARI,
            algorithms=[konfigurasyon.JWT_ALGORITMASI],
        )
        kullanici_adi: str = odeme.get("sub")
        rol: str = odeme.get("rol")
        if kullanici_adi is None or rol is None:
            return None
        return BelirtecVerisi(kullanici_adi=kullanici_adi, rol=rol)
    except JWTError:
        return None


def _kullaniciyi_veritabanindan_al(kullanici_adi: str) -> dict | None:
    with baglam_yoneticisi() as baglanti:
        imlec = baglanti.execute(
            "SELECT kullanici_adi, rol, aktif_mi FROM kullanicilar WHERE kullanici_adi = ?",
            (kullanici_adi,),
        )
        satir = imlec.fetchone()
        if satir is None:
            return None
        return {
            "kullanici_adi": satir["kullanici_adi"],
            "rol": satir["rol"],
            "aktif_mi": bool(satir["aktif_mi"]),
        }


async def mevcut_kullaniciyi_al(belirtec: Annotated[str, Depends(oauth2_semasi)]) -> KullaniciBilgisi:
    kimlik_kontrolu = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Gecersiz kimlik bilgileri",
        headers={"WWW-Authenticate": "Bearer"},
    )
    veri = belirtec_coz(belirtec)
    if veri is None:
        raise kimlik_kontrolu
    satir = await asyncio.to_thread(_kullaniciyi_veritabanindan_al, veri.kullanici_adi)
    if satir is None:
        raise kimlik_kontrolu
    if not satir["aktif_mi"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabiniz devre disi birakilmistir",
        )
    return KullaniciBilgisi(
        kullanici_adi=satir["kullanici_adi"],
        rol=satir["rol"],
        aktif_mi=satir["aktif_mi"],
    )


async def mevcut_yoneticiyi_al(
    mevcut_kullanici: Annotated[KullaniciBilgisi, Depends(mevcut_kullaniciyi_al)]
) -> KullaniciBilgisi:
    if mevcut_kullanici.rol != "YONETICI":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu islem icin yonetici yetkisi gereklidir",
        )
    return mevcut_kullanici


def _giris_kimlikleri(kullanici_adi: str, ip_adresi: str | None) -> list[str]:
    ham_kimlikler = [f"kullanici:{kullanici_adi.casefold()}"]
    if ip_adresi:
        ham_kimlikler.append(f"ip:{ip_adresi.strip().casefold()}")
    return [
        hashlib.sha256(kimlik.encode("utf-8")).hexdigest()
        for kimlik in ham_kimlikler
    ]


def brute_force_kontrol(kullanici_adi: str, ip_adresi: str | None = None) -> None:
    simdi = datetime.now(timezone.utc)
    kilitli_kimlik_var = False
    with baglam_yoneticisi() as baglanti:
        for giris_kimligi in _giris_kimlikleri(kullanici_adi, ip_adresi):
            satir = baglanti.execute(
                """
                SELECT kilitlenme_tarihi
                FROM giris_deneme_kayitlari
                WHERE kimlik_ozeti = ?
                """,
                (giris_kimligi,),
            ).fetchone()
            if satir is None or satir["kilitlenme_tarihi"] is None:
                continue
            kilit_zamani = datetime.fromisoformat(satir["kilitlenme_tarihi"])
            if kilit_zamani.tzinfo is None:
                kilit_zamani = kilit_zamani.replace(tzinfo=timezone.utc)
            gecen_sure = (simdi - kilit_zamani).total_seconds()
            if gecen_sure < _HESAP_KILITLEME_SURE_DAKIKA * 60:
                kilitli_kimlik_var = True
                continue
            baglanti.execute(
                """
                DELETE FROM giris_deneme_kayitlari
                WHERE kimlik_ozeti = ?
                """,
                (giris_kimligi,),
            )
    if kilitli_kimlik_var:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Cok fazla basarisiz giris denemesi. Lutfen 15 dakika sonra tekrar deneyin.",
        )


def basarisiz_giris_kaydet(
    kullanici_adi: str,
    ip_adresi: str | None = None,
) -> None:
    simdi = datetime.now(timezone.utc).isoformat()
    with baglam_yoneticisi() as baglanti:
        for giris_kimligi in _giris_kimlikleri(kullanici_adi, ip_adresi):
            baglanti.execute(
                """
                INSERT INTO giris_deneme_kayitlari (
                    kimlik_ozeti,
                    basarisiz_deneme_sayisi,
                    kilitlenme_tarihi,
                    son_deneme_tarihi
                )
                VALUES (?, 1, NULL, ?)
                ON CONFLICT(kimlik_ozeti) DO UPDATE SET
                    basarisiz_deneme_sayisi =
                        giris_deneme_kayitlari.basarisiz_deneme_sayisi + 1,
                    kilitlenme_tarihi = CASE
                        WHEN giris_deneme_kayitlari.basarisiz_deneme_sayisi + 1 >= ?
                        THEN COALESCE(
                            giris_deneme_kayitlari.kilitlenme_tarihi,
                            excluded.son_deneme_tarihi
                        )
                        ELSE giris_deneme_kayitlari.kilitlenme_tarihi
                    END,
                    son_deneme_tarihi = excluded.son_deneme_tarihi
                """,
                (giris_kimligi, simdi, _HESAP_KILITLEME_ESIK),
            )


def basarili_giris_sifirla(
    kullanici_adi: str,
    ip_adresi: str | None = None,
) -> None:
    with baglam_yoneticisi() as baglanti:
        for giris_kimligi in _giris_kimlikleri(kullanici_adi, ip_adresi):
            baglanti.execute(
                """
                DELETE FROM giris_deneme_kayitlari
                WHERE kimlik_ozeti = ?
                """,
                (giris_kimligi,),
            )
