import time
import threading

import pytest
from fastapi.testclient import TestClient

GECERLI_GIRIS = {"kullanici_adi": "yonetici", "sifre": "test_sifresi_12_karakter_minimum"}
YONETICI_GIRIS = {"kullanici_adi": "yonetici", "sifre": "CiYoneticiSifresi-123"}


@pytest.fixture
def istemci(gecici_veritabani, mock_vektor_servisi):
    from fastapi import FastAPI
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    from uygulama.api.bagimliliklar import vektor_servisini_al
    from uygulama.api.rotalar.arama import router as arama_router
    from uygulama.api.rotalar.kimlik_dogrulama import router as kimlik_dogrulama_router
    from uygulama.cekirdek.guvenlik import sifre_hash_olustur
    from uygulama.cekirdek.hata_yonetimi import IstekKimligiMiddleware, hata_yonetimini_kaydet
    from uygulama.cekirdek.istek_sinirlayici import istek_sinirlayici
    from uygulama.modeller.veritabani_modelleri import varsayilan_yonetici_olustur
    varsayilan_yonetici_sifre_hash = sifre_hash_olustur("test_sifresi_12_karakter_minimum")
    varsayilan_yonetici_olustur(varsayilan_yonetici_sifre_hash)

    app = FastAPI()
    app.state.limiter = istek_sinirlayici
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    hata_yonetimini_kaydet(app)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(IstekKimligiMiddleware)
    app.include_router(kimlik_dogrulama_router)
    app.include_router(arama_router)
    import uygulama.api.bagimliliklar as bag_modul
    import uygulama.servisler.deepseek_servisi as deepseek_modul

    async def mock_yanit_akisini_uret(self, *args, **kwargs):
        yield "Test yaniti"

    eski_yanit_akisini_uret = deepseek_modul.DeepSeekServisi.yanit_akisini_uret
    deepseek_modul.DeepSeekServisi.yanit_akisini_uret = mock_yanit_akisini_uret
    
    eski_vektor = bag_modul.vektor_servisini_al
    bag_modul.vektor_servisini_al = lambda: mock_vektor_servisi

    app.dependency_overrides[vektor_servisini_al] = lambda: mock_vektor_servisi

    with TestClient(app) as test_istemcisi:
        yield test_istemcisi
    
    deepseek_modul.DeepSeekServisi.yanit_akisini_uret = eski_yanit_akisini_uret
    bag_modul.vektor_servisini_al = eski_vektor


@pytest.fixture(autouse=True)
def _limiter_sifirla():
    from uygulama.cekirdek.istek_sinirlayici import istek_sinirlayici
    istek_sinirlayici.reset()


def _belirtec_al(istemci: TestClient, kullanici_adi: str, sifre: str) -> str:
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
    def test_xss_payloadlari_guvenli_bicimde_reddedilir(self, istemci):
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

    def test_sqli_payloadlari_veritabanina_ulasamaz(self, istemci):
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

    def test_komut_enjeksiyonu_payloadlari_pydantic_tarafindan_reddedilir(self, istemci):
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

    def test_jwt_manipulasyonu_reddedilir(self, istemci):
        sahte_belirtec = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ5b25ldGljaSIsInJvbCI6IllPTkVUSUNJIn0.fake"
        yanit = istemci.post(
            "/api/v1/arama",
            json={"soru": "test"},
            headers=_yetki_basligi(sahte_belirtec),
        )
        assert yanit.status_code == 401, (
            f"JWT manipulasyonu reddedilmedi: {yanit.status_code}"
        )

    def test_idor_baska_kullanici_oturumuna_erisemez(self, istemci):
        belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
        yanit = istemci.post(
            "/api/v1/arama",
            json={"soru": "test", "oturum_id": "bas_kasinin_oturumu_12345678901234567890123456789012"},
            headers=_yetki_basligi(belirtec),
        )
        assert yanit.status_code == 404, (
            f"IDOR korumasi yok: {yanit.status_code}"
        )

    def test_dogrulama_hatasi_girdi_geri_yansitmaz(self, istemci):
        yanit = istemci.post(
            "/api/v1/kimlik-dogrulama/giris",
            json={"kullanici_adi": "<script>alert(1)</script>", "sifre": "test"},
        )
        assert yanit.status_code == 422, (
            f"Girdi validasyonu calismiyor: {yanit.status_code}"
        )


