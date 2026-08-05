# ============================================================
# Test: Excel format okuma — ÜRETİM modülü testi
# ============================================================
"""
src.excel_format modülü: başlık algılama, alan eşleştirme,
UYDS/standart format tespiti. Notebook ile aynı modülü test eder;
test içine gömülü eşleştirme mantığı yoktur.
"""

import os
import sys
import tempfile

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import adi_normalize_et
from src.excel_format import (
    alan_eslestir,
    baslik_satiri_bul,
    excel_formatini_tespit_et,
    UYDS_HEDEF,
    STANDART_HEDEF,
    GEREKLI_UYDS,
    BILINEN_BASLIKLAR,
)


class TestBaslikNormallestirme:
    """adi_normalize_et yardımcı fonksiyonu testleri."""

    def test_turkce_buyuk_kucuk(self):
        assert adi_normalize_et("Modül") == adi_normalize_et("modul")
        assert adi_normalize_et("MODÜL") == adi_normalize_et("modul")

    def test_bosluk_farki(self):
        assert adi_normalize_et("  Konu  ") == adi_normalize_et("konu")


class TestAlanEslestir:
    """alan_eslestir — normalize tabanlı sütun eşleştirme (ÜRETİM)."""

    def test_uyds_bilinen_basliklar_eslesir(self):
        sutunlar = ["Modül", "Konu", "Açıklama", "Yapılacak", "Yapılan İşlem"]
        eslesme = alan_eslestir(sutunlar, UYDS_HEDEF)
        assert GEREKLI_UYDS.issubset(eslesme)
        assert eslesme["modul"] == "Modül"
        assert eslesme["yapilan_islem"] == "Yapılan İşlem"

    def test_yapilan_islem_alt_cizgi_kabul(self):
        sutunlar = ["Modül", "Konu", "Açıklama", "Yapılacak", "yapilan_islem"]
        eslesme = alan_eslestir(sutunlar, UYDS_HEDEF)
        assert eslesme["yapilan_islem"] == "yapilan_islem"

    def test_baslik_kismi_eslesme(self):
        eslesme = alan_eslestir(["Modül", "Konu"], UYDS_HEDEF)
        assert set(eslesme) == {"modul", "konu"}

    def test_bos_sutunlar(self):
        assert alan_eslestir([], UYDS_HEDEF) == {}


class TestExcelFormatTespiti:
    """excel_formatini_tespit_et — format kararı (ÜRETİM)."""

    def test_uyds_tam_5_alan(self):
        sutunlar = ["Modül", "Konu", "Açıklama", "Yapılacak", "Yapılan İşlem"]
        ft, eslesme = excel_formatini_tespit_et(sutunlar)
        assert ft == "uyds"
        assert GEREKLI_UYDS.issubset(eslesme)

    def test_standart_soru_cevap_kategori_yok(self):
        ft, eslesme = excel_formatini_tespit_et(["Soru", "Cevap"])
        assert ft == "standart"
        assert "soru" in eslesme
        assert "cevap" in eslesme
        assert "kategori" not in eslesme

    def test_standart_soru_cevap_kategori_var(self):
        ft, eslesme = excel_formatini_tespit_et(["Soru", "Cevap", "Kategori"])
        assert ft == "standart"
        assert eslesme["kategori"] == "Kategori"

    def test_sadece_soru_desteklenmez(self):
        with pytest.raises(ValueError):
            excel_formatini_tespit_et(["Soru"])

    def test_soru_var_cevap_yok_desteklenmez(self):
        with pytest.raises(ValueError):
            excel_formatini_tespit_et(["Soru", "Açıklama"])

    def test_bos_sutun_desteklenmez(self):
        with pytest.raises(ValueError):
            excel_formatini_tespit_et([])

    def test_uyds_yapilan_islem_yoksa_uyds_degil(self):
        sutunlar = ["Modül", "Konu", "Açıklama", "Yapılacak"]
        with pytest.raises(ValueError):
            excel_formatini_tespit_et(sutunlar)

    def test_uyds_ekstra_sutunlar_sorun_degil(self):
        sutunlar = ["Modül", "Konu", "Açıklama", "Yapılacak",
                    "Yapılan İşlem", "Müşteri", "Tarih"]
        ft, eslesme = excel_formatini_tespit_et(sutunlar)
        assert ft == "uyds"

    def test_kategori_isim_farklari_eslesir(self):
        for ad in ["Kategori", "kategori", "KATEGORİ"]:
            ft, eslesme = excel_formatini_tespit_et(["Soru", "Cevap", ad])
            assert ft == "standart"
            assert eslesme["kategori"] == ad


