import asyncio
from unittest.mock import patch

import pytest

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.servisler.veri_temizligi import VeriTemizligi


class TestVeriTemizligiZamanlama:
    def test_temizlik_aktif_degilse_calismaz(self, gecici_veritabani):
        temizlik = VeriTemizligi()
        temizlik.aktif = False
        sonuc = temizlik.eski_sorgulari_temizle()
        assert sonuc == {"durum": "pasif", "silinen_kayit": 0}

    def test_temizlik_bos_tabloda_hata_vermez(self, gecici_veritabani):
        temizlik = VeriTemizligi()
        temizlik.aktif = True
        sonuc = temizlik.eski_sorgulari_temizle()
        assert sonuc["durum"] == "basarili"
        assert sonuc["silinen_kayit"] == 0

    def test_temizlik_eski_kayitlari_siler(self, gecici_veritabani):
        from datetime import datetime, timedelta, timezone
        from uygulama.cekirdek.veritabani import baglam_yoneticisi

        eski_tarih = (
            datetime.now(timezone.utc) - timedelta(days=365)
        ).isoformat()
        with baglam_yoneticisi() as baglanti:
            for sira in range(5):
                baglanti.execute(
                    "INSERT INTO asistan_sorgulari "
                    "(kullanici_sorusu, olusturulma_tarihi) "
                    "VALUES (?, ?)",
                    (f"eski soru {sira}", eski_tarih),
                )

        temizlik = VeriTemizligi()
        temizlik.aktif = True
        temizlik.ay_siniri = 6
        sonuc = temizlik.eski_sorgulari_temizle()
        assert sonuc["durum"] == "basarili"
        assert sonuc["silinen_kayit"] == 5

    def test_temizlik_yeni_kayitlari_silmez(self, gecici_veritabani):
        from datetime import datetime, timezone
        from uygulama.cekirdek.veritabani import baglam_yoneticisi

        yeni_tarih = datetime.now(timezone.utc).isoformat()
        with baglam_yoneticisi() as baglanti:
            for sira in range(3):
                baglanti.execute(
                    "INSERT INTO asistan_sorgulari "
                    "(kullanici_sorusu, olusturulma_tarihi) "
                    "VALUES (?, ?)",
                    (f"yeni soru {sira}", yeni_tarih),
                )

        temizlik = VeriTemizligi()
        temizlik.aktif = True
        temizlik.ay_siniri = 6
        sonuc = temizlik.eski_sorgulari_temizle()
        assert sonuc["silinen_kayit"] == 0

    def test_temizlik_partili_siler(self, gecici_veritabani):
        from datetime import datetime, timedelta, timezone
        from uygulama.cekirdek.veritabani import baglam_yoneticisi

        eski_tarih = (
            datetime.now(timezone.utc) - timedelta(days=400)
        ).isoformat()
        with baglam_yoneticisi() as baglanti:
            for sira in range(25):
                baglanti.execute(
                    "INSERT INTO asistan_sorgulari "
                    "(kullanici_sorusu, olusturulma_tarihi) "
                    "VALUES (?, ?)",
                    (f"eski soru {sira}", eski_tarih),
                )

        temizlik = VeriTemizligi()
        temizlik.aktif = True
        temizlik.ay_siniri = 6
        temizlik.parti_boyutu = 10
        sonuc = temizlik.eski_sorgulari_temizle()
        assert sonuc["durum"] == "basarili"
        assert sonuc["silinen_kayit"] == 25

