import asyncio

from fastapi import APIRouter, Depends, Query

from uygulama.api.bagimliliklar import api_servisini_al
from uygulama.cekirdek.guvenlik import (
    KullaniciBilgisi,
    mevcut_yoneticiyi_al,
)
from uygulama.modeller.semalar import AnalitikVerisi
from uygulama.servisler.api_servisi import ApiServisi

router = APIRouter(prefix="/api/v1/analitik", tags=["Analitik"])


@router.get("", response_model=AnalitikVerisi)
async def analitik_verisini_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> AnalitikVerisi:
    sonuc = await asyncio.to_thread(servis.analitik_verisini_al)
    return AnalitikVerisi(**sonuc)


@router.get("/vektor-durumu")
async def vektor_durumunu_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.vektor_durumunu_al)


@router.get("/belge-dagilimi")
async def belge_dagilimini_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.belge_dagilimini_al)


@router.get("/senkronizasyon-durumu")
async def senkronizasyon_durumunu_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.senkronizasyon_durumunu_al)


@router.get("/karantina")
async def karantina_belgelerini_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.karantina_belgelerini_al)


@router.get("/kavram-bulutu")
async def kavram_bulutunu_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.kavram_bulutunu_al)


@router.get("/graf-istatistik")
async def graf_istatistik_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.graf_istatistik_al)


@router.get("/belge-surumleri")
async def belge_surumlerini_al(
    dosya_yolu: str | None = Query(default=None, max_length=1024),
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.belge_surumlerini_al, dosya_yolu)


@router.get("/parca-istatistikleri")
async def parca_istatistiklerini_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.parca_istatistiklerini_al)


@router.get("/sorgu-trendi")
async def sorgu_trendini_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.sorgu_trendini_al)


@router.get("/yetim-kavramlar")
async def yetim_kavramlari_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.yetim_kavramlari_al)


@router.get("/rapor/dokuman")
async def belge_analitik_raporunu_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.belge_analitik_raporunu_al)
