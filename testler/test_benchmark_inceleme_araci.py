import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

SYS_PATH = str(Path(__file__).resolve().parent.parent)
import sys
sys.path.insert(0, SYS_PATH)

from scripts.benchmark_inceleme_araci import _karar_dogrula, _validate, _export, _sonuclari_yukle, _sonuclari_kaydet, BENCHMARK_YOLU, SONUC_YOLU, GOLD_YOLU


GERCEK_SONUC_VAR = SONUC_YOLU.is_file()
GERCEK_BENCHMARK_VAR = BENCHMARK_YOLU.is_file()


class TestKararDogrulama:
    def test_tek_dogru_1_id_gecerli(self):
        gecerli, _ = _karar_dogrula("tek_dogru", [184])
        assert gecerli

    def test_tek_dogru_0_id_gecersiz(self):
        gecerli, mesaj = _karar_dogrula("tek_dogru", [])
        assert not gecerli
        assert "tam 1" in mesaj

    def test_tek_dogru_2_id_gecersiz(self):
        gecerli, _ = _karar_dogrula("tek_dogru", [1, 2])
        assert not gecerli

    def test_birden_fazla_dogru_2_id_gecerli(self):
        gecerli, _ = _karar_dogrula("birden_fazla_dogru", [10, 20])
        assert gecerli

    def test_birden_fazla_dogru_1_id_gecersiz(self):
        gecerli, _ = _karar_dogrula("birden_fazla_dogru", [10])
        assert not gecerli

    def test_kismen_dogru_1_id_gecerli(self):
        gecerli, _ = _karar_dogrula("kismen_dogru", [5])
        assert gecerli

    def test_kismen_dogru_0_id_gecersiz(self):
        gecerli, _ = _karar_dogrula("kismen_dogru", [])
        assert not gecerli

    def test_eslesme_yok_bos_id_gecerli(self):
        gecerli, _ = _karar_dogrula("eslesme_yok", [])
        assert gecerli

    def test_eslesme_yok_dolu_id_gecersiz(self):
        gecerli, _ = _karar_dogrula("eslesme_yok", [1])
        assert not gecerli

    def test_belirsiz_bos_id_gecerli(self):
        gecerli, _ = _karar_dogrula("belirsiz", [])
        assert gecerli

    def test_incelemeyi_atla_bos_id_gecerli(self):
        gecerli, _ = _karar_dogrula("incelemeyi_atla", [])
        assert gecerli

    def test_gecersiz_karar(self):
        gecerli, _ = _karar_dogrula("hayali_karar", [])
        assert not gecerli


class TestSentetikKayit:
    def test_kaydet_ve_geri_oku(self, tmp_path, monkeypatch):
        sentetik_yol = tmp_path / "test_sonuc.json"
        monkeypatch.setattr("scripts.benchmark_inceleme_araci.SONUC_YOLU", sentetik_yol)

        veri = {
            "BNC-0001": {
                "benchmark_id": "BNC-0001",
                "karar": "tek_dogru",
                "insan_onayli_sss_idler": [100],
                "inceleme_notu": "Test notu",
                "inceleme_tarihi": datetime.now(timezone.utc).isoformat(),
                "inceleyen": "manuel",
                "aday_sss_idler": [100, 200, 300],
            },
            "BNC-0002": {
                "benchmark_id": "BNC-0002",
                "karar": "belirsiz",
                "insan_onayli_sss_idler": [],
                "inceleme_notu": "",
                "inceleme_tarihi": datetime.now(timezone.utc).isoformat(),
                "inceleyen": "manuel",
                "aday_sss_idler": [],
            },
        }
        _sonuclari_kaydet(veri)
        assert sentetik_yol.is_file()
        okunan = _sonuclari_yukle()
        assert len(okunan) == 2
        assert okunan["BNC-0001"]["karar"] == "tek_dogru"
        assert okunan["BNC-0001"]["insan_onayli_sss_idler"] == [100]
        assert okunan["BNC-0002"]["karar"] == "belirsiz"
        assert okunan["BNC-0002"]["insan_onayli_sss_idler"] == []

    def test_coklu_secim_kaydi(self, tmp_path, monkeypatch):
        sentetik_yol = tmp_path / "test_coklu.json"
        monkeypatch.setattr("scripts.benchmark_inceleme_araci.SONUC_YOLU", sentetik_yol)

        veri = {
            "BNC-0010": {
                "benchmark_id": "BNC-0010",
                "karar": "birden_fazla_dogru",
                "insan_onayli_sss_idler": [100, 200, 300],
                "inceleme_notu": "",
                "inceleme_tarihi": datetime.now(timezone.utc).isoformat(),
                "inceleyen": "manuel",
                "aday_sss_idler": [100, 200],
            },
        }
        _sonuclari_kaydet(veri)
        okunan = _sonuclari_yukle()
        assert okunan["BNC-0010"]["karar"] == "birden_fazla_dogru"
        assert len(okunan["BNC-0010"]["insan_onayli_sss_idler"]) == 3

    def test_manuel_id_aday_disinda_ekleme(self, tmp_path, monkeypatch):
        sentetik_yol = tmp_path / "test_manuel.json"
        monkeypatch.setattr("scripts.benchmark_inceleme_araci.SONUC_YOLU", sentetik_yol)

        veri = {
            "BNC-0099": {
                "benchmark_id": "BNC-0099",
                "karar": "tek_dogru",
                "insan_onayli_sss_idler": [9999],
                "inceleme_notu": "Adaylarda yoktu, manuel eklendi",
                "inceleme_tarihi": datetime.now(timezone.utc).isoformat(),
                "inceleyen": "manuel",
                "aday_sss_idler": [100, 200],
            },
        }
        _sonuclari_kaydet(veri)
        okunan = _sonuclari_yukle()
        assert okunan["BNC-0099"]["insan_onayli_sss_idler"] == [9999]
        assert okunan["BNC-0099"]["aday_sss_idler"] == [100, 200]


