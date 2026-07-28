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
    islem_grubu = ayrıştırıcı.add_mutually_exclusive_group()
    islem_grubu.add_argument(
        "--kuru-calistir",
        action="store_true",
        help="Excel degisikliklerini verileri aktarmadan raporlar",
    )
    islem_grubu.add_argument(
        "--surum-geri-al",
        type=int,
        metavar="SURUM",
        help="Belirtilen veri surumunu yeni bir surum olarak etkinlestirir",
    )
    return ayrıştırıcı.parse_args()


def ana() -> None:
    argumanlar = argumanlari_al()
    try:
        yukleyici = ExcelYukleyici()
        if argumanlar.surum_geri_al is not None:
            sonuc = yukleyici.surumu_geri_al(argumanlar.surum_geri_al)
        elif argumanlar.kuru_calistir:
            sonuc = yukleyici.kuru_calistir(argumanlar.dosya)
        else:
            sonuc = yukleyici.ice_aktar(argumanlar.dosya)
        print(json.dumps(sonuc.sozluge_donustur(), ensure_ascii=False, indent=2))
    finally:
        veritabanini_sifrele()


if __name__ == "__main__":
    ana()
