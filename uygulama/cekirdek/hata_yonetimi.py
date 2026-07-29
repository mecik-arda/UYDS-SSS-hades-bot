from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from uygulama.cekirdek.gunlukleyici import gunlukleyici


class IstekKimligiMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, istek: Request, cagri_yoneticisi):
        gelen_kimlik = istek.headers.get("X-Istek-Kimligi", "")
        istek_kimligi = (
            gelen_kimlik
            if len(gelen_kimlik) == 32 and gelen_kimlik.isalnum()
            else uuid4().hex
        )
        istek.state.istek_kimligi = istek_kimligi
        yanit = await cagri_yoneticisi(istek)
        yanit.headers["X-Istek-Kimligi"] = istek_kimligi
        return yanit


def _istek_kimligini_al(istek: Request) -> str:
    return getattr(istek.state, "istek_kimligi", uuid4().hex)


async def dogrulama_hatasi_yanitla(
    istek: Request,
    hata: RequestValidationError,
) -> JSONResponse:
    alanlar = [
        {
            "konum": ".".join(str(parca) for parca in kayit["loc"]),
            "tur": kayit["type"],
        }
        for kayit in hata.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detay": "Istek dogrulamasi basarisiz",
            "alanlar": alanlar,
            "istek_kimligi": _istek_kimligini_al(istek),
        },
    )


async def http_hatasi_yanitla(
    istek: Request,
    hata: HTTPException,
) -> JSONResponse:
    return JSONResponse(
        status_code=hata.status_code,
        content={
            "detay": hata.detail,
            "istek_kimligi": _istek_kimligini_al(istek),
        },
        headers=hata.headers,
    )


async def beklenmeyen_hata_yanitla(
    istek: Request,
    hata: Exception,
) -> JSONResponse:
    istek_kimligi = _istek_kimligini_al(istek)
    gunlukleyici.error(
        "Beklenmeyen API hatasi: istek_kimligi=%s, yol=%s, tur=%s",
        istek_kimligi,
        istek.url.path,
        type(hata).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detay": "Istek islenirken beklenmeyen bir hata olustu",
            "istek_kimligi": istek_kimligi,
        },
    )


def hata_yonetimini_kaydet(uygulama: FastAPI) -> None:
    uygulama.add_exception_handler(
        RequestValidationError,
        dogrulama_hatasi_yanitla,
    )
    uygulama.add_exception_handler(HTTPException, http_hatasi_yanitla)
    uygulama.add_exception_handler(Exception, beklenmeyen_hata_yanitla)
