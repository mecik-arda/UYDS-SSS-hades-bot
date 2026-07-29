import hashlib
import json
from dataclasses import replace
from pathlib import Path
from threading import Lock
from typing import Any, Protocol, runtime_checkable

import numpy as np

from uygulama.modeller.semalar import AramaAdayi

YENIDEN_SIRALAMA_MODEL_KIMLIGI = (
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
)
YENIDEN_SIRALAMA_MODEL_REVIZYONU = (
    "1427fd652930e4ba29e8149678df786c240d8825"
)
YENIDEN_SIRALAMA_MANIFESTI = "model_guvenlik_manifesti.json"
YENIDEN_SIRALAMA_MODEL_DOSYALARI = (
    "config.json",
    "model.safetensors",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
)
YENIDEN_SIRALAMA_MODEL_OZETI = (
    "5daeca2481a76b5976a2bdc32f0a78532b6716da4f8cd3ff59460ef8d2f359b4"
)


class YenidenSiralamaHatasi(RuntimeError):
    pass


@runtime_checkable
class YenidenSiralayiciProtokolu(Protocol):
    def yeniden_sirala(
        self,
        soru: str,
        adaylar: list[AramaAdayi],
    ) -> list[AramaAdayi]:
        raise NotImplementedError


class CrossEncoderYenidenSiralayici:
    def __init__(
        self,
        model_yolu: str | Path,
        aday_sayisi: int,
        toplu_islem_boyutu: int,
        maksimum_token: int,
        model: Any | None = None,
    ) -> None:
        self._model_yolu = Path(model_yolu)
        self._aday_sayisi = aday_sayisi
        self._toplu_islem_boyutu = toplu_islem_boyutu
        self._maksimum_token = maksimum_token
        self._model = model
        self._model_kilidi = Lock()
        if aday_sayisi <= 0:
            raise ValueError("Yeniden siralama aday sayisi pozitif olmalidir")
        if toplu_islem_boyutu <= 0:
            raise ValueError("Yeniden siralama toplu islem boyutu pozitif olmalidir")
        if maksimum_token <= 0:
            raise ValueError("Yeniden siralama maksimum token sayisi pozitif olmalidir")

    def yeniden_sirala(
        self,
        soru: str,
        adaylar: list[AramaAdayi],
    ) -> list[AramaAdayi]:
        temiz_soru = soru.strip()
        if not temiz_soru or not adaylar:
            return list(adaylar)
        yeniden_siralanacaklar = adaylar[: self._aday_sayisi]
        model = self._modeli_yukle()
        ciftler = [
            (temiz_soru, aday.aday_metni)
            for aday in yeniden_siralanacaklar
        ]
        try:
            ham_skorlar = model.predict(
                ciftler,
                batch_size=self._toplu_islem_boyutu,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as hata:
            raise YenidenSiralamaHatasi(
                "Cross-Encoder skor uretimi basarisiz"
            ) from hata
        skorlar = np.asarray(ham_skorlar, dtype=np.float64).reshape(-1)
        if skorlar.size != len(yeniden_siralanacaklar):
            raise YenidenSiralamaHatasi(
                "Cross-Encoder beklenen sayida skor uretmedi"
            )
        if not np.isfinite(skorlar).all():
            raise YenidenSiralamaHatasi("Cross-Encoder sonlu olmayan skor uretti")
        skorlanmis_adaylar = [
            replace(aday, yeniden_siralama_skoru=float(skor))
            for aday, skor in zip(yeniden_siralanacaklar, skorlar, strict=True)
        ]
        skorlanmis_adaylar.sort(
            key=lambda aday: aday.yeniden_siralama_skoru,
            reverse=True,
        )
        return skorlanmis_adaylar + adaylar[self._aday_sayisi :]

    def _modeli_yukle(self) -> Any:
        if self._model is not None:
            return self._model
        with self._model_kilidi:
            if self._model is not None:
                return self._model
            yerel_model_yolu = self._model_yolu.resolve()
            yerel_yeniden_siralama_modelini_dogrula(yerel_model_yolu)
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(
                    str(yerel_model_yolu),
                    max_length=self._maksimum_token,
                    local_files_only=True,
                    trust_remote_code=False,
                    model_kwargs={"use_safetensors": True},
                    processor_kwargs={"use_fast": True},
                )
            except Exception as hata:
                raise YenidenSiralamaHatasi(
                    "Yerel Cross-Encoder cevrimdisi yuklenemedi"
                ) from hata
            return self._model


def yerel_yeniden_siralama_modelini_dogrula(model_yolu: Path) -> None:
    kok_yol = model_yolu.resolve()
    if not kok_yol.is_dir() or kok_yol.is_symlink():
        raise YenidenSiralamaHatasi("Yeniden siralama model dizini gecersiz")
    manifest_yolu = kok_yol / YENIDEN_SIRALAMA_MANIFESTI
    if not manifest_yolu.is_file() or manifest_yolu.is_symlink():
        raise YenidenSiralamaHatasi(
            "Yeniden siralama model guvenlik manifesti bulunamadi"
        )
    try:
        manifest = json.loads(manifest_yolu.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as hata:
        raise YenidenSiralamaHatasi(
            "Yeniden siralama model manifesti okunamadi"
        ) from hata
    if manifest.get("manifest_surumu") != 1:
        raise YenidenSiralamaHatasi("Yeniden siralama manifest surumu gecersiz")
    if manifest.get("model_kimligi") != YENIDEN_SIRALAMA_MODEL_KIMLIGI:
        raise YenidenSiralamaHatasi("Yeniden siralama model kimligi gecersiz")
    if manifest.get("model_revizyonu") != YENIDEN_SIRALAMA_MODEL_REVIZYONU:
        raise YenidenSiralamaHatasi("Yeniden siralama model revizyonu gecersiz")
    beklenen_dosyalar = set(YENIDEN_SIRALAMA_MODEL_DOSYALARI)
    beklenen_dosyalar.add(YENIDEN_SIRALAMA_MANIFESTI)
    mevcut_dosyalar = set()
    for dosya_yolu in kok_yol.rglob("*"):
        if dosya_yolu.is_symlink():
            raise YenidenSiralamaHatasi(
                "Yeniden siralama model dizini sembolik bag iceremez"
            )
        if dosya_yolu.is_file():
            mevcut_dosyalar.add(dosya_yolu.relative_to(kok_yol).as_posix())
    if mevcut_dosyalar != beklenen_dosyalar:
        raise YenidenSiralamaHatasi(
            "Yeniden siralama model dizini beklenmeyen dosya iceriyor"
        )
    manifest_ozetleri = manifest.get("dosya_ozetleri")
    if not isinstance(manifest_ozetleri, dict):
        raise YenidenSiralamaHatasi("Yeniden siralama dosya ozetleri gecersiz")
    if set(manifest_ozetleri) != set(YENIDEN_SIRALAMA_MODEL_DOSYALARI):
        raise YenidenSiralamaHatasi(
            "Yeniden siralama manifest dosya listesi gecersiz"
        )
    for goreli_yol in YENIDEN_SIRALAMA_MODEL_DOSYALARI:
        dosya_yolu = kok_yol / goreli_yol
        gercek_ozet = _dosya_ozetini_hesapla(dosya_yolu)
        if manifest_ozetleri.get(goreli_yol) != gercek_ozet:
            raise YenidenSiralamaHatasi(
                f"Yeniden siralama dosya ozeti eslesmiyor: {goreli_yol}"
            )
    if (
        _dosya_ozetini_hesapla(kok_yol / "model.safetensors")
        != YENIDEN_SIRALAMA_MODEL_OZETI
    ):
        raise YenidenSiralamaHatasi(
            "Yeniden siralama resmi safetensors ozeti eslesmiyor"
        )
    _yeniden_siralama_yapilandirmasini_dogrula(kok_yol)


def yeniden_siralama_manifestini_olustur(
    model_yolu: Path,
) -> dict[str, Any]:
    dosya_ozetleri = {
        goreli_yol: _dosya_ozetini_hesapla(model_yolu / goreli_yol)
        for goreli_yol in YENIDEN_SIRALAMA_MODEL_DOSYALARI
    }
    return {
        "manifest_surumu": 1,
        "model_kimligi": YENIDEN_SIRALAMA_MODEL_KIMLIGI,
        "model_revizyonu": YENIDEN_SIRALAMA_MODEL_REVIZYONU,
        "dosya_ozetleri": dosya_ozetleri,
    }


def _yeniden_siralama_yapilandirmasini_dogrula(model_yolu: Path) -> None:
    try:
        model_yapilandirmasi = json.loads(
            (model_yolu / "config.json").read_text(encoding="utf-8")
        )
        simgelestirici_yapilandirmasi = json.loads(
            (model_yolu / "tokenizer_config.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as hata:
        raise YenidenSiralamaHatasi(
            "Yeniden siralama model yapilandirmasi okunamadi"
        ) from hata
    if model_yapilandirmasi.get("architectures") != [
        "XLMRobertaForSequenceClassification"
    ]:
        raise YenidenSiralamaHatasi("Yeniden siralama model mimarisi gecersiz")
    if model_yapilandirmasi.get("model_type") != "xlm-roberta":
        raise YenidenSiralamaHatasi("Yeniden siralama model turu gecersiz")
    if model_yapilandirmasi.get("hidden_size") != 384:
        raise YenidenSiralamaHatasi("Yeniden siralama gizli boyutu gecersiz")
    etiket_haritasi = model_yapilandirmasi.get("id2label")
    if not isinstance(etiket_haritasi, dict) or len(etiket_haritasi) != 1:
        raise YenidenSiralamaHatasi("Yeniden siralama etiket sayisi gecersiz")
    if "auto_map" in model_yapilandirmasi:
        raise YenidenSiralamaHatasi("Yeniden siralama uzaktan kod iceremez")
    if model_yapilandirmasi.get("trust_remote_code"):
        raise YenidenSiralamaHatasi("Yeniden siralama uzaktan kod izni iceremez")
    if simgelestirici_yapilandirmasi.get("tokenizer_class") not in {
        "XLMRobertaTokenizer",
        "XLMRobertaTokenizerFast",
    }:
        raise YenidenSiralamaHatasi(
            "Yeniden siralama tokenizer sinifi gecersiz"
        )


def _dosya_ozetini_hesapla(dosya_yolu: Path) -> str:
    ozetleyici = hashlib.sha256()
    try:
        with dosya_yolu.open("rb") as dosya:
            for parca in iter(lambda: dosya.read(1024 * 1024), b""):
                ozetleyici.update(parca)
    except OSError as hata:
        raise YenidenSiralamaHatasi(
            "Yeniden siralama model dosyasi okunamadi"
        ) from hata
    return ozetleyici.hexdigest()
