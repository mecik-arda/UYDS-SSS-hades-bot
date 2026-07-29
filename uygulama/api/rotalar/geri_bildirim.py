import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from uygulama.api.bagimliliklar import api_servisini_al
from uygulama.cekirdek.guvenlik import KullaniciBilgisi, mevcut_kullaniciyi_al
from uygulama.modeller.semalar import (
    GeriBildirimIstegi,
    GeriBildirimYaniti,
)
from uygulama.servisler.api_servisi import ApiServisi, ApiServisiHatasi

router = APIRouter(prefix="/api/v1/geri-bildirim", tags=["Geri Bildirim"])


@router.post("", response_model=GeriBildirimYaniti)
async def geri_bildirim_olustur(
    istek_govdesi: GeriBildirimIstegi,
    kullanici: KullaniciBilgisi = Depends(mevcut_kullaniciyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> GeriBildirimYaniti:
    try:
        geri_bildirim_id = await asyncio.to_thread(
            servis.geri_bildirim_kaydet,
            istek_govdesi,
        )
    except ApiServisiHatasi as hata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(hata),
        ) from None
    await asyncio.to_thread(
        servis.sistem_gunlugu_kaydet,
        kullanici.kullanici_adi,
        "GERI_BILDIRIM_OLUSTURULDU",
        f"geri_bildirim_id={geri_bildirim_id}",
    )
    return GeriBildirimYaniti(
        id=geri_bildirim_id,
        durum="BEKLEMEDE",
        mesaj="Geri bildirim kaydedildi",
    )
