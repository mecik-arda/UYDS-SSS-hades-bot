import asyncio

from fastapi import APIRouter, Depends

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
