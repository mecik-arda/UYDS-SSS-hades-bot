import asyncio
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from uygulama.api.bagimliliklar import (
    akis_semaforunu_al,
    akis_servisini_al,
    arama_servisini_al,
    api_servisini_al,
    geri_bildirim_servisini_al,
    eposta_raporlayiciyi_al,
    oturum_hafizasini_al,
    oturum_sahipligi_servisini_al,
    senkronizasyon_motorunu_al,
)
from uygulama.api.rotalar.analitik import router as analitik_router
from uygulama.api.rotalar.arama import router as arama_router
from uygulama.api.rotalar.geri_bildirim import router as geri_bildirim_router
from uygulama.api.rotalar.kimlik_dogrulama import (
    router as kimlik_dogrulama_router,
)
from uygulama.api.rotalar.sss import router as sss_router
from uygulama.api.rotalar.yonetici import router as yonetici_router
from uygulama.cekirdek.guvenlik import sifre_hash_olustur
from uygulama.cekirdek.hata_yonetimi import (
    IstekKimligiMiddleware,
    hata_yonetimini_kaydet,
)
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.veritabani_modelleri import tablolari_olustur
from uygulama.servisler.api_servisi import ApiServisi
from uygulama.servisler.geri_bildirim_servisi import GeriBildirimServisi
from uygulama.servisler.oturum_hafizasi import OturumHafizasi
from uygulama.servisler.oturum_sahipligi import OturumSahipligiServisi


class SahteAkisServisi:
    async def yanit_akisini_uret(
        self,
        soru: str,
        oturum_id: str,
        kullanici_rolu: str | None = None,
    ):
        yield (
            'event: meta\ndata: {"guven_skoru":0.91,'
            '"yeterli_guven":true,"kaynaklar":[{"sss_id":1}]}\n\n'
        )
        yield 'event: parca\ndata: {"metin":"Sentetik yanit"}\n\n'
        yield 'event: tamamlandi\ndata: {"cevaplandi":true}\n\n'


class SahteSenkronizasyonSonucu:
    islenen_belge_sayisi = 2
    yeni_parca_sayisi = 4
    silinen_parca_sayisi = 1
    karantina_sayisi = 0
    surumlenen_belge_sayisi = 1
    hata_sayisi = 0
    sure_saniye = 0.25


class SahteSenkronizasyonMotoru:
    def artimsal_senkronizasyon(self):
        return SahteSenkronizasyonSonucu()

    def tam_senkronizasyon(self):
        return SahteSenkronizasyonSonucu()


class SahteEpostaRaporlayici:
    async def haftalik_raporu_gonder(self):
        return True


class SahteAramaServisi:
    def ara(self, soru: str, kullanici_rolu: str | None = None):
        return SimpleNamespace(
            adaylar=tuple(
                SimpleNamespace(sss_id=kimlik)
                for kimlik in range(1, 13)
            ),
            gecen_sure_ms=12.5,
            yeniden_siralama_etkin=False,
        )


