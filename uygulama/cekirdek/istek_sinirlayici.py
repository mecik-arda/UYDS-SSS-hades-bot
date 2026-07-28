from slowapi import Limiter
from slowapi.util import get_remote_address

from uygulama.cekirdek.konfigurasyon import konfigurasyon

varsayilan_istek_siniri = (
    f"{konfigurasyon.ISTEK_SINIRI}/{konfigurasyon.ISTEK_PENCERESI_SANIYE} seconds"
)

istek_sinirlayici = Limiter(
    key_func=get_remote_address,
    default_limits=[varsayilan_istek_siniri],
)
