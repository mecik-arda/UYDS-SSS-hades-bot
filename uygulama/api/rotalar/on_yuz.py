from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


SABLON_DIZINI = Path(__file__).resolve().parents[2] / "sablonlar"
sablonlar = Jinja2Templates(directory=str(SABLON_DIZINI))
router = APIRouter(include_in_schema=False)


def _sayfayi_goster(
    istek: Request,
    sablon_adi: str,
    sayfa: str,
    baslik: str,
) -> HTMLResponse:
    return sablonlar.TemplateResponse(
        request=istek,
        name=sablon_adi,
        context={
            "sayfa": sayfa,
            "baslik": baslik,
        },
    )


@router.get("/", response_class=HTMLResponse)
async def sohbet_sayfasi(istek: Request) -> HTMLResponse:
    return _sayfayi_goster(
        istek,
        "indeks.html",
        "sohbet",
        "Akıllı Destek Asistanı",
    )


@router.get("/yonetici", response_class=HTMLResponse)
async def yonetici_sayfasi(istek: Request) -> HTMLResponse:
    return _sayfayi_goster(
        istek,
        "yonetici.html",
        "yonetici",
        "Yönetici Merkezi",
    )


@router.get("/analitik", response_class=HTMLResponse)
async def analitik_sayfasi(istek: Request) -> HTMLResponse:
    return _sayfayi_goster(
        istek,
        "analitik.html",
        "analitik",
        "Analitik Görünümü",
    )
