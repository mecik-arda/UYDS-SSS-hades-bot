from time import perf_counter

from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.semalar import AramaAdayi, AramaSonucu
from uygulama.servisler.hibrit_arama import HibritArama, _RrfSonucu
from uygulama.servisler.sorgu_genisletici import SorguGenisletici
from uygulama.servisler.terim_haritasi import TerimHaritasi
from uygulama.servisler.vektor_servisi import VektorServisi
from uygulama.servisler.yeniden_siralayici import YenidenSiralayiciProtokolu


class AramaServisi:
    def __init__(
        self,
        vektor_servisi: VektorServisi,
        terim_haritasi: TerimHaritasi,
        yeniden_siralayici: YenidenSiralayiciProtokolu | None = None,
    ) -> None:
        self._sorgu_genisletici = SorguGenisletici(terim_haritasi)
        self._hibrit_arama = HibritArama(vektor_servisi)
        self._yeniden_siralayici = yeniden_siralayici

    def ara(self, soru: str) -> AramaSonucu:
        baslangic = perf_counter()
        genisletilmis = self._sorgu_genisletici.genislet(soru)
        fts_sonuclari = self._hibrit_arama.fts_ile_ara(genisletilmis.fts_sorgusu)
        vektor_sonuclari, gecersiz_vektor = self._hibrit_arama.vektor_ile_ara(soru)
        rrf_sonuclari = self._hibrit_arama.rrf_harmanla(fts_sonuclari, vektor_sonuclari)
        zenginlestirilmis = self._kaynak_ve_metin_ekle(rrf_sonuclari)
        if self._yeniden_siralayici is not None:
            zenginlestirilmis = self._yeniden_siralayici.yeniden_sirala(
                soru,
                zenginlestirilmis,
            )
        gecen_sure_ms = (perf_counter() - baslangic) * 1000.0
        return AramaSonucu(
            adaylar=tuple(zenginlestirilmis),
            gecen_sure_ms=round(gecen_sure_ms, 3),
            fts_aday_sayisi=len(fts_sonuclari),
            vektor_aday_sayisi=len(vektor_sonuclari),
            birlesik_aday_sayisi=len(rrf_sonuclari),
            gecersiz_vektor_sayisi=gecersiz_vektor,
            yeniden_siralama_etkin=self._yeniden_siralayici is not None,
        )

    def _kaynak_ve_metin_ekle(
        self,
        rrf_sonuclari: list[_RrfSonucu],
    ) -> list[AramaAdayi]:
        if not rrf_sonuclari:
            return []
        sss_kimlikleri = [sonuc.sss_id for sonuc in rrf_sonuclari]
        yer_tutucular = ",".join("?" for _ in sss_kimlikleri)
        with baglam_yoneticisi() as baglanti:
            satirlar = baglanti.execute(
                f"""
                SELECT
                    k.id AS sss_id,
                    k.kaynak_dokuman,
                    k.kaynak_sayfa,
                    k.kaynak_satir,
                    k.soru,
                    k.cevap,
                    (
                        SELECT p.parca_metni
                        FROM sss_parcalari p
                        WHERE p.sss_id = k.id
                        ORDER BY p.parca_sira_no
                        LIMIT 1
                    ) AS ilk_parca_metni
                FROM sss_kayitlari k
                WHERE k.id IN ({yer_tutucular}) AND k.durum = 'aktif'
                """,
                sss_kimlikleri,
            ).fetchall()
        kaynak_haritasi = {
            satir["sss_id"]: {
                "kaynak_dokuman": satir["kaynak_dokuman"],
                "kaynak_sayfa": satir["kaynak_sayfa"],
                "kaynak_satir": satir["kaynak_satir"],
                "soru": satir["soru"],
                "cevap": satir["cevap"],
                "ilk_parca_metni": satir["ilk_parca_metni"] or "",
            }
            for satir in satirlar
        }
        sonuc = []
        for rrf_sonucu in rrf_sonuclari:
            kaynak = kaynak_haritasi.get(rrf_sonucu.sss_id)
            if kaynak is None:
                continue
            aday_metni = self._aday_metnini_olustur(rrf_sonucu, kaynak)
            sonuc.append(
                AramaAdayi(
                    sss_id=rrf_sonucu.sss_id,
                    parca_id=rrf_sonucu.parca_id,
                    aday_metni=aday_metni,
                    kaynak_dokuman=kaynak["kaynak_dokuman"],
                    kaynak_sayfa=kaynak["kaynak_sayfa"],
                    kaynak_satir=kaynak["kaynak_satir"],
                    fts_sirasi=rrf_sonucu.fts_sirasi,
                    vektor_sirasi=rrf_sonucu.vektor_sirasi,
                    rrf_skoru=rrf_sonucu.rrf_skoru,
                    yeniden_siralama_skoru=None,
                )
            )
        return sonuc

    def _aday_metnini_olustur(
        self,
        rrf_sonucu: _RrfSonucu,
        kaynak: dict,
    ) -> str:
        if rrf_sonucu.parca_metni:
            return rrf_sonucu.parca_metni
        if kaynak.get("ilk_parca_metni"):
            return kaynak["ilk_parca_metni"]
        return f"{kaynak['soru']}\n{kaynak['cevap']}"