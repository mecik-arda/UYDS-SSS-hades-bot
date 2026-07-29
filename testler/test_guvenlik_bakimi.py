import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from uygulama.cekirdek.dagitim_guvenligi import (
    tek_worker_dagitimini_dogrula,
)
from uygulama.cekirdek.guvenlik import (
    BelirtecVerisi,
    belirtec_coz,
    erisim_belirteci_olustur,
    suresi_dolmus_guvenlik_kayitlarini_temizle,
)
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.veritabani_modelleri import tablolari_olustur
from uygulama.ana import periyodik_guvenlik_bakimini_calistir


def test_suresi_dolmus_guvenlik_kayitlari_aile_butunluguyle_temizlenir(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        konfigurasyon,
        "VERITABANI_YOLU",
        str(tmp_path / "guvenlik-bakimi.db"),
    )
    tablolari_olustur()
    simdi = datetime.now(timezone.utc)
    gecmis = (simdi - timedelta(days=1)).isoformat()
    gelecek = (simdi + timedelta(days=1)).isoformat()
    with baglam_yoneticisi() as baglanti:
        baglanti.execute(
            """
            INSERT INTO kullanicilar (
                kullanici_adi,
                sifre_hash,
                rol,
                aktif_mi
            )
            VALUES ('bakim', 'gecersiz-test-hash', 'KULLANICI', 1)
            """
        )
        baglanti.executemany(
            """
            INSERT INTO yenileme_belirtecleri (
                jti,
                aile_id,
                kullanici_adi,
                belirtec_ozeti,
                sona_erme_tarihi,
                olusturulma_tarihi,
                gecersiz_kilindi_mi
            )
            VALUES (?, ?, 'bakim', ?, ?, ?, 1)
            """,
            (
                ("eski-1", "eski-aile", "ozet-1", gecmis, gecmis),
                ("karma-1", "karma-aile", "ozet-2", gecmis, gecmis),
                ("karma-2", "karma-aile", "ozet-3", gelecek, gecmis),
            ),
        )
        baglanti.executemany(
            """
            INSERT INTO gecersiz_erisim_belirtecleri (
                jti,
                sona_erme_tarihi,
                gecersiz_kilinma_tarihi
            )
            VALUES (?, ?, ?)
            """,
            (
                ("eski-erisim", gecmis, gecmis),
                ("yeni-erisim", gelecek, gecmis),
            ),
        )
        baglanti.executemany(
            """
            INSERT INTO yonetici_imza_nonce_kayitlari (
                nonce_ozeti,
                sona_erme_tarihi
            )
            VALUES (?, ?)
            """,
            (
                ("eski-nonce", gecmis),
                ("yeni-nonce", gelecek),
            ),
        )

    sonuc = suresi_dolmus_guvenlik_kayitlarini_temizle(simdi)

    assert sonuc.silinen_yenileme_belirteci_sayisi == 1
    assert sonuc.silinen_erisim_karaliste_sayisi == 1
    assert sonuc.silinen_yonetici_nonce_sayisi == 1
    with baglam_yoneticisi() as baglanti:
        kalan_aileler = {
            satir["aile_id"]
            for satir in baglanti.execute(
                "SELECT aile_id FROM yenileme_belirtecleri"
            ).fetchall()
        }
        kalan_erisimler = {
            satir["jti"]
            for satir in baglanti.execute(
                "SELECT jti FROM gecersiz_erisim_belirtecleri"
            ).fetchall()
        }
        kalan_nonce_degerleri = {
            satir["nonce_ozeti"]
            for satir in baglanti.execute(
                "SELECT nonce_ozeti FROM yonetici_imza_nonce_kayitlari"
            ).fetchall()
        }
    assert kalan_aileler == {"karma-aile"}
    assert kalan_erisimler == {"yeni-erisim"}
    assert kalan_nonce_degerleri == {"yeni-nonce"}


def test_onceki_jwt_anahtari_rotasyon_penceresinde_kabul_edilir(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        konfigurasyon,
        "VERITABANI_YOLU",
        str(tmp_path / "jwt-rotasyonu.db"),
    )
    eski_anahtar = "eski_jwt_anahtari_32_karakterden_uzun"
    yeni_anahtar = "yeni_jwt_anahtari_32_karakterden_uzun"
    monkeypatch.setattr(konfigurasyon, "JWT_GIZLI_ANAHTARI", eski_anahtar)
    monkeypatch.setattr(konfigurasyon, "JWT_ANAHTAR_KIMLIGI", "eski")
    tablolari_olustur()
    belirtec = erisim_belirteci_olustur(
        BelirtecVerisi(kullanici_adi="kullanici", rol="KULLANICI")
    )
    monkeypatch.setattr(konfigurasyon, "JWT_GIZLI_ANAHTARI", yeni_anahtar)
    monkeypatch.setattr(konfigurasyon, "JWT_ANAHTAR_KIMLIGI", "yeni")
    monkeypatch.setattr(
        konfigurasyon,
        "JWT_ONCEKI_GIZLI_ANAHTAR",
        eski_anahtar,
    )
    monkeypatch.setattr(
        konfigurasyon,
        "JWT_ONCEKI_ANAHTAR_KIMLIGI",
        "eski",
    )

    cozulmus = belirtec_coz(belirtec)

    assert cozulmus is not None
    assert cozulmus.kullanici_adi == "kullanici"
    monkeypatch.setattr(konfigurasyon, "JWT_ONCEKI_GIZLI_ANAHTAR", "")
    monkeypatch.setattr(konfigurasyon, "JWT_ONCEKI_ANAHTAR_KIMLIGI", "")
    assert belirtec_coz(belirtec) is None


@pytest.mark.parametrize(
    "ortam",
    (
        {"WEB_CONCURRENCY": "2"},
        {"UVICORN_WORKERS": "4"},
        {"UVICORN_WORKERS": "gecersiz"},
    ),
)
def test_coklu_ve_gecersiz_worker_yapilandirmasi_reddedilir(ortam):
    with pytest.raises(RuntimeError):
        tek_worker_dagitimini_dogrula(1, ortam)


def test_tek_worker_yapilandirmasi_kabul_edilir():
    tek_worker_dagitimini_dogrula(
        1,
        {"WEB_CONCURRENCY": "1", "UVICORN_WORKERS": "1"},
    )


def test_periyodik_bakim_durdurma_olayiyla_temiz_kapanir():
    async def senaryo():
        durdurma_olayi = asyncio.Event()
        durdurma_olayi.set()
        await asyncio.wait_for(
            periyodik_guvenlik_bakimini_calistir(durdurma_olayi),
            timeout=0.1,
        )

    asyncio.run(senaryo())
