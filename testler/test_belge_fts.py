import sqlite3

import pytest

from uygulama.cekirdek.veritabani import baglam_yoneticisi
import uygulama.modeller.veritabani_modelleri as veritabani_modelleri


def _belge_ve_parca_ekle():
    with baglam_yoneticisi() as baglanti:
        belge_id = baglanti.execute(
            """
            INSERT INTO belge_kayitlari (
                dosya_adi,
                dosya_formati,
                orijinal_yol,
                sha256_ozeti
            )
            VALUES ('prosedur.html', '.html', 'prosedur.html', 'belge-ozeti')
            """
        ).lastrowid
        return baglanti.execute(
            """
            INSERT INTO yapisal_parcalar (
                belge_id,
                metin,
                parca_turu,
                baslik_zinciri_json,
                sira,
                sha256_ozeti
            )
            VALUES (?, 'izin proseduru', 'paragraf', '["izin"]', 1, 'parca-ozeti')
            """,
            (belge_id,),
        ).lastrowid


def test_belge_fts_ekleme_guncelleme_ve_silmeyi_izler(
    gecici_veritabani,
):
    parca_id = _belge_ve_parca_ekle()

    with baglam_yoneticisi() as baglanti:
        bulunan = baglanti.execute(
            "SELECT rowid FROM belge_fts WHERE belge_fts MATCH 'proseduru'"
        ).fetchone()
        assert bulunan["rowid"] == parca_id
        baglanti.execute(
            "UPDATE yapisal_parcalar SET metin = 'izin politikasi' WHERE id = ?",
            (parca_id,),
        )

    with baglam_yoneticisi() as baglanti:
        eski_eslesme = baglanti.execute(
            "SELECT rowid FROM belge_fts WHERE belge_fts MATCH 'proseduru'"
        ).fetchone()
        yeni_eslesme = baglanti.execute(
            "SELECT rowid FROM belge_fts WHERE belge_fts MATCH 'politikasi'"
        ).fetchone()
        assert eski_eslesme is None
        assert yeni_eslesme["rowid"] == parca_id
        baglanti.execute(
            "DELETE FROM yapisal_parcalar WHERE id = ?",
            (parca_id,),
        )

    with baglam_yoneticisi() as baglanti:
        silinen_eslesme = baglanti.execute(
            "SELECT rowid FROM belge_fts WHERE belge_fts MATCH 'politikasi'"
        ).fetchone()
        assert silinen_eslesme is None


def test_eski_belge_fts_semasi_veri_kaybetmeden_yukseltilir(
    gecici_veritabani,
):
    parca_id = _belge_ve_parca_ekle()
    with baglam_yoneticisi() as baglanti:
        for tetikleyici_adi in (
            "yapisal_parcalar_fts_ekle",
            "yapisal_parcalar_fts_sil",
            "yapisal_parcalar_fts_guncelle",
        ):
            baglanti.execute(
                f"DROP TRIGGER IF EXISTS {tetikleyici_adi}"
            )
        baglanti.execute("DROP TABLE belge_fts")
        baglanti.execute(
            """
            CREATE VIRTUAL TABLE belge_fts USING fts5(
                parca_id UNINDEXED,
                baslik_zinciri,
                belge_adi,
                content='yapisal_parcalar',
                content_rowid='id'
            )
            """
        )

    veritabani_modelleri.tablolari_olustur()

    with baglam_yoneticisi() as baglanti:
        kolonlar = [
            satir["name"]
            for satir in baglanti.execute(
                "PRAGMA table_info('belge_fts')"
            ).fetchall()
        ]
        bulunan = baglanti.execute(
            "SELECT rowid FROM belge_fts WHERE belge_fts MATCH 'proseduru'"
        ).fetchone()
        assert kolonlar == ["metin", "baslik_zinciri_json"]
        assert bulunan["rowid"] == parca_id


def test_belge_deposu_sema_hatasi_gizlenmez(
    gecici_veritabani,
    monkeypatch,
):
    monkeypatch.setattr(
        veritabani_modelleri,
        "BELGE_DEPOSU_TABLOLARI",
        ["GECERSIZ SQL"],
    )

    with pytest.raises(sqlite3.OperationalError):
        veritabani_modelleri.tablolari_olustur()
