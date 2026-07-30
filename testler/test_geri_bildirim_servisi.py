import asyncio
import hashlib
import sqlite3

import numpy as np
import pytest

import uygulama.cekirdek.konfigurasyon as konfigurasyon_modulu
import uygulama.cekirdek.veritabani as veritabani_modulu
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.semalar import GeriBildirimIstegi
from uygulama.servisler.geri_bildirim_servisi import (
    GeriBildirimServisi,
    GeriBildirimServisiHatasi,
)


@pytest.fixture
def servis(mock_vektor_servisi):
    return GeriBildirimServisi(vektor_servisi=mock_vektor_servisi)


class TestGeriBildirimServisi:
    def test_geri_bildirim_beklemede_olarak_kaydedilir(self, servis, gecici_veritabani):
        istek = GeriBildirimIstegi(
            sss_id=None,
            kullanici_sorusu="Bu bir test sorusudur",
            verilen_cevap="Test cevabi",
            puan=3,
        )
        kayit_id = asyncio.run(asyncio.to_thread(servis.geri_bildirim_kaydet, istek))
        assert kayit_id > 0
        with baglam_yoneticisi() as baglanti:
            satir = baglanti.execute(
                "SELECT durum FROM geri_bildirimler WHERE id = ?",
                (kayit_id,),
            ).fetchone()
        assert satir["durum"] == "BEKLEMEDE"

    def test_gecersiz_sss_id_reddedilir(self, servis, gecici_veritabani):
        istek = GeriBildirimIstegi(
            sss_id=99999,
            kullanici_sorusu="Deneme sorusu",
            verilen_cevap="Deneme",
            puan=2,
        )
        with pytest.raises(GeriBildirimServisiHatasi, match="Aktif SSS kaydi bulunamadi"):
            asyncio.run(asyncio.to_thread(servis.geri_bildirim_kaydet, istek))

    def test_secili_sss_id_ile_geri_bildirim_kaydedilir(self, servis, gecici_veritabani):
        with baglam_yoneticisi() as baglanti:
            imlec = baglanti.execute(
                """
                INSERT INTO sss_kayitlari (
                    kategori, soru, cevap, kaynak_dokuman, durum
                )
                VALUES (
                    'Test', 'Test sorusu', 'Test cevabi',
                    'Test dokumani', 'aktif'
                )
                """
            )
            sss_id = int(imlec.lastrowid)
        istek = GeriBildirimIstegi(
            sss_id=sss_id,
            kullanici_sorusu="Kullanici sorusu",
            verilen_cevap="Sistem cevabi",
            puan=2,
            secili_sss_id=sss_id,
        )
        kayit_id = asyncio.run(asyncio.to_thread(servis.geri_bildirim_kaydet, istek))
        assert kayit_id > 0
        with baglam_yoneticisi() as baglanti:
            satir = baglanti.execute(
                "SELECT secili_sss_id FROM geri_bildirimler WHERE id = ?",
                (kayit_id,),
            ).fetchone()
        assert satir["secili_sss_id"] == sss_id

    def test_onayla_alternatif_soru_ekler(self, servis, gecici_veritabani):
        with baglam_yoneticisi() as baglanti:
            imlec = baglanti.execute(
                """
                INSERT INTO sss_kayitlari (
                    kategori, soru, cevap, kaynak_dokuman, durum
                )
                VALUES (
                    'Test', 'Test sorusu', 'Test cevabi',
                    'Test dokumani', 'aktif'
                )
                """
            )
            sss_id = int(imlec.lastrowid)
            baglanti.execute(
                """
                INSERT INTO geri_bildirimler (
                    sss_id, kullanici_sorusu, verilen_cevap,
                    puan, yorum, secili_sss_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sss_id,
                    "Alternatif ifade",
                    "Eski cevap",
                    2,
                    None,
                    sss_id,
                ),
            )
            geri_bildirim_id = int(baglanti.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0])
        sonuc = asyncio.run(
            asyncio.to_thread(servis.geri_bildirimi_onayla, geri_bildirim_id)
        )
        assert sonuc["yeni_durum"] == "ONAYLANDI"
        assert sonuc["alternatif_soru_id"] is not None
        with baglam_yoneticisi() as baglanti:
            satir = baglanti.execute(
                """
                SELECT durum, model_adi, vektor_boyutu, metin_ozeti
                FROM alternatif_sorular
                WHERE id = ?
                """,
                (sonuc["alternatif_soru_id"],),
            ).fetchone()
        assert satir is not None
        assert satir["durum"] == "onaylandi"
        assert satir["model_adi"] == "test_model"
        assert satir["vektor_boyutu"] == 384
        assert satir["metin_ozeti"]
        sorgu_vektoru = servis.vektor_servisi.metni_vektore_donustur(
            "Alternatif ifade"
        )
        arama_sonuclari = servis.alternatif_sorulari_ara(
            sorgu_vektoru,
            5,
        )
        assert arama_sonuclari[0]["sss_id"] == sss_id
        assert arama_sonuclari[0]["benzerlik_skoru"] == pytest.approx(1.0)

    def test_yonetici_kullanicinin_secimini_degistirebilir(
        self,
        servis,
        gecici_veritabani,
    ):
        with baglam_yoneticisi() as baglanti:
            sss_kimlikleri = []
            for sira in range(2):
                imlec = baglanti.execute(
                    """
                    INSERT INTO sss_kayitlari (
                        kategori, soru, cevap, kaynak_dokuman, durum
                    )
                    VALUES (?, ?, ?, ?, 'aktif')
                    """,
                    (
                        "Test",
                        f"Test sorusu {sira}",
                        f"Test cevabi {sira}",
                        "Test dokumani",
                    ),
                )
                sss_kimlikleri.append(int(imlec.lastrowid))
            imlec = baglanti.execute(
                """
                INSERT INTO geri_bildirimler (
                    sss_id, kullanici_sorusu, verilen_cevap,
                    puan, secili_sss_id
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    sss_kimlikleri[0],
                    "Yonetici duzeltmesi",
                    "Eski cevap",
                    1,
                    sss_kimlikleri[0],
                ),
            )
            geri_bildirim_id = int(imlec.lastrowid)
        sonuc = servis.geri_bildirimi_onayla(
            geri_bildirim_id,
            sss_kimlikleri[1],
        )
        with baglam_yoneticisi() as baglanti:
            geri_bildirim = baglanti.execute(
                """
                SELECT secili_sss_id
                FROM geri_bildirimler
                WHERE id = ?
                """,
                (geri_bildirim_id,),
            ).fetchone()
            alternatif = baglanti.execute(
                """
                SELECT sss_id, durum
                FROM alternatif_sorular
                WHERE id = ?
                """,
                (sonuc["alternatif_soru_id"],),
            ).fetchone()
        assert geri_bildirim["secili_sss_id"] == sss_kimlikleri[1]
        assert alternatif["sss_id"] == sss_kimlikleri[1]
        assert alternatif["durum"] == "onaylandi"

    def test_onayla_secili_sss_yoksa_alternatif_eklenmez(self, servis, gecici_veritabani):
        with baglam_yoneticisi() as baglanti:
            imlec = baglanti.execute(
                """
                INSERT INTO sss_kayitlari (
                    kategori, soru, cevap, kaynak_dokuman, durum
                )
                VALUES (
                    'Test', 'Test sorusu', 'Test cevabi',
                    'Test dokumani', 'aktif'
                )
                """
            )
            sss_id = int(imlec.lastrowid)
            baglanti.execute(
                """
                INSERT INTO geri_bildirimler (
                    sss_id, kullanici_sorusu, verilen_cevap,
                    puan, yorum, secili_sss_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sss_id, "Kullanici sorusu", "Cevap", 2, None, None),
            )
            geri_bildirim_id = int(baglanti.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0])
        sonuc = asyncio.run(
            asyncio.to_thread(servis.geri_bildirimi_onayla, geri_bildirim_id)
        )
        assert sonuc["yeni_durum"] == "ONAYLANDI"
        assert sonuc["alternatif_soru_id"] is None

    def test_reddet_durumu_gunceller(self, servis, gecici_veritabani):
        with baglam_yoneticisi() as baglanti:
            baglanti.execute(
                """
                INSERT INTO geri_bildirimler (
                    sss_id, kullanici_sorusu, verilen_cevap,
                    puan, yorum
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (None, "Kullanici sorusu", "Cevap", 1, "Kotu yanit"),
            )
            geri_bildirim_id = int(baglanti.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0])
        yeni_durum = asyncio.run(
            asyncio.to_thread(servis.geri_bildirimi_reddet, geri_bildirim_id)
        )
        assert yeni_durum == "REDDEDILDI"
        with baglam_yoneticisi() as baglanti:
            satir = baglanti.execute(
                "SELECT durum FROM geri_bildirimler WHERE id = ?",
                (geri_bildirim_id,),
            ).fetchone()
        assert satir["durum"] == "REDDEDILDI"

    def test_bekleyenleri_listeler(self, servis, gecici_veritabani):
        with baglam_yoneticisi() as baglanti:
            for i in range(3):
                baglanti.execute(
                    """
                    INSERT INTO geri_bildirimler (
                        sss_id, kullanici_sorusu, verilen_cevap,
                        puan, yorum
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (None, f"Soru {i}", f"Cevap {i}", 3, None),
                )
        bildirimler, toplam = asyncio.run(
            asyncio.to_thread(
                servis.bekleyen_geri_bildirimleri_listele, 1, 10
            )
        )
        assert toplam >= 3

    def test_gecersiz_bekleyen_onay_reddedilir(self, servis, gecici_veritabani):
        with pytest.raises(
            GeriBildirimServisiHatasi, match="Bekleyen geri bildirim bulunamadi"
        ):
            asyncio.run(asyncio.to_thread(servis.geri_bildirimi_onayla, 99999))

    def test_alternatif_sorulari_ara_bos_doner(self, servis, gecici_veritabani):
        sonuclar = servis.alternatif_sorulari_ara(
            np.zeros(384, dtype=np.float32),
            5,
        )
        assert sonuclar == []

    def test_bozuk_alternatif_soru_vektoru_atlanir(
        self,
        servis,
        gecici_veritabani,
    ):
        soru = "Bozuk vektor sorusu"
        with baglam_yoneticisi() as baglanti:
            imlec = baglanti.execute(
                """
                INSERT INTO sss_kayitlari (
                    kategori, soru, cevap, kaynak_dokuman, durum
                )
                VALUES ('Test', 'Soru', 'Cevap', 'Dokuman', 'aktif')
                """
            )
            baglanti.execute(
                """
                INSERT INTO alternatif_sorular (
                    sss_id, soru, vektor_verisi, model_adi,
                    vektor_boyutu, metin_ozeti, kaynak, durum
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'onaylandi')
                """,
                (
                    int(imlec.lastrowid),
                    soru,
                    b"\x00",
                    "test_model",
                    384,
                    hashlib.sha256(soru.encode("utf-8")).hexdigest(),
                    "test",
                ),
            )
        sorgu_vektoru = servis.vektor_servisi.metni_vektore_donustur(soru)
        assert servis.alternatif_sorulari_ara(sorgu_vektoru, 5) == []

    def test_sistem_gunlugu_kaydeder(self, servis, gecici_veritabani):
        servis.sistem_gunlugu_kaydet(
            "test_kullanici",
            "TEST_ISLEMI",
            "Test detayi",
        )


def test_eski_geri_bildirim_tablosuna_secili_sss_migrasyonu_uygulanir(
    tmp_path,
    monkeypatch,
):
    veritabani_yolu = tmp_path / "eski.db"
    with sqlite3.connect(veritabani_yolu) as baglanti:
        baglanti.execute(
            """
            CREATE TABLE geri_bildirimler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sss_id INTEGER,
                kullanici_sorusu TEXT NOT NULL,
                verilen_cevap TEXT NOT NULL,
                puan INTEGER NOT NULL,
                yorum TEXT,
                durum TEXT NOT NULL DEFAULT 'BEKLEMEDE',
                tarih DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        baglanti.execute(
            """
            CREATE TABLE alternatif_sorular (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sss_id INTEGER NOT NULL,
                soru TEXT NOT NULL,
                vektor_verisi BLOB,
                kaynak TEXT NOT NULL,
                durum TEXT NOT NULL DEFAULT 'beklemede',
                olusturulma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    test_konfigurasyonu = konfigurasyon_modulu.konfigurasyon.model_copy(
        update={"VERITABANI_YOLU": str(veritabani_yolu)}
    )
    monkeypatch.setattr(
        konfigurasyon_modulu,
        "konfigurasyon",
        test_konfigurasyonu,
    )
    monkeypatch.setattr(
        veritabani_modulu,
        "konfigurasyon",
        test_konfigurasyonu,
    )
    from uygulama.modeller.veritabani_modelleri import tablolari_olustur

    tablolari_olustur()
    with sqlite3.connect(veritabani_yolu) as baglanti:
        kolonlar = {
            satir[1]
            for satir in baglanti.execute(
                "PRAGMA table_info(geri_bildirimler)"
            ).fetchall()
        }
        alternatif_kolonlari = {
            satir[1]
            for satir in baglanti.execute(
                "PRAGMA table_info(alternatif_sorular)"
            ).fetchall()
        }
    assert "secili_sss_id" in kolonlar
    assert {
        "model_adi",
        "vektor_boyutu",
        "metin_ozeti",
    }.issubset(alternatif_kolonlari)
