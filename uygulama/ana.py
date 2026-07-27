import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.istek_sinirlayici import istek_sinirlayici
from uygulama.cekirdek.guvenlik import sifre_hash_olustur
from uygulama.modeller.veritabani_modelleri import tablolari_olustur, varsayilan_yonetici_olustur


@asynccontextmanager
async def uygulama_omru(uygulama: FastAPI):
    gunlukleyici.info("UYDS Asistani baslatiliyor")
    try:
        tablolari_olustur()
        varsayilan_yonetici_sifre_hash = await asyncio.to_thread(sifre_hash_olustur, "yonetici123")
        varsayilan_yonetici_olustur(varsayilan_yonetici_sifre_hash)
        gunlukleyici.info("Veritabani baslatma islemleri tamamlandi")
    except Exception as hata:
        gunlukleyici.error(f"Baslatma islemleri sirasinda hata olustu: {hata}")
        raise
    yield
    gunlukleyici.info("UYDS Asistani kapatiliyor")


uygulama = FastAPI(
    title="UYDS Akilli SSS Chatbot",
    description="UYDS Sik Sorulan Sorular Akilli Destek Asistani API",
    version="1.0.0",
    lifespan=uygulama_omru,
)

uygulama.state.limiter = istek_sinirlayici
uygulama.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

sablonlar = Jinja2Templates(directory="uygulama/sablonlar")
uygulama.mount("/statik", StaticFiles(directory="uygulama/statik"), name="statik")


@uygulama.get("/api/saglik")
async def saglik_kontrolu():
    return {
        "durum": "saglikli",
        "uygulama": "UYDS Akilli SSS Chatbot",
        "surum": "1.0.0",
    }