import hashlib
import sqlite3

import numpy as np
import pytest

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.modeller.veritabani_modelleri import tablolari_olustur
from uygulama.servisler.hibrit_arama import HibritArama, _FtsSonucu, _VektorSonucu


class _SahteVektorServisi:
    def __init__(self):
        self.model_adi = "test_model"
        self.vektor_boyutu = 384

    def metni_vektore_donustur(self, metin):
        metin_ozeti = hashlib.sha256(metin.encode("utf-8")).digest()
        tohum = int.from_bytes(metin_ozeti[:4], "little")
        rng = np.random.RandomState(tohum)
        vektor = rng.randn(self.vektor_boyutu).astype(np.float32)
        norm = np.linalg.norm(vektor)
        return (vektor / norm).astype(np.float32)

    def blobu_vektore_donustur(self, blob):
        if len(blob) != self.vektor_boyutu * 4:
            raise ValueError("Gecersiz BLOB boyutu")
        vektor = np.frombuffer(blob, dtype="<f4").astype(np.float32)
        if not np.isfinite(vektor).all():
            raise ValueError("Sonlu olmayan deger")
        return vektor


@pytest.fixture
def ornek_veritabani(gecici_veritabani):
    tablolari_olustur()
    baglanti = sqlite3.connect(str(gecici_veritabani))
    baglanti.execute("PRAGMA journal_mode=WAL")
    baglanti.execute("PRAGMA foreign_keys=ON")
    baglanti.executemany(
        "INSERT INTO sss_kayitlari (kategori, soru, cevap, kaynak_dokuman, durum, aktif_mi, arama_metni) VALUES (?, ?, ?, ?, 'aktif', 1, ?)",
        [
            ("muhasebe", "fatura nasil kesilir", "fatura kesim adimlari",
             "Muhasebe Kilavuzu", "muhasebe fatura nasil kesilir fatura kesim adimlari"),
            ("izin", "yillik izin nasil alinir", "izin basvuru sureci",
             "IK Kilavuzu", "izin yillik izin nasil alinir izin basvuru sureci"),
            ("rapor", "haftalik rapor nasil hazirlanir", "rapor sablonu kullanin",
             "Raporlama Kilavuzu", "rapor haftalik rapor nasil hazirlanir rapor sablonu kullanin"),
        ],
    )
    baglanti.executemany(
        "INSERT INTO sss_parcalari (sss_id, parca_metni, parca_sira_no) VALUES (?, ?, ?)",
        [
            (1, "fatura nasil kesilir", 1),
            (1, "fatura kesim adimlari", 2),
            (2, "yillik izin nasil alinir", 1),
            (3, "haftalik rapor nasil hazirlanir", 1),
        ],
    )
    baglanti.commit()
    baglanti.close()
    yield gecici_veritabani


@pytest.fixture
def vektorlu_veritabani(ornek_veritabani):
    servis = _SahteVektorServisi()
    baglanti = sqlite3.connect(str(ornek_veritabani))
    import hashlib
    for parca_id, metin in [(1, "fatura nasil kesilir"), (2, "fatura kesim adimlari"),
                              (3, "yillik izin nasil alinir"), (4, "haftalik rapor nasil hazirlanir")]:
        vektor = servis.metni_vektore_donustur(metin)
        blob = np.ascontiguousarray(vektor.astype("<f4")).tobytes(order="C")
        metin_ozeti = hashlib.sha256(metin.encode("utf-8")).hexdigest()
        baglanti.execute(
            "INSERT INTO sss_vektorleri (sss_id, parca_id, vektor_verisi, model_adi, vektor_boyutu, metin_ozeti) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (1 if parca_id <= 2 else parca_id - 1, parca_id, blob, "test_model", 384, metin_ozeti),
        )
    baglanti.commit()
    baglanti.close()
    yield ornek_veritabani


