import asyncio

import pytest

from uygulama.cekirdek.istek_boyutu import (
    IstekGovdesiBoyutMiddleware,
    IstekGovdesiBoyutuAsildi,
)


def _kapsam(basliklar):
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/arama",
        "raw_path": b"/api/v1/arama",
        "query_string": b"",
        "headers": basliklar,
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }


def _middleware(uygulama):
    return IstekGovdesiBoyutMiddleware(
        uygulama,
        maksimum_boyut=10,
        dosya_yukleme_maksimum_boyutu=20,
        dosya_yukleme_yollari={"/api/v1/yonetici/excel-yukle"},
    )


def test_coklu_content_length_uygulamaya_ulasmadan_reddedilir():
    uygulama_cagirildi = False
    gonderilenler = []

    async def uygulama(kapsam, al, gonder):
        nonlocal uygulama_cagirildi
        uygulama_cagirildi = True

    async def al():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def gonder(mesaj):
        gonderilenler.append(mesaj)

    asyncio.run(
        _middleware(uygulama)(
            _kapsam(
                [
                    (b"content-length", b"5"),
                    (b"content-length", b"5"),
                ]
            ),
            al,
            gonder,
        )
    )
    assert uygulama_cagirildi is False
    assert gonderilenler[0]["status"] == 400


def test_content_length_ve_transfer_encoding_birlikte_reddedilir():
    uygulama_cagirildi = False
    gonderilenler = []

    async def uygulama(kapsam, al, gonder):
        nonlocal uygulama_cagirildi
        uygulama_cagirildi = True

    async def al():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def gonder(mesaj):
        gonderilenler.append(mesaj)

    asyncio.run(
        _middleware(uygulama)(
            _kapsam(
                [
                    (b"content-length", b"5"),
                    (b"transfer-encoding", b"chunked"),
                ]
            ),
            al,
            gonder,
        )
    )
    assert uygulama_cagirildi is False
    assert gonderilenler[0]["status"] == 400


def test_bildirilmeyen_fazla_govde_413_dondurur():
    gonderilenler = []

    async def uygulama(kapsam, al, gonder):
        await al()
        await gonder(
            {
                "type": "http.response.start",
                "status": 204,
                "headers": [],
            }
        )

    async def al():
        return {
            "type": "http.request",
            "body": b"on_bir_bayt",
            "more_body": False,
        }

    async def gonder(mesaj):
        gonderilenler.append(mesaj)

    asyncio.run(
        _middleware(uygulama)(
            _kapsam([]),
            al,
            gonder,
        )
    )
    assert gonderilenler[0]["status"] == 413


def test_yanit_basladiktan_sonra_limit_asimi_baglantiyi_hatayla_kapatir():
    gonderilenler = []

    async def uygulama(kapsam, al, gonder):
        await gonder(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await al()

    async def al():
        return {
            "type": "http.request",
            "body": b"on_bir_bayt",
            "more_body": False,
        }

    async def gonder(mesaj):
        gonderilenler.append(mesaj)

    with pytest.raises(IstekGovdesiBoyutuAsildi):
        asyncio.run(
            _middleware(uygulama)(
                _kapsam([]),
                al,
                gonder,
            )
        )
    assert len(gonderilenler) == 1
    assert gonderilenler[0]["status"] == 200
