from pydantic_settings import BaseSettings
from pydantic import Field


class Konfigurasyon(BaseSettings):
    DEEPSEEK_API_ANAHTARI: str = Field(default="")
    VERITABANI_YOLU: str = Field(default="veriler/veri_deposu.db")
    GUVEN_ESIGI: float = Field(default=0.70)
    VEKTOR_MODEL_ADI: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2")
    JWT_GIZLI_ANAHTARI: str = Field(default="varsayilan_gizli_anahtar_degistir")
    JWT_ALGORITMASI: str = Field(default="HS256")
    JWT_OMRU_DAKIKA: int = Field(default=30)
    ISTEK_SINIRI: int = Field(default=100)
    ISTEK_PENCERESI_SANIYE: int = Field(default=60)
    UYGULAMA_PORT: int = Field(default=8000)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


konfigurasyon = Konfigurasyon()