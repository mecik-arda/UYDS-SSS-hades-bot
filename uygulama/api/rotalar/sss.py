import asyncio

from fastapi import APIRouter, Depends, Query

from uygulama.api.bagimliliklar import api_servisini_al
from uygulama.cekirdek.guvenlik import KullaniciBilgisi, mevcut_kullaniciyi_al
from uygulama.modeller.semalar import SssListesiYaniti
from uygulama.servisler.api_servisi import ApiServisi

router = APIRouter(prefix="/api/v1/sss", tags=["SSS"])


@router.get("", response_model=SssListesiYaniti)
async def sss_kayitlarini_listele(
    sayfa: int = Query(default=1, ge=1),
    sayfa_basina: int = Query(default=20, ge=1, le=100),
    kategori: str | None = Query(default=None, max_length=200),
    kullanici: KullaniciBilgisi = Depends(mevcut_kullaniciyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> SssListesiYaniti:
    kayitlar, toplam = await asyncio.to_thread(
        servis.sss_kayitlarini_listele,
        sayfa,
        sayfa_basina,
        kategori,
    )
    return SssListesiYaniti(
        kayitlar=kayitlar,
        toplam=toplam,
        sayfa=sayfa,
        sayfa_basina=sayfa_basina,
    )
