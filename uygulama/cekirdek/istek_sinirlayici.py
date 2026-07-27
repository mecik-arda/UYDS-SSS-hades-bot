from slowapi import Limiter
from slowapi.util import get_remote_address

istek_sinirlayici = Limiter(key_func=get_remote_address)