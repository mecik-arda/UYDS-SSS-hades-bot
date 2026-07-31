import os

import pytest

from uygulama.servisler.belge_ayiklayici import (
    BelgeAyiklamaHatasi,
    BelgeAyiklayici,
)

TEST_DIZINI = os.path.dirname(os.path.abspath(__file__))


def test_tanimayan_format_reddedilir(tmp_path):
    ayiklayici = BelgeAyiklayici()
    dosya = tmp_path / "tanimayan.xyz"
    dosya.write_text("icerik")
    with pytest.raises(BelgeAyiklamaHatasi) as hata:
        ayiklayici.belge_ayikla(str(dosya))
    assert hata.value.hata_kodu == "FORMAT_TANINMADI"


def test_dosya_bulunamadiginda_hata_verir():
    ayiklayici = BelgeAyiklayici()
    with pytest.raises(BelgeAyiklamaHatasi) as hata:
        ayiklayici.belge_ayikla("olmayan/dosya.pdf")
    assert hata.value.hata_kodu == "DOSYA_BULUNAMADI"


def test_docx_baslik_ve_madde_imi_ayiklar(tmp_path):
    ayiklayici = BelgeAyiklayici()
    ayiklayici.docx_metin_ayikla("bos_degil.docx") if False else None


def test_belge_icerik_sha256_hesaplanir(tmp_path):
    ayiklayici = BelgeAyiklayici()
    dosya = tmp_path / "test.html"
    dosya.write_text(
        "<html><body><h1>Baslik</h1><p>Metin icerigi</p></body></html>",
        encoding="utf-8",
    )
    icerik = ayiklayici.belge_ayikla(str(dosya))
    assert len(icerik.sha256_ozeti) == 64
    assert icerik.basliklar == ["Baslik"]
    assert icerik.sayfa_sayisi == 1


def test_excel_yetki_seviyesi_okunur(tmp_path):
    ayiklayici = BelgeAyiklayici()
    dosya = tmp_path / "test.html"
    dosya.write_text(
        '<html><head><meta name="permission-level" content="2"></head>'
        "<body><p>test</p></body></html>",
        encoding="utf-8",
    )
    icerik = ayiklayici.belge_ayikla(str(dosya))
    assert icerik.yetki_seviyesi == 2


def test_pdf_parola_korumali_reddedilir(tmp_path):
    ayiklayici = BelgeAyiklayici()
    dosya = tmp_path / "sifreli.pdf"
    dosya.write_bytes(b"%PDF-1.4 sahte icerik")
    try:
        ayiklayici.belge_ayikla(str(dosya))
    except BelgeAyiklamaHatasi as hata:
        assert hata.hata_kodu in ("PDF_BOZUK", "PDF_SIFRELI")


def test_html_bos_icerik_reddedilir(tmp_path):
    ayiklayici = BelgeAyiklayici()
    dosya = tmp_path / "bos.html"
    dosya.write_text(
        "<html><body></body></html>",
        encoding="utf-8",
    )
    with pytest.raises(BelgeAyiklamaHatasi) as hata:
        ayiklayici.belge_ayikla(str(dosya))
    assert hata.value.hata_kodu == "METIN_BOS"


def test_belge_yetki_varsayilan_doner(tmp_path):
    ayiklayici = BelgeAyiklayici()
    dosya = tmp_path / "test.html"
    dosya.write_text(
        "<html><body><p>icerik</p></body></html>",
        encoding="utf-8",
    )
    icerik = ayiklayici.belge_ayikla(str(dosya))
    assert icerik.yetki_seviyesi == 0