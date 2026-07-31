from dataclasses import replace
from time import perf_counter

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.semalar import AramaAdayi, AramaSonucu
from uygulama.servisler.geri_bildirim_servisi import GeriBildirimServisi
from uygulama.servisler.hibrit_arama import HibritArama, _RrfSonucu
from uygulama.servisler.sorgu_genisletici import SorguGenisletici
from uygulama.servisler.terim_haritasi import TerimHaritasi
from uygulama.servisler.vektor_servisi import VektorServisi
from uygulama.servisler.yeniden_siralayici import (
    YenidenSiralamaHatasi,
    YenidenSiralayiciProtokolu,
)


class AramaServisi:
    def __init__(
        self,
        vektor_servisi: VektorServisi,
        terim_haritasi: TerimHaritasi,
        yeniden_siralayici: YenidenSiralayiciProtokolu | None = None,
        geri_bildirim_servisi: GeriBildirimServisi | None = None,
    ) -> None:
        self._sorgu_genisletici = SorguGenisletici(terim_haritasi)
        self._hibrit_arama = HibritArama(vektor_servisi)
        self._yeniden_siralayici = yeniden_siralayici
        self._geri_bildirim_servisi = geri_bildirim_servisi
        self._vektor_servisi = vektor_servisi

    def ara(
        self,
        soru: str,
        kullanici_rolu: str | None = None,
    ) -> AramaSonucu:
        baslangic = perf_counter()
        genisletilmis = self._sorgu_genisletici.genislet(soru)
        fts_sonuclari = self._hibrit_arama.fts_ile_ara(
            genisletilmis.fts_sorgusu,
            kullanici_rolu=kullanici_rolu,
        )
        vektor_sonuclari, gecersiz_vektor = self._hibrit_arama.vektor_ile_ara(
            soru,
            kullanici_rolu=kullanici_rolu,
        )
        rrf_sonuclari = self._hibrit_arama.rrf_harmanla(fts_sonuclari, vektor_sonuclari)
        alternatif_sonuclar = self._alternatif_sorulari_tara(soru)
        rrf_sonuclari = self._alternatif_sonuclari_birlestir(
            rrf_sonuclari,
            alternatif_sonuclar,
        )
        zenginlestirilmis = self._kaynak_ve_metin_ekle(rrf_sonuclari)
        yeniden_siralama_etkin = self._yeniden_siralayici is not None
        if yeniden_siralama_etkin:
            try:
                zenginlestirilmis = self._yeniden_siralayici.yeniden_sirala(
                    soru,
                    zenginlestirilmis,
                )
            except YenidenSiralamaHatasi as hata:
                yeniden_siralama_etkin = False
                gunlukleyici.warning(
                    "Yeniden siralama basarisiz; RRF sirasi korundu: "
                    f"{type(hata).__name__}"
                )
        gecen_sure_ms = (perf_counter() - baslangic) * 1000.0
        return AramaSonucu(
            adaylar=tuple(zenginlestirilmis),
            gecen_sure_ms=round(gecen_sure_ms, 3),
            genisletilmis_fts_sorgusu=genisletilmis.fts_sorgusu,
            genisletilen_terim_sayisi=(
                genisletilmis.genisletilen_terim_sayisi
            ),
            kullanilan_grup_sayisi=genisletilmis.kullanilan_grup_sayisi,
            fts_aday_sayisi=len(fts_sonuclari),
            vektor_aday_sayisi=len(vektor_sonuclari),
            birlesik_aday_sayisi=len(rrf_sonuclari),
            gecersiz_vektor_sayisi=gecersiz_vektor,
            yeniden_siralama_etkin=yeniden_siralama_etkin,
        )

    def _kaynak_ve_metin_ekle(
        self,
        rrf_sonuclari: list[_RrfSonucu],
    ) -> list[AramaAdayi]:
        if not rrf_sonuclari:
            return []
        sss_kimlikleri = list(
            dict.fromkeys(sonuc.sss_id for sonuc in rrf_sonuclari)
        )
        with baglam_yoneticisi() as baglanti:
            baglanti.execute(
                """
                CREATE TEMP TABLE IF NOT EXISTS secili_sss_kimlikleri (
                    id INTEGER PRIMARY KEY
                )
                """
            )
            baglanti.execute("DELETE FROM secili_sss_kimlikleri")
            baglanti.executemany(
                "INSERT INTO secili_sss_kimlikleri (id) VALUES (?)",
                ((kimlik,) for kimlik in sss_kimlikleri),
            )
            satirlar = baglanti.execute(
                """
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
                JOIN secili_sss_kimlikleri secili ON secili.id = k.id
                WHERE k.durum = 'aktif'
                """
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
                    vektor_benzerlik_skoru=(
                        rrf_sonucu.vektor_benzerlik_skoru
                    ),
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

    def _alternatif_sorulari_tara(
        self,
        soru: str,
    ) -> list[_RrfSonucu]:
        if self._geri_bildirim_servisi is None:
            return []
        try:
            sorgu_vektoru = self._vektor_servisi.metni_vektore_donustur(soru)
        except ValueError:
            return []
        alternatifler = self._geri_bildirim_servisi.alternatif_sorulari_ara(
            sorgu_vektoru,
            konfigurasyon.ALTERNATIF_SORU_ADAY_SAYISI,
        )
        sonuclar = []
        islenen_sss_kimlikleri = set()
        for sira, alt in enumerate(alternatifler, start=1):
            if (
                alt["benzerlik_skoru"]
                < konfigurasyon.ALTERNATIF_SORU_BENZERLIK_ESIGI
            ):
                continue
            if alt["sss_id"] in islenen_sss_kimlikleri:
                continue
            islenen_sss_kimlikleri.add(alt["sss_id"])
            sonuclar.append(
                _RrfSonucu(
                    sss_id=alt["sss_id"],
                    parca_id=None,
                    parca_metni=None,
                    fts_sirasi=None,
                    vektor_sirasi=None,
                    rrf_skoru=1.0 / (konfigurasyon.RRF_K + sira),
                    vektor_benzerlik_skoru=alt["benzerlik_skoru"],
                )
            )
        return sonuclar

    def _alternatif_sonuclari_birlestir(
        self,
        rrf_sonuclari: list[_RrfSonucu],
        alternatif_sonuclar: list[_RrfSonucu],
    ) -> list[_RrfSonucu]:
        birlesik = {sonuc.sss_id: sonuc for sonuc in rrf_sonuclari}
        for alternatif in alternatif_sonuclar:
            mevcut = birlesik.get(alternatif.sss_id)
            if mevcut is None:
                birlesik[alternatif.sss_id] = alternatif
                continue
            benzerlik_skorlari = [
                skor
                for skor in (
                    mevcut.vektor_benzerlik_skoru,
                    alternatif.vektor_benzerlik_skoru,
                )
                if skor is not None
            ]
            birlesik[alternatif.sss_id] = replace(
                mevcut,
                rrf_skoru=mevcut.rrf_skoru + alternatif.rrf_skoru,
                vektor_benzerlik_skoru=(
                    max(benzerlik_skorlari)
                    if benzerlik_skorlari
                    else None
                ),
            )
        return sorted(
            birlesik.values(),
            key=lambda sonuc: (
                -sonuc.rrf_skoru,
                sonuc.fts_sirasi
                if sonuc.fts_sirasi is not None
                else 999999,
                sonuc.sss_id,
            ),
        )[: konfigurasyon.RRF_ADAY_SAYISI]