class TestBaslikSatiriBul:
    """baslik_satiri_bul — başlık satırı otomatik tespiti (ÜRETİM)."""

    def test_baslik_4_satirda(self):
        df = pd.DataFrame([
            ["Başlık", "", "", ""],
            ["", "", "", ""],
            ["", "", "", ""],
            ["Modül", "Konu", "Açıklama", "Yapılacak"],
            ["Hakediş", "Onay", "Sorun", "Kontrol"],
        ])
        assert baslik_satiri_bul(df) == 3

    def test_baslik_yoksa_none(self):
        df = pd.DataFrame([
            ["rastgele", "veri", "satiri"],
            ["baska", "veri", "satiri"],
        ])
        assert baslik_satiri_bul(df) is None

    def test_baslik_ilk_satirda(self):
        df = pd.DataFrame([
            ["Modül", "Konu", "Açıklama", "Yapılacak", "Yapılan İşlem"],
            ["Hakediş", "Onay", "Sorun", "Kontrol", "Yapıldı"],
        ])
        assert baslik_satiri_bul(df) == 0

    def test_baslik_pencere_disinda_bulunmaz(self):
        satirlar = [["x", "y", "z"]] * 25
        satirlar.append(["Modül", "Konu", "Açıklama", "Yapılacak"])
        df = pd.DataFrame(satirlar)
        assert baslik_satiri_bul(df, pencere=20) is None


class TestXlsxKaynakOkuma:
    """document_loader._xlsx_oku — çok sayfalı XLSX okuma (ÜRETİM)."""

    @pytest.fixture
    def temp_xlsx(self):
        try:
            import openpyxl
        except ImportError:
            pytest.skip("openpyxl kurulu degil")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sayfa1"
        ws.append(["Baslik", "Deger"])
        ws.append(["Madde 1", "Aciklama 1"])
        ws.append(["Madde 2", "Aciklama 2"])

        ws2 = wb.create_sheet("Sayfa2")
        ws2.append(["Kolon A", "Kolon B"])
        ws2.append(["Veri 1", "Veri 2"])

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            wb.save(f.name)
            yield f.name
        os.unlink(f.name)

    def test_xlsx_cok_sayfali_okunur(self, temp_xlsx):
        from src.document_loader import _xlsx_oku

        sayfalar = _xlsx_oku(temp_xlsx)
        assert len(sayfalar) == 1
        metin = sayfalar[0][1]
        assert "Sayfa1" in metin
        assert "Sayfa2" in metin
        assert "Madde 1" in metin
        assert "Veri 1" in metin


class TestNotebookExcelDavranisi:
    """
    Notebook CELL 10 ile birebir aynı üretim fonksiyonlarını kullanarak
    standart Excel'in _modul davranışını doğrular (kategori yoksa boş).
    """

    def _mtd(self, d):
        if d is None or (isinstance(d, float) and pd.isna(d)):
            return ""
        return str(int(d)) if isinstance(d, float) and d == int(d) else str(d).strip()

    def test_standart_kategori_yok_modul_bos(self):
        ft, eslesme = excel_formatini_tespit_et(["Soru", "Cevap"])
        modul = eslesme["kategori"] if "kategori" in eslesme else ""
        assert ft == "standart"
        assert modul == ""

    def test_standart_kategori_var_modul_dolu(self):
        ft, eslesme = excel_formatini_tespit_et(["Soru", "Cevap", "Kategori"])
        modul = eslesme["kategori"] if "kategori" in eslesme else ""
        assert ft == "standart"
        assert modul == "Kategori"
