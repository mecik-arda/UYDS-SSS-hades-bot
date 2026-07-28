import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.istek_boyutu import IstekGovdesiBoyutMiddleware
from uygulama.cekirdek.istek_sinirlayici import istek_sinirlayici
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.guvenlik import sifre_hash_olustur
from uygulama.cekirdek.guvenlik_basliklari import GuvenlikBasliklariMiddleware
from uygulama.cekirdek.veritabani import (
    veritabani_hazirligini_denetle,
    veritabanini_sifrele,
)
from uygulama.modeller.veritabani_modelleri import tablolari_olustur, varsayilan_yonetici_olustur


@asynccontextmanager
async def uygulama_omru(uygulama: FastAPI):
    gunlukleyici.info("UYDS Asistani baslatiliyor")
    try:
        tablolari_olustur()
        varsayilan_yonetici_sifre_hash = await asyncio.to_thread(
            sifre_hash_olustur,
            konfigurasyon.VARSAYILAN_YONETICI_SIFRESI,
        )
        varsayilan_yonetici_olustur(varsayilan_yonetici_sifre_hash)
        gunlukleyici.info("Veritabani baslatma islemleri tamamlandi")
    except Exception as hata:
        gunlukleyici.error(f"Baslatma islemleri sirasinda hata olustu: {hata}")
        raise
    try:
        yield
    finally:
        gunlukleyici.info("UYDS Asistani kapatiliyor")
        await asyncio.to_thread(veritabanini_sifrele)


uygulama = FastAPI(
    title="UYDS Akilli SSS Chatbot",
    description="UYDS Sik Sorulan Sorular Akilli Destek Asistani API",
    version="1.0.0",
    lifespan=uygulama_omru,
)

uygulama.state.limiter = istek_sinirlayici
uygulama.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
uygulama.add_middleware(SlowAPIMiddleware)

uygulama.add_middleware(GuvenlikBasliklariMiddleware)
uygulama.add_middleware(
    IstekGovdesiBoyutMiddleware,
    maksimum_boyut=konfigurasyon.ISTEK_GOVDE_MAKS_BOYUT,
    dosya_yukleme_maksimum_boyutu=konfigurasyon.DOSYA_YUKLEME_MAKS_BOYUT,
    dosya_yukleme_yollari={"/api/v1/yonetici/excel-yukle"},
)

uygulama.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

sablonlar = Jinja2Templates(directory="uygulama/sablonlar")
uygulama.mount("/statik", StaticFiles(directory="uygulama/statik"), name="statik")


@uygulama.get("/api/saglik")
async def saglik_kontrolu():
    return {
        "durum": "saglikli",
        "uygulama": "UYDS Akilli SSS Chatbot",
        "surum": "1.0.0",
    }


@uygulama.get("/api/hazirlik")
async def hazirlik_kontrolu():
    try:
        sonuc = await asyncio.to_thread(veritabani_hazirligini_denetle)
        return sonuc
    except Exception as hata:
        gunlukleyici.error(f"Hazirlik denetimi basarisiz: {hata}")
        return JSONResponse(
            status_code=503,
            content={
                "durum": "hazir_degil",
                "veritabani": "erisilemiyor",
            },
        )
