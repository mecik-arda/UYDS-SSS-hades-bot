import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from uygulama.api.bagimliliklar import (
    akis_semaforunu_al,
    akis_servisini_al,
    api_servisini_al,
    oturum_sahipligi_servisini_al,
)
from uygulama.cekirdek.guvenlik import KullaniciBilgisi, mevcut_kullaniciyi_al
from uygulama.modeller.semalar import AramaIstegi
from uygulama.servisler.akis_servisi import AkisServisi
from uygulama.servisler.api_servisi import ApiServisi
from uygulama.servisler.oturum_sahipligi import (
    OturumSahipligiHatasi,
    OturumSahipligiServisi,
)

router = APIRouter(prefix="/api/v1", tags=["Arama"])


def _sse_olayi_olustur(olay: str, veri: dict) -> str:
    json_verisi = json.dumps(
        veri,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: {olay}\ndata: {json_verisi}\n\n"


def _sse_olayini_ayristir(ham_olay: str) -> tuple[str, dict]:
    satirlar = ham_olay.strip().splitlines()
    olay = satirlar[0].removeprefix("event: ")
    veri = json.loads(satirlar[1].removeprefix("data: "))
    return olay, veri


@router.post("/arama")
async def arama_yap(
    istek_govdesi: AramaIstegi,
    istek: Request,
    kullanici: KullaniciBilgisi = Depends(mevcut_kullaniciyi_al),
    akis_servisi: AkisServisi = Depends(akis_servisini_al),
    api_servisi: ApiServisi = Depends(api_servisini_al),
    sahiplik: OturumSahipligiServisi = Depends(
        oturum_sahipligi_servisini_al
    ),
    semafor: asyncio.Semaphore = Depends(akis_semaforunu_al),
) -> StreamingResponse:
    kota_doldu = await asyncio.to_thread(
        api_servisi.gunluk_kota_kullanildi_mi,
        kullanici.kullanici_adi,
    )
    if kota_doldu:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Gunluk mesaj kotasi doldu",
        )
    try:
        oturum_id = await sahiplik.oturum_al_veya_olustur(
            kullanici.kullanici_adi,
            istek_govdesi.oturum_id,
        )
    except OturumSahipligiHatasi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oturum bulunamadi",
        ) from None
    try:
        await asyncio.wait_for(semafor.acquire(), timeout=0.1)
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Eszamanli akis kapasitesi dolu",
        ) from None

    async def yanit_akisi():
        parcalar: list[str] = []
        guven_skoru = 0.0
        kaynak_sss_idleri: list[int] = []
        tamamlandi = False
        try:
            yield _sse_olayi_olustur(
                "oturum",
                {"oturum_id": oturum_id},
            )
            async for ham_olay in akis_servisi.yanit_akisini_uret(
                istek_govdesi.soru,
                oturum_id,
                kullanici_rolu=kullanici.rol,
            ):
                if await istek.is_disconnected():
                    return
                olay, veri = _sse_olayini_ayristir(ham_olay)
                if olay == "meta":
                    guven_skoru = float(veri.get("guven_skoru", 0.0))
                    kaynak_sss_idleri = [
                        int(kaynak["sss_id"])
                        for kaynak in veri.get("kaynaklar", [])
                        if isinstance(kaynak.get("sss_id"), int)
                    ]
                elif olay == "parca":
                    parcalar.append(str(veri.get("metin", "")))
                elif olay == "tamamlandi":
                    tamamlandi = True
                    await asyncio.to_thread(
                        api_servisi.sorguyu_kaydet,
                        kullanici.kullanici_adi,
                        oturum_id,
                        istek_govdesi.soru,
                        "".join(parcalar),
                        guven_skoru,
                        bool(veri.get("cevaplandi")),
                        kaynak_sss_idleri,
                    )
                yield ham_olay
        except asyncio.CancelledError:
            raise
        except Exception:
            if not tamamlandi:
                yield _sse_olayi_olustur(
                    "hata",
                    {"mesaj": "Yanit akisi tamamlanamadi"},
                )
        finally:
            semafor.release()

    return StreamingResponse(
        yanit_akisi(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
        },
    )
