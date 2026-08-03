import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from uygulama.servisler.belge_ayiklayici import BelgeAyiklamaHatasi
import uygulama.servisler.senkronizasyon_motoru as senkronizasyon_modulu
from uygulama.servisler.senkronizasyon_motoru import (
    SenkronizasyonMotoru,
    SenkronizasyonPlani,
    SenkronizasyonSonucu,
)


def test_dizin_tara_bos_dizin_bos_doner(tmp_path):
    motor = SenkronizasyonMotoru()
    sonuc = motor.dizin_tara([str(tmp_path)])
    assert sonuc == []


def test_dizin_tara_desteklenmeyen_format_atlanir(tmp_path):
    motor = SenkronizasyonMotoru()
    dosya = tmp_path / "test.txt"
    dosya.write_text("icerik")
    sonuc = motor.dizin_tara([str(tmp_path)])
    assert sonuc == []


def test_dizin_tara_html_dosyasi_bulur(tmp_path):
    motor = SenkronizasyonMotoru()
    dosya = tmp_path / "test.html"
    dosya.write_text("<html></html>")
    sonuc = motor.dizin_tara([str(tmp_path)])
    assert len(sonuc) == 1
    assert sonuc[0].dosya_adi == "test.html"


def test_senkronizasyon_sonucu_sure_hesaplanir():
    baslangic = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    bitis = datetime(2026, 1, 1, 12, 1, 30, tzinfo=timezone.utc)
    sonuc = SenkronizasyonSonucu(
        baslangic_zamani=baslangic,
        bitis_zamani=bitis,
    )
    assert sonuc.sure_saniye == 90.0


def test_senkronizasyon_plani_degisiklik_var_mi():
    plan = SenkronizasyonPlani()
    assert not plan.degisiklik_var_mi


def _senkronizasyon_konfigurasyonu(tmp_path):
    return SimpleNamespace(
        BELGE_DIZINLERI=str(tmp_path),
        BELGE_ALT_DIZINLER_DAHIL=True,
        BELGE_DESTEK_FORMATLAR="html",
        BELGE_SURUMLE_AKTIF=True,
        BELGE_MAKS_SURUM_SAKLA=10,
        SENKRONIZASYON_MAKS_HATA=5,
        GRAF_AKTIF=True,
        GRAF_KAVRAM_STRATEJISI="hafif",
    )


def _belge_icerigi(dosya, sha256_ozeti):
    return SimpleNamespace(
        sha256_ozeti=sha256_ozeti,
        sayfa_sayisi=1,
        yetki_seviyesi=0,
        kaynak_dosya=str(dosya),
        ham_metin="Prosedur adimlari ve prosedur kurallari",
    )


def test_tam_senkronizasyon_basari_sayaclarini_dogru_raporlar(
    gecici_veritabani,
    tmp_path,
    monkeypatch,
    mock_vektor_servisi,
):
    dosya = tmp_path / "prosedur.html"
    dosya.write_text("<p>Prosedur</p>", encoding="utf-8")
    motor = SenkronizasyonMotoru(mock_vektor_servisi)
    motor._belge_ayiklayici = SimpleNamespace(
        belge_ayikla=lambda _: _belge_icerigi(dosya, "yeni-ozet")
    )
    monkeypatch.setattr(
        senkronizasyon_modulu,
        "konfigurasyon",
        _senkronizasyon_konfigurasyonu(tmp_path),
    )

    sonuc = motor.tam_senkronizasyon()

    assert sonuc.islenen_belge_sayisi == 1
    assert sonuc.karantina_sayisi == 0
    assert sonuc.hata_sayisi == 0
    assert sonuc.bitis_zamani >= sonuc.baslangic_zamani


def test_tam_senkronizasyon_karantinayi_ve_hatayi_raporlar(
    gecici_veritabani,
    tmp_path,
    monkeypatch,
):
    dosya = tmp_path / "bozuk.html"
    dosya.write_text("bozuk", encoding="utf-8")
    motor = SenkronizasyonMotoru()

    def hata_uret(_):
        raise BelgeAyiklamaHatasi("Belge bozuk", "HTML_BOZUK")

    motor._belge_ayiklayici = SimpleNamespace(belge_ayikla=hata_uret)
    monkeypatch.setattr(
        senkronizasyon_modulu,
        "konfigurasyon",
        _senkronizasyon_konfigurasyonu(tmp_path),
    )

    sonuc = motor.tam_senkronizasyon()

    assert sonuc.islenen_belge_sayisi == 0
    assert sonuc.karantina_sayisi == 1
    assert sonuc.hata_sayisi == 1
    assert sonuc.hata_mesajlari == ["bozuk.html: HTML_BOZUK"]


