import asyncio
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from uygulama.cekirdek.guvenlik import (
    KullaniciBilgisi,
    mevcut_yoneticiyi_al,
)
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.servisler.akis_servisi import AkisServisi
from uygulama.servisler.api_servisi import ApiServisi
from uygulama.servisler.arama_servisi import AramaServisi
from uygulama.servisler.deepseek_servisi import DeepSeekServisi
from uygulama.servisler.geri_bildirim_servisi import GeriBildirimServisi
from uygulama.servisler.niyet_siniflandirici import NiyetSiniflandirici
from uygulama.servisler.oturum_hafizasi import OturumHafizasi
from uygulama.servisler.oturum_sahipligi import OturumSahipligiServisi
from uygulama.servisler.eposta_raporlayici import EpostaRaporlayici
from uygulama.servisler.senkronizasyon_motoru import SenkronizasyonMotoru
from uygulama.servisler.terim_haritasi import TerimHaritasi
from uygulama.servisler.vektor_servisi import VektorServisi
from uygulama.servisler.yeniden_siralayici import (
    CrossEncoderYenidenSiralayici,
    YenidenSiralayiciProtokolu,
)

_NONCE_KALIBI = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_IMZA_KALIBI = re.compile(r"^[a-f0-9]{64}$")


@lru_cache
def vektor_servisini_al() -> VektorServisi:
    return VektorServisi()


@lru_cache
def yeniden_siralayiciyi_al() -> YenidenSiralayiciProtokolu | None:
    if not konfigurasyon.YENIDEN_SIRALAMA_ETKIN:
        return None
    return CrossEncoderYenidenSiralayici(
        model_yolu=konfigurasyon.YENIDEN_SIRALAMA_MODEL_YOLU,
        aday_sayisi=konfigurasyon.YENIDEN_SIRALAMA_ADAY_SAYISI,
        toplu_islem_boyutu=(
            konfigurasyon.YENIDEN_SIRALAMA_TOPLU_ISLEM_BOYUTU
        ),
        maksimum_token=konfigurasyon.YENIDEN_SIRALAMA_MAKS_TOKEN,
    )


@lru_cache
def arama_servisini_al() -> AramaServisi:
    return AramaServisi(
        vektor_servisi=vektor_servisini_al(),
        terim_haritasi=TerimHaritasi(),
        yeniden_siralayici=yeniden_siralayiciyi_al(),
        geri_bildirim_servisi=geri_bildirim_servisini_al(),
    )


@lru_cache
def oturum_hafizasini_al() -> OturumHafizasi:
    return OturumHafizasi()


@lru_cache
def oturum_sahipligi_servisini_al() -> OturumSahipligiServisi:
    return OturumSahipligiServisi()


@lru_cache
def niyet_siniflandiriciyi_al() -> NiyetSiniflandirici | None:
    if not konfigurasyon.NIYET_SINIFLANDIRMA_AKTIF:
        return None
    return NiyetSiniflandirici()


@lru_cache
def akis_servisini_al() -> AkisServisi:
    return AkisServisi(
        arama_servisi=arama_servisini_al(),
        deepseek_servisi=DeepSeekServisi(),
        oturum_hafizasi=oturum_hafizasini_al(),
        niyet_siniflandirici=niyet_siniflandiriciyi_al(),
    )


@lru_cache
def api_servisini_al() -> ApiServisi:
    return ApiServisi()


@lru_cache
def geri_bildirim_servisini_al() -> GeriBildirimServisi:
    return GeriBildirimServisi(vektor_servisi=vektor_servisini_al())


@lru_cache
def senkronizasyon_motorunu_al() -> SenkronizasyonMotoru:
    return SenkronizasyonMotoru(vektor_servisi=vektor_servisini_al())


@lru_cache
def eposta_raporlayiciyi_al() -> EpostaRaporlayici:
    return EpostaRaporlayici()


@lru_cache
def akis_semaforunu_al() -> asyncio.Semaphore:
    return asyncio.Semaphore(konfigurasyon.ESZAMANLI_AKIS_MAKS_SAYI)


