import argparse
import json

from uygulama.cekirdek.veritabani import veritabanini_sifrele
from uygulama.servisler.vektor_servisi import VektorServisi


def argumanlari_al() -> argparse.Namespace:
    ayristirici = argparse.ArgumentParser(
        prog="vektorleri_olustur.py",
        description="Aktif SSS parcalari icin yerel vektorleri uretir",
    )
    ayristirici.add_argument(
        "--tumunu-yenile",
        action="store_true",
        help="Secili modele ait tum vektorleri yeniden uretir",
    )
    ayristirici.add_argument(
        "--durum",
        action="store_true",
        help="Modeli yuklemeden vektor hazirlik durumunu raporlar",
    )
    return ayristirici.parse_args()


def ana() -> None:
    argumanlar = argumanlari_al()
    try:
        servis = VektorServisi()
        sonuc = (
            servis.durumu_al()
            if argumanlar.durum
            else servis.vektorleri_uret(argumanlar.tumunu_yenile)
        )
        print(
            json.dumps(
                sonuc.sozluge_donustur(),
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        veritabanini_sifrele()


if __name__ == "__main__":
    ana()