def test_zamanlanmis_senkronizasyon_bloklayici_isi_is_parcacigina_aktarir(
    monkeypatch,
):
    motor = SenkronizasyonMotoru()
    cagrilan_fonksiyonlar = []
    monkeypatch.setattr(
        senkronizasyon_modulu,
        "konfigurasyon",
        SimpleNamespace(
            SENKRONIZASYON_SAATI="00:00",
            ARTIMSAL_SENKRONIZASYON_DAKIKA=30,
            SENKRONIZASYON_ZAMAN_ASIMI_SANIYE=3600,
        ),
    )

    async def beklemeden_devam_et(_):
        return None

    async def is_parcaciginda_calistir(fonksiyon):
        cagrilan_fonksiyonlar.append(fonksiyon)
        raise RuntimeError("donguyu-durdur")

    monkeypatch.setattr(
        senkronizasyon_modulu.asyncio,
        "sleep",
        beklemeden_devam_et,
    )
    monkeypatch.setattr(
        senkronizasyon_modulu.asyncio,
        "to_thread",
        is_parcaciginda_calistir,
    )

    async def zaman_asimini_uygula(islem, timeout):
        return await islem

    monkeypatch.setattr(
        senkronizasyon_modulu.asyncio,
        "wait_for",
        zaman_asimini_uygula,
    )

    with pytest.raises(RuntimeError, match="donguyu-durdur"):
        asyncio.run(motor._zamanlanmis_senkronizasyon_gorevi())

    assert cagrilan_fonksiyonlar == [motor.artimsal_senkronizasyon]


def test_senkronizasyon_parca_vektor_surum_ve_silme_zincirini_tamamlar(
    gecici_veritabani,
    tmp_path,
    monkeypatch,
    mock_vektor_servisi,
):
    dosya = tmp_path / "yonetmelik.html"
    dosya.write_text(
        "<html><body><h1>İzin</h1><p>Yıllık izin yirmi gündür.</p></body></html>",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        senkronizasyon_modulu,
        "konfigurasyon",
        _senkronizasyon_konfigurasyonu(tmp_path),
    )
    motor = SenkronizasyonMotoru(mock_vektor_servisi)

    ilk_sonuc = motor.tam_senkronizasyon()
    dosya.write_text(
        "<html><body><h1>İzin</h1><p>Yıllık izin otuz gündür.</p></body></html>",
        encoding="utf-8",
    )
    ikinci_sonuc = motor.tam_senkronizasyon()
    dosya.unlink()
    ucuncu_sonuc = motor.tam_senkronizasyon()

    from uygulama.cekirdek.veritabani import baglam_yoneticisi

    with baglam_yoneticisi() as baglanti:
        belge_sayisi = baglanti.execute(
            "SELECT COUNT(*) FROM belge_kayitlari WHERE islenme_durumu = 'tamamlandi'"
        ).fetchone()[0]
        aktif_belge_sayisi = baglanti.execute(
            "SELECT COUNT(*) FROM belge_kayitlari WHERE aktif = 1"
        ).fetchone()[0]
        parca_sayisi = baglanti.execute(
            "SELECT COUNT(*) FROM yapisal_parcalar"
        ).fetchone()[0]
        vektor_sayisi = baglanti.execute(
            "SELECT COUNT(*) FROM parca_vektorleri"
        ).fetchone()[0]

    assert ilk_sonuc.yeni_parca_sayisi > 0
    assert ikinci_sonuc.surumlenen_belge_sayisi == 1
    assert ucuncu_sonuc.silinen_parca_sayisi > 0
    assert belge_sayisi == 2
    assert aktif_belge_sayisi == 0
    assert parca_sayisi == vektor_sayisi


def test_erisim_disindaki_belge_dizini_mevcut_kayitlari_pasiflestirmez(
    gecici_veritabani,
    tmp_path,
    monkeypatch,
):
    from uygulama.cekirdek.veritabani import baglam_yoneticisi

    belge_yolu = str(tmp_path / "bagli-olmayan" / "belge.html")
    with baglam_yoneticisi() as baglanti:
        baglanti.execute(
            """
            INSERT INTO belge_kayitlari (
                dosya_adi, dosya_formati, orijinal_yol,
                sha256_ozeti, islenme_durumu, aktif
            ) VALUES ('belge.html', '.html', ?, 'ozet', 'tamamlandi', 1)
            """,
            (belge_yolu,),
        )
    ayarlar = _senkronizasyon_konfigurasyonu(tmp_path / "bagli-olmayan")
    monkeypatch.setattr(senkronizasyon_modulu, "konfigurasyon", ayarlar)

    sonuc = SenkronizasyonMotoru().tam_senkronizasyon()

    with baglam_yoneticisi() as baglanti:
        aktif = baglanti.execute(
            "SELECT aktif FROM belge_kayitlari WHERE orijinal_yol = ?",
            (belge_yolu,),
        ).fetchone()[0]
    assert sonuc.silinen_parca_sayisi == 0
    assert aktif == 1