class TestFtsArama:
    def test_bos_fts_sorgusu_bos_doner(self, ornek_veritabani):
        hibrit = HibritArama(_SahteVektorServisi())
        sonuc = hibrit.fts_ile_ara("")
        assert sonuc == []

    def test_fts_eslesme_bulur(self, ornek_veritabani):
        hibrit = HibritArama(_SahteVektorServisi())
        sonuc = hibrit.fts_ile_ara('"fatura"')
        assert len(sonuc) > 0
        assert isinstance(sonuc[0], _FtsSonucu)
        assert sonuc[0].fts_sirasi == 1

    def test_bm25_kucuk_skor_daha_iyi(self, ornek_veritabani):
        hibrit = HibritArama(_SahteVektorServisi())
        sonuc = hibrit.fts_ile_ara('"fatura" OR "izin"')
        assert len(sonuc) >= 2
        assert sonuc[0].bm25_skoru <= sonuc[-1].bm25_skoru

    def test_eslesme_yoksa_bos_doner(self, ornek_veritabani):
        hibrit = HibritArama(_SahteVektorServisi())
        sonuc = hibrit.fts_ile_ara('"xyzbulunmayankelime"')
        assert sonuc == []

    def test_bm25_alan_agirliklari_siralamayi_degistirir(
        self,
        ornek_veritabani,
        monkeypatch,
    ):
        baglanti = sqlite3.connect(str(ornek_veritabani))
        soru_kaydi = baglanti.execute(
            """
            INSERT INTO sss_kayitlari (
                kategori,
                soru,
                cevap,
                kaynak_dokuman,
                durum,
                aktif_mi,
                arama_metni
            )
            VALUES ('test', 'hedef', 'diger', 'test', 'aktif', 1, '')
            """
        ).lastrowid
        cevap_kaydi = baglanti.execute(
            """
            INSERT INTO sss_kayitlari (
                kategori,
                soru,
                cevap,
                kaynak_dokuman,
                durum,
                aktif_mi,
                arama_metni
            )
            VALUES ('test', 'diger', 'hedef', 'test', 'aktif', 1, '')
            """
        ).lastrowid
        baglanti.commit()
        baglanti.close()
        monkeypatch.setattr(konfigurasyon, "FTS_SORU_AGIRLIGI", 10.0)
        monkeypatch.setattr(konfigurasyon, "FTS_CEVAP_AGIRLIGI", 0.1)
        monkeypatch.setattr(konfigurasyon, "FTS_KATEGORI_AGIRLIGI", 0.0)
        monkeypatch.setattr(konfigurasyon, "FTS_HARICI_KOD_AGIRLIGI", 0.0)
        monkeypatch.setattr(konfigurasyon, "FTS_MODUL_AGIRLIGI", 0.0)
        monkeypatch.setattr(
            konfigurasyon,
            "FTS_ARAMA_METNI_AGIRLIGI",
            0.0,
        )
        hibrit = HibritArama(_SahteVektorServisi())
        soru_oncelikli = hibrit.fts_ile_ara('"hedef"')
        assert soru_oncelikli[0].sss_id == soru_kaydi
        monkeypatch.setattr(konfigurasyon, "FTS_SORU_AGIRLIGI", 0.1)
        monkeypatch.setattr(konfigurasyon, "FTS_CEVAP_AGIRLIGI", 10.0)
        cevap_oncelikli = hibrit.fts_ile_ara('"hedef"')
        assert cevap_oncelikli[0].sss_id == cevap_kaydi


