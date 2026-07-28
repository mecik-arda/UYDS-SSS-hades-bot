import hashlib
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any

import numpy as np

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.modeller.veritabani_modelleri import tablolari_olustur
from uygulama.servisler.model_guvenligi import yerel_modeli_dogrula

_MODEL_KILIDI = Lock()
_URETIM_KILIDI = Lock()


class VektorModeliHatasi(RuntimeError):
    pass


@dataclass(frozen=True)
class VektorUretimSonucu:
    model_adi: str
    vektor_boyutu: int
    toplam_aktif_parca: int
    uretilen_vektor_sayisi: int
    korunan_vektor_sayisi: int
    silinen_vektor_sayisi: int
    gecen_saniye: float

    def sozluge_donustur(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VektorDurumu:
    model_adi: str
    vektor_boyutu: int
    toplam_aktif_parca: int
    hazir_vektor_sayisi: int
    eksik_vektor_sayisi: int
    gecersiz_vektor_sayisi: int
    pasif_vektor_sayisi: int

    def sozluge_donustur(self) -> dict[str, Any]:
        return asdict(self)


class VektorServisi:
    def __init__(
        self,
        model_adi: str | None = None,
        model_yolu: str | Path | None = None,
        vektor_boyutu: int | None = None,
        toplu_islem_boyutu: int | None = None,
        model: Any | None = None,
    ) -> None:
        self.model_adi = model_adi or konfigurasyon.VEKTOR_MODEL_ADI
        self.model_yolu = Path(
            model_yolu or konfigurasyon.VEKTOR_MODEL_YOLU
        ).expanduser()
        self.vektor_boyutu = vektor_boyutu or konfigurasyon.VEKTOR_BOYUTU
        self.toplu_islem_boyutu = (
            toplu_islem_boyutu or konfigurasyon.VEKTOR_TOPLU_ISLEM_BOYUTU
        )
        if not self.model_adi.strip():
            raise ValueError("Vektor model adi bos olamaz")
        if self.vektor_boyutu < 1:
            raise ValueError("Vektor boyutu en az 1 olmalidir")
        if self.toplu_islem_boyutu < 1:
            raise ValueError("Toplu islem boyutu en az 1 olmalidir")
        self._model = model

    def modeli_yukle(self) -> Any:
        if self._model is not None:
            self._model_boyutunu_dogrula(self._model)
            return self._model
        with _MODEL_KILIDI:
            if self._model is not None:
                return self._model
            yerel_model_yolu = self.model_yolu.resolve()
            if not yerel_model_yolu.is_dir():
                raise VektorModeliHatasi(
                    "Yerel vektor modeli bulunamadi; once "
                    "`python vektor_modelini_hazirla.py` komutunu calistirin"
                )
            try:
                yerel_modeli_dogrula(yerel_model_yolu)
            except RuntimeError as hata:
                raise VektorModeliHatasi(
                    "Yerel model guvenlik dogrulamasindan gecemedi"
                ) from hata
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            os.environ["HF_DATASETS_OFFLINE"] = "1"
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as hata:
                raise VektorModeliHatasi(
                    "sentence-transformers kutuphanesi kurulu degil"
                ) from hata
            try:
                self._model = SentenceTransformer(
                    str(yerel_model_yolu),
                    device="cpu",
                    trust_remote_code=False,
                )
            except Exception as hata:
                raise VektorModeliHatasi(
                    "Yerel vektor modeli cevrimdisi yuklenemedi"
                ) from hata
            self._model_boyutunu_dogrula(self._model)
            return self._model

    def _model_boyutunu_dogrula(self, model: Any) -> None:
        boyut_alici = getattr(model, "get_embedding_dimension", None)
        if not callable(boyut_alici):
            boyut_alici = getattr(
                model,
                "get_sentence_embedding_dimension",
                None,
            )
        if not callable(boyut_alici):
            raise VektorModeliHatasi("Model vektor boyutunu bildirmiyor")
        model_boyutu = int(boyut_alici())
        if model_boyutu != self.vektor_boyutu:
            raise VektorModeliHatasi(
                f"Model boyutu {model_boyutu}, beklenen boyut {self.vektor_boyutu}"
            )

    def metinleri_vektore_donustur(self, metinler: list[str]) -> np.ndarray:
        if not metinler:
            return np.empty((0, self.vektor_boyutu), dtype=np.float32)
        if any(not isinstance(metin, str) or not metin.strip() for metin in metinler):
            raise ValueError("Vektore donusturulecek metinler bos olamaz")
        model = self.modeli_yukle()
        try:
            ham_vektorler = model.encode(
                metinler,
                batch_size=min(self.toplu_islem_boyutu, len(metinler)),
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception as hata:
            raise VektorModeliHatasi("Vektor uretimi basarisiz oldu") from hata
        vektorler = np.asarray(ham_vektorler, dtype=np.float32)
        beklenen_sekil = (len(metinler), self.vektor_boyutu)
        if vektorler.shape != beklenen_sekil:
            raise VektorModeliHatasi(
                f"Vektor matrisi {vektorler.shape}, beklenen {beklenen_sekil}"
            )
        if not np.isfinite(vektorler).all():
            raise VektorModeliHatasi("Vektorler sonlu olmayan deger iceriyor")
        normlar = np.linalg.norm(vektorler, axis=1, keepdims=True)
        if np.any(normlar <= 0):
            raise VektorModeliHatasi("Sifir normlu vektor uretildi")
        return np.ascontiguousarray(vektorler / normlar, dtype=np.float32)

    def metni_vektore_donustur(self, metin: str) -> np.ndarray:
        return self.metinleri_vektore_donustur([metin])[0]

    def vektoru_bloba_donustur(self, vektor: np.ndarray) -> bytes:
        dizi = np.asarray(vektor, dtype="<f4")
        if dizi.shape != (self.vektor_boyutu,):
            raise ValueError("Vektor boyutu beklenen degerle eslesmiyor")
        if not np.isfinite(dizi).all():
            raise ValueError("Vektor sonlu olmayan deger iceriyor")
        return np.ascontiguousarray(dizi).tobytes(order="C")

    def blobu_vektore_donustur(self, vektor_verisi: bytes) -> np.ndarray:
        beklenen_bayt = self.vektor_boyutu * np.dtype("<f4").itemsize
        if len(vektor_verisi) != beklenen_bayt:
            raise ValueError("Vektor BLOB boyutu gecersiz")
        return np.frombuffer(vektor_verisi, dtype="<f4").astype(
            np.float32,
            copy=True,
        )

    def durumu_al(self) -> VektorDurumu:
        tablolari_olustur()
        with baglam_yoneticisi() as baglanti:
            aktif_parcalar = baglanti.execute(
                """
                SELECT
                    parca.parca_metni,
                    vektor.id AS vektor_id,
                    vektor.vektor_boyutu,
                    vektor.vektor_verisi,
                    vektor.metin_ozeti
                FROM sss_parcalari AS parca
                JOIN sss_kayitlari AS kayit ON kayit.id = parca.sss_id
                LEFT JOIN sss_vektorleri AS vektor
                    ON vektor.parca_id = parca.id
                    AND vektor.model_adi = ?
                WHERE kayit.durum = 'aktif'
                """,
                (self.model_adi,),
            ).fetchall()
            pasif_vektor_sayisi = baglanti.execute(
                """
                SELECT COUNT(*)
                FROM sss_vektorleri AS vektor
                LEFT JOIN sss_parcalari AS parca ON parca.id = vektor.parca_id
                LEFT JOIN sss_kayitlari AS kayit ON kayit.id = parca.sss_id
                WHERE vektor.model_adi = ?
                    AND (kayit.id IS NULL OR kayit.durum != 'aktif')
                """,
                (self.model_adi,),
            ).fetchone()[0]
        toplam_aktif_parca = len(aktif_parcalar)
        hazir_vektor_sayisi = 0
        gecersiz_vektor_sayisi = 0
        beklenen_bayt = self.vektor_boyutu * np.dtype("<f4").itemsize
        for parca in aktif_parcalar:
            if parca["vektor_id"] is None:
                continue
            metin_ozeti = self._metin_ozetini_hesapla(parca["parca_metni"])
            boyut_gecerli = (
                parca["vektor_boyutu"] == self.vektor_boyutu
                and len(parca["vektor_verisi"]) == beklenen_bayt
            )
            ozet_gecerli = parca["metin_ozeti"] == metin_ozeti
            if boyut_gecerli and ozet_gecerli:
                hazir_vektor_sayisi += 1
            else:
                gecersiz_vektor_sayisi += 1
        eksik_vektor_sayisi = max(
            toplam_aktif_parca - hazir_vektor_sayisi,
            0,
        )
        return VektorDurumu(
            model_adi=self.model_adi,
            vektor_boyutu=self.vektor_boyutu,
            toplam_aktif_parca=toplam_aktif_parca,
            hazir_vektor_sayisi=hazir_vektor_sayisi,
            eksik_vektor_sayisi=eksik_vektor_sayisi,
            gecersiz_vektor_sayisi=gecersiz_vektor_sayisi,
            pasif_vektor_sayisi=pasif_vektor_sayisi,
        )

    def vektorleri_uret(self, tumunu_yenile: bool = False) -> VektorUretimSonucu:
        baslangic = perf_counter()
        with _URETIM_KILIDI:
            tablolari_olustur()
            silinen_vektor_sayisi, parcalar = self._uretim_planini_olustur(
                tumunu_yenile
            )
            uretilen_vektor_sayisi = 0
            toplam_toplu_islem = math.ceil(
                len(parcalar) / self.toplu_islem_boyutu
            )
            for baslangic_indeksi in range(
                0,
                len(parcalar),
                self.toplu_islem_boyutu,
            ):
                toplu_parcalar = parcalar[
                    baslangic_indeksi : baslangic_indeksi
                    + self.toplu_islem_boyutu
                ]
                vektorler = self.metinleri_vektore_donustur(
                    [parca["parca_metni"] for parca in toplu_parcalar]
                )
                uretilen_vektor_sayisi += self._vektorleri_kaydet(
                    toplu_parcalar,
                    vektorler,
                )
                tamamlanan_toplu_islem = (
                    baslangic_indeksi // self.toplu_islem_boyutu + 1
                )
                if (
                    tamamlanan_toplu_islem % 10 == 0
                    or tamamlanan_toplu_islem == toplam_toplu_islem
                ):
                    gunlukleyici.info(
                        "Vektor uretimi ilerliyor: tamamlanan_toplu_islem=%s, toplam_toplu_islem=%s, uretilen=%s",
                        tamamlanan_toplu_islem,
                        toplam_toplu_islem,
                        uretilen_vektor_sayisi,
                    )
            silinen_vektor_sayisi += self._pasif_vektorleri_sil()
            durum = self.durumu_al()
            if durum.eksik_vektor_sayisi or durum.gecersiz_vektor_sayisi:
                raise RuntimeError("Aktif parcalar icin vektor uretimi tamamlanamadi")
        sonuc = VektorUretimSonucu(
            model_adi=self.model_adi,
            vektor_boyutu=self.vektor_boyutu,
            toplam_aktif_parca=durum.toplam_aktif_parca,
            uretilen_vektor_sayisi=uretilen_vektor_sayisi,
            korunan_vektor_sayisi=(
                durum.toplam_aktif_parca - uretilen_vektor_sayisi
            ),
            silinen_vektor_sayisi=silinen_vektor_sayisi,
            gecen_saniye=round(perf_counter() - baslangic, 3),
        )
        gunlukleyici.info(
            "Vektor uretimi tamamlandi: model=%s, aktif_parca=%s, uretilen=%s, korunan=%s, silinen=%s",
            sonuc.model_adi,
            sonuc.toplam_aktif_parca,
            sonuc.uretilen_vektor_sayisi,
            sonuc.korunan_vektor_sayisi,
            sonuc.silinen_vektor_sayisi,
        )
        return sonuc

    def _uretim_planini_olustur(
        self,
        tumunu_yenile: bool,
    ) -> tuple[int, list[dict[str, Any]]]:
        with baglam_yoneticisi() as baglanti:
            baglanti.execute("BEGIN IMMEDIATE")
            silme_imleci = baglanti.execute(
                """
                DELETE FROM sss_vektorleri
                WHERE model_adi = ?
                    AND NOT EXISTS (
                        SELECT 1
                        FROM sss_parcalari AS parca
                        JOIN sss_kayitlari AS kayit
                            ON kayit.id = parca.sss_id
                        WHERE parca.id = sss_vektorleri.parca_id
                            AND kayit.durum = 'aktif'
                    )
                """,
                (self.model_adi,),
            )
            satirlar = baglanti.execute(
                """
                SELECT
                    parca.id AS parca_id,
                    parca.sss_id,
                    parca.parca_metni,
                    vektor.id AS vektor_id,
                    vektor.vektor_boyutu,
                    vektor.metin_ozeti
                FROM sss_parcalari AS parca
                JOIN sss_kayitlari AS kayit ON kayit.id = parca.sss_id
                LEFT JOIN sss_vektorleri AS vektor
                    ON vektor.parca_id = parca.id
                    AND vektor.model_adi = ?
                WHERE kayit.durum = 'aktif'
                ORDER BY parca.id
                """,
                (self.model_adi,),
            ).fetchall()
        parcalar = []
        for satir in satirlar:
            metin_ozeti = self._metin_ozetini_hesapla(satir["parca_metni"])
            if (
                tumunu_yenile
                or satir["vektor_id"] is None
                or satir["vektor_boyutu"] != self.vektor_boyutu
                or satir["metin_ozeti"] != metin_ozeti
            ):
                parcalar.append(
                    {
                        "parca_id": satir["parca_id"],
                        "sss_id": satir["sss_id"],
                        "parca_metni": satir["parca_metni"],
                        "metin_ozeti": metin_ozeti,
                    }
                )
        return max(silme_imleci.rowcount, 0), parcalar

    def _vektorleri_kaydet(
        self,
        parcalar: list[dict[str, Any]],
        vektorler: np.ndarray,
    ) -> int:
        parca_kimlikleri = [parca["parca_id"] for parca in parcalar]
        yer_tutucular = ",".join("?" for _ in parca_kimlikleri)
        with baglam_yoneticisi() as baglanti:
            baglanti.execute("BEGIN IMMEDIATE")
            etkin_parca_kimlikleri = {
                satir["id"]
                for satir in baglanti.execute(
                    f"""
                    SELECT parca.id
                    FROM sss_parcalari AS parca
                    JOIN sss_kayitlari AS kayit ON kayit.id = parca.sss_id
                    WHERE kayit.durum = 'aktif'
                        AND parca.id IN ({yer_tutucular})
                    """,
                    parca_kimlikleri,
                ).fetchall()
            }
            kaydedilecekler = [
                (
                    parca["sss_id"],
                    parca["parca_id"],
                    self.vektoru_bloba_donustur(vektor),
                    self.model_adi,
                    self.vektor_boyutu,
                    parca["metin_ozeti"],
                )
                for parca, vektor in zip(parcalar, vektorler, strict=True)
                if parca["parca_id"] in etkin_parca_kimlikleri
            ]
            baglanti.executemany(
                """
                INSERT INTO sss_vektorleri (
                    sss_id,
                    parca_id,
                    vektor_verisi,
                    model_adi,
                    vektor_boyutu,
                    metin_ozeti,
                    olusturulma_tarihi
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(parca_id, model_adi)
                    WHERE parca_id IS NOT NULL
                DO UPDATE SET
                    sss_id = excluded.sss_id,
                    vektor_verisi = excluded.vektor_verisi,
                    vektor_boyutu = excluded.vektor_boyutu,
                    metin_ozeti = excluded.metin_ozeti,
                    olusturulma_tarihi = CURRENT_TIMESTAMP
                """,
                kaydedilecekler,
            )
        return len(kaydedilecekler)

    def _pasif_vektorleri_sil(self) -> int:
        with baglam_yoneticisi() as baglanti:
            baglanti.execute("BEGIN IMMEDIATE")
            imlec = baglanti.execute(
                """
                DELETE FROM sss_vektorleri
                WHERE model_adi = ?
                    AND NOT EXISTS (
                        SELECT 1
                        FROM sss_parcalari AS parca
                        JOIN sss_kayitlari AS kayit ON kayit.id = parca.sss_id
                        WHERE parca.id = sss_vektorleri.parca_id
                            AND kayit.durum = 'aktif'
                    )
                """,
                (self.model_adi,),
            )
        return max(imlec.rowcount, 0)

    def _metin_ozetini_hesapla(self, metin: str) -> str:
        return hashlib.sha256(metin.encode("utf-8")).hexdigest()
