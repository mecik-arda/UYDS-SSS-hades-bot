from functools import lru_cache
from typing import Callable


def onbellek_olustur(maksimum_boyut: int = 128):
    def dekorator(fonksiyon: Callable) -> Callable:
        onbellekli_fonksiyon = lru_cache(maxsize=maksimum_boyut)(fonksiyon)
        return onbellekli_fonksiyon

    return dekorator


def onbellegi_temizle(fonksiyon: Callable):
    if hasattr(fonksiyon, "cache_clear"):
        fonksiyon.cache_clear()