class TestVektorArama:
    def test_vektor_arama_sonuc_dondurur(self, vektorlu_veritabani):
        hibrit = HibritArama(_SahteVektorServisi())
        sonuc, gecersiz = hibrit.vektor_ile_ara("fatura")
        assert len(sonuc) > 0
        assert isinstance(sonuc[0], _VektorSonucu)
        assert gecersiz == 0

    def test_ayni_sss_parcalari_gruplanir(self, vektorlu_veritabani):
        hibrit = HibritArama(_SahteVektorServisi())
        sonuc, _ = hibrit.vektor_ile_ara("fatura")
        sss_kimlikleri = [s.sss_id for s in sonuc]
        assert len(sss_kimlikleri) == len(set(sss_kimlikleri))

    def test_bozuk_blob_atlanir(self, vektorlu_veritabani):
        baglanti = sqlite3.connect(str(vektorlu_veritabani))
        baglanti.execute("DROP TRIGGER IF EXISTS sss_vektorleri_dogrula_guncelle")
        baglanti.execute(
            "UPDATE sss_vektorleri SET vektor_verisi = ?, vektor_boyutu = 999 WHERE parca_id = 3 AND model_adi = 'test_model'",
            (b"kisa_blob",),
        )
        baglanti.commit()
        baglanti.close()
        hibrit = HibritArama(_SahteVektorServisi())
        sonuc, gecersiz = hibrit.vektor_ile_ara("fatura")
        assert gecersiz > 0

    def test_bos_vektor_tablosu_bos_doner(self, ornek_veritabani):
        class _CagrilamazVektorServisi(_SahteVektorServisi):
            def metni_vektore_donustur(self, metin):
                raise AssertionError("Bos tabloda sorgu vektoru uretilmemeli")

        hibrit = HibritArama(_CagrilamazVektorServisi())
        sonuc, gecersiz = hibrit.vektor_ile_ara("fatura")
        assert sonuc == []
        assert gecersiz == 0

    def test_guncelligini_yitirmis_metin_ozeti_atlanir(
        self,
        vektorlu_veritabani,
    ):
        baglanti = sqlite3.connect(str(vektorlu_veritabani))
        baglanti.execute(
            "UPDATE sss_vektorleri SET metin_ozeti = ? WHERE parca_id = ?",
            ("gecersiz_ozet", 3),
        )
        baglanti.commit()
        baglanti.close()
        hibrit = HibritArama(_SahteVektorServisi())
        sonuc, gecersiz = hibrit.vektor_ile_ara("fatura")
        assert gecersiz == 1
        assert all(kayit.parca_id != 3 for kayit in sonuc)

    def test_birim_normdan_uzak_vektor_atlanir(self, vektorlu_veritabani):
        sifir_vektor = np.zeros(384, dtype="<f4").tobytes(order="C")
        baglanti = sqlite3.connect(str(vektorlu_veritabani))
        baglanti.execute(
            "UPDATE sss_vektorleri SET vektor_verisi = ? WHERE parca_id = ?",
            (sifir_vektor, 3),
        )
        baglanti.commit()
        baglanti.close()
        hibrit = HibritArama(_SahteVektorServisi())
        sonuc, gecersiz = hibrit.vektor_ile_ara("fatura")
        assert gecersiz == 1
        assert all(kayit.parca_id != 3 for kayit in sonuc)


class TestRrfHarmanlama:
    def test_her_iki_liste_birlesir(self):
        hibrit = HibritArama(_SahteVektorServisi())
        fts = [_FtsSonucu(sss_id=1, fts_sirasi=1, bm25_skoru=1.0)]
        vektor = [_VektorSonucu(sss_id=2, parca_id=3, parca_metni="metin", vektor_sirasi=1, benzerlik_skoru=0.9)]
        sonuc = hibrit.rrf_harmanla(fts, vektor)
        assert len(sonuc) == 2

    def test_sadece_fts_sonucu_icin_vektor_sirasi_none(self):
        hibrit = HibritArama(_SahteVektorServisi())
        fts = [_FtsSonucu(sss_id=1, fts_sirasi=1, bm25_skoru=1.0)]
        sonuc = hibrit.rrf_harmanla(fts, [])
        assert len(sonuc) == 1
        assert sonuc[0].vektor_sirasi is None
        assert sonuc[0].parca_metni is None

    def test_sadece_vektor_sonucu_icin_fts_sirasi_none(self):
        hibrit = HibritArama(_SahteVektorServisi())
        vektor = [_VektorSonucu(sss_id=2, parca_id=3, parca_metni="metin", vektor_sirasi=1, benzerlik_skoru=0.9)]
        sonuc = hibrit.rrf_harmanla([], vektor)
        assert len(sonuc) == 1
        assert sonuc[0].fts_sirasi is None

    def test_esit_rrf_skorunda_fts_sirasi_oncelikli(self):
        hibrit = HibritArama(_SahteVektorServisi())
        fts = [
            _FtsSonucu(sss_id=1, fts_sirasi=1, bm25_skoru=1.0),
            _FtsSonucu(sss_id=2, fts_sirasi=2, bm25_skoru=2.0),
        ]
        vektor = [
            _VektorSonucu(sss_id=2, parca_id=3, parca_metni="metin", vektor_sirasi=1, benzerlik_skoru=0.9),
            _VektorSonucu(sss_id=1, parca_id=1, parca_metni="metin", vektor_sirasi=2, benzerlik_skoru=0.8),
        ]
        sonuc = hibrit.rrf_harmanla(fts, vektor)
        assert sonuc[0].sss_id == 1
