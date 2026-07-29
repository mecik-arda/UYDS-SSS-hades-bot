import asyncio
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi

oauth2_semasi = OAuth2PasswordBearer(
    tokenUrl="/api/v1/kimlik-dogrulama/giris"
)

_HESAP_KILITLEME_ESIK = 5
_HESAP_KILITLEME_SURE_DAKIKA = 15
_BELIRTEC_YAYINCISI = "uyds-asistani"
_BELIRTEC_HEDEFI = "uyds-api"


class BelirtecHatasi(ValueError):
    def __init__(self, mesaj: str) -> None:
        super().__init__(mesaj)


class BelirtecVerisi(BaseModel):
    kullanici_adi: str
    rol: str
    jti: str = ""
    sona_erme_zamani: int = 0


class KullaniciBilgisi(BaseModel):
    kullanici_adi: str
    rol: str
    aktif_mi: bool = True


@dataclass(frozen=True)
class YenilemeBelirteci:
    belirtec: str
    jti: str
    aile_id: str
    sona_erme_tarihi: datetime


@dataclass(frozen=True)
class GuvenlikBakimSonucu:
    silinen_yenileme_belirteci_sayisi: int
    silinen_erisim_karaliste_sayisi: int
    silinen_yonetici_nonce_sayisi: int


def suresi_dolmus_guvenlik_kayitlarini_temizle(
    simdi: datetime | None = None,
) -> GuvenlikBakimSonucu:
    denetim_zamani = simdi or datetime.now(timezone.utc)
    if denetim_zamani.tzinfo is None:
        denetim_zamani = denetim_zamani.replace(tzinfo=timezone.utc)
    zaman_metni = denetim_zamani.isoformat()
    with baglam_yoneticisi() as baglanti:
        baglanti.execute("BEGIN IMMEDIATE")
        yenileme_imleci = baglanti.execute(
            """
            DELETE FROM yenileme_belirtecleri
            WHERE aile_id IN (
                SELECT aile_id
                FROM yenileme_belirtecleri
                GROUP BY aile_id
                HAVING MAX(sona_erme_tarihi) <= ?
            )
            """,
            (zaman_metni,),
        )
        erisim_imleci = baglanti.execute(
            """
            DELETE FROM gecersiz_erisim_belirtecleri
            WHERE sona_erme_tarihi <= ?
            """,
            (zaman_metni,),
        )
        nonce_imleci = baglanti.execute(
            """
            DELETE FROM yonetici_imza_nonce_kayitlari
            WHERE sona_erme_tarihi <= ?
            """,
            (zaman_metni,),
        )
    return GuvenlikBakimSonucu(
        silinen_yenileme_belirteci_sayisi=max(yenileme_imleci.rowcount, 0),
        silinen_erisim_karaliste_sayisi=max(erisim_imleci.rowcount, 0),
        silinen_yonetici_nonce_sayisi=max(nonce_imleci.rowcount, 0),
    )


