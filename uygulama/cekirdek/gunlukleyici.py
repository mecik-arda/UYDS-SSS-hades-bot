import logging
import json
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


class YapilandirilmisFormatlayici(logging.Formatter):
    def format(self, kayit):
        giris = {
            "zaman_damgasi": datetime.now(timezone.utc).isoformat(),
            "duzey": kayit.levelname,
            "modul": kayit.name,
            "mesaj": kayit.getMessage(),
        }
        return json.dumps(giris, ensure_ascii=False)


def gunlukleyici_olustur() -> logging.Logger:
    kok_gunlukleyici = logging.getLogger("uyds_asistani")
    kok_gunlukleyici.setLevel(logging.DEBUG)
    kok_gunlukleyici.handlers.clear()

    konsol_isleyici = logging.StreamHandler(sys.stdout)
    konsol_isleyici.setLevel(logging.INFO)
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
        dosya_isleyici.setLevel(logging.DEBUG)
        dosya_isleyici.setFormatter(YapilandirilmisFormatlayici())
        kok_gunlukleyici.addHandler(dosya_isleyici)
    except Exception:
        pass

    return kok_gunlukleyici


gunlukleyici = gunlukleyici_olustur()