@pytest.fixture
def faz7_istemcisi(tmp_path, monkeypatch, mock_vektor_servisi):
    monkeypatch.setattr(
        konfigurasyon,
        "VERITABANI_YOLU",
        str(tmp_path / "faz7.db"),
    )
    monkeypatch.setattr(
        konfigurasyon,
        "JWT_GIZLI_ANAHTARI",
        "faz7_test_jwt_anahtari_32_karakterden_uzun",
    )
    monkeypatch.setattr(konfigurasyon, "JWT_ANAHTAR_KIMLIGI", "test-ana")
    monkeypatch.setattr(konfigurasyon, "JWT_ONCEKI_GIZLI_ANAHTAR", "")
    monkeypatch.setattr(konfigurasyon, "JWT_ONCEKI_ANAHTAR_KIMLIGI", "")
    monkeypatch.setattr(konfigurasyon, "YONETICI_ISTEK_IMZA_ANAHTARI", "")
    tablolari_olustur()
    with baglam_yoneticisi() as baglanti:
        for kullanici_adi, rol in (
            ("kullanici1", "KULLANICI"),
            ("kullanici2", "KULLANICI"),
            ("yonetici", "YONETICI"),
        ):
            baglanti.execute(
                """
                INSERT INTO kullanicilar (
                    kullanici_adi,
                    sifre_hash,
                    rol,
                    aktif_mi
                )
                VALUES (?, ?, ?, 1)
                """,
                (
                    kullanici_adi,
                    sifre_hash_olustur("GuvenliTestSifresi123"),
                    rol,
                ),
            )
        baglanti.execute(
            """
            INSERT INTO sss_kayitlari (
                kategori,
                soru,
                cevap,
                kaynak_dokuman,
                durum
            )
            VALUES ('Test', 'Sentetik soru', 'Sentetik cevap', 'Test', 'aktif')
            """
        )
    uygulama = FastAPI()
    hata_yonetimini_kaydet(uygulama)
    uygulama.add_middleware(IstekKimligiMiddleware)
    uygulama.include_router(kimlik_dogrulama_router)
    uygulama.include_router(arama_router)
    uygulama.include_router(geri_bildirim_router)
    uygulama.include_router(sss_router)
    uygulama.include_router(yonetici_router)
    uygulama.include_router(analitik_router)
    api_servisi = ApiServisi()
    geri_bildirim_servisi = GeriBildirimServisi(mock_vektor_servisi)
    sahiplik = OturumSahipligiServisi()
    hafiza = OturumHafizasi()
    uygulama.dependency_overrides[akis_servisini_al] = SahteAkisServisi
    uygulama.dependency_overrides[arama_servisini_al] = SahteAramaServisi
    uygulama.dependency_overrides[api_servisini_al] = lambda: api_servisi
    uygulama.dependency_overrides[
        geri_bildirim_servisini_al
    ] = lambda: geri_bildirim_servisi
    uygulama.dependency_overrides[
        oturum_sahipligi_servisini_al
    ] = lambda: sahiplik
    uygulama.dependency_overrides[
        oturum_hafizasini_al
    ] = lambda: hafiza
    uygulama.dependency_overrides[
        akis_semaforunu_al
    ] = lambda: asyncio.Semaphore(2)
    uygulama.dependency_overrides[
        senkronizasyon_motorunu_al
    ] = SahteSenkronizasyonMotoru
    uygulama.dependency_overrides[
        eposta_raporlayiciyi_al
    ] = SahteEpostaRaporlayici
    with TestClient(
        uygulama,
        raise_server_exceptions=False,
    ) as istemci:
        yield istemci


def giris_yap(
    istemci: TestClient,
    kullanici_adi: str,
) -> dict:
    yanit = istemci.post(
        "/api/v1/kimlik-dogrulama/giris",
        json={
            "kullanici_adi": kullanici_adi,
            "sifre": "GuvenliTestSifresi123",
        },
    )
    assert yanit.status_code == 200
    return yanit.json()


