import os
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Konfigurasyon(BaseSettings):
    DEEPSEEK_API_ANAHTARI: str = Field(default="")
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
    VERITABANI_YOLU: str = Field(default="veriler/veri_deposu.db")
    VERITABANI_SIFRELEME_ANAHTARI: str = Field(min_length=32)
    GUVEN_ESIGI: float = Field(default=0.70)
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
    ISTEK_GOVDE_MAKS_BOYUT: int = Field(default=1048576, gt=0)
    DOSYA_YUKLEME_MAKS_BOYUT: int = Field(default=52428800, gt=0)
    LOG_SEVIYESI: str = Field(default="INFO")
    ORTAM_PROFILI: str = Field(default="prod")
    RRF_K: int = Field(default=60, gt=0)
    FTS_ADAY_SAYISI: int = Field(default=50, gt=0, le=500)
    VEKTOR_ADAY_SAYISI: int = Field(default=50, gt=0, le=500)
    RRF_ADAY_SAYISI: int = Field(default=20, gt=0, le=100)
    FTS_SORU_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    FTS_CEVAP_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    FTS_KATEGORI_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    FTS_HARICI_KOD_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    FTS_MODUL_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)
    FTS_ARAMA_METNI_AGIRLIGI: float = Field(default=1.0, ge=0, le=100)

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
        if kucuk_deger == "yonetici123" or "buraya_yazin" in kucuk_deger:
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
        if not ayrismis.netloc or not (guvenli_mi or yerel_mi):
            raise ValueError(
                "DeepSeek API adresi HTTPS veya yerel HTTP adresi olmalidir"
            )
        return deger.rstrip("/")


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
