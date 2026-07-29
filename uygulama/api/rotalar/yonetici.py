import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status

from uygulama.api.bagimliliklar import (
    api_servisini_al,
    vektor_servisini_al,
    yonetici_istek_imzasini_dogrula,
)
from uygulama.cekirdek.guvenlik import (
    KullaniciBilgisi,
    mevcut_yoneticiyi_al,
)
from uygulama.modeller.semalar import (
    BekleyenGeriBildirimListesi,
    Sayfalama,
    YenidenIndekslemeYaniti,
    YoneticiOnayIstegi,
    YoneticiOnayYaniti,
)
from uygulama.servisler.api_servisi import ApiServisi, ApiServisiHatasi
from uygulama.servisler.vektor_servisi import VektorServisi

router = APIRouter(prefix="/api/v1/yonetici", tags=["Yönetici"])


@router.get(
    "/geri-bildirimler",
    response_model=BekleyenGeriBildirimListesi,
)
async def bekleyen_geri_bildirimleri_listele(
    sayfa: int = Query(default=1, ge=1),
    sayfa_basina: int = Query(default=20, ge=1, le=100),
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> BekleyenGeriBildirimListesi:
    bildirimler, toplam = await asyncio.to_thread(
        servis.bekleyen_geri_bildirimleri_listele,
        sayfa,
        sayfa_basina,
    )
    return BekleyenGeriBildirimListesi(
        bildirimler=bildirimler,
        toplam=toplam,
        sayfalama=Sayfalama(
            sayfa=sayfa,
            sayfa_basina=sayfa_basina,
        ),
    )


@router.post("/geri-bildirim/onay", response_model=YoneticiOnayYaniti)
async def geri_bildirim_durumunu_guncelle(
    istek_govdesi: YoneticiOnayIstegi,
    yonetici: KullaniciBilgisi = Depends(
        yonetici_istek_imzasini_dogrula
    ),
    servis: ApiServisi = Depends(api_servisini_al),
) -> YoneticiOnayYaniti:
    try:
        yeni_durum = await asyncio.to_thread(
            servis.geri_bildirim_durumunu_guncelle,
            istek_govdesi.geri_bildirim_id,
            istek_govdesi.islem,
        )
    except ApiServisiHatasi as hata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(hata),
        ) from None
    await asyncio.to_thread(
        servis.sistem_gunlugu_kaydet,
        yonetici.kullanici_adi,
        "GERI_BILDIRIM_DURUMU_GUNCELLENDI",
        (
            f"geri_bildirim_id={istek_govdesi.geri_bildirim_id},"
            f"durum={yeni_durum}"
        ),
    )
    return YoneticiOnayYaniti(
        id=istek_govdesi.geri_bildirim_id,
        yeni_durum=yeni_durum,
        mesaj="Geri bildirim durumu guncellendi",
    )


@router.post("/yeniden-indeksle", response_model=YenidenIndekslemeYaniti)
async def yeniden_indeksle(
    yonetici: KullaniciBilgisi = Depends(
        yonetici_istek_imzasini_dogrula
    ),
    servis: ApiServisi = Depends(api_servisini_al),
    vektor_servisi: VektorServisi = Depends(vektor_servisini_al),
) -> YenidenIndekslemeYaniti:
    fts_sayisi, vektor_sonucu = await asyncio.to_thread(
        servis.fts_ve_vektorleri_yeniden_indeksle,
        vektor_servisi,
    )
    await asyncio.to_thread(
        servis.sistem_gunlugu_kaydet,
        yonetici.kullanici_adi,
        "YENIDEN_INDEKSLEME",
        (
            f"fts={fts_sayisi},"
            f"vektor={vektor_sonucu.uretilen_vektor_sayisi}"
        ),
    )
    return YenidenIndekslemeYaniti(
        fts_kayit_sayisi=fts_sayisi,
        vektor_toplam_parca=vektor_sonucu.toplam_aktif_parca,
        uretilen_vektor_sayisi=vektor_sonucu.uretilen_vektor_sayisi,
        mesaj="FTS ve vektor indeksleri yenilendi",
    )