class TestValidateSentetik:
    def test_bos_sonuc_dosyasi_validate(self, tmp_path, monkeypatch):
        yok_yol = tmp_path / "yok.json"
        monkeypatch.setattr("scripts.benchmark_inceleme_araci.SONUC_YOLU", yok_yol)
        sonuc = _validate()
        assert not sonuc["gecerli"]
        assert "bulunamadi" in str(sonuc.get("hata", ""))

    @pytest.mark.skipif(not GERCEK_SONUC_VAR, reason="Gercek sonuc dosyasi yok")
    def test_validate_gercek_dosya(self):
        sonuc = _validate()
        assert isinstance(sonuc, dict)


class TestExportSentetik:
    def test_export_yok_dosya(self, tmp_path, monkeypatch):
        yok_yol = tmp_path / "yok.json"
        altin_yol = tmp_path / "gold_test.json"
        monkeypatch.setattr("scripts.benchmark_inceleme_araci.SONUC_YOLU", yok_yol)
        monkeypatch.setattr("scripts.benchmark_inceleme_araci.GOLD_YOLU", altin_yol)
        sonuc = _export()
        assert "bulunamadi" in str(sonuc.get("hata", ""))

    def test_export_gecersiz_karar_atlanir(self, tmp_path, monkeypatch):
        sentetik_bench = tmp_path / "bench_test.json"
        sentetik_bench.write_text(json.dumps({
            "sorgular": [
                {"id": "A1", "soru": "S1", "aday_sss_idler": [1, 2]},
                {"id": "A2", "soru": "S2", "aday_sss_idler": [3, 4]},
            ]
        }), encoding="utf-8")

        sentetik_sonuc = tmp_path / "sonuc_test.json"
        sentetik_sonuc.write_text(json.dumps({
            "A1": {
                "benchmark_id": "A1", "karar": "tek_dogru",
                "insan_onayli_sss_idler": [1], "inceleme_notu": "ok",
                "inceleme_tarihi": "2026-01-01T00:00:00", "inceleyen": "test", "aday_sss_idler": [1]
            },
            "A2": {
                "benchmark_id": "A2", "karar": "eslesme_yok",
                "insan_onayli_sss_idler": [], "inceleme_notu": "",
                "inceleme_tarihi": "2026-01-01T00:00:00", "inceleyen": "test", "aday_sss_idler": []
            },
        }), encoding="utf-8")

        altin_yol = tmp_path / "gold_test.json"
        monkeypatch.setattr("scripts.benchmark_inceleme_araci.BENCHMARK_YOLU", sentetik_bench)
        monkeypatch.setattr("scripts.benchmark_inceleme_araci.SONUC_YOLU", sentetik_sonuc)
        monkeypatch.setattr("scripts.benchmark_inceleme_araci.GOLD_YOLU", altin_yol)

        sonuc = _export()
        assert sonuc["altin_kayit"] == 1
        assert sonuc["bilinmeyen"] == 1

        assert altin_yol.is_file()
        gold = json.loads(altin_yol.read_text(encoding="utf-8"))
        assert len(gold["sorgular"]) == 1
        assert len(gold["bilinmeyen_sorgulari"]) == 1