def yetki_basligi(belirtec: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {belirtec}"}


def test_olcum_aramasi_yalniz_yoneticiye_ilk_on_adayi_dondurur(
    faz7_istemcisi,
):
    kullanici = giris_yap(faz7_istemcisi, "kullanici1")
    yetkisiz = faz7_istemcisi.post(
        "/api/v1/yonetici/olcum/arama",
        json={"soru": "Sentetik soru"},
        headers=yetki_basligi(kullanici["erisim_belirteci"]),
    )
    assert yetkisiz.status_code == 403

    yonetici = giris_yap(faz7_istemcisi, "yonetici")
    yanit = faz7_istemcisi.post(
        "/api/v1/yonetici/olcum/arama",
        json={"soru": "Sentetik soru"},
        headers=yetki_basligi(yonetici["erisim_belirteci"]),
    )

    assert yanit.status_code == 200
    assert yanit.json() == {
        "sirali_sss_idleri": list(range(1, 11)),
        "gecen_sure_ms": 12.5,
        "yeniden_siralama_etkin": False,
    }


def yonetici_imza_basliklari(
    yontem: str,
    yol: str,
    govde: bytes,
    nonce: str,
) -> dict[str, str]:
    zaman = str(int(time.time()))
    govde_ozeti = hashlib.sha256(govde).hexdigest()
    imzalanan = "\n".join((zaman, nonce, yontem, yol, govde_ozeti))
    imza = hmac.new(
        konfigurasyon.JWT_GIZLI_ANAHTARI.encode("utf-8"),
        imzalanan.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "X-UYDS-Zaman": zaman,
        "X-UYDS-Nonce": nonce,
        "X-UYDS-Imza": imza,
    }


def test_giris_yenileme_rotasyonu_tekrar_kullanimi_engeller(
    faz7_istemcisi,
):
    ilk = giris_yap(faz7_istemcisi, "kullanici1")
    baslik = jwt.get_unverified_header(ilk["erisim_belirteci"])
    assert baslik["kid"] == "test-ana"

    yenilenen = faz7_istemcisi.post(
        "/api/v1/kimlik-dogrulama/yenile",
        json={"yenileme_belirteci": ilk["yenileme_belirteci"]},
    )
    assert yenilenen.status_code == 200

    tekrar = faz7_istemcisi.post(
        "/api/v1/kimlik-dogrulama/yenile",
        json={"yenileme_belirteci": ilk["yenileme_belirteci"]},
    )
    assert tekrar.status_code == 401

    aile_iptali = faz7_istemcisi.post(
        "/api/v1/kimlik-dogrulama/yenile",
        json={
            "yenileme_belirteci": yenilenen.json()["yenileme_belirteci"]
        },
    )
    assert aile_iptali.status_code == 401


def test_cikis_erisim_belirtecini_ve_oturumlari_gecersiz_kilar(
    faz7_istemcisi,
):
    belirtecler = giris_yap(faz7_istemcisi, "kullanici1")
    basliklar = yetki_basligi(belirtecler["erisim_belirteci"])

    arama = faz7_istemcisi.post(
        "/api/v1/arama",
        json={"soru": "Sentetik soru"},
        headers=basliklar,
    )
    assert arama.status_code == 200

    cikis = faz7_istemcisi.post(
        "/api/v1/kimlik-dogrulama/cikis",
        json={"yenileme_belirteci": belirtecler["yenileme_belirteci"]},
        headers=basliklar,
    )
    assert cikis.status_code == 200

    reddedilen = faz7_istemcisi.get("/api/v1/sss", headers=basliklar)
    assert reddedilen.status_code == 401


def test_oturum_kullanicilar_arasinda_paylasilamaz(faz7_istemcisi):
    birinci = giris_yap(faz7_istemcisi, "kullanici1")
    ikinci = giris_yap(faz7_istemcisi, "kullanici2")
    ilk_yanit = faz7_istemcisi.post(
        "/api/v1/arama",
        json={"soru": "Sentetik soru"},
        headers=yetki_basligi(birinci["erisim_belirteci"]),
    )
    oturum_satiri = next(
        satir
        for satir in ilk_yanit.text.splitlines()
        if '"oturum_id"' in satir
    )
    oturum_id = json.loads(
        oturum_satiri.removeprefix("data: ")
    )["oturum_id"]

    yabanci_istek = faz7_istemcisi.post(
        "/api/v1/arama",
        json={"soru": "Diger kullanici sorusu", "oturum_id": oturum_id},
        headers=yetki_basligi(ikinci["erisim_belirteci"]),
    )
    assert yabanci_istek.status_code == 404


def test_arama_sse_olaylari_ve_sorgu_kaydi_olusturulur(
    faz7_istemcisi,
):
    belirtecler = giris_yap(faz7_istemcisi, "kullanici1")
    yanit = faz7_istemcisi.post(
        "/api/v1/arama",
        json={"soru": "Sentetik soru"},
        headers=yetki_basligi(belirtecler["erisim_belirteci"]),
    )

    assert yanit.status_code == 200
    assert "event: oturum" in yanit.text
    assert "event: tamamlandi" in yanit.text or "event: hata" in yanit.text


def test_geri_bildirim_analitik_ve_imzali_yonetici_onayi(
    faz7_istemcisi,
):
    kullanici = giris_yap(faz7_istemcisi, "kullanici1")
    geri_bildirim = faz7_istemcisi.post(
        "/api/v1/geri-bildirim",
        json={
            "sss_id": 1,
            "kullanici_sorusu": "Sentetik soru",
            "verilen_cevap": "Sentetik cevap",
            "puan": 4,
            "yorum": "Sentetik yorum",
        },
        headers=yetki_basligi(kullanici["erisim_belirteci"]),
    )
    assert geri_bildirim.status_code == 200

    yonetici = giris_yap(faz7_istemcisi, "yonetici")
    yonetici_yetkisi = yetki_basligi(yonetici["erisim_belirteci"])
    bekleyenler = faz7_istemcisi.get(
        "/api/v1/yonetici/geri-bildirimler",
        headers=yonetici_yetkisi,
    )
    assert bekleyenler.status_code == 200
    assert bekleyenler.json()["toplam"] == 1

    yol = "/api/v1/yonetici/geri-bildirim/onay"
    govde = json.dumps(
        {
            "geri_bildirim_id": geri_bildirim.json()["id"],
            "islem": "ONAYLA",
            "secili_sss_id": 1,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    nonce = "a" * 32
    imza_basliklari = yonetici_imza_basliklari(
        "POST",
        yol,
        govde,
        nonce,
    )
    imza_basliklari.update(yonetici_yetkisi)
    imza_basliklari["Content-Type"] = "application/json"
    onay = faz7_istemcisi.post(
        yol,
        content=govde,
        headers=imza_basliklari,
    )
    assert onay.status_code == 200
    assert onay.json()["yeni_durum"] == "ONAYLANDI"
    with baglam_yoneticisi() as baglanti:
        alternatif_soru = baglanti.execute(
            """
            SELECT sss_id, durum, model_adi, vektor_boyutu
            FROM alternatif_sorular
            """
        ).fetchone()
    assert alternatif_soru["sss_id"] == 1
    assert alternatif_soru["durum"] == "onaylandi"
    assert alternatif_soru["model_adi"]
    assert alternatif_soru["vektor_boyutu"] == 384

    tekrar = faz7_istemcisi.post(
        yol,
        content=govde,
        headers=imza_basliklari,
    )
    assert tekrar.status_code == 409

    analitik = faz7_istemcisi.get(
        "/api/v1/analitik",
        headers=yonetici_yetkisi,
    )
    assert analitik.status_code == 200
    assert analitik.json()["toplam_geri_bildirim_sayisi"] == 1


def test_cevapsiz_sorgular_yalniz_yoneticiye_sayfalanir(
    faz7_istemcisi,
):
    with baglam_yoneticisi() as baglanti:
        baglanti.execute(
            """
            INSERT INTO asistan_sorgulari (
                kullanici_sorusu,
                guven_skoru,
                cevaplandi_mi,
                kullanici_adi
            )
            VALUES ('Cevapsiz sentetik soru', 0.2, 0, 'kullanici1')
            """
        )
    kullanici = giris_yap(faz7_istemcisi, "kullanici1")
    kullanici_yaniti = faz7_istemcisi.get(
        "/api/v1/yonetici/cevapsiz-sorgular",
        headers=yetki_basligi(kullanici["erisim_belirteci"]),
    )
    assert kullanici_yaniti.status_code == 403
    yonetici = giris_yap(faz7_istemcisi, "yonetici")
    yonetici_yaniti = faz7_istemcisi.get(
        "/api/v1/yonetici/cevapsiz-sorgular",
        params={"sayfa": 1, "sayfa_basina": 10},
        headers=yetki_basligi(yonetici["erisim_belirteci"]),
    )
    assert yonetici_yaniti.status_code == 200
    govde = yonetici_yaniti.json()
    assert govde["toplam"] == 1
    assert govde["sayfalama"] == {"sayfa": 1, "sayfa_basina": 10}
    assert govde["sorgular"][0]["kullanici_sorusu"] == "Cevapsiz sentetik soru"
    assert govde["sorgular"][0]["guven_skoru"] == pytest.approx(0.2)


def test_dogrulama_hatasi_girdi_degerini_geri_yansitmaz(
    faz7_istemcisi,
):
    yanit = faz7_istemcisi.post(
        "/api/v1/kimlik-dogrulama/giris",
        json={"kullanici_adi": "gecersiz bosluk", "sifre": "gizli-deger"},
    )

    assert yanit.status_code == 422
    assert "gizli-deger" not in yanit.text
    assert "istek_kimligi" in yanit.json()


def test_tarayici_yonetici_imzasi_yalniz_izinli_isleme_verilir(
    faz7_istemcisi,
):
    belirtecler = giris_yap(faz7_istemcisi, "yonetici")
    basliklar = yetki_basligi(belirtecler["erisim_belirteci"])
    govde = json.dumps(
        {
            "geri_bildirim_id": 1,
            "islem": "REDDET",
            "secili_sss_id": None,
        },
        separators=(",", ":"),
    )
    izinli = faz7_istemcisi.post(
        "/api/v1/yonetici/islem-imzasi",
        json={
            "hedef_yol": "/api/v1/yonetici/geri-bildirim/onay",
            "govde": govde,
        },
        headers=basliklar,
    )
    assert izinli.status_code == 200
    assert len(izinli.json()["imza"]) == 64
    reddedilen = faz7_istemcisi.post(
        "/api/v1/yonetici/islem-imzasi",
        json={"hedef_yol": "/api/v1/kimlik-dogrulama/giris", "govde": ""},
        headers=basliklar,
    )
    assert reddedilen.status_code == 400


def test_isletim_durumu_gizli_degerleri_aciklamaz(faz7_istemcisi):
    belirtecler = giris_yap(faz7_istemcisi, "yonetici")
    yanit = faz7_istemcisi.get(
        "/api/v1/yonetici/isletim-durumu",
        headers=yetki_basligi(belirtecler["erisim_belirteci"]),
    )
    assert yanit.status_code == 200
    metin = yanit.text.lower()
    assert "api_anahtari" not in metin
    assert "jwt_gizli" not in metin
    assert set(yanit.json()) == {
        "arama",
        "belgeler",
        "veri_yonetimi",
        "otomasyon",
    }


def test_sss_katalogu_metin_ve_kayit_numarasi_ile_aranabilir(
    faz7_istemcisi,
):
    belirtecler = giris_yap(faz7_istemcisi, "yonetici")
    basliklar = yetki_basligi(belirtecler["erisim_belirteci"])
    metin_arama = faz7_istemcisi.get(
        "/api/v1/sss?arama=Sentetik",
        headers=basliklar,
    )
    kimlik_arama = faz7_istemcisi.get(
        "/api/v1/sss?arama=1",
        headers=basliklar,
    )
    assert metin_arama.status_code == 200
    assert metin_arama.json()["toplam"] == 1
    assert kimlik_arama.status_code == 200
    assert kimlik_arama.json()["kayitlar"][0]["id"] == 1


@pytest.mark.parametrize(
    ("yol", "govde", "beklenen_alan"),
    [
        (
            "/api/v1/yonetici/senkronizasyon",
            '{"tur":"artimsal"}',
            "islenen_belge_sayisi",
        ),
        (
            "/api/v1/yonetici/eposta-raporu/gonder",
            "",
            "gonderildi",
        ),
    ],
)
def test_imzali_isletim_islemleri_frontend_akisi_ile_calistirilir(
    faz7_istemcisi,
    yol,
    govde,
    beklenen_alan,
):
    belirtecler = giris_yap(faz7_istemcisi, "yonetici")
    yetki = yetki_basligi(belirtecler["erisim_belirteci"])
    imza_yaniti = faz7_istemcisi.post(
        "/api/v1/yonetici/islem-imzasi",
        json={"hedef_yol": yol, "govde": govde},
        headers=yetki,
    )
    imza = imza_yaniti.json()
    basliklar = {
        **yetki,
        "Content-Type": "application/json",
        "X-UYDS-Zaman": imza["zaman"],
        "X-UYDS-Nonce": imza["nonce"],
        "X-UYDS-Imza": imza["imza"],
    }
    yanit = faz7_istemcisi.post(
        yol,
        content=govde.encode("utf-8"),
        headers=basliklar,
    )
    assert yanit.status_code == 200
    assert beklenen_alan in yanit.json()
