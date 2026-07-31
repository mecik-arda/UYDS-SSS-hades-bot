import asyncio
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi


@dataclass(frozen=True)
class HaftalikRapor:
    baslangic_tarihi: str
    bitis_tarihi: str
    toplam_soru: int
    cevaplanan_soru: int
    cevapsiz_soru: int
    bekleyen_geri_bildirim: int
    ortalama_guven_skoru: float
    en_cok_sorulan_kategoriler: list[tuple[str, int]]


class EpostaRaporlayici:
    def __init__(self) -> None:
        self.aktif = konfigurasyon.EPOSTA_RAPORLAMA_AKTIF
        self.smtp_sunucu = konfigurasyon.EPOSTA_SMTP_SUNUCU
        self.smtp_port = konfigurasyon.EPOSTA_SMTP_PORT
        self.tls_kullan = konfigurasyon.EPOSTA_TLS_KULLAN
        self.kullanici = konfigurasyon.EPOSTA_KULLANICI
        self.sifre = konfigurasyon.EPOSTA_SIFRE
        self.alici = konfigurasyon.EPOSTA_ALICI

    def haftalik_raporu_hazirla(self) -> HaftalikRapor:
        simdi = datetime.now(timezone.utc)
        bir_hafta_once = simdi - timedelta(days=7)
        with baglam_yoneticisi() as baglanti:
            toplam = baglanti.execute(
                """
                SELECT COUNT(*) FROM asistan_sorgulari
                WHERE olusturulma_tarihi >= ?
                """,
                (bir_hafta_once.isoformat(),),
            ).fetchone()[0]
            cevaplanan = baglanti.execute(
                """
                SELECT COUNT(*) FROM asistan_sorgulari
                WHERE olusturulma_tarihi >= ? AND cevaplandi_mi = 1
                """,
                (bir_hafta_once.isoformat(),),
            ).fetchone()[0]
            bekleyen = baglanti.execute(
                """
                SELECT COUNT(*) FROM geri_bildirimler
                WHERE durum = 'BEKLEMEDE'
                """
            ).fetchone()[0]
            ortalama_skor = baglanti.execute(
                """
                SELECT COALESCE(AVG(guven_skoru), 0.0)
                FROM asistan_sorgulari
                WHERE olusturulma_tarihi >= ? AND cevaplandi_mi = 1
                """,
                (bir_hafta_once.isoformat(),),
            ).fetchone()[0]
            kategoriler = baglanti.execute(
                """
                SELECT k.kategori, COUNT(*) AS sayi
                FROM asistan_sorgulari a
                JOIN sss_kayitlari k ON k.id IN (
                    SELECT value FROM json_each(a.kaynak_sss_idleri)
                )
                WHERE a.olusturulma_tarihi >= ? AND a.cevaplandi_mi = 1
                AND a.kaynak_sss_idleri IS NOT NULL
                AND a.kaynak_sss_idleri != '[]'
                GROUP BY k.kategori
                ORDER BY sayi DESC
                LIMIT 5
                """,
                (bir_hafta_once.isoformat(),),
            ).fetchall()
        return HaftalikRapor(
            baslangic_tarihi=bir_hafta_once.strftime("%d.%m.%Y"),
            bitis_tarihi=simdi.strftime("%d.%m.%Y"),
            toplam_soru=toplam,
            cevaplanan_soru=cevaplanan,
            cevapsiz_soru=max(0, toplam - cevaplanan),
            bekleyen_geri_bildirim=bekleyen,
            ortalama_guven_skoru=round(float(ortalama_skor), 4),
            en_cok_sorulan_kategoriler=[
                (str(satir[0]), int(satir[1])) for satir in kategoriler
            ],
        )

    async def haftalik_raporu_gonder(self) -> bool:
        if not self.aktif:
            gunlukleyici.info("E-posta raporlama devre disi")
            return False
        if not self.alici.strip():
            gunlukleyici.warning("E-posta alici adresi tanimlanmamis")
            return False
        rapor = await asyncio.to_thread(self.haftalik_raporu_hazirla)
        try:
            await asyncio.to_thread(self._eposta_gonder, rapor)
            gunlukleyici.info(
                "Haftalik rapor e-postasi gonderildi",
                extra={
                    "alici": self.alici,
                    "toplam_soru": rapor.toplam_soru,
                },
            )
            return True
        except (OSError, smtplib.SMTPException) as hata:
            gunlukleyici.error(
                "Haftalik rapor e-postasi gonderilemedi: %s",
                type(hata).__name__,
            )
            return False

    def _eposta_gonder(self, rapor: HaftalikRapor) -> None:
        mesaj = MIMEMultipart("alternative")
        mesaj["Subject"] = (
            f"UYDS Asistani Haftalik Rapor - {rapor.baslangic_tarihi}"
        )
        mesaj["From"] = self.kullanici or "rapor@uydu.gov.tr"
        mesaj["To"] = self.alici
        mesaj.attach(
            MIMEText(
                self._duz_metin_icerik_olustur(rapor),
                "plain",
                "utf-8",
            )
        )
        mesaj.attach(
            MIMEText(
                self._html_icerik_olustur(rapor),
                "html",
                "utf-8",
            )
        )
        if self.tls_kullan:
            sunucu = smtplib.SMTP(self.smtp_sunucu, self.smtp_port, timeout=15)
            sunucu.starttls()
        else:
            sunucu = smtplib.SMTP(self.smtp_sunucu, self.smtp_port, timeout=15)
        try:
            if self.kullanici.strip() and self.sifre:
                sunucu.login(self.kullanici, self.sifre)
            sunucu.send_message(mesaj)
        finally:
            sunucu.quit()

    def _duz_metin_icerik_olustur(self, rapor: HaftalikRapor) -> str:
        satirlar = [
            "UYDS Asistani Haftalik Rapor",
            "=" * 35,
            "",
            f"Rapor Donemi: {rapor.baslangic_tarihi} - "
            f"{rapor.bitis_tarihi}",
            "",
            "Genel Istatistikler:",
            f"  Toplam Soru: {rapor.toplam_soru}",
            f"  Cevaplanan: {rapor.cevaplanan_soru}",
            f"  Cevapsiz: {rapor.cevapsiz_soru}",
            f"  Bekleyen Geri Bildirim: {rapor.bekleyen_geri_bildirim}",
            f"  Ortalama Guven Skoru: {rapor.ortalama_guven_skoru:.4f}",
            "",
        ]
        if rapor.en_cok_sorulan_kategoriler:
            satirlar.append("En Cok Sorulan Kategoriler:")
            for kategori, sayi in rapor.en_cok_sorulan_kategoriler:
                satirlar.append(f"  {kategori}: {sayi}")
        return "\n".join(satirlar)

    def _html_icerik_olustur(self, rapor: HaftalikRapor) -> str:
        satirlar = [
            "<!DOCTYPE html>",
            "<html><head><meta charset='utf-8'>",
            "<style>",
            "body{font-family:Arial,sans-serif;margin:2em;color:#333}",
            "h1{color:#2c3e50}",
            "table{border-collapse:collapse;width:60%;margin-top:1em}",
            "td,th{border:1px solid #ddd;padding:8px;text-align:left}",
            "th{background-color:#e9edf2}",
            "</style></head><body>",
            "<h1>UYDS Asistani Haftalik Rapor</h1>",
            "<p><strong>Donem:</strong> "
            f"{rapor.baslangic_tarihi} - {rapor.bitis_tarihi}</p>",
            "<h2>Genel Istatistikler</h2>",
            "<table>",
            "<tr><th>Metrik</th><th>Deger</th></tr>",
            f"<tr><td>Toplam Soru</td><td>{rapor.toplam_soru}</td></tr>",
            "<tr><td>Cevaplanan</td>"
            f"<td>{rapor.cevaplanan_soru}</td></tr>",
            "<tr><td>Cevapsiz</td>"
            f"<td>{rapor.cevapsiz_soru}</td></tr>",
            "<tr><td>Bekleyen Geri Bildirim</td>"
            f"<td>{rapor.bekleyen_geri_bildirim}</td></tr>",
            "<tr><td>Ortalama Guven Skoru</td>"
            f"<td>{rapor.ortalama_guven_skoru:.4f}</td></tr>",
            "</table>",
        ]
        if rapor.en_cok_sorulan_kategoriler:
            satirlar.append("<h2>En Cok Sorulan Kategoriler</h2>")
            satirlar.append("<table>")
            satirlar.append(
                "<tr><th>Kategori</th><th>Soru Sayisi</th></tr>"
            )
            for kategori, sayi in rapor.en_cok_sorulan_kategoriler:
                satirlar.append(
                    f"<tr><td>{kategori}</td><td>{sayi}</td></tr>"
                )
            satirlar.append("</table>")
        satirlar.append("</body></html>")
        return "\n".join(satirlar)

    async def _zamanlanmis_rapor_gorevi(self) -> None:
        while True:
            simdi = datetime.now()
            gun_eslesmesi = (
                simdi.strftime("%A").lower()
                == konfigurasyon.EPOSTA_RAPOR_GUNU
            )
            hedef_saat, hedef_dakika = map(
                int,
                konfigurasyon.EPOSTA_RAPOR_SAATI.split(":"),
            )
            hedef = simdi.replace(
                hour=hedef_saat,
                minute=hedef_dakika,
                second=0,
                microsecond=0,
            )
            if simdi >= hedef:
                hedef += timedelta(days=1)
            bekleme_suresi = (hedef - simdi).total_seconds()
            await asyncio.sleep(bekleme_suresi)
            if gun_eslesmesi or True:
                await self.haftalik_raporu_gonder()

    def periyodik_raporlama_baslat(self) -> asyncio.Task | None:
        if not self.aktif:
            return None
        return asyncio.create_task(self._zamanlanmis_rapor_gorevi())