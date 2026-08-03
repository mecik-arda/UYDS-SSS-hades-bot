import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status

from uygulama.api.bagimliliklar import (
    arama_servisini_al,
    api_servisini_al,
    eposta_raporlayiciyi_al,
    geri_bildirim_servisini_al,
    senkronizasyon_motorunu_al,
    yonetici_istek_imzasi_olustur,
    yonetici_istek_imzasini_dogrula,
)
from uygulama.cekirdek.guvenlik import (
    KullaniciBilgisi,
    mevcut_yoneticiyi_al,
)
from uygulama.modeller.semalar import (
    AramaIstegi,
    BekleyenGeriBildirimListesi,
    CevapsizSorguListesi,
    Sayfalama,
    SenkronizasyonIstegi,
    YenidenIndekslemeYaniti,
    YoneticiImzaIstegi,
    YoneticiImzaYaniti,
    YoneticiOnayIstegi,
    YoneticiOnayYaniti,
)
from uygulama.servisler.arama_servisi import AramaServisi
from uygulama.servisler.api_servisi import ApiServisi
from uygulama.servisler.geri_bildirim_servisi import (
    GeriBildirimServisi,
    GeriBildirimServisiHatasi,
)
from uygulama.servisler.eposta_raporlayici import EpostaRaporlayici
from uygulama.servisler.senkronizasyon_motoru import SenkronizasyonMotoru

router = APIRouter(prefix="/api/v1/yonetici", tags=["Yönetici"])

IMZALANABILIR_YOLLAR = frozenset(
    {
        "/api/v1/yonetici/geri-bildirim/onay",
        "/api/v1/yonetici/yeniden-indeksle",
        "/api/v1/yonetici/senkronizasyon",
        "/api/v1/yonetici/eposta-raporu/gonder",
    }
)


@router.post("/islem-imzasi", response_model=YoneticiImzaYaniti)
async def yonetici_islem_imzasi_olustur(
    istek_govdesi: YoneticiImzaIstegi,
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
) -> YoneticiImzaYaniti:
    if istek_govdesi.hedef_yol not in IMZALANABILIR_YOLLAR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu yonetici islemi tarayici icin imzalanamaz",
        )
    sonuc = yonetici_istek_imzasi_olustur(
        istek_govdesi.hedef_yol,
        istek_govdesi.govde,
    )
    return YoneticiImzaYaniti(**sonuc)


@router.get("/isletim-durumu")
async def isletim_durumunu_al(
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: ApiServisi = Depends(api_servisini_al),
) -> dict:
    return await asyncio.to_thread(servis.isletim_durumunu_al)


@router.post("/olcum/arama")
async def olcum_aramasi_yap(
    istek_govdesi: AramaIstegi,
    yonetici: KullaniciBilgisi = Depends(mevcut_yoneticiyi_al),
    servis: AramaServisi = Depends(arama_servisini_al),
) -> dict:
    sonuc = await asyncio.to_thread(
        servis.ara,
        istek_govdesi.soru,
        yonetici.rol,
    )
    return {
        "sirali_sss_idleri": [aday.sss_id for aday in sonuc.adaylar[:10]],
        "gecen_sure_ms": sonuc.gecen_sure_ms,
        "yeniden_siralama_etkin": sonuc.yeniden_siralama_etkin,
    }


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


@router.post("/senkronizasyon")
async def belge_senkronizasyonunu_calistir(
    istek_govdesi: SenkronizasyonIstegi,
    yonetici: KullaniciBilgisi = Depends(
        yonetici_istek_imzasini_dogrula
    ),
    servis: SenkronizasyonMotoru = Depends(senkronizasyon_motorunu_al),
    gunluk_servisi: GeriBildirimServisi = Depends(
        geri_bildirim_servisini_al
    ),
) -> dict:
    islem = (
        servis.tam_senkronizasyon
        if istek_govdesi.tur == "tam"
        else servis.artimsal_senkronizasyon
    )
    sonuc = await asyncio.to_thread(islem)
    await asyncio.to_thread(
        gunluk_servisi.sistem_gunlugu_kaydet,
        yonetici.kullanici_adi,
        "BELGE_SENKRONIZASYONU",
        (
            f"tur={istek_govdesi.tur},"
            f"belge={sonuc.islenen_belge_sayisi},"
            f"hata={sonuc.hata_sayisi}"
        ),
    )
    return {
        "tur": istek_govdesi.tur,
        "islenen_belge_sayisi": sonuc.islenen_belge_sayisi,
        "yeni_parca_sayisi": sonuc.yeni_parca_sayisi,
        "silinen_parca_sayisi": sonuc.silinen_parca_sayisi,
        "karantina_sayisi": sonuc.karantina_sayisi,
        "surumlenen_belge_sayisi": sonuc.surumlenen_belge_sayisi,
        "hata_sayisi": sonuc.hata_sayisi,
        "sure_saniye": sonuc.sure_saniye,
    }


@router.post("/eposta-raporu/gonder")
async def eposta_raporunu_gonder(
    yonetici: KullaniciBilgisi = Depends(
        yonetici_istek_imzasini_dogrula
    ),
    servis: EpostaRaporlayici = Depends(eposta_raporlayiciyi_al),
    gunluk_servisi: GeriBildirimServisi = Depends(
        geri_bildirim_servisini_al
    ),
) -> dict:
    gonderildi = await servis.haftalik_raporu_gonder()
    await asyncio.to_thread(
        gunluk_servisi.sistem_gunlugu_kaydet,
        yonetici.kullanici_adi,
        "EPOSTA_RAPORU_GONDERIMI",
        f"gonderildi={gonderildi}",
    )
    if not gonderildi:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-posta raporu yapilandirmasi etkin veya tamamlanmis degil",
        )
    return {"gonderildi": True, "mesaj": "Haftalik rapor gonderildi"}
