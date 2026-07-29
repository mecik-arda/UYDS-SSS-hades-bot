import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, status

from uygulama.api.bagimliliklar import (
    oturum_hafizasini_al,
    oturum_sahipligi_servisini_al,
)
from uygulama.cekirdek.guvenlik import (
    BelirtecHatasi,
    BelirtecVerisi,
    KullaniciBilgisi,
    basarili_giris_sifirla,
    basarisiz_giris_kaydet,
    erisim_belirteci_olustur,
    erisim_belirtecini_gecersiz_kil,
    kaba_kuvvet_girisimini_kontrol_et,
    kullanici_kimlik_bilgilerini_al,
    mevcut_belirteci_al,
    mevcut_kullaniciyi_al,
    sifre_dogrula,
    sifre_hash_olustur,
    yenileme_ailesini_gecersiz_kil,
    yenileme_belirteci_olustur,
    yenileme_belirtecini_dondur,
)
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.modeller.semalar import (
    BelirtecYaniti,
    BelirtecYenilemeIstegi,
    CikisIstegi,
    GenelMesajYaniti,
    KimlikDogrulamaIstegi,
)
from uygulama.servisler.oturum_hafizasi import OturumHafizasi
from uygulama.servisler.oturum_sahipligi import OturumSahipligiServisi

router = APIRouter(
    prefix="/api/v1/kimlik-dogrulama",
    tags=["Kimlik Doğrulama"],
)
_SAHTE_SIFRE_HASH = sifre_hash_olustur(
    "KullanilmayanSabitZamanDogrulamaSifresi"
)


def _istemci_ip_adresini_al(istek: Request) -> str | None:
    return istek.client.host if istek.client is not None else None


def _belirtec_yaniti_olustur(
    kullanici: KullaniciBilgisi,
    yenileme_belirteci: str,
) -> BelirtecYaniti:
    erisim_belirteci = erisim_belirteci_olustur(
        BelirtecVerisi(
            kullanici_adi=kullanici.kullanici_adi,
            rol=kullanici.rol,
        )
    )
    return BelirtecYaniti(
        erisim_belirteci=erisim_belirteci,
        yenileme_belirteci=yenileme_belirteci,
        rol=kullanici.rol,
        erisim_belirteci_omru_saniye=(
            konfigurasyon.JWT_OMRU_DAKIKA * 60
        ),
    )


@router.post("/giris", response_model=BelirtecYaniti)
async def giris_yap(
    istek_govdesi: KimlikDogrulamaIstegi,
    istek: Request,
) -> BelirtecYaniti:
    ip_adresi = _istemci_ip_adresini_al(istek)
    await asyncio.to_thread(
        kaba_kuvvet_girisimini_kontrol_et,
        istek_govdesi.kullanici_adi,
        ip_adresi,
    )
    kullanici = await asyncio.to_thread(
        kullanici_kimlik_bilgilerini_al,
        istek_govdesi.kullanici_adi,
    )
    dogrulanacak_hash = (
        kullanici["sifre_hash"]
        if kullanici is not None
        else _SAHTE_SIFRE_HASH
    )
    sifre_gecerli = await asyncio.to_thread(
        sifre_dogrula,
        istek_govdesi.sifre,
        dogrulanacak_hash,
    )
    if (
        kullanici is None
        or not sifre_gecerli
        or not kullanici["aktif_mi"]
    ):
        await asyncio.to_thread(
            basarisiz_giris_kaydet,
            istek_govdesi.kullanici_adi,
            ip_adresi,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanici adi veya sifre gecersiz",
        )
    await asyncio.to_thread(
        basarili_giris_sifirla,
        kullanici["kullanici_adi"],
        ip_adresi,
    )
    yenileme = await asyncio.to_thread(
        yenileme_belirteci_olustur,
        kullanici["kullanici_adi"],
        ip_adresi,
    )
    return _belirtec_yaniti_olustur(
        KullaniciBilgisi(
            kullanici_adi=kullanici["kullanici_adi"],
            rol=kullanici["rol"],
            aktif_mi=True,
        ),
        yenileme.belirtec,
    )


@router.post("/yenile", response_model=BelirtecYaniti)
async def belirteci_yenile(
    istek_govdesi: BelirtecYenilemeIstegi,
    istek: Request,
) -> BelirtecYaniti:
    try:
        yenileme, kullanici = await asyncio.to_thread(
            yenileme_belirtecini_dondur,
            istek_govdesi.yenileme_belirteci,
            _istemci_ip_adresini_al(istek),
        )
    except BelirtecHatasi:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz yenileme belirteci",
        ) from None
    return _belirtec_yaniti_olustur(kullanici, yenileme.belirtec)


@router.post("/cikis", response_model=GenelMesajYaniti)
async def cikis_yap(
    istek_govdesi: CikisIstegi,
    belirtec_verisi: BelirtecVerisi = Depends(mevcut_belirteci_al),
    kullanici: KullaniciBilgisi = Depends(mevcut_kullaniciyi_al),
    sahiplik: OturumSahipligiServisi = Depends(
        oturum_sahipligi_servisini_al
    ),
    hafiza: OturumHafizasi = Depends(oturum_hafizasini_al),
) -> GenelMesajYaniti:
    await asyncio.to_thread(
        erisim_belirtecini_gecersiz_kil,
        belirtec_verisi,
    )
    await asyncio.to_thread(
        yenileme_ailesini_gecersiz_kil,
        istek_govdesi.yenileme_belirteci,
    )
    oturumlar = await sahiplik.kullanicinin_oturumlarini_sil(
        kullanici.kullanici_adi
    )
    for oturum_id in oturumlar:
        await hafiza.oturumu_sil(oturum_id)
    return GenelMesajYaniti(mesaj="Cikis islemi tamamlandi")
