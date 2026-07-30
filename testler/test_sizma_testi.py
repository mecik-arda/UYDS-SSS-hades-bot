import asyncio
import time

import httpx
import pytest


TEST_SUNUCUSU = "http://127.0.0.1:8000"
GECERLI_GIRIS = {"kullanici_adi": "yonetici", "sifre": "test_sifresi_12_karakter_minimum"}
YONETICI_GIRIS = {"kullanici_adi": "yonetici", "sifre": "CiYoneticiSifresi-123"}


def _belirtec_al(istemci: httpx.Client, kullanici_adi: str, sifre: str) -> str:
    yanit = istemci.post(
        "/api/v1/kimlik-dogrulama/giris",
        json={"kullanici_adi": kullanici_adi, "sifre": sifre},
    )
    if yanit.status_code != 200:
        raise RuntimeError(f"Giris basarisiz: {yanit.status_code} {yanit.text}")
    return yanit.json()["erisim_belirteci"]


def _yetki_basligi(belirtec: str) -> dict:
    return {"Authorization": f"Bearer {belirtec}"}


XSS_PAYLOADLARI = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert(1)",
    "%3Cscript%3Ealert(1)%3C/script%3E",
    "&#x3C;script&#x3E;alert(1)&#x3C;/script&#x3E;",
    "<ScRiPt>alert(1)</ScRiPt>",
]


SQLI_PAYLOADLARI = [
    "' OR '1'='1",
    "1' OR '1'='1' --",
    "admin'--",
    "' UNION SELECT * FROM kullanicilar --",
    "1; DROP TABLE sss_kayitlari; --",
    "' OR 1=1 /*",
]

KOMUT_ENJEKSIYON_PAYLOADLARI = [
    "127.0.0.1\"; rm -rf /",
    "$(whoami)",
    "`cat /etc/passwd`",
    "; ls -la /",
    "| dir C:\\",
]


class TestOwaspSizma:
    def test_xss_payloadlari_guvenli_bicimde_reddedilir(self):
        with httpx.Client(base_url=TEST_SUNUCUSU, timeout=10) as istemci:
            belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
            for payload in XSS_PAYLOADLARI:
                yanit = istemci.post(
                    "/api/v1/arama",
                    json={"soru": payload},
                    headers=_yetki_basligi(belirtec),
                )
                assert yanit.status_code in (200, 422), (
                    f"XSS payload beklenmeyen durum: {yanit.status_code}"
                )

    def test_sqli_payloadlari_veritabanina_ulasamaz(self):
        with httpx.Client(base_url=TEST_SUNUCUSU, timeout=10) as istemci:
            belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
            for payload in SQLI_PAYLOADLARI:
                yanit = istemci.post(
                    "/api/v1/arama",
                    json={"soru": payload},
                    headers=_yetki_basligi(belirtec),
                )
                assert yanit.status_code not in (500,), (
                    f"SQLi payload 500 hatasi uretti: {payload}"
                )

    def test_komut_enjeksiyonu_payloadlari_pydantic_tarafindan_reddedilir(self):
        with httpx.Client(base_url=TEST_SUNUCUSU, timeout=10) as istemci:
            belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
            for payload in KOMUT_ENJEKSIYON_PAYLOADLARI:
                yanit = istemci.post(
                    "/api/v1/arama",
                    json={"soru": payload},
                    headers=_yetki_basligi(belirtec),
                )
                assert yanit.status_code in (200, 422), (
                    f"Komut enjeksiyonu beklenmeyen durum: {yanit.status_code}"
                )

    def test_jwt_manipulasyonu_reddedilir(self):
        with httpx.Client(base_url=TEST_SUNUCUSU, timeout=10) as istemci:
            sahte_belirtec = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ5b25ldGljaSIsInJvbCI6IllPTkVUSUNJIn0.fake"
            yanit = istemci.post(
                "/api/v1/arama",
                json={"soru": "test"},
                headers=_yetki_basligi(sahte_belirtec),
            )
            assert yanit.status_code == 401, (
                f"JWT manipulasyonu reddedilmedi: {yanit.status_code}"
            )

    def test_idor_baska_kullanici_oturumuna_erisemez(self):
        with httpx.Client(base_url=TEST_SUNUCUSU, timeout=10) as istemci:
            belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
            yanit = istemci.post(
                "/api/v1/arama",
                json={"soru": "test", "oturum_id": "bas_kasinin_oturumu_12345678901234567890123456789012"},
                headers=_yetki_basligi(belirtec),
            )
            assert yanit.status_code == 404, (
                f"IDOR korumasi yok: {yanit.status_code}"
            )

    def test_dogrulama_hatasi_girdi_geri_yansitmaz(self):
        with httpx.Client(base_url=TEST_SUNUCUSU, timeout=10) as istemci:
            yanit = istemci.post(
                "/api/v1/kimlik-dogrulama/giris",
                json={"kullanici_adi": "<script>alert(1)</script>", "sifre": "test"},
            )
            assert yanit.status_code == 422, (
                f"Girdi validasyonu calismiyor: {yanit.status_code}"
            )


