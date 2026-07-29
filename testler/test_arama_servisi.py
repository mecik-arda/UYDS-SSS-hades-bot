import hashlib
import sqlite3
from dataclasses import replace

import numpy as np
import pytest

from uygulama.modeller.semalar import AramaSonucu
from uygulama.modeller.veritabani_modelleri import tablolari_olustur
from uygulama.servisler.arama_servisi import AramaServisi
from uygulama.servisler.terim_haritasi import TerimHaritasi
from uygulama.servisler.vektor_servisi import VektorServisi


class _SahteTerimHaritasi(TerimHaritasi):
    def __init__(self, harita=None):
        self._harita_dict = harita or {}
        self._ters_harita_dict = {}
        if harita:
            for ana_terim, es_anlamlilar in harita.items():
                for terim in (ana_terim,) + es_anlamlilar:
                    self._ters_harita_dict[terim] = ana_terim

    def yukle(self):
        self._harita = dict(self._harita_dict)
        self._ters_harita = dict(self._ters_harita_dict)
        return dict(self._harita)

    def es_anlamlilari_al(self, terim):
        return ()


class _SahteVektorServisi(VektorServisi):
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
def dolu_veritabani(gecici_veritabani):
    tablolari_olustur()
    baglanti = sqlite3.connect(str(gecici_veritabani))
    baglanti.execute("PRAGMA journal_mode=WAL")
    baglanti.execute("PRAGMA foreign_keys=ON")
    baglanti.executemany(
        "INSERT INTO sss_kayitlari (kategori, soru, cevap, kaynak_dokuman, kaynak_sayfa, kaynak_satir, durum, aktif_mi, arama_metni) "
        "VALUES (?, ?, ?, ?, ?, ?, 'aktif', 1, ?)",
        [
            ("muhasebe", "fatura nasil kesilir", "fatura kesim adimlari",
             "Muhasebe Kilavuzu", "Sayfa1", 5, "muhasebe fatura nasil kesilir fatura kesim adimlari"),
            ("izin", "yillik izin nasil alinir", "izin basvuru sureci",
             "IK Kilavuzu", "Sayfa2", 10, "izin yillik izin nasil alinir izin basvuru sureci"),
        ],
    )
    baglanti.executemany(
        "INSERT INTO sss_parcalari (sss_id, parca_metni, parca_sira_no) VALUES (?, ?, ?)",
        [
            (1, "fatura nasil kesilir", 1),
            (1, "fatura kesim adimlari", 2),
            (2, "yillik izin nasil alinir", 1),
        ],
    )
    vektor_servisi = _SahteVektorServisi()
    import hashlib
    for parca_id, metin in [(1, "fatura nasil kesilir"), (2, "fatura kesim adimlari"),
                              (3, "yillik izin nasil alinir")]:
        vektor = vektor_servisi.metni_vektore_donustur(metin)
        blob = np.ascontiguousarray(vektor.astype("<f4")).tobytes(order="C")
        metin_ozeti = hashlib.sha256(metin.encode("utf-8")).hexdigest()
        sss_id = 1 if parca_id <= 2 else 2
        baglanti.execute(
            "INSERT INTO sss_vektorleri (sss_id, parca_id, vektor_verisi, model_adi, vektor_boyutu, metin_ozeti) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sss_id, parca_id, blob, "test_model", 384, metin_ozeti),
        )
    baglanti.commit()
    baglanti.close()
    yield gecici_veritabani


@pytest.fixture
def harita():
    return _SahteTerimHaritasi({
        "harcama belgesi": ("fatura", "dekont"),
    })


@pytest.fixture
def arama_servisi(dolu_veritabani, harita):
    vektor_servisi = _SahteVektorServisi()
    return AramaServisi(vektor_servisi, harita)


class TestAramaServisi:
    def test_bos_veritabani_icin_bos_sonuc(self, gecici_veritabani, harita):
        tablolari_olustur()
        vektor_servisi = _SahteVektorServisi()
        servis = AramaServisi(vektor_servisi, harita)
        sonuc = servis.ara("fatura")
        assert isinstance(sonuc, AramaSonucu)
        assert len(sonuc.adaylar) == 0

    def test_arama_sonuc_dondurur(self, arama_servisi):
        sonuc = arama_servisi.ara("fatura")
        assert isinstance(sonuc, AramaSonucu)
        assert len(sonuc.adaylar) > 0
        assert sonuc.gecen_sure_ms > 0

    def test_aday_metni_her_zaman_dolu(self, arama_servisi):
        sonuc = arama_servisi.ara("fatura")
        for aday in sonuc.adaylar:
            assert aday.aday_metni
            assert len(aday.aday_metni) > 0

    def test_kaynak_bilgileri_tasinir(self, arama_servisi):
        sonuc = arama_servisi.ara("fatura")
        fatura_adayi = [a for a in sonuc.adaylar if a.sss_id == 1][0]
        assert fatura_adayi.kaynak_dokuman == "Muhasebe Kilavuzu"
        assert fatura_adayi.kaynak_sayfa == "Sayfa1"
        assert fatura_adayi.kaynak_satir == 5

    def test_yeniden_siralayici_none_ise_etkin_false(self, arama_servisi):
        sonuc = arama_servisi.ara("fatura")
        assert sonuc.yeniden_siralama_etkin is False

    def test_gecen_sure_ms_sonlu(self, arama_servisi):
        sonuc = arama_servisi.ara("fatura")
        assert sonuc.gecen_sure_ms > 0
        assert sonuc.gecen_sure_ms < 60000

    def test_adaylar_icerisinde_yeniden_siralama_skoru_none(self, arama_servisi):
        sonuc = arama_servisi.ara("fatura")
        for aday in sonuc.adaylar:
            assert aday.yeniden_siralama_skoru is None

    def test_vektor_benzerlik_skoru_adaya_tasinir(self, arama_servisi):
        sonuc = arama_servisi.ara("fatura")
        vektorlu_adaylar = [
            aday
            for aday in sonuc.adaylar
            if aday.vektor_benzerlik_skoru is not None
        ]

        assert vektorlu_adaylar
        assert all(
            -1.0 <= aday.vektor_benzerlik_skoru <= 1.0
            for aday in vektorlu_adaylar
        )

    def test_sorgu_genisletme_teshisleri_sonuca_tasinir(self, arama_servisi):
        sonuc = arama_servisi.ara("fatura")
        assert '"harcama belgesi"' in sonuc.genisletilmis_fts_sorgusu
        assert sonuc.genisletilen_terim_sayisi == 3
        assert sonuc.kullanilan_grup_sayisi == 1

    def test_yeniden_siralayici_etkin_dali_sonucu_gunceller(
        self,
        dolu_veritabani,
        harita,
    ):
        class _SahteYenidenSiralayici:
            def yeniden_sirala(self, soru, adaylar):
                siralanmis_adaylar = sorted(
                    adaylar,
                    key=lambda aday: aday.sss_id,
                    reverse=True,
                )
                return [
                    replace(aday, yeniden_siralama_skoru=0.75)
                    for aday in siralanmis_adaylar
                ]

        servis = AramaServisi(
            _SahteVektorServisi(),
            harita,
            _SahteYenidenSiralayici(),
        )
        sonuc = servis.ara("fatura")
        assert sonuc.yeniden_siralama_etkin is True
        assert all(
            aday.yeniden_siralama_skoru == 0.75
            for aday in sonuc.adaylar
        )
        assert [aday.sss_id for aday in sonuc.adaylar] == sorted(
            (aday.sss_id for aday in sonuc.adaylar),
            reverse=True,
        )
