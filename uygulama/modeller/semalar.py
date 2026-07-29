from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field, JsonValue, field_validator


def metni_dogrula(deger: str) -> str:
    temiz_deger = deger.strip()
    if any(ord(karakter) < 32 and karakter not in "\n\r\t" for karakter in temiz_deger):
        raise ValueError("Metin kontrol karakteri iceremez")
    return temiz_deger


class KaynakRozeti(BaseModel):
    kaynak_dokuman: str
    kaynak_metni: str


class AramaIstegi(BaseModel):
    soru: str = Field(..., min_length=1, max_length=2000)
    oturum_id: str | None = Field(default=None, min_length=32, max_length=128)

    @field_validator("soru")
    @classmethod
    def soruyu_dogrula(cls, deger: str) -> str:
        return metni_dogrula(deger)


class AramaYaniti(BaseModel):
    soru: str
    cevap: str
    guven_skoru: float
    kaynaklar: list[KaynakRozeti] = Field(default_factory=list)
    islem_suresi_ms: float | None = None


class GeriBildirimIstegi(BaseModel):
    sss_id: int | None = Field(default=None, gt=0)
    kullanici_sorusu: str = Field(min_length=1, max_length=2000)
    verilen_cevap: str = Field(min_length=1, max_length=32768)
    puan: int = Field(..., ge=1, le=5)
    yorum: str | None = Field(default=None, max_length=2000)

    @field_validator("kullanici_sorusu", "verilen_cevap", "yorum")
    @classmethod
    def geri_bildirim_metnini_dogrula(cls, deger: str | None) -> str | None:
        return metni_dogrula(deger) if deger is not None else None


class GeriBildirimYaniti(BaseModel):
    id: int
    durum: str
    mesaj: str


class YoneticiOnayIstegi(BaseModel):
    geri_bildirim_id: int
    islem: str = Field(..., pattern="^(ONAYLA|REDDET)$")


class YoneticiOnayYaniti(BaseModel):
    id: int
    yeni_durum: str
    mesaj: str


class AnalitikVerisi(BaseModel):
    toplam_soru_sayisi: int
    toplam_geri_bildirim_sayisi: int
    ortalama_puan: float
    bekleyen_onay_sayisi: int
    en_cok_sorulan_kategoriler: list[dict[str, JsonValue]] = Field(
        default_factory=list
    )
    cevapsiz_kalan_sorular: list[dict[str, JsonValue]] = Field(
        default_factory=list
    )


class KimlikDogrulamaIstegi(BaseModel):
    kullanici_adi: str = Field(min_length=1, max_length=64, pattern=r"^[\w.-]+$")
    sifre: str = Field(min_length=1, max_length=128)

    @field_validator("kullanici_adi")
    @classmethod
    def kullanici_adini_normalize_et(cls, deger: str) -> str:
        return deger.strip().casefold()


class BelirtecYenilemeIstegi(BaseModel):
    yenileme_belirteci: str = Field(min_length=32, max_length=512)


class CikisIstegi(BaseModel):
    yenileme_belirteci: str = Field(min_length=32, max_length=512)


class BelirtecYaniti(BaseModel):
    erisim_belirteci: str
    yenileme_belirteci: str
    belirtec_turu: str = "bearer"
    rol: str
    erisim_belirteci_omru_saniye: int


class GenelMesajYaniti(BaseModel):
    mesaj: str


class SssOzetKaydi(BaseModel):
    id: int
    kategori: str
    soru: str
    kaynak_dokuman: str | None
    modul: str | None


class SssListesiYaniti(BaseModel):
    kayitlar: list[SssOzetKaydi]
    toplam: int
    sayfa: int
    sayfa_basina: int


class YenidenIndekslemeYaniti(BaseModel):
    fts_kayit_sayisi: int
    vektor_toplam_parca: int
    uretilen_vektor_sayisi: int
    mesaj: str


class Sayfalama(BaseModel):
    sayfa: int = Field(default=1, ge=1)
    sayfa_basina: int = Field(default=20, ge=1, le=100)


class BekleyenGeriBildirim(BaseModel):
    id: int
    sss_id: int | None
    kullanici_sorusu: str
    verilen_cevap: str
    puan: int
    yorum: str | None
    durum: str
    tarih: datetime


class BekleyenGeriBildirimListesi(BaseModel):
    bildirimler: list[BekleyenGeriBildirim]
    toplam: int
    sayfalama: Sayfalama


@dataclass(frozen=True)
class AramaAdayi:
    sss_id: int
    parca_id: int | None
    aday_metni: str
    kaynak_dokuman: str | None
    kaynak_sayfa: str | None
    kaynak_satir: int | None
    fts_sirasi: int | None
    vektor_sirasi: int | None
    rrf_skoru: float
    vektor_benzerlik_skoru: float | None
    yeniden_siralama_skoru: float | None


@dataclass(frozen=True)
class AramaSonucu:
    adaylar: tuple[AramaAdayi, ...]
    gecen_sure_ms: float
    genisletilmis_fts_sorgusu: str
    genisletilen_terim_sayisi: int
    kullanilan_grup_sayisi: int
    fts_aday_sayisi: int
    vektor_aday_sayisi: int
    birlesik_aday_sayisi: int
    gecersiz_vektor_sayisi: int
    yeniden_siralama_etkin: bool
