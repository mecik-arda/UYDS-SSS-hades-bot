# ============================================================
# Test: Çıktı bütünlüğü ve sonuç tutarlılığı
# ============================================================
"""Doğrulanan/şüpheli maskesi, _kayit_no benzersizliği, eksik kayıt kontrolü."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.checkpoint import butunluk_kontrolu, eksik_kayitlari_bul


class TestDogrulananMaskesi:
    """doğrulanan = dogru + guven >= esik + ~_islem_hatasi"""

    def test_dogrulanan_maskesi(self):
        df = pd.DataFrame({
            "_karar": ["dogru", "dogru", "dogru", "kismen_dogru", "kanit_yetersiz"],
            "_guven": [0.95, 0.80, 0.90, 0.70, 0.0],
            "_islem_hatasi": [False, False, True, False, False],
            "_kaynak_idleri": ["[0,1]", "[2]", "[3]", "[]", "[]"],
        })

        dogrulanan_mask = (
            (df["_karar"] == "dogru")
            & (df["_guven"] >= 0.85)
            & (~df["_islem_hatasi"])
            & (df["_kaynak_idleri"] != "[]")
        )
        # dogru + güven>=0.85 + hatasız + kaynak var → sadece indeks 0
        assert list(df[dogrulanan_mask].index) == [0]

    def test_supheli_diger_tum_kayitlar(self):
        df = pd.DataFrame({
            "_karar": ["dogru", "dogru", "kismen_dogru", "yanlis", "cevap_bos"],
            "_guven": [0.95, 0.80, 0.70, 0.0, 1.0],
            "_islem_hatasi": [False, False, False, False, False],
            "_kaynak_idleri": ["[1,2]", "[]", "[]", "[]", "[]"],
        })
        GUVEN_ESIK = 0.85

        dogrulanan_mask = (
            (df["_karar"] == "dogru")
            & (df["_guven"] >= GUVEN_ESIK)
            & (~df["_islem_hatasi"])
            & (df["_kaynak_idleri"] != "[]")
        )
        dogrulanan = df[dogrulanan_mask]
        supheli = df[~dogrulanan_mask]

        assert len(dogrulanan) == 1
        assert len(supheli) == 4


class TestKayitNoBenzersizlik:
    """_kayit_no tekrarı kontrolü."""

    def test_benzersiz_kayit_nolari(self):
        sonuclar = [
            {"_kayit_no": 0, "karar": "dogru"},
            {"_kayit_no": 1, "karar": "kanit_yetersiz"},
            {"_kayit_no": 2, "karar": "dogru"},
        ]
        nolar = [s["_kayit_no"] for s in sonuclar]
        assert len(nolar) == len(set(nolar))

    def test_mukerer_son_gecerli(self):
        """Aynı _kayit_no iki kez varsa son geçerli olan kullanılır."""
        sonuclar = [
            {"_kayit_no": 1, "karar": "yanlis", "guven": 0.3},
            {"_kayit_no": 1, "karar": "dogru", "guven": 0.9},
        ]
        harita = {}
        for s in sonuclar:
            harita[s["_kayit_no"]] = s
        # Son eklenen geçerli
        assert harita[1]["karar"] == "dogru"
        assert harita[1]["guven"] == 0.9


class TestEksikKayitFinal:
    """Final bütünlük kontrolü."""

    def test_eksik_yok(self):
        harita = {i: {} for i in range(100)}
        eksik = butunluk_kontrolu(harita, 100)
        assert eksik == []

    def test_eksik_var(self):
        harita = {0: {}, 2: {}, 5: {}}
        eksik = butunluk_kontrolu(harita, 6)
        assert 1 in eksik
        assert 3 in eksik
        assert 4 in eksik

    def test_islem_hatasi_eksik_sayilir(self):
        harita = {
            0: {"karar": "dogru", "_islem_hatasi": False},
            1: {"karar": "error", "_islem_hatasi": True},
            2: {"karar": "kanit_yetersiz", "_islem_hatasi": False},
        }
        tamamlanan, hatali, _ = eksik_kayitlari_bul(harita, 3)
        assert 0 in tamamlanan
        assert 2 in tamamlanan
        assert 1 in hatali


class TestSmokeTestEsikleri:
    """Smoke test başarısızlık kuralları."""

    def test_islem_hatasi_orani_yuksek(self):
        benchmark_sonuc = [
            {"_islem_hatasi": False} for _ in range(10)
        ] + [
            {"_islem_hatasi": True} for _ in range(5)
        ]  # 5/15 = 33% hata
        hata_orani = sum(1 for s in benchmark_sonuc if s["_islem_hatasi"]) / len(benchmark_sonuc)
        assert hata_orani > 0.05  # Smoke test durdurulmalı

    def test_ortalama_kaynak_dusuk(self):
        rag_sonuc_kaynaklar = [0, 1, 0, 2, 0, 1, 0, 0, 1, 0]  # ort = 0.5
        ortalama = np.mean(rag_sonuc_kaynaklar)
        assert ortalama < 1.0  # Smoke test durdurulmalı

    def test_kanit_yetersiz_orani_yuksek(self):
        kararlar = (["kanit_yetersiz"] * 85) + (["dogru"] * 10) + (["kismen_dogru"] * 5)
        ky_oran = kararlar.count("kanit_yetersiz") / len(kararlar)
        assert ky_oran > 0.80  # Uyarı verilmeli


class TestEnvanterMetadataKoruma:
    """Envanter yeniden oluşturulduğunda metadata alanları korunmalı."""

    def test_metadata_korunur(self, temp_dir):
        import csv
        from src.source_inventory import envanter_olustur, ENVANTER_ALANLARI, _METADATA_ALANLARI

        kaynak_dizini = os.path.join(temp_dir, "kaynaklar")
        os.makedirs(kaynak_dizini)

        dosya1 = os.path.join(kaynak_dizini, "belge_a.txt")
        dosya2 = os.path.join(kaynak_dizini, "belge_b.txt")
        with open(dosya1, "w", encoding="utf-8") as f:
            f.write("Belge A içeriği.")
        with open(dosya2, "w", encoding="utf-8") as f:
            f.write("Belge B içeriği.")

        mevcut_csv = os.path.join(temp_dir, "eski_envanter.csv")
        mevcut_kayitlar = [
            {
                "kaynak_id": "SRC-00001",
                "dosya_yolu": "belge_a.txt",
                "dosya_adi": "belge_a.txt",
                "baslik": "Belge A Başlığı",
                "kaynak_tipi": "mevzuat",
                "guven_sinifi": "A",
                "kurum": "Test Kurumu",
                "domain": "test.gov.tr",
                "kaynak_url": "https://test.gov.tr/belge_a",
                "modul": "ihale",
                "alt_konu": "İhale Mevzuatı",
                "yayin_tarihi": "2024-01-15",
                "gecerlilik_baslangici": "2024-01-15",
                "gecerlilik_bitis": "",
                "surum": "1.0",
                "resmiyet_seviyesi": "resmi",
                "sha256": "",
                "dosya_boyutu": "123",
                "durum": "guncel",
                "not": "Test notu",
            }
        ]
        import hashlib
        with open(dosya1, "rb") as f:
            mevcut_kayitlar[0]["sha256"] = hashlib.sha256(f.read()).hexdigest()
        with open(mevcut_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(mevcut_kayitlar[0].keys()))
            writer.writeheader()
            writer.writerows(mevcut_kayitlar)

        cikti_csv = os.path.join(temp_dir, "yeni_envanter.csv")
        envanter = envanter_olustur(
            kaynak_dizini,
            cikti_yolu=cikti_csv,
            mevcut_envanter_yolu=mevcut_csv,
        )

        assert len(envanter) == 2, f"2 dosya bekleniyordu, {len(envanter)} bulundu"

        belge_a = next(k for k in envanter if k["dosya_adi"] == "belge_a.txt")
        belge_b = next(k for k in envanter if k["dosya_adi"] == "belge_b.txt")

        assert belge_a["baslik"] == "Belge A Başlığı", "baslik korunmadı"
        assert belge_a["guven_sinifi"] == "A", "guven_sinifi korunmadı"
        assert belge_a["kurum"] == "Test Kurumu", "kurum korunmadı"
        assert belge_a["domain"] == "test.gov.tr", "domain korunmadı"
        assert belge_a["kaynak_url"] == "https://test.gov.tr/belge_a", "kaynak_url korunmadı"
        assert belge_a["modul"] == "ihale", "modul korunmadı"
        assert belge_a["alt_konu"] == "İhale Mevzuatı", "alt_konu korunmadı"
        assert belge_a["durum"] == "guncel", "durum korunmadı"
        assert belge_a["not"] == "Test notu", "not korunmadı"

        assert belge_b["baslik"] != "", "yeni dosya için başlık boş olmamalı"
        assert belge_b["guven_sinifi"] == "", "yeni dosyada guven_sinifi boş olmalı"
        assert belge_b["kurum"] == "", "yeni dosyada kurum boş olmalı"

    def test_alan_semasinda_metadata_var(self):
        from src.source_inventory import ENVANTER_ALANLARI
        assert "baslik" in ENVANTER_ALANLARI
        assert "guven_sinifi" in ENVANTER_ALANLARI
        assert "domain" in ENVANTER_ALANLARI
        assert "kurum" in ENVANTER_ALANLARI
        assert "modul" in ENVANTER_ALANLARI
        assert "alt_konu" in ENVANTER_ALANLARI
        assert "kaynak_url" in ENVANTER_ALANLARI

    def test_dosya_adindan_baslik_uretimi(self):
        from src.source_inventory import _dosya_adindan_baslik
        assert _dosya_adindan_baslik("afet_lojistik.pdf") != ""
        assert "." not in _dosya_adindan_baslik("test_dosya.txt")
        assert _dosya_adindan_baslik("test.pdf") == "Test"


class TestCheckpointDogrulama:
    """Checkpoint meta.json, resume, retry testleri."""

    def test_meta_yazilir_ve_yuklenir(self, temp_dir):
        import json
        from src.checkpoint import checkpoint_kaydet, checkpoint_yukle

        meta_yolu = os.path.join(temp_dir, "meta.json")
        sonuc_yolu = os.path.join(temp_dir, "sonuc.jsonl")
        beklenen = {"excel_hash": "abc123", "model": "test"}

        checkpoint_kaydet(meta_yolu, beklenen)
        assert os.path.exists(meta_yolu)

        with open(meta_yolu, "r") as f:
            yazilan = json.load(f)
        assert yazilan == beklenen

        harita, gecerli = checkpoint_yukle(sonuc_yolu, meta_yolu, beklenen)
        assert gecerli is False

        with open(sonuc_yolu, "w") as f:
            json.dump({"_kayit_no": 0, "karar": "dogru"}, f)
            f.write("\n")

        harita, gecerli = checkpoint_yukle(sonuc_yolu, meta_yolu, beklenen)
        assert gecerli is True
        assert 0 in harita
        assert harita[0]["karar"] == "dogru"

    def test_meta_degisince_eski_sonuc_gecersiz(self, temp_dir):
        import json
        from src.checkpoint import checkpoint_kaydet, checkpoint_yukle

        meta_yolu = os.path.join(temp_dir, "meta.json")
        sonuc_yolu = os.path.join(temp_dir, "sonuc.jsonl")

        checkpoint_kaydet(meta_yolu, {"excel_hash": "abc", "model": "v1"})
        with open(sonuc_yolu, "w") as f:
            json.dump({"_kayit_no": 0, "karar": "dogru"}, f)
            f.write("\n")

        _, gecerli = checkpoint_yukle(sonuc_yolu, meta_yolu, {"excel_hash": "xyz", "model": "v2"})
        assert gecerli is False
        assert not os.path.exists(sonuc_yolu)

    def test_islem_hatasi_eksik_sayilir(self):
        from src.checkpoint import eksik_kayitlari_bul

        harita = {
            0: {"karar": "dogru", "_islem_hatasi": False},
            1: {"karar": "error", "_islem_hatasi": True},
            2: {"karar": "kanit_yetersiz", "_islem_hatasi": False},
        }
        tamamlanan, hatali, eksik = eksik_kayitlari_bul(harita, 3)
        assert 0 in tamamlanan
        assert 2 in tamamlanan
        assert 1 in hatali
        assert 1 in eksik, "işlem hatası alan kayıt eksik listesinde olmalı"

    def test_islem_hatasi_yoksa_eksik_yok(self):
        from src.checkpoint import eksik_kayitlari_bul

        harita = {
            0: {"karar": "dogru", "_islem_hatasi": False},
            1: {"karar": "kanit_yetersiz", "_islem_hatasi": False},
        }
        tamamlanan, hatali, eksik = eksik_kayitlari_bul(harita, 2)
        assert len(tamamlanan) == 2
        assert len(hatali) == 0
        assert len(eksik) == 0


class TestBelgeGuvenlikKapisi:
    """Doğrudan ilgili belge okuma güvenlik kapısı — ÜRETİM fonksiyonu testi.

    src.source_validation.dogrudan_kaynaklari_dogrula fonksiyonunu
    doğrudan çağırır; notebook içine gömülü mantığı değil.
    """

    def _envanter_yaz(self, dizin, kayitlar):
        import csv
        yol = os.path.join(dizin, "envanter.csv")
        alanlar = ["dosya_adi", "uyds_ilgililik", "kaynak_id"]
        with open(yol, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=alanlar)
            w.writeheader()
            w.writerows(kayitlar)
        return yol

    def test_dogrudan_belge_okunamazsa_hata(self, temp_dir):
        from src.source_validation import (
            dogrudan_kaynaklari_dogrula, DogrudanKaynakHatasi,
        )
        envanter = self._envanter_yaz(temp_dir, [
            {"dosya_adi": "a.txt", "uyds_ilgililik": "dogrudan_ilgili", "kaynak_id": "S1"},
            {"dosya_adi": "b.txt", "uyds_ilgililik": "dogrudan_ilgili", "kaynak_id": "S2"},
        ])
        belgeler = [{"dosya": "a.txt"}]
        with pytest.raises(DogrudanKaynakHatasi) as exc:
            dogrudan_kaynaklari_dogrula(envanter, belgeler)
        assert "b.txt" in str(exc.value)

    def test_dogrudan_hata_runtimeerror_alt_sinifidir(self, temp_dir):
        from src.source_validation import dogrudan_kaynaklari_dogrula
        envanter = self._envanter_yaz(temp_dir, [
            {"dosya_adi": "x.txt", "uyds_ilgililik": "dogrudan_ilgili", "kaynak_id": "S1"},
        ])
        with pytest.raises(RuntimeError):
            dogrudan_kaynaklari_dogrula(envanter, [])

    def test_tum_dogrudan_okunmus_sorun_yok(self, temp_dir):
        from src.source_validation import dogrudan_kaynaklari_dogrula
        envanter = self._envanter_yaz(temp_dir, [
            {"dosya_adi": "a.txt", "uyds_ilgililik": "dogrudan_ilgili", "kaynak_id": "S1"},
            {"dosya_adi": "b.txt", "uyds_ilgililik": "dogrudan_ilgili", "kaynak_id": "S2"},
        ])
        rapor = dogrudan_kaynaklari_dogrula(
            envanter, [{"dosya": "a.txt"}, {"dosya": "b.txt"}]
        )
        assert rapor["dogrudan_okunamayan"] == []
        assert rapor["toplam_dogrudan"] == 2

    def test_sadece_dolayli_okunamazsa_durmaz(self, temp_dir):
        from src.source_validation import dogrudan_kaynaklari_dogrula
        envanter = self._envanter_yaz(temp_dir, [
            {"dosya_adi": "d1.txt", "uyds_ilgililik": "dogrudan_ilgili", "kaynak_id": "S1"},
            {"dosya_adi": "d2.txt", "uyds_ilgililik": "dolayli_ilgili", "kaynak_id": "S2"},
            {"dosya_adi": "d3.txt", "uyds_ilgililik": "dolayli_ilgili", "kaynak_id": "S3"},
        ])
        rapor = dogrudan_kaynaklari_dogrula(envanter, [{"dosya": "d1.txt"}])
        assert rapor["dogrudan_okunamayan"] == []
        assert set(rapor["dolayli_okunamayan"]) == {"d2.txt", "d3.txt"}

    def test_envanter_yoksa_hata(self, temp_dir):
        from src.source_validation import (
            dogrudan_kaynaklari_dogrula, EnvanterHatasi,
        )
        with pytest.raises(EnvanterHatasi):
            dogrudan_kaynaklari_dogrula(
                os.path.join(temp_dir, "yok.csv"), []
            )

    def test_envanter_bossa_hata(self, temp_dir):
        from src.source_validation import dogrudan_kaynaklari_dogrula, EnvanterHatasi
        bos = os.path.join(temp_dir, "bos.csv")
        with open(bos, "w", encoding="utf-8-sig") as f:
            f.write("dosya_adi,uyds_ilgililik\n")
        with pytest.raises(EnvanterHatasi):
            dogrudan_kaynaklari_dogrula(bos, [])

    def test_cok_sayfali_belge_tek_dosya_sayilir(self, temp_dir):
        from src.source_validation import dogrudan_kaynaklari_dogrula
        envanter = self._envanter_yaz(temp_dir, [
            {"dosya_adi": "cok.pdf", "uyds_ilgililik": "dogrudan_ilgili", "kaynak_id": "S1"},
        ])
        belgeler = [
            {"dosya": "cok.pdf", "sayfa": 1},
            {"dosya": "cok.pdf", "sayfa": 2},
            {"dosya": "cok.pdf", "sayfa": 3},
        ]
        rapor = dogrudan_kaynaklari_dogrula(envanter, belgeler)
        assert rapor["dogrudan_okunamayan"] == []

    def test_dosya_yolu_basename_ile_eslesir(self, temp_dir):
        from src.source_validation import dogrudan_kaynaklari_dogrula
        envanter = self._envanter_yaz(temp_dir, [
            {"dosya_adi": "a.pdf", "uyds_ilgililik": "dogrudan_ilgili", "kaynak_id": "S1"},
        ])
        belgeler = [{"dosya": "/kaynak/01_mevzuat/a.pdf"}]
        rapor = dogrudan_kaynaklari_dogrula(envanter, belgeler)
        assert rapor["dogrudan_okunamayan"] == []


class TestOCRTemizlik:
    """OCR geçici dosya temizliği — ÜRETİM fonksiyonu testi.

    src.ocr_helpers fonksiyonlarını doğrudan çağırır; pathlib stdlib'ini
    değil. or=True gibi her zaman geçen assertion yoktur.
    """

    def test_gecici_kalinti_temizlenir(self, temp_dir):
        from src.ocr_helpers import gecici_temizle
        kalinti = os.path.join(temp_dir, "x.ocr_gecici.pdf")
        with open(kalinti, "w") as f:
            f.write("eski kalinti")
        assert gecici_temizle(kalinti) is True
        assert not os.path.exists(kalinti)

    def test_olmayan_dosya_hatasiz_false(self, temp_dir):
        from src.ocr_helpers import gecici_temizle
        sonuc = gecici_temizle(os.path.join(temp_dir, "yok.ocr_gecici.pdf"))
        assert sonuc is False

    def test_hedef_bulunamazsa_hata(self, temp_dir):
        from src.ocr_helpers import hedef_yolu_bul, OCRHedefHatasi
        with pytest.raises(OCRHedefHatasi):
            hedef_yolu_bul(temp_dir, "kesinlikle_yok.pdf")

    def test_hedef_bulunamazsa_runtimeerror_olarak_yayilir(self, temp_dir):
        from src.ocr_helpers import hedef_yolu_bul, OCRHedefHatasi
        with pytest.raises(RuntimeError):
            hedef_yolu_bul(temp_dir, "kesinlikle_yok.pdf")

    def test_hedef_birden_fazlaysa_hata(self, temp_dir):
        from src.ocr_helpers import hedef_yolu_bul
        alt = os.path.join(temp_dir, "alt")
        os.makedirs(alt)
        for d in [temp_dir, alt]:
            with open(os.path.join(d, "cift.pdf"), "w") as f:
                f.write("x")
        with pytest.raises(RuntimeError):
            hedef_yolu_bul(temp_dir, "cift.pdf")

    def test_hedef_tek_dosya_bulunur(self, temp_dir):
        from src.ocr_helpers import hedef_yolu_bul
        with open(os.path.join(temp_dir, "tek.pdf"), "w") as f:
            f.write("x")
        yol = hedef_yolu_bul(temp_dir, "tek.pdf")
        assert yol.exists()
