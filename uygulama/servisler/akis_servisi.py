import asyncio
import json
from collections.abc import AsyncIterator

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.modeller.semalar import AramaAdayi
from uygulama.servisler.arama_servisi import AramaServisi
from uygulama.servisler.deepseek_servisi import DeepSeekServisi, DeepSeekServisiHatasi
from uygulama.servisler.niyet_siniflandirici import NiyetSiniflandirici
from uygulama.servisler.oturum_hafizasi import OturumHafizasi

_YETERSIZ_BILGI_YANITI = (
    "İlgili UYDS kaynaklarında bu soruya ilişkin yeterli bilgi bulunamamıştır"
)
_URETIM_HATASI_YANITI = "Yanıt üretimi şu anda tamamlanamadı"


_CELISKI_SSS_BILGI_METNI = (
    "Dikkat: Asagidaki kaynaklar arasinda benzer konuda farkli veya celisen bilgiler "
    "tespit edilmistir. Yanitinda her iki kaynagin ne soyledigini belirt ve "
    "kullanicidan hangi baglamda oldugunu dogrulamasini iste."
)


class AkisServisi:
    def __init__(
        self,
        arama_servisi: AramaServisi,
        deepseek_servisi: DeepSeekServisi,
        oturum_hafizasi: OturumHafizasi,
        niyet_siniflandirici: NiyetSiniflandirici | None = None,
    ) -> None:
        self._arama_servisi = arama_servisi
        self._deepseek_servisi = deepseek_servisi
        self._oturum_hafizasi = oturum_hafizasi
        self._niyet_siniflandirici = niyet_siniflandirici

    async def yanit_akisini_uret(
        self,
        soru: str,
        oturum_id: str,
        kullanici_rolu: str | None = None,
    ) -> AsyncIterator[str]:
        temiz_soru = soru.strip()
        if not temiz_soru:
            raise ValueError("Bos soru yanitlanamaz")
        if len(temiz_soru) > konfigurasyon.MESAJ_MAKS_KARAKTER:
            raise ValueError("Soru izin verilen karakter sinirini asiyor")
        arama_sonucu = await asyncio.to_thread(
            self._arama_servisi.ara,
            temiz_soru,
            kullanici_rolu,
        )
        kaynaklar = tuple(
            arama_sonucu.adaylar[: konfigurasyon.DEEPSEEK_KAYNAK_SAYISI]
        )
        guven_skoru = self._guven_skorunu_hesapla(kaynaklar)
        yeterli_guven = bool(kaynaklar) and guven_skoru >= konfigurasyon.GUVEN_ESIGI
        yield self._olay_olustur(
            "meta",
            {
                "guven_skoru": guven_skoru,
                "yeterli_guven": yeterli_guven,
                "kaynaklar": (
                    self._kaynak_ozetlerini_olustur(kaynaklar)
                    if yeterli_guven
                    else []
                ),
            },
        )
        if not yeterli_guven:
            await self._oturum_hafizasi.konusmayi_ekle(
                oturum_id,
                temiz_soru,
                _YETERSIZ_BILGI_YANITI,
            )
            yield self._olay_olustur(
                "parca",
                {"metin": _YETERSIZ_BILGI_YANITI},
            )
            yield self._olay_olustur("tamamlandi", {"cevaplandi": False})
            return

        celiski_bilgisi = self._celiski_tespit_et(kaynaklar)
        if celiski_bilgisi["celiski_var"]:
            yield self._olay_olustur("celiski", celiski_bilgisi)

        niyet_sonucu = None
        if self._niyet_siniflandirici is not None:
            niyet_sonucu = self._niyet_siniflandirici.siniflandir(temiz_soru)
            if niyet_sonucu.eslesme_var_mi:
                yield self._olay_olustur(
                    "eylem",
                    {
                        "eylemler": [
                            {
                                "niyet_adi": e.niyet_adi,
                                "buton_metni": e.buton_metni,
                                "hedef_url": e.hedef_url,
                                "buton_tipi": e.buton_tipi,
                            }
                            for e in niyet_sonucu.eslesmeler
                        ]
                    },
                )
        gecmis = await self._oturum_hafizasi.mesajlari_al(oturum_id)
        yanit_parcalari = []
        etkili_soru = temiz_soru
        if celiski_bilgisi["celiski_var"]:
            etkili_soru = f"{_CELISKI_SSS_BILGI_METNI}\n\nSORU: {temiz_soru}"
        try:
            async for parca in self._deepseek_servisi.yanit_akisini_uret(
                etkili_soru,
                kaynaklar,
                gecmis,
            ):
                yanit_parcalari.append(parca)
                yield self._olay_olustur("parca", {"metin": parca})
        except DeepSeekServisiHatasi:
            yedek_kaynaklari = self._kaynak_ozetlerini_olustur(
                kaynaklar[: konfigurasyon.YEDEK_KAYNAK_SAYISI]
            )
            yield self._olay_olustur(
                "yedek",
                {
                    "mesaj": _URETIM_HATASI_YANITI,
                    "kaynaklar": yedek_kaynaklari,
                },
            )
            await self._oturum_hafizasi.konusmayi_ekle(
                oturum_id,
                temiz_soru,
                _URETIM_HATASI_YANITI,
            )
            yield self._olay_olustur("tamamlandi", {"cevaplandi": False})
            return
        tam_yanit = "".join(yanit_parcalari).strip()
        if not tam_yanit:
            yield self._olay_olustur(
                "hata",
                {"mesaj": _URETIM_HATASI_YANITI},
            )
            return
        await self._oturum_hafizasi.konusmayi_ekle(
            oturum_id,
            temiz_soru,
            tam_yanit,
        )
        yield self._olay_olustur("tamamlandi", {"cevaplandi": True})

    def _guven_skorunu_hesapla(
        self,
        kaynaklar: tuple[AramaAdayi, ...],
    ) -> float:
        skorlar = [
            kaynak.vektor_benzerlik_skoru
            for kaynak in kaynaklar
            if kaynak.vektor_benzerlik_skoru is not None
        ]
        if not skorlar:
            return 0.0
        return round(max(0.0, min(1.0, max(skorlar))), 6)

    def _celiski_tespit_et(
        self,
        kaynaklar: tuple[AramaAdayi, ...],
    ) -> dict:
        if len(kaynaklar) < 2:
            return {"celiski_var": False, "ilgili_sss_idler": [], "aciklama": ""}

        modul_gruplari: dict[str, list[AramaAdayi]] = {}
        for aday in kaynaklar:
            dokuman = aday.kaynak_dokuman or ""
            if dokuman not in modul_gruplari:
                modul_gruplari[dokuman] = []
            modul_gruplari[dokuman].append(aday)

        celiskiler = []
        for modul, adaylar in modul_gruplari.items():
            if len(adaylar) < 2:
                continue
            skorlar = [a.rrf_skoru for a in adaylar]
            skor_araligi = max(skorlar) - min(skorlar)
            if skor_araligi > 0.15:
                continue
            metin_uzunluklari = [len(a.aday_metni) for a in adaylar]
            if max(metin_uzunluklari) > 0 and min(metin_uzunluklari) / max(metin_uzunluklari) < 0.3:
                continue
            celiski_adaylari = [a for a in adaylar if a.sss_id is not None]
            if len(celiski_adaylari) >= 2:
                celiskiler.append({
                    "modul": modul,
                    "ilgili_sss_idler": [a.sss_id for a in celiski_adaylari],
                    "skor_benzerligi": round(skor_araligi, 4),
                })

        if celiskiler:
            tum_idler: list[int] = []
            for c in celiskiler:
                for sss_id in c["ilgili_sss_idler"]:
                    if sss_id not in tum_idler:
                        tum_idler.append(sss_id)
            return {
                "celiski_var": True,
                "ilgili_sss_idler": tum_idler,
                "aciklama": f"{len(celiskiler)} belge grubunda benzer skorlu farkli SSS kaydi tespit edildi",
                "detay": celiskiler,
            }
        return {"celiski_var": False, "ilgili_sss_idler": [], "aciklama": ""}

    def _kaynak_ozetlerini_olustur(
        self,
        kaynaklar: tuple[AramaAdayi, ...],
    ) -> list[dict]:
        return [
            {
                "sss_id": kaynak.sss_id,
                "dokuman": kaynak.kaynak_dokuman,
                "sayfa": kaynak.kaynak_sayfa,
                "satir": kaynak.kaynak_satir,
            }
            for kaynak in kaynaklar
        ]

    def _olay_olustur(self, olay: str, veri: dict) -> str:
        json_verisi = json.dumps(
            veri,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return f"event: {olay}\ndata: {json_verisi}\n\n"
