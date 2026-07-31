import asyncio
import concurrent.futures

import pytest

from uygulama.cekirdek.veritabani import baglam_yoneticisi, _baglanti_olustur_kilitliyken


class TestSQLiteEszamanlilik:
    def test_10_eszamanli_yazma_wal_hatasi_vermez(self, gecici_veritabani):
        hata_listesi = []

        def yazma_islemi(sira):
            try:
                with baglam_yoneticisi() as baglanti:
                    baglanti.execute(
                        "INSERT INTO asistan_sorgulari "
                        "(kullanici_sorusu) VALUES (?)",
                        (f"eszamanli test {sira}",),
                    )
            except Exception as hata:
                hata_listesi.append(str(hata))

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=10
        ) as yurutucu:
            gelecekler = [
                yurutucu.submit(yazma_islemi, sira)
                for sira in range(10)
            ]
            for gelecek in concurrent.futures.as_completed(gelecekler):
                gelecek.result()

        assert len(hata_listesi) == 0, (
            f"Eszamanli yazmada hata olustu: {hata_listesi}"
        )

    def test_veritabani_wal_modu_aktif(self, gecici_veritabani):
        baglanti = _baglanti_olustur_kilitliyken()
        try:
            journal_modu = baglanti.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0]
            assert journal_modu.lower() == "wal"
        finally:
            baglanti.close()