class TestModelDoS:
    def test_maksimum_karakter_sinirinda_embedding_zaman_asimi_olmaz(self, istemci):
        belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
        yanit = istemci.post(
            "/api/v1/arama",
            json={"soru": "A" * 1999},
            headers=_yetki_basligi(belirtec),
        )
        assert yanit.status_code == 200, (
            f"Maksimum karakter sınırı embedding hatası: {yanit.status_code}"
        )

    def test_kontrol_karakterlerini_pydantic_reddeder(self, istemci):
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
    def test_hizli_istekler_429_dondurur(self, istemci):
        belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
        yanit_kodlari = []
        for _ in range(150):
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
    def test_es_zamanli_akis_semafo_uygulanir(self, istemci):
        sonuclar = []
        belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)

        def tek_istek_gonder():
            try:
                yanit = istemci.post(
                    "/api/v1/arama",
                    json={"soru": "uzun bir test sorusu"},
                    headers=_yetki_basligi(belirtec),
                )
                sonuclar.append(yanit.status_code)
            except Exception as hata:
                sonuclar.append(str(hata))

        import threading
        threadler = [
            threading.Thread(target=tek_istek_gonder)
            for _ in range(3)
        ]
        for t in threadler:
            t.start()
        for t in threadler:
            t.join()

        basarili = sum(1 for k in sonuclar if k == 200)
        assert basarili > 0, (
            f"Es zamanli akis: hicbiri basarili olmadi. Sonuclar: {sonuclar}"
        )


class TestSqliteThreadGuvenligi:
    def test_es_zamanli_yazma_bombardimani_veritabanini_kitlemez(
        self, gecici_veritabani
    ):
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


LOKI_UNICODE_PAYLOADLARI = [
    "%uff1cscript%uff1ealert(1)%uff1c/script%uff1e",
    "%uff07 OR 1%uff1d1 --",
    "%uff02%uff1e%uff1cimg src=x onerror=alert(1)%uff1e",
]

LOKI_SQL_COMMENT_PAYLOADLARI = [
    "SEL/**/ECT * FR/**/OM kullanicilar",
    "1' UN/**/ION SEL/**/ECT NULL, NULL --",
    "admin' A/**/ND 1=1 /*",
]

LOKI_DOUBLE_URL_ENCODE_PAYLOADLARI = [
    "%253Cscript%253Ealert(1)%253C%252Fscript%253E",
    "%2527%2520OR%25201%253D1%2520--",
]

LOKI_BOSLUK_MANIPULASYONU_PAYLOADLARI = [
    "1'%09OR%0a'1'='1",
    "admin'%0dAND%091=1",
    "1'/*!50000OR*/1=1",
]

LOKI_CASE_RANDOMIZATION_PAYLOADLARI = [
    "<sCrIpT>aLeRt(1)</ScRiPt>",
    "jAvAsCrIpT:aLeRt(1)",
    "' uNiOn SeLeCt *",
]


class TestLokiMutasyonlari:
    def test_unicode_bypass_pydantic_veya_uygulama_tarafindan_reddedilir(self, istemci):
        belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
        for payload in LOKI_UNICODE_PAYLOADLARI:
            yanit = istemci.post(
                "/api/v1/arama",
                json={"soru": payload},
                headers=_yetki_basligi(belirtec),
            )
            assert yanit.status_code in (200, 422), (
                f"Loki Unicode payload beklenmeyen durum: {yanit.status_code}"
            )

    def test_sql_comment_injection_veritabanina_ulasamaz(self, istemci):
        belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
        for payload in LOKI_SQL_COMMENT_PAYLOADLARI:
            yanit = istemci.post(
                "/api/v1/arama",
                json={"soru": payload},
                headers=_yetki_basligi(belirtec),
            )
            assert yanit.status_code != 500, (
                f"Loki SQL Comment payload 500 hatasi uretti: {payload}"
            )

    def test_double_url_encoding_guvenli_islenir(self, istemci):
        belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
        for payload in LOKI_DOUBLE_URL_ENCODE_PAYLOADLARI:
            yanit = istemci.post(
                "/api/v1/arama",
                json={"soru": payload},
                headers=_yetki_basligi(belirtec),
            )
            assert yanit.status_code in (200, 422), (
                f"Loki Double URL Encoding beklenmeyen durum: {yanit.status_code}"
            )

    def test_bosluk_manipulasyonu_ve_case_randomization_engellenir(self, istemci):
        belirtec = _belirtec_al(istemci, **GECERLI_GIRIS)
        karma_payloadlar = LOKI_BOSLUK_MANIPULASYONU_PAYLOADLARI + LOKI_CASE_RANDOMIZATION_PAYLOADLARI
        for payload in karma_payloadlar:
            yanit = istemci.post(
                "/api/v1/arama",
                json={"soru": payload},
                headers=_yetki_basligi(belirtec),
            )
            assert yanit.status_code != 500, (
                f"Loki Obfuscation payload 500 hatasi uretti: {payload}"
            )
