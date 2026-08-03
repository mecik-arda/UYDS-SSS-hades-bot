import json
from datetime import datetime, timezone

from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.servisler.belge_arama import BelgeArama
import uygulama.servisler.belge_arama as belge_arama_modulu


def _belge_ekle(
    dosya_adi,
    yol,
    tarih,
    yetki,
    aktif,
    metin,
    mock_vektor_servisi,
):
    with baglam_yoneticisi() as baglanti:
        belge_imleci = baglanti.execute(
            """
            INSERT INTO belge_kayitlari (
                dosya_adi, dosya_formati, orijinal_yol,
                son_degistirilme_tarihi, sha256_ozeti,
                yetki_seviyesi, islenme_durumu, aktif
            ) VALUES (?, '.html', ?, ?, ?, ?, 'tamamlandi', ?)
            """,
            (dosya_adi, yol, tarih, dosya_adi, yetki, aktif),
        )
        belge_id = int(belge_imleci.lastrowid)
        parca_imleci = baglanti.execute(
            """
            INSERT INTO yapisal_parcalar (
                belge_id, metin, parca_turu, baslik_zinciri_json,
                sira, sha256_ozeti, token_sayisi, yetki_seviyesi, aktif
            ) VALUES (?, ?, 'paragraf', ?, 1, ?, 8, ?, ?)
            """,
            (
                belge_id,
                metin,
                json.dumps([]),
                dosya_adi,
                yetki,
                aktif,
            ),
        )
        parca_id = int(parca_imleci.lastrowid)
        vektor = mock_vektor_servisi.metni_vektore_donustur(metin)
        baglanti.execute(
            """
            INSERT INTO parca_vektorleri (
                parca_id, vektor, model_surumu, vektor_boyutu
            ) VALUES (?, ?, ?, ?)
            """,
            (
                parca_id,
                mock_vektor_servisi.vektoru_bloba_donustur(vektor),
                mock_vektor_servisi.model_adi,
                mock_vektor_servisi.vektor_boyutu,
            ),
        )
    return belge_id


def test_yetkisiz_belge_arama_ve_rag_adayina_sizmaz(
    gecici_veritabani,
    mock_vektor_servisi,
    monkeypatch,
):
    monkeypatch.setattr(
        belge_arama_modulu.konfigurasyon,
        "RBAC_YETKI_ESLEME",
        '{"yonetici":3,"kullanici":0}',
    )
    _belge_ekle(
        "genel.html",
        "genel.html",
        datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
        0,
        1,
        "izin proseduru tum calisanlar icindir",
        mock_vektor_servisi,
    )
    _belge_ekle(
        "gizli.html",
        "gizli.html",
        datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
        3,
        1,
        "izin proseduru yonetici maaslarini icerir",
        mock_vektor_servisi,
    )

    kullanici_sonuclari = BelgeArama(mock_vektor_servisi).ara(
        "izin proseduru",
        "izin AND proseduru",
        "KULLANICI",
    )
    yonetici_sonuclari = BelgeArama(mock_vektor_servisi).ara(
        "izin proseduru",
        "izin AND proseduru",
        "YONETICI",
    )

    assert {aday.kaynak_dokuman for aday in kullanici_sonuclari} == {
        "genel.html"
    }
    assert {aday.kaynak_dokuman for aday in yonetici_sonuclari} == {
        "genel.html",
        "gizli.html",
    }


def test_tarih_referansi_dogru_belge_surumunu_secer(
    gecici_veritabani,
    mock_vektor_servisi,
):
    _belge_ekle(
        "yonetmelik.html",
        "yonetmelik.html",
        datetime(2024, 5, 1, tzinfo=timezone.utc).isoformat(),
        0,
        0,
        "2024 izin hakki yirmi gundur",
        mock_vektor_servisi,
    )
    _belge_ekle(
        "yonetmelik.html",
        "yonetmelik.html",
        datetime(2026, 5, 1, tzinfo=timezone.utc).isoformat(),
        0,
        1,
        "2026 izin hakki otuz gundur",
        mock_vektor_servisi,
    )

    sonuclar = BelgeArama(mock_vektor_servisi).ara(
        "2024 izin hakki",
        "izin AND hakki",
        "KULLANICI",
    )

    assert sonuclar
    assert all("2024" in aday.aday_metni for aday in sonuclar)
