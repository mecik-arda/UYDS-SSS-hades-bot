from functools import lru_cache, wraps
from threading import RLock
from typing import Callable


def onbellek_olustur(maksimum_boyut: int = 128):
    def dekorator(fonksiyon: Callable) -> Callable:
        onbellekli_fonksiyon = lru_cache(maxsize=maksimum_boyut)(fonksiyon)
        erisim_kilidi = RLock()

        @wraps(fonksiyon)
        def eszamanli_guvenli_fonksiyon(*argumanlar, **anahtar_argumanlar):
            with erisim_kilidi:
                return onbellekli_fonksiyon(*argumanlar, **anahtar_argumanlar)

        setattr(
            eszamanli_guvenli_fonksiyon,
            "cache_clear",
            onbellekli_fonksiyon.cache_clear,
        )
        setattr(
            eszamanli_guvenli_fonksiyon,
            "cache_info",
            onbellekli_fonksiyon.cache_info,
        )
        setattr(
            eszamanli_guvenli_fonksiyon,
            "cache_parameters",
            onbellekli_fonksiyon.cache_parameters,
        )
        return eszamanli_guvenli_fonksiyon

    return dekorator


def onbellegi_temizle(fonksiyon: Callable):
    if hasattr(fonksiyon, "cache_clear"):
        fonksiyon.cache_clear()
