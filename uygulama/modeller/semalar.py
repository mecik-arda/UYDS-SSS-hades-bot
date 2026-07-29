from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field, JsonValue


class KaynakRozeti(BaseModel):
    kaynak_dokuman: str
    kaynak_metni: str


class AramaIstegi(BaseModel):
    soru: str = Field(..., min_length=1, max_length=2000)
    oturum_id: str | None = None


class AramaYaniti(BaseModel):
    soru: str
    cevap: str
    guven_skoru: float
    kaynaklar: list[KaynakRozeti] = Field(default_factory=list)
    islem_suresi_ms: float | None = None


class GeriBildirimIstegi(BaseModel):
    sss_id: int | None = None
    kullanici_sorusu: str
    verilen_cevap: str
    puan: int = Field(..., ge=1, le=5)
    yorum: str | None = None


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
    kullanici_adi: str
    sifre: str


class BelirtecYaniti(BaseModel):
    erisim_belirteci: str
    belirtec_turu: str = "bearer"
    rol: str


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