def bagimlilik_onbelleklerini_temizle() -> None:
    vektor_servisini_al.cache_clear()
    yeniden_siralayiciyi_al.cache_clear()
    arama_servisini_al.cache_clear()
    oturum_hafizasini_al.cache_clear()
    oturum_sahipligi_servisini_al.cache_clear()
    niyet_siniflandiriciyi_al.cache_clear()
    akis_servisini_al.cache_clear()
    api_servisini_al.cache_clear()
    geri_bildirim_servisini_al.cache_clear()
    senkronizasyon_motorunu_al.cache_clear()
    eposta_raporlayiciyi_al.cache_clear()
    akis_semaforunu_al.cache_clear()


def _nonce_kaydini_olustur(nonce: str, sona_erme_tarihi: datetime) -> bool:
    nonce_ozeti = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    simdi = datetime.now(timezone.utc).isoformat()
    with baglam_yoneticisi() as baglanti:
        baglanti.execute("BEGIN IMMEDIATE")
        baglanti.execute(
            """
            DELETE FROM yonetici_imza_nonce_kayitlari
            WHERE sona_erme_tarihi <= ?
            """,
            (simdi,),
        )
        imlec = baglanti.execute(
            """
            INSERT OR IGNORE INTO yonetici_imza_nonce_kayitlari (
                nonce_ozeti,
                sona_erme_tarihi
            )
            VALUES (?, ?)
            """,
            (nonce_ozeti, sona_erme_tarihi.isoformat()),
        )
    return imlec.rowcount == 1


async def yonetici_istek_imzasini_dogrula(
    istek: Request,
    yonetici: Annotated[
        KullaniciBilgisi,
        Depends(mevcut_yoneticiyi_al),
    ],
    zaman: Annotated[str, Header(alias="X-UYDS-Zaman")],
    nonce: Annotated[str, Header(alias="X-UYDS-Nonce")],
    imza: Annotated[str, Header(alias="X-UYDS-Imza")],
) -> KullaniciBilgisi:
    if not _NONCE_KALIBI.fullmatch(nonce) or not _IMZA_KALIBI.fullmatch(imza):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz yonetici istek imzasi",
        )
    try:
        zaman_degeri = int(zaman)
        istek_zamani = datetime.fromtimestamp(zaman_degeri, tz=timezone.utc)
    except (ValueError, OSError, OverflowError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz yonetici istek zamani",
        ) from None
    simdi = datetime.now(timezone.utc)
    pencere = konfigurasyon.YONETICI_IMZA_ZAMAN_PENCERESI_SANIYE
    if abs((simdi - istek_zamani).total_seconds()) > pencere:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yonetici istek imzasinin suresi dolmus",
        )
    govde = await istek.body()
    govde_ozeti = hashlib.sha256(govde).hexdigest()
    imzalanan_metin = "\n".join(
        (
            zaman,
            nonce,
            istek.method.upper(),
            istek.url.path,
            govde_ozeti,
        )
    )
    imza_anahtari = (
        konfigurasyon.YONETICI_ISTEK_IMZA_ANAHTARI.strip()
        or konfigurasyon.JWT_GIZLI_ANAHTARI
    )
    beklenen_imza = hmac.new(
        imza_anahtari.encode("utf-8"),
        imzalanan_metin.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(imza, beklenen_imza):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz yonetici istek imzasi",
        )
    nonce_kabul_edildi = await asyncio.to_thread(
        _nonce_kaydini_olustur,
        nonce,
        simdi + timedelta(seconds=pencere),
    )
    if not nonce_kabul_edildi:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Yonetici istek imzasi tekrar kullanildi",
        )
    return yonetici


def yonetici_istek_imzasi_olustur(
    hedef_yol: str,
    govde: str,
) -> dict[str, str]:
    zaman = str(int(datetime.now(timezone.utc).timestamp()))
    nonce = secrets.token_urlsafe(32)
    govde_ozeti = hashlib.sha256(govde.encode("utf-8")).hexdigest()
    imzalanan_metin = "\n".join(
        (zaman, nonce, "POST", hedef_yol, govde_ozeti)
    )
    imza_anahtari = (
        konfigurasyon.YONETICI_ISTEK_IMZA_ANAHTARI.strip()
        or konfigurasyon.JWT_GIZLI_ANAHTARI
    )
    imza = hmac.new(
        imza_anahtari.encode("utf-8"),
        imzalanan_metin.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {"zaman": zaman, "nonce": nonce, "imza": imza}
