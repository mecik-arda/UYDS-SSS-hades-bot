import argparse
import json
from pathlib import Path

from uygulama.cekirdek.veritabani import veritabanini_sifrele
from uygulama.servisler.excel_yukleyici import ExcelYukleyici


def argumanlari_al() -> argparse.Namespace:
    ayrıştırıcı = argparse.ArgumentParser(
        prog="excel_ice_aktar",
        description="UYDS SSS Excel dosyasini guvenli bicimde ice aktarir",
    )
    ayrıştırıcı.add_argument(
        "dosya",
        nargs="?",
        type=Path,
        default=Path("veriler/UYDS_SSS_Listesi.xlsx"),
    )
    return ayrıştırıcı.parse_args()


def ana() -> None:
    argumanlar = argumanlari_al()
    try:
        sonuc = ExcelYukleyici().ice_aktar(argumanlar.dosya)
        print(json.dumps(sonuc.sozluge_donustur(), ensure_ascii=False, indent=2))
    finally:
        veritabanini_sifrele()


if __name__ == "__main__":
    ana()