class TestModelDoS:
    def test_maksimum_karakter_sinirinda_embedding_zaman_asimi_olmaz(self):
        with httpx.Client(base_url=TEST_SUNUCUSU, timeout=15) as istemci:
            belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
            yanit = istemci.post(
                "/api/v1/arama",
                json={"soru": "A" * 1999},
                headers=_yetki_basligi(belirtec),
            )
            assert yanit.status_code == 200, (
                f"Maksimum karakter sınırı embedding hatası: {yanit.status_code}"
            )

    def test_kontrol_karakterlerini_pydantic_reddeder(self):
        with httpx.Client(base_url=TEST_SUNUCUSU, timeout=10) as istemci:
            belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
            yanit = istemci.post(
                "/api/v1/arama",
                json={"soru": "test\x00\x01\x02"},
                headers=_yetki_basligi(belirtec),
            )
            assert yanit.status_code == 422, (
                f"Kontrol karakterleri reddedilmedi: {yanit.status_code}"
            )


class TestRateLimiting:
    def test_hizli_istekler_429_dondurur(self):
        with httpx.Client(base_url=TEST_SUNUCUSU, timeout=5) as istemci:
            belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
            yanit_kodlari = []
            for _ in range(50):
                yanit = istemci.post(
                    "/api/v1/arama",
                    json={"soru": "test"},
                    headers=_yetki_basligi(belirtec),
                )
                yanit_kodlari.append(yanit.status_code)
                if 429 in yanit_kodlari:
                    break
                time.sleep(0.01)
            assert 429 in yanit_kodlari, (
                f"Rate limiting 429 dondurmedi. Kodlar: {set(yanit_kodlari)}"
            )


class TestEsZamanliAkis:
    @pytest.mark.asyncio
    async def test_es_zamanli_akis_semafo_uygulanir(self):
        async def tek_istek_gonder(istemci: httpx.AsyncClient, belirtec: str) -> int:
            try:
                yanit = await istemci.post(
                    "/api/v1/arama",
                    json={"soru": "uzun bir test sorusu"},
                    headers=_yetki_basligi(belirtec),
                    timeout=30,
                )
                return yanit.status_code
            except httpx.TimeoutException:
                return 504

        async with httpx.AsyncClient(base_url=TEST_SUNUCUSU, timeout=30) as istemci:
            belirtec = _belirtec_al(httpx.Client(base_url=TEST_SUNUCUSU, timeout=10), **GECERLI_GIRIS)
            gorevler = [tek_istek_gonder(istemci, belirtec) for _ in range(10)]
            sonuclar = await asyncio.gather(*gorevler)
            basarili = sum(1 for k in sonuclar if k == 200)
            assert basarili > 0, (
                f"Es zamanli akis: hicbiri basarili olmadi. Sonuclar: {sonuclar}"
            )


class TestSqliteThreadGuvenligi:
    def test_es_zamanli_yazma_bombardimani_veritabanini_kitlemez(
        self, gecici_veritabani
    ):
        import threading
        import sqlite3

        hatalar = []

        def hizli_yaz(veritabani_yolu: str) -> None:
            try:
                baglanti = sqlite3.connect(str(veritabani_yolu))
                baglanti.execute("PRAGMA journal_mode=WAL")
                for i in range(20):
                    baglanti.execute(
                        "INSERT INTO sss_kayitlari (kategori, soru, cevap, durum) VALUES (?, ?, ?, ?)",
                        ("Test", f"Soru {i}", f"Cevap {i}", "aktif"),
                    )
                    baglanti.commit()
            except sqlite3.OperationalError as hata:
                hatalar.append(str(hata))
            finally:
                baglanti.close()

        threadler = [
            threading.Thread(target=hizli_yaz, args=(str(gecici_veritabani),))
            for _ in range(5)
        ]
        for t in threadler:
            t.start()
        for t in threadler:
            t.join()
        assert not hatalar, f"SQLite thread-safety hatasi: {hatalar}"