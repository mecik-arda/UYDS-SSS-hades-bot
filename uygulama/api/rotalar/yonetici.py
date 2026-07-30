import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status

from uygulama.api.bagimliliklar import (
    api_servisini_al,
    geri_bildirim_servisini_al,
    yonetici_istek_imzasini_dogrula,
)
from uygulama.cekirdek.guvenlik import (
    KullaniciBilgisi,
    mevcut_yoneticiyi_al,
)
from uygulama.modeller.semalar import (
    BekleyenGeriBildirimListesi,
    CevapsizSorguListesi,
    Sayfalama,
    YenidenIndekslemeYaniti,
    YoneticiOnayIstegi,
    YoneticiOnayYaniti,
)
from uygulama.servisler.api_servisi import ApiServisi
from uygulama.servisler.geri_bildirim_servisi import (
    GeriBildirimServisi,
    GeriBildirimServisiHatasi,
)

router = APIRouter(prefix="/api/v1/yonetici", tags=["Yönetici"])


@router.get(
    "/cevapsiz-sorgular",
    response_model=CevapsizSorguListesi,
)
async def cevapsiz_sorgulari_listele(
    sayfa: int = Query(default=1, ge=1),
    sayfa_basina: int = Query(default=20, ge=1, le=100),
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> CevapsizSorguListesi:
    sorgular, toplam = await asyncio.to_thread(
        servis.cevapsiz_sorgulari_listele,
        sayfa,
        sayfa_basina,
    )
    return CevapsizSorguListesi(
        sorgular=sorgular,
        toplam=toplam,
        sayfalama=Sayfalama(
            sayfa=sayfa,
            sayfa_basina=sayfa_basina,
        ),
    )


@router.get(
    "/geri-bildirimler",
    response_model=BekleyenGeriBildirimListesi,
)
async def bekleyen_geri_bildirimleri_listele(
    sayfa: int = Query(default=1, ge=1),
    sayfa_basina: int = Query(default=20, ge=1, le=100),
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: GeriBildirimServisi = Depends(geri_bildirim_servisini_al),
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
    servis: GeriBildirimServisi = Depends(geri_bildirim_servisini_al),
) -> YoneticiOnayYaniti:
    try:
        if istek_govdesi.islem == "ONAYLA":
            sonuc = await asyncio.to_thread(
                servis.geri_bildirimi_onayla,
                istek_govdesi.geri_bildirim_id,
                istek_govdesi.secili_sss_id,
            )
            yeni_durum = sonuc["yeni_durum"]
            detay = (
                f"geri_bildirim_id={istek_govdesi.geri_bildirim_id},"
                f"alternatif_soru_id={sonuc.get('alternatif_soru_id')}"
            )
        else:
            yeni_durum = await asyncio.to_thread(
                servis.geri_bildirimi_reddet,
                istek_govdesi.geri_bildirim_id,
            )
            detay = f"geri_bildirim_id={istek_govdesi.geri_bildirim_id}"
    except GeriBildirimServisiHatasi as hata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(hata),
        ) from None
    await asyncio.to_thread(
        servis.sistem_gunlugu_kaydet,
        yonetici.kullanici_adi,
        "GERI_BILDIRIM_DURUMU_GUNCELLENDI",
        f"{detay},durum={yeni_durum}",
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
    servis: GeriBildirimServisi = Depends(geri_bildirim_servisini_al),
) -> YenidenIndekslemeYaniti:
    fts_sayisi, vektor_sonucu = await asyncio.to_thread(
        servis.fts_ve_vektorleri_yeniden_indeksle,
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
        mesaj="FTS ve vektor indeksleri alternatif sorularla birlikte yenilendi",
    )
