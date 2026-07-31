import asyncio
import time
from datetime import datetime, timedelta, timezone

from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.gunlukleyici import gunlukleyici


class VeriTemizligi:
    def __init__(self):
        self.ay_siniri = konfigurasyon.VERI_SAKLAMA_SURESI_AY
        self.parti_boyutu = konfigurasyon.VERI_TEMIZLIK_PARTI_BOYUTU
        self.aktif = konfigurasyon.VERI_TEMIZLIK_AKTIF
        self.saat = konfigurasyon.VERI_TEMIZLIK_SAATI

    def eski_sorgulari_temizle(self) -> dict:
        if not self.aktif:
            return {"durum": "pasif", "silinen_kayit": 0}

        sinir_tarihi = (
            datetime.now(timezone.utc) - timedelta(days=self.ay_siniri * 30)
        ).isoformat()

        toplam_silinen = 0
        baslangic_zamani = time.monotonic()

        try:
            with baglam_yoneticisi() as baglanti:
                while True:
                    imlec = baglanti.execute(
                        "SELECT id FROM asistan_sorgulari "
                        "WHERE olusturulma_tarihi < ? "
                        "LIMIT ?",
                        (sinir_tarihi, self.parti_boyutu),
                    )
                    silinecekler = [satir[0] for satir in imlec.fetchall()]
                    if not silinecekler:
                        break

                    baglanti.execute("BEGIN IMMEDIATE")
                    yer_tutucular = ",".join("?" * len(silinecekler))
                    baglanti.execute(
                        f"DELETE FROM asistan_sorgulari WHERE id IN ({yer_tutucular})",  # nosec B608
                        silinecekler,
                    )
                    baglanti.commit()
                    toplam_silinen += len(silinecekler)

            gecen_sure = time.monotonic() - baslangic_zamani
            gunlukleyici.info(
                "Veri temizligi tamamlandi",
                extra={
                    "silinen_kayit": toplam_silinen,
                    "sinir_tarihi": sinir_tarihi,
                    "sure_saniye": round(gecen_sure, 2),
                },
            )
            return {"durum": "basarili", "silinen_kayit": toplam_silinen}

        except Exception as hata:
            gunlukleyici.error(
                "Veri temizligi sirasinda hata",
                extra={"hata": str(hata)},
            )
            return {"durum": "hata", "silinen_kayit": 0, "hata": str(hata)}

    async def _zamanlanmis_temizlik_gorevi(self):
        while True:
            simdi = datetime.now()
            saat, dakika = map(int, self.saat.split(":"))
            hedef = simdi.replace(hour=saat, minute=dakika, second=0, microsecond=0)
            if simdi >= hedef:
                hedef += timedelta(days=1)
            bekleme_suresi = (hedef - simdi).total_seconds()
            await asyncio.sleep(bekleme_suresi)
            self.eski_sorgulari_temizle()

    def periyodik_temizlik_baslat(self) -> asyncio.Task:
        return asyncio.create_task(self._zamanlanmis_temizlik_gorevi())