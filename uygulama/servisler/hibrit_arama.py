import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.servisler.vektor_servisi import VektorServisi

_NORM_TOLERANSI = 0.01


@dataclass(frozen=True)
class _FtsSonucu:
    sss_id: int
    fts_sirasi: int
    bm25_skoru: float


@dataclass(frozen=True)
class _VektorSonucu:
    sss_id: int
    parca_id: int
    parca_metni: str
    vektor_sirasi: int
    benzerlik_skoru: float


@dataclass(frozen=True)
class _RrfSonucu:
    sss_id: int
    parca_id: int | None
    parca_metni: str | None
    fts_sirasi: int | None
    vektor_sirasi: int | None
    rrf_skoru: float
    vektor_benzerlik_skoru: float | None


class HibritAramaHatasi(RuntimeError):
    def __init__(self, mesaj: str) -> None:
        super().__init__(mesaj)


class HibritArama:
    def __init__(self, vektor_servisi: VektorServisi) -> None:
        self._vektor_servisi = vektor_servisi

    def fts_ile_ara(
        self,
        fts_sorgusu: str,
        kullanici_rolu: str | None = None,
    ) -> list[_FtsSonucu]:
        if not fts_sorgusu.strip():
            return []
        rol_kosulu = ""
        rol_parametreleri: list[Any] = []
        if kullanici_rolu and kullanici_rolu != "YONETICI":
            rol_kosulu = (
                "AND (k.kullanici_rolu IS NULL "
                "OR k.kullanici_rolu = '' "
                "OR k.kullanici_rolu = ?)"
            )
            rol_parametreleri.append(kullanici_rolu)
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                f"""
                SELECT
                    fts.rowid AS sss_id,
                    bm25(sss_fts, ?, ?, ?, ?, ?, ?) AS bm25_skoru
                FROM sss_fts AS fts
                JOIN sss_kayitlari k ON k.id = fts.rowid
                WHERE sss_fts MATCH ? {rol_kosulu}
                ORDER BY bm25_skoru
                LIMIT ?
                """,  # nosec B608
                (
                    konfigurasyon.FTS_SORU_AGIRLIGI,
                    konfigurasyon.FTS_CEVAP_AGIRLIGI,
                    konfigurasyon.FTS_KATEGORI_AGIRLIGI,
                    konfigurasyon.FTS_HARICI_KOD_AGIRLIGI,
                    konfigurasyon.FTS_MODUL_AGIRLIGI,
                    konfigurasyon.FTS_ARAMA_METNI_AGIRLIGI,
                    fts_sorgusu,
                    *rol_parametreleri,
                    konfigurasyon.FTS_ADAY_SAYISI,
                ),
            ).fetchall()
        sonuc = []
        for sira, satir in enumerate(satirlar, 1):
            sonuc.append(
                _FtsSonucu(
                    sss_id=int(satir["sss_id"]),
                    fts_sirasi=sira,
                    bm25_skoru=float(satir["bm25_skoru"]),
                )
            )
        return sonuc

    def vektor_ile_ara(
        self,
        soru: str,
        kullanici_rolu: str | None = None,
    ) -> tuple[list[_VektorSonucu], int]:
        beklenen_bayt = self._vektor_servisi.vektor_boyutu * np.dtype("<f4").itemsize
        rol_kosulu = ""
        rol_parametreleri: list[Any] = []
        if kullanici_rolu and kullanici_rolu != "YONETICI":
            rol_kosulu = (
                "AND (k.kullanici_rolu IS NULL "
                "OR k.kullanici_rolu = '' "
                "OR k.kullanici_rolu = ?)"
            )
            rol_parametreleri.append(kullanici_rolu)
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                f"""
                SELECT
                    v.parca_id,
                    v.sss_id,
                    v.vektor_verisi,
                    v.vektor_boyutu,
                    v.metin_ozeti,
                    p.parca_metni
                FROM sss_vektorleri v
                JOIN sss_parcalari p ON p.id = v.parca_id
                JOIN sss_kayitlari k ON k.id = v.sss_id
                WHERE v.model_adi = ? {rol_kosulu} AND k.durum = 'aktif'
                """,  # nosec B608
                (
                    self._vektor_servisi.model_adi,
                    *rol_parametreleri,
                ),
            ).fetchall()
        gecerli_vektorler = []
        parca_bilgileri = []
        gecersiz_vektor_sayisi = 0
        for satir in satirlar:
            vektor_verisi = satir["vektor_verisi"]
            if len(vektor_verisi) != beklenen_bayt:
                gecersiz_vektor_sayisi += 1
                gunlukleyici.warning(
                    "Gecersiz vektor BLOB boyutu: parca_id=%s, beklenen=%s, alinan=%s",
                    satir["parca_id"],
                    beklenen_bayt,
                    len(vektor_verisi),
                )
                continue
            if satir["vektor_boyutu"] != self._vektor_servisi.vektor_boyutu:
                gecersiz_vektor_sayisi += 1
                gunlukleyici.warning(
                    "Vektor boyutu uyusmazligi: parca_id=%s, beklenen=%s, alinan=%s",
                    satir["parca_id"],
                    self._vektor_servisi.vektor_boyutu,
                    satir["vektor_boyutu"],
                )
                continue
            guncel_ozet = self._metin_ozetini_hesapla(satir["parca_metni"])
            if satir["metin_ozeti"] != guncel_ozet:
                gecersiz_vektor_sayisi += 1
                gunlukleyici.warning(
                    "Vektor metin ozeti guncel degil: parca_id=%s",
                    satir["parca_id"],
                )
                continue
            try:
                vektor = self._vektor_servisi.blobu_vektore_donustur(
                    vektor_verisi
                )
            except (ValueError, TypeError, IndexError) as hata:
                gecersiz_vektor_sayisi += 1
                gunlukleyici.warning(
                    "Vektor BLOB donusturulemedi: parca_id=%s, hata=%s",
                    satir["parca_id"],
                    type(hata).__name__,
                )
                continue
            if not np.isfinite(vektor).all():
                gecersiz_vektor_sayisi += 1
                gunlukleyici.warning(
                    "Vektor sonlu olmayan deger iceriyor: parca_id=%s",
                    satir["parca_id"],
                )
                continue
            vektor_normu = float(np.linalg.norm(vektor))
            if abs(vektor_normu - 1.0) > _NORM_TOLERANSI:
                gecersiz_vektor_sayisi += 1
                gunlukleyici.warning(
                    "Vektor normu birim normdan uzak: parca_id=%s, norm=%s",
                    satir["parca_id"],
                    vektor_normu,
                )
                continue
            gecerli_vektorler.append(vektor)
            parca_bilgileri.append(
                {
                    "parca_id": satir["parca_id"],
                    "sss_id": satir["sss_id"],
                    "parca_metni": satir["parca_metni"],
                }
            )
        if not gecerli_vektorler:
            return [], gecersiz_vektor_sayisi
        sorgu_vektoru = self._vektor_servisi.metni_vektore_donustur(soru)
        vektor_matrisi = np.vstack(gecerli_vektorler)
        benzerlikler = np.dot(vektor_matrisi, sorgu_vektoru)
        sss_gruplari: dict[int, tuple[float, int, str]] = {}
        for indeks, (skor, bilgi) in enumerate(
            zip(benzerlikler, parca_bilgileri, strict=True)
        ):
            sss_id = int(bilgi["sss_id"])
            mevcut_skor, _, _ = sss_gruplari.get(sss_id, (-2.0, 0, ""))
            if skor > mevcut_skor:
                sss_gruplari[sss_id] = (
                    float(skor),
                    int(bilgi["parca_id"]),
                    str(bilgi["parca_metni"]),
                )
        siralanmis = sorted(
            sss_gruplari.items(),
            key=lambda x: x[1][0],
            reverse=True,
        )[: konfigurasyon.VEKTOR_ADAY_SAYISI]
        sonuc = []
        for sira, (sss_id, (skor, parca_id, parca_metni)) in enumerate(siralanmis, 1):
            sonuc.append(
                _VektorSonucu(
                    sss_id=sss_id,
                    parca_id=parca_id,
                    parca_metni=parca_metni,
                    vektor_sirasi=sira,
                    benzerlik_skoru=skor,
                )
            )
        return sonuc, gecersiz_vektor_sayisi

    def rrf_harmanla(
        self,
        fts_sonuclari: list[_FtsSonucu],
        vektor_sonuclari: list[_VektorSonucu],
    ) -> list[_RrfSonucu]:
        rrf_k = float(konfigurasyon.RRF_K)
        rrf_skorlari: dict[int, float] = {}
        fts_sira_haritasi: dict[int, int] = {}
        vektor_bilgileri: dict[int, dict[str, Any]] = {}
        for sonuc in fts_sonuclari:
            rrf_skorlari[sonuc.sss_id] = 1.0 / (rrf_k + sonuc.fts_sirasi)
            fts_sira_haritasi[sonuc.sss_id] = sonuc.fts_sirasi
        for sonuc in vektor_sonuclari:
            mevcut = rrf_skorlari.get(sonuc.sss_id, 0.0)
            rrf_skorlari[sonuc.sss_id] = mevcut + 1.0 / (rrf_k + sonuc.vektor_sirasi)
            vektor_bilgileri[sonuc.sss_id] = {
                "parca_id": sonuc.parca_id,
                "parca_metni": sonuc.parca_metni,
                "vektor_sirasi": sonuc.vektor_sirasi,
                "benzerlik_skoru": sonuc.benzerlik_skoru,
            }
        birlesik = sorted(
            rrf_skorlari.items(),
            key=lambda x: (
                -x[1],
                fts_sira_haritasi.get(x[0], 999999),
            ),
        )[: konfigurasyon.RRF_ADAY_SAYISI]
        sonuc = []
        for sss_id, rrf_skoru in birlesik:
            vektor_bilgi = vektor_bilgileri.get(sss_id)
            sonuc.append(
                _RrfSonucu(
                    sss_id=sss_id,
                    parca_id=vektor_bilgi["parca_id"] if vektor_bilgi else None,
                    parca_metni=(
                        vektor_bilgi["parca_metni"] if vektor_bilgi else None
                    ),
                    fts_sirasi=fts_sira_haritasi.get(sss_id),
                    vektor_sirasi=(
                        vektor_bilgi["vektor_sirasi"] if vektor_bilgi else None
                    ),
                    rrf_skoru=rrf_skoru,
                    vektor_benzerlik_skoru=(
                        vektor_bilgi["benzerlik_skoru"]
                        if vektor_bilgi
                        else None
                    ),
                )
            )
        return sonuc

    def _metin_ozetini_hesapla(self, metin: str) -> str:
        return hashlib.sha256(metin.encode("utf-8")).hexdigest()
