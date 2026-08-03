import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.semalar import AramaAdayi
from uygulama.servisler.bilgi_grafi import BilgiGrafi
from uygulama.servisler.vektor_servisi import VektorServisi


@dataclass(frozen=True)
class _BelgeFtsSonucu:
    parca_id: int
    belge_id: int
    sira: int


@dataclass(frozen=True)
class _BelgeVektorSonucu:
    parca_id: int
    belge_id: int
    sira: int
    benzerlik_skoru: float


class BelgeArama:
    def __init__(self, vektor_servisi: VektorServisi) -> None:
        self._vektor_servisi = vektor_servisi
        self._bilgi_grafi = BilgiGrafi()

    def ara(
        self,
        soru: str,
        fts_sorgusu: str,
        kullanici_rolu: str | None,
    ) -> list[AramaAdayi]:
        hedef_yil = self._hedef_yili_bul(soru)
        yetki_seviyesi = self._rol_yetki_seviyesini_bul(kullanici_rolu)
        izinli_belgeler = self._izinli_belgeleri_bul(
            yetki_seviyesi,
            hedef_yil,
        )
        if not izinli_belgeler:
            return []
        fts_sonuclari = self._fts_ile_ara(
            fts_sorgusu,
            izinli_belgeler,
            yetki_seviyesi,
        )
        vektor_sonuclari = self._vektor_ile_ara(
            soru,
            izinli_belgeler,
            yetki_seviyesi,
        )
        return self._rrf_ile_birlestir(
            soru,
            fts_sonuclari,
            vektor_sonuclari,
            izinli_belgeler,
        )

    def _hedef_yili_bul(self, soru: str) -> int | None:
        eslesme = re.search(r"\b(20\d{2})\b", soru)
        if eslesme:
            return int(eslesme.group(1))
        tarihsel_ifadeler = ("eski", "önceki", "onceki", "geçmiş", "gecmis")
        if any(ifade in soru.casefold() for ifade in tarihsel_ifadeler):
            return datetime.now(timezone.utc).year - 1
        return None

    def _rol_yetki_seviyesini_bul(self, kullanici_rolu: str | None) -> int:
        if not konfigurasyon.BELGE_ACL_AKTIF:
            return 4
        try:
            esleme = json.loads(konfigurasyon.RBAC_YETKI_ESLEME)
        except (json.JSONDecodeError, TypeError):
            return 0
        rol = (kullanici_rolu or "kullanici").casefold()
        try:
            return max(0, min(4, int(esleme.get(rol, 0))))
        except (TypeError, ValueError):
            return 0

    def _izinli_belgeleri_bul(
        self,
        yetki_seviyesi: int,
        hedef_yil: int | None,
    ) -> set[int]:
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                """
                SELECT id, orijinal_yol, son_degistirilme_tarihi,
                       yetki_seviyesi, aktif, surum
                FROM belge_kayitlari
                WHERE islenme_durumu = 'tamamlandi'
                  AND yetki_seviyesi <= ?
                ORDER BY orijinal_yol, surum DESC
                """,
                (yetki_seviyesi,),
            ).fetchall()
        if hedef_yil is None:
            return {int(satir["id"]) for satir in satirlar if satir["aktif"] == 1}
        secilenler = {}
        for satir in satirlar:
            tarih_metni = satir["son_degistirilme_tarihi"] or ""
            try:
                belge_yili = datetime.fromisoformat(tarih_metni).year
            except ValueError:
                continue
            if belge_yili <= hedef_yil and satir["orijinal_yol"] not in secilenler:
                secilenler[satir["orijinal_yol"]] = int(satir["id"])
        return set(secilenler.values())

    def _fts_ile_ara(
        self,
        fts_sorgusu: str,
        izinli_belgeler: set[int],
        yetki_seviyesi: int,
    ) -> list[_BelgeFtsSonucu]:
        if not fts_sorgusu.strip():
            return []
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                """
                SELECT parca.id AS parca_id, parca.belge_id,
                       parca.yetki_seviyesi
                FROM belge_fts AS fts
                JOIN yapisal_parcalar AS parca ON parca.id = fts.rowid
                WHERE belge_fts MATCH ?
                ORDER BY bm25(belge_fts)
                LIMIT ?
                """,
                (fts_sorgusu, konfigurasyon.FTS_ADAY_SAYISI * 10),
            ).fetchall()
        sonuc = []
        for satir in satirlar:
            if int(satir["belge_id"]) not in izinli_belgeler:
                continue
            if int(satir["yetki_seviyesi"]) > yetki_seviyesi:
                continue
            sonuc.append(
                _BelgeFtsSonucu(
                    parca_id=int(satir["parca_id"]),
                    belge_id=int(satir["belge_id"]),
                    sira=len(sonuc) + 1,
                )
            )
            if len(sonuc) >= konfigurasyon.FTS_ADAY_SAYISI:
                break
        return sonuc

    def _vektor_ile_ara(
        self,
        soru: str,
        izinli_belgeler: set[int],
        yetki_seviyesi: int,
    ) -> list[_BelgeVektorSonucu]:
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                """
                SELECT vektor.parca_id, parca.belge_id,
                       vektor.vektor, vektor.vektor_boyutu,
                       parca.yetki_seviyesi
                FROM parca_vektorleri AS vektor
                JOIN yapisal_parcalar AS parca ON parca.id = vektor.parca_id
                WHERE vektor.model_surumu = ?
                """,
                (self._vektor_servisi.model_adi,),
            ).fetchall()
        gecerli = []
        for satir in satirlar:
            if int(satir["belge_id"]) not in izinli_belgeler:
                continue
            if int(satir["yetki_seviyesi"]) > yetki_seviyesi:
                continue
            if int(satir["vektor_boyutu"]) != self._vektor_servisi.vektor_boyutu:
                continue
            try:
                vektor = self._vektor_servisi.blobu_vektore_donustur(
                    satir["vektor"]
                )
            except (ValueError, TypeError):
                continue
            if not np.isfinite(vektor).all():
                continue
            norm = float(np.linalg.norm(vektor))
            if abs(norm - 1.0) > 0.01:
                continue
            gecerli.append((satir, vektor))
        if not gecerli:
            return []
        sorgu_vektoru = self._vektor_servisi.metni_vektore_donustur(soru)
        skorlar = np.dot(
            np.vstack([vektor for _, vektor in gecerli]),
            sorgu_vektoru,
        )
        siralanmis = sorted(
            zip(gecerli, skorlar, strict=True),
            key=lambda deger: float(deger[1]),
            reverse=True,
        )[: konfigurasyon.VEKTOR_ADAY_SAYISI]
        return [
            _BelgeVektorSonucu(
                parca_id=int(satir["parca_id"]),
                belge_id=int(satir["belge_id"]),
                sira=sira,
                benzerlik_skoru=float(skor),
            )
            for sira, ((satir, _), skor) in enumerate(siralanmis, 1)
        ]

    def _rrf_ile_birlestir(
        self,
        soru: str,
        fts_sonuclari: list[_BelgeFtsSonucu],
        vektor_sonuclari: list[_BelgeVektorSonucu],
        izinli_belgeler: set[int],
    ) -> list[AramaAdayi]:
        rrf_k = float(konfigurasyon.RRF_K)
        birlesik = {}
        for sonuc in fts_sonuclari:
            birlesik[sonuc.parca_id] = {
                "belge_id": sonuc.belge_id,
                "fts_sirasi": sonuc.sira,
                "vektor_sirasi": None,
                "benzerlik": None,
                "skor": 1.0 / (rrf_k + sonuc.sira),
            }
        for sonuc in vektor_sonuclari:
            kayit = birlesik.setdefault(
                sonuc.parca_id,
                {
                    "belge_id": sonuc.belge_id,
                    "fts_sirasi": None,
                    "vektor_sirasi": None,
                    "benzerlik": None,
                    "skor": 0.0,
                },
            )
            kayit["vektor_sirasi"] = sonuc.sira
            kayit["benzerlik"] = sonuc.benzerlik_skoru
            kayit["skor"] += 1.0 / (rrf_k + sonuc.sira)
        if not birlesik:
            return []
        graf_skorlari = self._graf_skorlarini_hesapla(soru, izinli_belgeler)
        for kayit in birlesik.values():
            graf_skoru = graf_skorlari.get(kayit["belge_id"], 0.0)
            kayit["skor"] *= 1.0 + konfigurasyon.GRAF_BONUS_SKORU * graf_skoru
        secilenler = sorted(
            birlesik.items(),
            key=lambda deger: -deger[1]["skor"],
        )[: konfigurasyon.RRF_ADAY_SAYISI]
        parca_kimlikleri = [parca_id for parca_id, _ in secilenler]
        kaynaklar = self._kaynaklari_al(parca_kimlikleri)
        return [
            AramaAdayi(
                sss_id=None,
                parca_id=parca_id,
                aday_metni=kaynaklar[parca_id]["metin"],
                kaynak_dokuman=kaynaklar[parca_id]["dosya_adi"],
                kaynak_sayfa=(
                    str(kaynaklar[parca_id]["sayfa_numarasi"])
                    if kaynaklar[parca_id]["sayfa_numarasi"] is not None
                    else None
                ),
                kaynak_satir=None,
                fts_sirasi=kayit["fts_sirasi"],
                vektor_sirasi=kayit["vektor_sirasi"],
                rrf_skoru=float(kayit["skor"]),
                vektor_benzerlik_skoru=kayit["benzerlik"],
                yeniden_siralama_skoru=None,
            )
            for parca_id, kayit in secilenler
            if parca_id in kaynaklar
        ]

    def _graf_skorlarini_hesapla(
        self,
        soru: str,
        izinli_belgeler: set[int],
    ) -> dict[int, float]:
        if not konfigurasyon.GRAF_AKTIF:
            return {}
        sorgu_kavramlari = self._bilgi_grafi.kavram_cikar(soru)
        if not sorgu_kavramlari:
            return {}
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                "SELECT belge_id, kavram FROM belge_kavramlari"
            ).fetchall()
        belge_kavramlari = {}
        for satir in satirlar:
            belge_id = int(satir["belge_id"])
            if belge_id in izinli_belgeler:
                belge_kavramlari.setdefault(str(belge_id), []).append(
                    satir["kavram"]
                )
        return {
            int(belge_id): skor
            for belge_id, skor in self._bilgi_grafi.graf_skor_hesapla(
                sorgu_kavramlari,
                belge_kavramlari,
            ).items()
        }

    def _kaynaklari_al(self, parca_kimlikleri: list[int]) -> dict[int, dict]:
        if not parca_kimlikleri:
            return {}
        kaynaklar = {}
        with baglam_yoneticisi() as baglanti:
            for parca_id in parca_kimlikleri:
                satir = baglanti.execute(
                    """
                    SELECT parca.id, parca.metin, parca.sayfa_numarasi,
                           belge.dosya_adi
                    FROM yapisal_parcalar AS parca
                    JOIN belge_kayitlari AS belge ON belge.id = parca.belge_id
                    WHERE parca.id = ?
                    """,
                    (parca_id,),
                ).fetchone()
                if satir is not None:
                    kaynaklar[parca_id] = dict(satir)
        return kaynaklar
