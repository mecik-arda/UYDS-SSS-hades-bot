import asyncio
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi

sifre_baglami = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_semasi = OAuth2PasswordBearer(tokenUrl="/api/v1/kimlik-dogrulama/giris")


class BelirtecVerisi(BaseModel):
    kullanici_adi: str
    rol: str


class KullaniciBilgisi(BaseModel):
    kullanici_adi: str
    rol: str
    aktif_mi: bool = True


def sifre_hash_olustur(duz_metin_sifre: str) -> str:
    return sifre_baglami.hash(duz_metin_sifre)


def sifre_dogrula(duz_metin_sifre: str, hash_degeri: str) -> bool:
    return sifre_baglami.verify(duz_metin_sifre, hash_degeri)


def erisim_belirteci_olustur(veri: BelirtecVerisi) -> str:
    sonlanma = datetime.now(timezone.utc) + timedelta(minutes=konfigurasyon.JWT_OMRU_DAKIKA)
    odeme = {
        "sub": veri.kullanici_adi,
        "rol": veri.rol,
        "exp": sonlanma,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(odeme, konfigurasyon.JWT_GIZLI_ANAHTARI, algorithm=konfigurasyon.JWT_ALGORITMASI)


def belirtec_coz(belirtec: str) -> Optional[BelirtecVerisi]:
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


def _kullaniciyi_veritabanindan_al(kullanici_adi: str) -> Optional[dict]:
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