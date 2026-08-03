from fastapi.testclient import TestClient
import pytest

from uygulama.ana import uygulama
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.servisler.api_servisi import ApiServisi


istemci = TestClient(uygulama)


def test_analitik_endpoint_yetkisiz_reddeder():
    yanit = istemci.get("/api/v1/analitik")
    assert yanit.status_code == 401


def test_vektor_durumu_endpoint_yetkisiz_reddeder():
    yanit = istemci.get("/api/v1/analitik/vektor-durumu")
    assert yanit.status_code == 401


def test_belge_dagilimi_endpoint_yetkisiz_reddeder():
    yanit = istemci.get("/api/v1/analitik/belge-dagilimi")
    assert yanit.status_code == 401


def test_senkronizasyon_durumu_endpoint_yetkisiz_reddeder():
    yanit = istemci.get("/api/v1/analitik/senkronizasyon-durumu")
    assert yanit.status_code == 401


def test_karantina_endpoint_yetkisiz_reddeder():
    yanit = istemci.get("/api/v1/analitik/karantina")
    assert yanit.status_code == 401


def test_kavram_bulutu_endpoint_yetkisiz_reddeder():
    yanit = istemci.get("/api/v1/analitik/kavram-bulutu")
    assert yanit.status_code == 401


def test_graf_istatistik_endpoint_yetkisiz_reddeder():
    yanit = istemci.get("/api/v1/analitik/graf-istatistik")
    assert yanit.status_code == 401


@pytest.mark.parametrize(
    "yol",
    [
        "/api/v1/analitik/belge-surumleri",
        "/api/v1/analitik/parca-istatistikleri",
        "/api/v1/analitik/sorgu-trendi",
        "/api/v1/analitik/yetim-kavramlar",
        "/api/v1/analitik/rapor/dokuman",
    ],
)
def test_yeni_belge_analitik_endpointleri_yetkisiz_reddeder(yol):
    yanit = istemci.get(yol)
    assert yanit.status_code == 401


def test_vektor_durumu_eksik_sss_ve_belge_vektorlerini_sayar(
    gecici_veritabani,
):
    with baglam_yoneticisi() as baglanti:
        sss_id = baglanti.execute(
            """
            INSERT INTO sss_kayitlari (kategori, soru, cevap)
            VALUES ('genel', 'Soru', 'Cevap')
            """
        ).lastrowid
        baglanti.execute(
            """
            INSERT INTO sss_parcalari (sss_id, parca_metni, parca_sira_no)
            VALUES (?, 'Cevap', 0)
            """,
            (sss_id,),
        )
        belge_id = baglanti.execute(
            """
            INSERT INTO belge_kayitlari (
                dosya_adi,
                dosya_formati,
                orijinal_yol,
                sha256_ozeti
            )
            VALUES ('belge.html', '.html', 'belge.html', 'belge-ozeti')
            """
        ).lastrowid
        parca_id = baglanti.execute(
            """
            INSERT INTO yapisal_parcalar (
                belge_id,
                metin,
                parca_turu,
                sira,
                sha256_ozeti
            )
            VALUES (?, 'Belge parcasi', 'paragraf', 0, 'parca-ozeti')
            """,
            (belge_id,),
        ).lastrowid

    ilk_durum = ApiServisi().vektor_durumunu_al()
    assert ilk_durum["toplam_vektor"] == 0
    assert ilk_durum["eksik_vektor"] == 2

    with baglam_yoneticisi() as baglanti:
        baglanti.execute(
            """
            INSERT INTO parca_vektorleri (
                parca_id,
                vektor,
                model_surumu,
                vektor_boyutu
            )
            VALUES (?, ?, ?, 1)
            """,
            (parca_id, b"vektor", konfigurasyon.VEKTOR_MODEL_ADI),
        )

    son_durum = ApiServisi().vektor_durumunu_al()
    assert son_durum["toplam_vektor"] == 1
    assert son_durum["eksik_vektor"] == 1


def test_belge_analitik_raporu_tum_alt_bolumleri_icerir(
    gecici_veritabani,
):
    rapor = ApiServisi().belge_analitik_raporunu_al()

    assert set(rapor) == {
        "belge_dagilimi",
        "vektor_durumu",
        "senkronizasyon",
        "karantina",
        "kavram_bulutu",
        "graf",
        "parcalar",
        "sorgu_trendi",
    }
