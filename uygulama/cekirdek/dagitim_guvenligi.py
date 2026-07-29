import os
from collections.abc import Mapping


_HARICI_WORKER_DEGISKENLERI = (
    "WEB_CONCURRENCY",
    "UVICORN_WORKERS",
)


def tek_worker_dagitimini_dogrula(
    yapilandirilan_worker_sayisi: int,
    ortam: Mapping[str, str] | None = None,
) -> None:
    if yapilandirilan_worker_sayisi != 1:
        raise RuntimeError(
            "Bellek ici oturum sahipligi yalnizca tek worker destekler"
        )
    etkin_ortam = ortam if ortam is not None else os.environ
    for degisken_adi in _HARICI_WORKER_DEGISKENLERI:
        ham_deger = etkin_ortam.get(degisken_adi, "").strip()
        if not ham_deger:
            continue
        try:
            worker_sayisi = int(ham_deger)
        except ValueError as hata:
            raise RuntimeError(
                f"{degisken_adi} pozitif bir tam sayi olmalidir"
            ) from hata
        if worker_sayisi != 1:
            raise RuntimeError(
                "Bellek ici oturum sahipligi yalnizca tek worker destekler"
            )
