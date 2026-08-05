# ============================================================
# Test: Excel format okuma — başlık algılama, UYDS formatı
# ============================================================
"""Excel başlık satırı algılama ve UYDS soru/cevap alan eşleme testleri."""

import os
import sys
import tempfile
import unicodedata

import pytest

# src modülünü path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import adi_normalize_et


class TestBaslikNormallestirme:
    """Başlık normalleştirme fonksiyonunun testleri."""

    def test_turkce_buyuk_kucuk(self):
        """Türkçe karakterler doğru normalize edilmeli."""
        assert adi_normalize_et("Modül") == adi_normalize_et("modul")
        assert adi_normalize_et("MODÜL") == adi_normalize_et("modul")

    def test_bosluk_farki(self):
        """Başındaki/sonundaki boşluklar göz ardı edilmeli."""
        assert adi_normalize_et("  Konu  ") == adi_normalize_et("konu")

    def test_bilinen_basliklar(self):
        """Bilinen UYDS başlıkları tanınmalı."""
        bilinen = {"modul", "konu", "aciklama", "yapilacak", "yapilan islem"}
        for baslik in bilinen:
            norm = adi_normalize_et(baslik)
            assert norm in {
                adi_normalize_et(b)
                for b in [
                    "Modül", "Konu", "Açıklama", "Yapılacak", "Yapılan İşlem",
                    "modul", "konu", "aciklama", "yapilacak", "yapilan islem",
                ]
            }


class TestUYDSFormatEsleme:
    """UYDS formatında soru/cevap alan eşleme testleri."""

    def _ad_esle(self, sutun_adlari, hedef_adlar):
        """Sütun adlarını normalize edip eşleştirir."""
        mk = {adi_normalize_et(k): k for k in sutun_adlari}
        eslesme = {}
        for anahtar, adaylar in hedef_adlar.items():
            for aday in adaylar:
                if adi_normalize_et(aday) in mk:
                    eslesme[anahtar] = mk[adi_normalize_et(aday)]
                    break
        return eslesme

    def test_uyds_format_tespiti(self):
        """5 alanın en az 4'ü bulunursa UYDS formatı."""
        sutunlar = ["Modül", "Konu", "Açıklama", "Yapılacak", "Yapılan İşlem", "Müşteri"]
        hedef = {
            "modul": ["modul"], "konu": ["konu"], "aciklama": ["aciklama"],
            "yapilacak": ["yapilacak"], "yapilan_islem": ["yapilan islem", "yapilan_islem"],
        }
        eslesme = self._ad_esle(sutunlar, hedef)
        assert len(eslesme) >= 4
        assert "modul" in eslesme
        assert "konu" in eslesme

    def test_soru_olusturma(self):
        """soru = Modül + Konu + Açıklama + Yapılacak"""
        modul = "Hakediş"
        konu = "Hakediş onay problemi"
        aciklama = "Hakediş onaylanamıyor"
        yapilacak = "Hakediş durumunu kontrol et"

        soru = f"{modul}\n{konu}\n{aciklama}\n{yapilacak}"
        assert "Hakediş" in soru
        assert "onay problemi" in soru
        assert len(soru) > 0

    def test_bos_cevap_tespiti(self):
        """Boş cevap doğru tespit edilmeli."""
        bos_cevap = "   "
        assert bos_cevap.strip() == ""


class TestExcelBaslikSatiri:
    """Excel başlık satırı otomatik tespit testleri."""

    @pytest.fixture
    def temp_excel(self):
        """Test için geçici Excel dosyası oluşturur."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas kurulu değil")

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            # 4. satırda başlık olan bir UYDS Excel'i simüle et
            df = pd.DataFrame({
                "Unnamed: 0": ["Başlık", "", "", "Modül", "Hakediş", "İhale"],
                "Unnamed: 1": ["", "", "", "Konu", "Onay", "Teklif"],
                "Unnamed: 2": ["", "", "", "Açıklama", "Sorun", "Hata"],
                "Unnamed: 3": ["", "", "", "Yapılacak", "Kontrol", "İncele"],
                "Unnamed: 4": ["", "", "", "Yapılan İşlem", "Yapıldı", ""],
            })
            df.to_excel(f.name, index=False, header=False)
            yield f.name
        os.unlink(f.name)

    def test_baslik_4_satirda(self, temp_excel):
        """Başlık 4. satırda (index 3) algılanmalı."""
        import pandas as pd

        ham = pd.read_excel(temp_excel, sheet_name=0, header=None, dtype=object,
                            engine="openpyxl", nrows=10)
        bilinen = {"modul", "konu", "aciklama", "yapilacak", "yapilan islem"}

        baslik_satiri = None
        for i, satir in ham.iterrows():
            norm_set = {adi_normalize_et(str(v)) for v in satir.tolist()}
            if len(norm_set & bilinen) >= 3:
                baslik_satiri = i
                break

        assert baslik_satiri is not None, "Başlık satırı bulunamadı"
        assert baslik_satiri == 3, f"Başlık 4. satırda (index 3) olmalı, bulunan: {baslik_satiri}"


class TestXlsxKaynakOkuma:
    """document_loader.py XLSX okuma testi."""

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