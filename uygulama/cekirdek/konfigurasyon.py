import os
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Konfigurasyon(BaseSettings):
    DEEPSEEK_API_ANAHTARI: str = Field(default="")
    DEEPSEEK_API_ANAHTAR_DOSYASI: str = Field(default="")
    DEEPSEEK_API_ADRESI: str = Field(
        default="https://api.deepseek.com/chat/completions"
    )
    DEEPSEEK_MODEL_ADI: str = Field(default="deepseek-v4-pro", min_length=1)
    DEEPSEEK_ZAMAN_ASIMI_SANIYE: float = Field(default=120.0, gt=0, le=600)
    DEEPSEEK_YENIDEN_DENEME_SAYISI: int = Field(default=2, ge=0, le=5)
    DEEPSEEK_YENIDEN_DENEME_TABAN_SANIYE: float = Field(
        default=0.5,
        ge=0,
        le=10,
    )
    DEEPSEEK_KAYNAK_SAYISI: int = Field(default=5, gt=0, le=10)
    DEEPSEEK_KAYNAK_MAKS_KARAKTER: int = Field(
        default=6000,
        ge=500,
        le=20000,
    )
    DEEPSEEK_IZINLI_ALAN_ADLARI: str = Field(default="api.deepseek.com")
    DEEPSEEK_YANIT_MAKS_KARAKTER: int = Field(
        default=32768,
        gt=0,
        le=1000000,
    )
    DEEPSEEK_AKIS_MAKS_SANIYE: float = Field(default=180, gt=0, le=900)
    VERITABANI_YOLU: str = Field(default="veriler/veri_deposu.db")
    VERITABANI_SIFRELEME_ANAHTARI: str = Field(min_length=32)
    GUVEN_ESIGI: float = Field(default=0.70, ge=0, le=1)
    VEKTOR_MODEL_ADI: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2")
    VEKTOR_MODEL_YOLU: str = Field(
        default="modeller/paraphrase-multilingual-MiniLM-L12-v2"
    )
    VEKTOR_BOYUTU: int = Field(default=384, gt=0)
    VEKTOR_TOPLU_ISLEM_BOYUTU: int = Field(default=32, gt=0, le=512)
    ES_ANLAMLILAR_YOLU: str = Field(default="veriler/es_anlamlilar.json")
    JWT_GIZLI_ANAHTARI: str = Field(min_length=32)
    JWT_ALGORITMASI: str = Field(default="HS256")
    JWT_OMRU_DAKIKA: int = Field(default=30)
    JWT_YENILEME_OMRU_GUN: int = Field(default=7, gt=0, le=90)
    JWT_ANAHTAR_KIMLIGI: str = Field(default="ana-1", min_length=1, max_length=64)
    JWT_ONCEKI_GIZLI_ANAHTAR: str = Field(default="")
    JWT_ONCEKI_ANAHTAR_KIMLIGI: str = Field(default="", max_length=64)
    YONETICI_ISTEK_IMZA_ANAHTARI: str = Field(default="")
    YONETICI_IMZA_ZAMAN_PENCERESI_SANIYE: int = Field(
        default=300,
        gt=0,
        le=900,
    )
    VARSAYILAN_YONETICI_SIFRESI: str = Field(min_length=12)
    ISTEK_SINIRI: int = Field(default=100, gt=0)
    ISTEK_PENCERESI_SANIYE: int = Field(default=60, gt=0)
    UYGULAMA_PORT: int = Field(default=8000, ge=1, le=65535)
    MESAJ_MAKS_KARAKTER: int = Field(default=2000, gt=0)
    DEEPSEEK_MAKS_TOKEN: int = Field(default=4096, gt=0)
    GUNLUK_MESAJ_KOTASI: int = Field(default=500, gt=0)
    OTURUM_MAKS_MESAJ: int = Field(default=50, gt=0)
    OTURUM_TTL_DAKIKA: int = Field(default=30, gt=0, le=1440)
    OTURUM_MAKS_SAYI: int = Field(default=1000, gt=0, le=100000)
    ESZAMANLI_AKIS_MAKS_SAYI: int = Field(default=10, gt=0, le=1000)
    UYGULAMA_WORKER_SAYISI: int = Field(default=1, ge=1, le=1)
    GUVENLIK_BAKIM_ARALIGI_SAAT: int = Field(default=6, gt=0, le=168)
    ISTEK_GOVDE_MAKS_BOYUT: int = Field(default=1048576, gt=0)
    DOSYA_YUKLEME_MAKS_BOYUT: int = Field(default=52428800, gt=0)
    LOG_SEVIYESI: str = Field(default="INFO")
    ORTAM_PROFILI: str = Field(default="prod")
    RRF_K: int = Field(default=60, gt=0)
    FTS_ADAY_SAYISI: int = Field(default=50, gt=0, le=500)
    VEKTOR_ADAY_SAYISI: int = Field(default=50, gt=0, le=500)
    RRF_ADAY_SAYISI: int = Field(default=20, gt=0, le=100)
    ALTERNATIF_SORU_ADAY_SAYISI: int = Field(default=5, gt=0, le=100)
    ALTERNATIF_SORU_BENZERLIK_ESIGI: float = Field(
        default=0.70,
        ge=0,
        le=1,
    )
    YENIDEN_SIRALAMA_ETKIN: bool = Field(default=False)
    YENIDEN_SIRALAMA_MODEL_YOLU: str = Field(
        default="modeller/mmarco-mMiniLMv2-L12-H384-v1"
    )
    YENIDEN_SIRALAMA_ADAY_SAYISI: int = Field(default=10, gt=0, le=100)
    YENIDEN_SIRALAMA_TOPLU_ISLEM_BOYUTU: int = Field(
        default=8,
        gt=0,
        le=128,
    )
    YENIDEN_SIRALAMA_MAKS_TOKEN: int = Field(default=512, ge=64, le=512)
    FTS_SORU_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    FTS_CEVAP_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    FTS_KATEGORI_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    FTS_HARICI_KOD_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    FTS_MODUL_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    FTS_ARAMA_METNI_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    VERI_SAKLAMA_SURESI_AY: int = Field(default=6, gt=0, le=120)
    VERI_TEMIZLIK_AKTIF: bool = Field(default=True)
    VERI_TEMIZLIK_SAATI: str = Field(default="02:00", min_length=1, max_length=5)
    VERI_TEMIZLIK_PARTI_BOYUTU: int = Field(default=1000, gt=0, le=10000)
    PII_MASKELEME_AKTIF: bool = Field(default=True)
    KULLANICI_SORULARINI_GIZLE: bool = Field(default=False)
    FALLBACK_KAYNAK_SAYISI: int = Field(default=3, gt=0, le=10)
    NIYET_SINIFLANDIRMA_AKTIF: bool = Field(default=True)
    NIYET_GUVEN_ESIGI: float = Field(default=0.80, ge=0, le=1)
    NIYET_EYLEMLERI_YOLU: str = Field(default="veriler/niyet_eylemleri.json")
    EPOSTA_RAPORLAMA_AKTIF: bool = Field(default=False)
    EPOSTA_SMTP_SUNUCU: str = Field(default="smtp.kurum.gov.tr")
    EPOSTA_SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    EPOSTA_TLS_KULLAN: bool = Field(default=True)
    EPOSTA_KULLANICI: str = Field(default="")
    EPOSTA_SIFRE: str = Field(default="")
    EPOSTA_ALICI: str = Field(default="")
    EPOSTA_RAPOR_GUNU: str = Field(default="pazartesi")
    EPOSTA_RAPOR_SAATI: str = Field(default="09:00")
    BELGE_DIZINLERI: str = Field(default="veriler/belgeler/,veriler/mevzuat/")
    BELGE_TARAMA_RECURSIVE: bool = Field(default=True)
    BELGE_DESTEK_FORMATLAR: str = Field(default="xlsx,pdf,docx,html")
    BELGE_VARSAYILAN_YETKI: int = Field(default=0, ge=0, le=4)
    BELGE_MAKS_BOYUT_MB: int = Field(default=50, gt=0, le=500)
    BELGE_ACL_AKTIF: bool = Field(default=True)
    RBAC_YETKI_ESLEME: str = Field(default='{"yonetici":3,"editor":2,"kullanici":0}')
    BELGE_SURUMLE_AKTIF: bool = Field(default=True)
    BELGE_MAKS_SURUM_SAKLA: int = Field(default=10, gt=0, le=100)
    PDF_TABLO_MOTORU: str = Field(default="auto")
    PDF_TABLO_MIN_GUVEN: float = Field(default=0.7, ge=0, le=1)
    SENKRONIZASYON_AKTIF: bool = Field(default=True)
    SENKRONIZASYON_SAATI: str = Field(default="03:00")
    ARTIMSAL_SENKRONIZASYON_DAKIKA: int = Field(default=30, gt=0, le=1440)
    SENKRONIZASYON_ZAMAN_ASIMI_SANIYE: int = Field(default=3600, gt=0, le=86400)
    SENKRONIZASYON_MAKS_HATA: int = Field(default=5, ge=0, le=100)
    YAPISAL_PARCALAMA_AKTIF: bool = Field(default=True)
    PARCALAMA_MAKS_TOKEN: int = Field(default=512, gt=0, le=4096)
    PARCALAMA_ORTAK_TOKEN: int = Field(default=64, ge=0, le=512)
    GRAF_AKTIF: bool = Field(default=True)
    NEO4J_AKTIF: bool = Field(default=False)
    GRAF_KOMSULUK_DERINLIK: int = Field(default=2, ge=1, le=5)
    GRAF_BONUS_SKORU: float = Field(default=0.15, ge=0, le=1)
    GRAF_KAVRAM_STRATEJISI: str = Field(default="hafif")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("JWT_GIZLI_ANAHTARI", "VERITABANI_SIFRELEME_ANAHTARI")
    @classmethod
    def gizli_anahtari_dogrula(cls, deger: str) -> str:
        kucuk_deger = deger.lower()
        yasakli_parcalar = ("varsayilan", "buraya_yazin", "change_me", "ornek")
        if any(parca in kucuk_deger for parca in yasakli_parcalar):
            raise ValueError("Guvenli ve benzersiz bir gizli anahtar kullanilmalidir")
        return deger

    @field_validator("VARSAYILAN_YONETICI_SIFRESI")
    @classmethod
    def yonetici_sifresini_dogrula(cls, deger: str) -> str:
        kucuk_deger = deger.lower()
        yasakli_parcalar = ("yonetici123", "buraya_yazin")
        if any(parca in kucuk_deger for parca in yasakli_parcalar):
            raise ValueError("Varsayilan yonetici sifresi guclu ve benzersiz olmalidir")
        return deger

    @field_validator("LOG_SEVIYESI")
    @classmethod
    def log_seviyesini_dogrula(cls, deger: str) -> str:
        buyuk_deger = deger.upper()
        if buyuk_deger not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Gecersiz log seviyesi")
        return buyuk_deger

    @field_validator("ORTAM_PROFILI")
    @classmethod
    def ortam_profilini_dogrula(cls, deger: str) -> str:
        kucuk_deger = deger.lower()
        if kucuk_deger not in {"dev", "test", "prod"}:
            raise ValueError("Gecersiz ortam profili")
        return kucuk_deger

    @field_validator("DEEPSEEK_API_ADRESI")
    @classmethod
    def deepseek_api_adresini_dogrula(cls, deger: str) -> str:
        ayrismis = urlparse(deger)
        yerel_adresler = {"localhost", "127.0.0.1", "::1"}
        guvenli_mi = ayrismis.scheme == "https"
        yerel_mi = ayrismis.scheme == "http" and ayrismis.hostname in yerel_adresler
        adres_bilesenleri_gecerli = (
            ayrismis.hostname is not None
            and ayrismis.username is None
            and ayrismis.password is None
            and not ayrismis.query
            and not ayrismis.fragment
        )
        if not adres_bilesenleri_gecerli or not (guvenli_mi or yerel_mi):
            raise ValueError(
                "DeepSeek API adresi HTTPS veya yerel HTTP adresi olmalidir"
            )
        return deger.rstrip("/")

    @model_validator(mode="after")
    def deepseek_uretim_hedefini_dogrula(self) -> "Konfigurasyon":
        izinli_alan_adlari = {
            alan_adi.strip().lower()
            for alan_adi in self.DEEPSEEK_IZINLI_ALAN_ADLARI.split(",")
            if alan_adi.strip()
        }
        if not izinli_alan_adlari:
            raise ValueError("En az bir DeepSeek alan adi izinli olmalidir")
        hedef_alan_adi = urlparse(self.DEEPSEEK_API_ADRESI).hostname
        if (
            self.ORTAM_PROFILI == "prod"
            and hedef_alan_adi not in izinli_alan_adlari
        ):
            raise ValueError("Uretim DeepSeek API alan adi izinli listede degil")
        return self

    @model_validator(mode="after")
    def jwt_rotasyonunu_dogrula(self) -> "Konfigurasyon":
        onceki_anahtar = self.JWT_ONCEKI_GIZLI_ANAHTAR.strip()
        onceki_kimlik = self.JWT_ONCEKI_ANAHTAR_KIMLIGI.strip()
        if bool(onceki_anahtar) != bool(onceki_kimlik):
            raise ValueError(
                "Onceki JWT anahtari ve anahtar kimligi birlikte verilmelidir"
            )
        if onceki_anahtar and len(onceki_anahtar) < 32:
            raise ValueError("Onceki JWT gizli anahtari en az 32 karakter olmalidir")
        if onceki_kimlik == self.JWT_ANAHTAR_KIMLIGI:
            raise ValueError("JWT anahtar kimlikleri benzersiz olmalidir")
        imza_anahtari = self.YONETICI_ISTEK_IMZA_ANAHTARI.strip()
        if imza_anahtari and len(imza_anahtari) < 32:
            raise ValueError(
                "Yonetici istek imza anahtari en az 32 karakter olmalidir"
            )
        return self


def env_dosyasindan_ortam_profilini_al() -> str:
    env_yolu = Path(".env")
    if not env_yolu.is_file():
        return "prod"
    for satir in env_yolu.read_text(encoding="utf-8").splitlines():
        temiz_satir = satir.strip()
        if temiz_satir.startswith("ORTAM_PROFILI="):
            deger = temiz_satir.split("=", 1)[1].strip().strip("\"'")
            return deger or "prod"
    return "prod"


def ortam_dosyalarini_al() -> tuple[str, ...]:
    ortam_profili = os.getenv(
        "ORTAM_PROFILI",
        env_dosyasindan_ortam_profilini_al(),
    ).lower()
    if ortam_profili not in {"dev", "test", "prod"}:
        raise ValueError("Gecersiz ORTAM_PROFILI degeri")
    return ".env", f".env.{ortam_profili}"


konfigurasyon = Konfigurasyon(_env_file=ortam_dosyalarini_al())
