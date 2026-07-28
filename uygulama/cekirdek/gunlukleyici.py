import logging
import json
import re
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from uygulama.cekirdek.konfigurasyon import konfigurasyon

_HASSAS_KELIME_KALIPLARI = [
    (r'(api[_-]?anahtar[_\s]*[:=]\s*)(\S+)', r'\1[GIZLI]'),
    (r'(sifre[_\s]*[:=]\s*)(\S+)', r'\1[GIZLI]'),
    (r'(token[_\s]*[:=]\s*)(\S+)', r'\1[GIZLI]'),
    (r'(secret[_\s]*[:=]\s*)(\S+)', r'\1[GIZLI]'),
    (r'(Authorization:\s*Bearer\s+)(\S+)', r'\1[GIZLI]'),
    (r'(DEEPSEEK_API_ANAHTARI\s*=\s*)(\S+)', r'\1[GIZLI]'),
    (r'(JWT_GIZLI_ANAHTARI\s*=\s*)(\S+)', r'\1[GIZLI]'),
]


def hassas_verileri_maskele(mesaj: str) -> str:
    for kalip, degistirme in _HASSAS_KELIME_KALIPLARI:
        mesaj = re.sub(kalip, degistirme, mesaj, flags=re.IGNORECASE)
    return mesaj


class YapilandirilmisFormatlayici(logging.Formatter):
    def format(self, kayit):
        giris = {
            "zaman_damgasi": datetime.now(timezone.utc).isoformat(),
            "duzey": kayit.levelname,
            "modul": kayit.name,
            "mesaj": hassas_verileri_maskele(kayit.getMessage()),
        }
        return json.dumps(giris, ensure_ascii=False)


def gunlukleyici_olustur() -> logging.Logger:
    kok_gunlukleyici = logging.getLogger("uyds_asistani")
    yapilandirilan_seviye = getattr(logging, konfigurasyon.LOG_SEVIYESI)
    kok_gunlukleyici.setLevel(yapilandirilan_seviye)
    kok_gunlukleyici.handlers.clear()

    konsol_isleyici = logging.StreamHandler(sys.stdout)
    konsol_isleyici.setLevel(yapilandirilan_seviye)
    konsol_isleyici.setFormatter(YapilandirilmisFormatlayici())
    kok_gunlukleyici.addHandler(konsol_isleyici)

    try:
        gunluk_dizini = Path("veriler/gunlukler")
        gunluk_dizini.mkdir(parents=True, exist_ok=True)

        dosya_isleyici = RotatingFileHandler(
            gunluk_dizini / "uygulama.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        dosya_isleyici.setLevel(yapilandirilan_seviye)
        dosya_isleyici.setFormatter(YapilandirilmisFormatlayici())
        kok_gunlukleyici.addHandler(dosya_isleyici)
    except Exception:
        pass

    return kok_gunlukleyici


gunlukleyici = gunlukleyici_olustur()