def sifre_hash_olustur(duz_metin_sifre: str) -> str:
    sifre_baytlari = duz_metin_sifre.encode("utf-8")
    if len(sifre_baytlari) > 72:
        raise ValueError("Sifre bcrypt icin izin verilen 72 bayti asamaz")
    return bcrypt.hashpw(
        sifre_baytlari,
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def sifre_dogrula(duz_metin_sifre: str, hash_degeri: str) -> bool:
    try:
        return bcrypt.checkpw(
            duz_metin_sifre.encode("utf-8"),
            hash_degeri.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def erisim_belirteci_olustur(veri: BelirtecVerisi) -> str:
    simdi = datetime.now(timezone.utc)
    sonlanma = simdi + timedelta(minutes=konfigurasyon.JWT_OMRU_DAKIKA)
    odeme = {
        "sub": veri.kullanici_adi,
        "rol": veri.rol,
        "jti": uuid4().hex,
        "tur": "erisim",
        "iss": _BELIRTEC_YAYINCISI,
        "aud": _BELIRTEC_HEDEFI,
        "exp": sonlanma,
        "iat": simdi,
        "nbf": simdi,
    }
    return jwt.encode(
        odeme,
        konfigurasyon.JWT_GIZLI_ANAHTARI,
        algorithm=konfigurasyon.JWT_ALGORITMASI,
        headers={"kid": konfigurasyon.JWT_ANAHTAR_KIMLIGI},
    )


def _jwt_anahtarini_sec(belirtec: str) -> str | None:
    try:
        baslik = jwt.get_unverified_header(belirtec)
    except jwt.InvalidTokenError:
        return None
    anahtar_kimligi = baslik.get("kid")
    if anahtar_kimligi == konfigurasyon.JWT_ANAHTAR_KIMLIGI:
        return konfigurasyon.JWT_GIZLI_ANAHTARI
    if (
        konfigurasyon.JWT_ONCEKI_GIZLI_ANAHTAR
        and anahtar_kimligi == konfigurasyon.JWT_ONCEKI_ANAHTAR_KIMLIGI
    ):
        return konfigurasyon.JWT_ONCEKI_GIZLI_ANAHTAR
    return None


def belirtec_coz(belirtec: str) -> BelirtecVerisi | None:
    anahtar = _jwt_anahtarini_sec(belirtec)
    if anahtar is None:
        return None
    try:
        odeme = jwt.decode(
            belirtec,
            anahtar,
            algorithms=[konfigurasyon.JWT_ALGORITMASI],
            audience=_BELIRTEC_HEDEFI,
            issuer=_BELIRTEC_YAYINCISI,
            options={
                "require": [
                    "sub",
                    "rol",
                    "jti",
                    "tur",
                    "exp",
                    "iat",
                    "nbf",
                ]
            },
        )
        if odeme.get("tur") != "erisim":
            return None
        kullanici_adi = odeme.get("sub")
        rol = odeme.get("rol")
        jti = odeme.get("jti")
        sona_erme_zamani = odeme.get("exp")
        if not all(
            isinstance(deger, str) and deger
            for deger in (kullanici_adi, rol, jti)
        ):
            return None
        if not isinstance(sona_erme_zamani, int):
            return None
        if _erisim_belirteci_gecersiz_mi(jti):
            return None
        return BelirtecVerisi(
            kullanici_adi=kullanici_adi,
            rol=rol,
            jti=jti,
            sona_erme_zamani=sona_erme_zamani,
        )
    except jwt.InvalidTokenError:
        return None


def _erisim_belirteci_gecersiz_mi(jti: str) -> bool:
    simdi = datetime.now(timezone.utc).isoformat()
    with baglam_yoneticisi() as baglanti:
        baglanti.execute(
            """
            DELETE FROM gecersiz_erisim_belirtecleri
            WHERE sona_erme_tarihi <= ?
            """,
            (simdi,),
        )
        satir = baglanti.execute(
            """
            SELECT 1
            FROM gecersiz_erisim_belirtecleri
            WHERE jti = ?
            """,
            (jti,),
        ).fetchone()
    return satir is not None


def erisim_belirtecini_gecersiz_kil(veri: BelirtecVerisi) -> None:
    sona_erme_tarihi = datetime.fromtimestamp(
        veri.sona_erme_zamani,
        tz=timezone.utc,
    ).isoformat()
    with baglam_yoneticisi() as baglanti:
        baglanti.execute(
            """
            INSERT OR IGNORE INTO gecersiz_erisim_belirtecleri (
                jti,
                sona_erme_tarihi,
                gecersiz_kilinma_tarihi
            )
            VALUES (?, ?, ?)
            """,
            (
                veri.jti,
                sona_erme_tarihi,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def _belirtec_ozetini_hesapla(belirtec: str) -> str:
    return hashlib.sha256(belirtec.encode("utf-8")).hexdigest()


def _ip_ozetini_hesapla(ip_adresi: str | None) -> str | None:
    if not ip_adresi:
        return None
    ham_deger = (
        f"{ip_adresi.strip().casefold()}:{konfigurasyon.JWT_GIZLI_ANAHTARI}"
    )
    return hashlib.sha256(ham_deger.encode("utf-8")).hexdigest()


def _yenileme_belirteci_degerlerini_olustur(
    aile_id: str | None = None,
) -> YenilemeBelirteci:
    simdi = datetime.now(timezone.utc)
    return YenilemeBelirteci(
        belirtec=secrets.token_urlsafe(64),
        jti=uuid4().hex,
        aile_id=aile_id or uuid4().hex,
        sona_erme_tarihi=simdi
        + timedelta(days=konfigurasyon.JWT_YENILEME_OMRU_GUN),
    )


def yenileme_belirteci_olustur(
    kullanici_adi: str,
    ip_adresi: str | None = None,
) -> YenilemeBelirteci:
    sonuc = _yenileme_belirteci_degerlerini_olustur()
    simdi = datetime.now(timezone.utc).isoformat()
    with baglam_yoneticisi() as baglanti:
        baglanti.execute(
            """
            INSERT INTO yenileme_belirtecleri (
                jti,
                aile_id,
                kullanici_adi,
                belirtec_ozeti,
                sona_erme_tarihi,
                olusturulma_tarihi,
                ip_ozeti
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sonuc.jti,
                sonuc.aile_id,
                kullanici_adi,
                _belirtec_ozetini_hesapla(sonuc.belirtec),
                sonuc.sona_erme_tarihi.isoformat(),
                simdi,
                _ip_ozetini_hesapla(ip_adresi),
            ),
        )
    return sonuc


def yenileme_belirtecini_dondur(
    belirtec: str,
    ip_adresi: str | None = None,
) -> tuple[YenilemeBelirteci, KullaniciBilgisi]:
    belirtec_ozeti = _belirtec_ozetini_hesapla(belirtec)
    simdi = datetime.now(timezone.utc)
    yeni_belirtec = None
    kullanici = None
    reddetme_mesaji = None
    with baglam_yoneticisi() as baglanti:
        baglanti.execute("BEGIN IMMEDIATE")
        satir = baglanti.execute(
            """
            SELECT
                y.jti,
                y.aile_id,
                y.kullanici_adi,
                y.sona_erme_tarihi,
                y.gecersiz_kilindi_mi,
                k.rol,
                k.aktif_mi
            FROM yenileme_belirtecleri y
            JOIN kullanicilar k ON k.kullanici_adi = y.kullanici_adi
            WHERE y.belirtec_ozeti = ?
            """,
            (belirtec_ozeti,),
        ).fetchone()
        if satir is None:
            raise BelirtecHatasi("Gecersiz yenileme belirteci")
        sona_erme_tarihi = datetime.fromisoformat(satir["sona_erme_tarihi"])
        if sona_erme_tarihi.tzinfo is None:
            sona_erme_tarihi = sona_erme_tarihi.replace(tzinfo=timezone.utc)
        if satir["gecersiz_kilindi_mi"]:
            baglanti.execute(
                """
                UPDATE yenileme_belirtecleri
                SET gecersiz_kilindi_mi = 1
                WHERE aile_id = ?
                """,
                (satir["aile_id"],),
            )
            reddetme_mesaji = "Yenileme belirteci tekrar kullanildi"
        elif sona_erme_tarihi <= simdi or not satir["aktif_mi"]:
            baglanti.execute(
                """
                UPDATE yenileme_belirtecleri
                SET gecersiz_kilindi_mi = 1
                WHERE aile_id = ?
                """,
                (satir["aile_id"],),
            )
            reddetme_mesaji = "Yenileme belirtecinin suresi doldu"
        else:
            yeni_belirtec = _yenileme_belirteci_degerlerini_olustur(
                satir["aile_id"]
            )
            baglanti.execute(
                """
                UPDATE yenileme_belirtecleri
                SET gecersiz_kilindi_mi = 1, yerine_gecen_jti = ?
                WHERE jti = ?
                """,
                (yeni_belirtec.jti, satir["jti"]),
            )
            baglanti.execute(
                """
                INSERT INTO yenileme_belirtecleri (
                    jti,
                    aile_id,
                    kullanici_adi,
                    belirtec_ozeti,
                    sona_erme_tarihi,
                    olusturulma_tarihi,
                    ip_ozeti
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    yeni_belirtec.jti,
                    yeni_belirtec.aile_id,
                    satir["kullanici_adi"],
                    _belirtec_ozetini_hesapla(yeni_belirtec.belirtec),
                    yeni_belirtec.sona_erme_tarihi.isoformat(),
                    simdi.isoformat(),
                    _ip_ozetini_hesapla(ip_adresi),
                ),
            )
            kullanici = KullaniciBilgisi(
                kullanici_adi=satir["kullanici_adi"],
                rol=satir["rol"],
                aktif_mi=True,
            )
    if reddetme_mesaji is not None:
        raise BelirtecHatasi(reddetme_mesaji)
    if yeni_belirtec is None or kullanici is None:
        raise BelirtecHatasi("Yenileme belirteci dondurulemedi")
    return yeni_belirtec, kullanici


def yenileme_ailesini_gecersiz_kil(belirtec: str) -> None:
    belirtec_ozeti = _belirtec_ozetini_hesapla(belirtec)
    with baglam_yoneticisi() as baglanti:
        baglanti.execute("BEGIN IMMEDIATE")
        satir = baglanti.execute(
            """
            SELECT aile_id
            FROM yenileme_belirtecleri
            WHERE belirtec_ozeti = ?
            """,
            (belirtec_ozeti,),
        ).fetchone()
        if satir is None:
            return
        baglanti.execute(
            """
            UPDATE yenileme_belirtecleri
            SET gecersiz_kilindi_mi = 1
            WHERE aile_id = ?
            """,
            (satir["aile_id"],),
        )


def kullanici_kimlik_bilgilerini_al(kullanici_adi: str) -> dict | None:
    with baglam_yoneticisi() as baglanti:
        satir = baglanti.execute(
            """
            SELECT kullanici_adi, sifre_hash, rol, aktif_mi
            FROM kullanicilar
            WHERE kullanici_adi = ?
            """,
            (kullanici_adi,),
        ).fetchone()
    if satir is None:
        return None
    return {
        "kullanici_adi": satir["kullanici_adi"],
        "sifre_hash": satir["sifre_hash"],
        "rol": satir["rol"],
        "aktif_mi": bool(satir["aktif_mi"]),
    }


def _kullaniciyi_veritabanindan_al(kullanici_adi: str) -> dict | None:
    kullanici = kullanici_kimlik_bilgilerini_al(kullanici_adi)
    if kullanici is None:
        return None
    kullanici.pop("sifre_hash")
    return kullanici


async def mevcut_belirteci_al(
    belirtec: Annotated[str, Depends(oauth2_semasi)],
) -> BelirtecVerisi:
    veri = await asyncio.to_thread(belirtec_coz, belirtec)
    if veri is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz kimlik bilgileri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return veri


async def mevcut_kullaniciyi_al(
    belirtec_verisi: Annotated[
        BelirtecVerisi,
        Depends(mevcut_belirteci_al),
    ],
) -> KullaniciBilgisi:
    satir = await asyncio.to_thread(
        _kullaniciyi_veritabanindan_al,
        belirtec_verisi.kullanici_adi,
    )
    if satir is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz kimlik bilgileri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not satir["aktif_mi"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabiniz devre disi birakilmistir",
        )
    if satir["rol"] != belirtec_verisi.rol:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz kimlik bilgileri",
        )
    return KullaniciBilgisi(
        kullanici_adi=satir["kullanici_adi"],
        rol=satir["rol"],
        aktif_mi=satir["aktif_mi"],
    )


async def mevcut_yoneticiyi_al(
    mevcut_kullanici: Annotated[
        KullaniciBilgisi,
        Depends(mevcut_kullaniciyi_al),
    ],
) -> KullaniciBilgisi:
    if mevcut_kullanici.rol != "YONETICI":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu islem icin yonetici yetkisi gereklidir",
        )
    return mevcut_kullanici


def _giris_kimlikleri(
    kullanici_adi: str,
    ip_adresi: str | None,
) -> list[str]:
    ham_kimlikler = [f"kullanici:{kullanici_adi.casefold()}"]
    if ip_adresi:
        ham_kimlikler.append(f"ip:{ip_adresi.strip().casefold()}")
    return [
        hashlib.sha256(kimlik.encode("utf-8")).hexdigest()
        for kimlik in ham_kimlikler
    ]


def kaba_kuvvet_girisimini_kontrol_et(
    kullanici_adi: str,
    ip_adresi: str | None = None,
) -> None:
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
            detail=(
                "Cok fazla basarisiz giris denemesi. "
                "Lutfen 15 dakika sonra tekrar deneyin."
            ),
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
                        WHEN giris_deneme_kayitlari.basarisiz_deneme_sayisi
                            + 1 >= ?
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
