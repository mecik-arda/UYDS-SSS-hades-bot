import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from uygulama.api.bagimliliklar import bagimlilik_onbelleklerini_temizle
from uygulama.api.rotalar.analitik import router as analitik_router
from uygulama.api.rotalar.arama import router as arama_router
from uygulama.api.rotalar.geri_bildirim import router as geri_bildirim_router
from uygulama.api.rotalar.kimlik_dogrulama import (
    router as kimlik_dogrulama_router,
)
from uygulama.api.rotalar.sss import router as sss_router
from uygulama.api.rotalar.yonetici import router as yonetici_router
from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.dagitim_guvenligi import (
    tek_worker_dagitimini_dogrula,
)
from uygulama.cekirdek.hata_yonetimi import (
    IstekKimligiMiddleware,
    hata_yonetimini_kaydet,
)
from uygulama.cekirdek.istek_boyutu import IstekGovdesiBoyutMiddleware
from uygulama.cekirdek.istek_sinirlayici import istek_sinirlayici
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.guvenlik import (
    sifre_hash_olustur,
    suresi_dolmus_guvenlik_kayitlarini_temizle,
)
from uygulama.cekirdek.guvenlik_basliklari import GuvenlikBasliklariMiddleware
from uygulama.cekirdek.veritabani import (
    veritabani_hazirligini_denetle,
    veritabanini_sifrele,
)
from uygulama.modeller.veritabani_modelleri import tablolari_olustur, varsayilan_yonetici_olustur


async def guvenlik_bakimini_yurut() -> None:
    bakim_sonucu = await asyncio.to_thread(
        suresi_dolmus_guvenlik_kayitlarini_temizle
    )
    gunlukleyici.info(
        "Suresi dolmus guvenlik kayitlari temizlendi: "
        f"yenileme={bakim_sonucu.silinen_yenileme_belirteci_sayisi}, "
        f"erisim={bakim_sonucu.silinen_erisim_karaliste_sayisi}, "
        f"nonce={bakim_sonucu.silinen_yonetici_nonce_sayisi}"
    )


async def periyodik_guvenlik_bakimini_calistir(
    durdurma_olayi: asyncio.Event,
) -> None:
    bekleme_saniyesi = (
        konfigurasyon.GUVENLIK_BAKIM_ARALIGI_SAAT * 60 * 60
    )
    while True:
        try:
            await asyncio.wait_for(
                durdurma_olayi.wait(),
                timeout=bekleme_saniyesi,
            )
            return
        except TimeoutError:
            pass
        try:
            await guvenlik_bakimini_yurut()
        except Exception as hata:
            gunlukleyici.error(
                "Periyodik guvenlik bakimi basarisiz: "
                f"{type(hata).__name__}"
            )


@asynccontextmanager
async def uygulama_omru(uygulama: FastAPI):
    gunlukleyici.info("UYDS Asistani baslatiliyor")
    bakim_gorevi = None
    bakim_durdurma_olayi = asyncio.Event()
    try:
        tek_worker_dagitimini_dogrula(
            konfigurasyon.UYGULAMA_WORKER_SAYISI
        )
        tablolari_olustur()
        await guvenlik_bakimini_yurut()
        varsayilan_yonetici_sifre_hash = await asyncio.to_thread(
            sifre_hash_olustur,
            konfigurasyon.VARSAYILAN_YONETICI_SIFRESI,
        )
        varsayilan_yonetici_olustur(varsayilan_yonetici_sifre_hash)
        bakim_gorevi = asyncio.create_task(
            periyodik_guvenlik_bakimini_calistir(
                bakim_durdurma_olayi
            )
        )
        gunlukleyici.info("Veritabani baslatma islemleri tamamlandi")
    except Exception as hata:
        gunlukleyici.error(f"Baslatma islemleri sirasinda hata olustu: {hata}")
        raise
    try:
        yield
    finally:
        gunlukleyici.info("UYDS Asistani kapatiliyor")
        if bakim_gorevi is not None:
            bakim_durdurma_olayi.set()
            await bakim_gorevi
        bagimlilik_onbelleklerini_temizle()
        await asyncio.to_thread(veritabanini_sifrele)


uygulama = FastAPI(
    title="UYDS Akilli SSS Chatbot",
    description="UYDS Sik Sorulan Sorular Akilli Destek Asistani API",
    version="1.0.0",
    lifespan=uygulama_omru,
)

uygulama.state.limiter = istek_sinirlayici
uygulama.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
hata_yonetimini_kaydet(uygulama)
uygulama.add_middleware(SlowAPIMiddleware)

uygulama.add_middleware(IstekKimligiMiddleware)
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

uygulama.include_router(kimlik_dogrulama_router)
uygulama.include_router(arama_router)
uygulama.include_router(geri_bildirim_router)
uygulama.include_router(sss_router)
uygulama.include_router(yonetici_router)
uygulama.include_router(analitik_router)


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
