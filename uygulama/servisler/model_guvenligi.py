import hashlib
import json
from pathlib import Path
from typing import Any

GUVENILIR_MODEL_KIMLIGI = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
GUVENILIR_MODEL_REVIZYONU = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
MODEL_GUVENLIK_MANIFESTI = "model_guvenlik_manifesti.json"
GUVENILIR_MODEL_DOSYALARI = (
    "1_Pooling/config.json",
    "config.json",
    "config_sentence_transformers.json",
    "model.safetensors",
    "modules.json",
    "sentence_bert_config.json",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
)
GUVENILIR_LFS_DOSYALARI = {
    "model.safetensors": (
        470641600,
        "eaa086f0ffee582aeb45b36e34cdd1fe2d6de2bef61f8a559a1bbc9bd955917b",
    ),
    "sentencepiece.bpe.model": (
        5069051,
        "cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865",
    ),
    "tokenizer.json": (
        9081518,
        "2c3387be76557bd40970cec13153b3bbf80407865484b209e655e5e4729076b8",
    ),
}
IZINLI_MODEL_MODULLERI = (
    "sentence_transformers.models.Transformer",
    "sentence_transformers.models.Pooling",
)


class ModelGuvenlikHatasi(RuntimeError):
    def __init__(self, mesaj: str) -> None:
        super().__init__(mesaj)


def dosya_ozetini_hesapla(dosya_yolu: Path) -> str:
    ozetleyici = hashlib.sha256()
    with dosya_yolu.open("rb") as dosya:
        for parca in iter(lambda: dosya.read(1024 * 1024), b""):
            ozetleyici.update(parca)
    return ozetleyici.hexdigest()


def model_manifestini_olustur(model_yolu: Path) -> dict[str, Any]:
    dosya_ozetleri = {
        goreli_yol: dosya_ozetini_hesapla(model_yolu / goreli_yol)
        for goreli_yol in GUVENILIR_MODEL_DOSYALARI
    }
    return {
        "manifest_surumu": 1,
        "model_kimligi": GUVENILIR_MODEL_KIMLIGI,
        "model_revizyonu": GUVENILIR_MODEL_REVIZYONU,
        "dosya_ozetleri": dosya_ozetleri,
    }


def yerel_modeli_dogrula(model_yolu: Path) -> dict[str, Any]:
    kok_yol = model_yolu.resolve()
    if not kok_yol.is_dir() or kok_yol.is_symlink():
        raise ModelGuvenlikHatasi("Yerel model dizini gecersiz")
    manifest_yolu = kok_yol / MODEL_GUVENLIK_MANIFESTI
    if not manifest_yolu.is_file() or manifest_yolu.is_symlink():
        raise ModelGuvenlikHatasi("Model guvenlik manifesti bulunamadi")
    try:
        manifest = json.loads(manifest_yolu.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as hata:
        raise ModelGuvenlikHatasi("Model guvenlik manifesti okunamadi") from hata
    if manifest.get("manifest_surumu") != 1:
        raise ModelGuvenlikHatasi("Model manifest surumu desteklenmiyor")
    if manifest.get("model_kimligi") != GUVENILIR_MODEL_KIMLIGI:
        raise ModelGuvenlikHatasi("Model kimligi guvenilir modelle eslesmiyor")
    if manifest.get("model_revizyonu") != GUVENILIR_MODEL_REVIZYONU:
        raise ModelGuvenlikHatasi("Model revizyonu sabit guvenilir revizyon degil")
    beklenen_dosyalar = set(GUVENILIR_MODEL_DOSYALARI)
    beklenen_dosyalar.add(MODEL_GUVENLIK_MANIFESTI)
    mevcut_dosyalar = set()
    for dosya_yolu in kok_yol.rglob("*"):
        if dosya_yolu.is_symlink():
            raise ModelGuvenlikHatasi("Model dizini sembolik bag iceremez")
        if dosya_yolu.is_file():
            mevcut_dosyalar.add(dosya_yolu.relative_to(kok_yol).as_posix())
    if mevcut_dosyalar != beklenen_dosyalar:
        raise ModelGuvenlikHatasi("Model dizini beklenmeyen veya eksik dosya iceriyor")
    manifest_ozetleri = manifest.get("dosya_ozetleri")
    if not isinstance(manifest_ozetleri, dict):
        raise ModelGuvenlikHatasi("Model dosya ozetleri gecersiz")
    if set(manifest_ozetleri) != set(GUVENILIR_MODEL_DOSYALARI):
        raise ModelGuvenlikHatasi("Model manifesti beklenmeyen dosya iceriyor")
    for goreli_yol in GUVENILIR_MODEL_DOSYALARI:
        dosya_yolu = kok_yol / goreli_yol
        gercek_ozet = dosya_ozetini_hesapla(dosya_yolu)
        if manifest_ozetleri.get(goreli_yol) != gercek_ozet:
            raise ModelGuvenlikHatasi(f"Model dosya ozeti eslesmiyor: {goreli_yol}")
    for goreli_yol, (beklenen_boyut, beklenen_ozet) in (
        GUVENILIR_LFS_DOSYALARI.items()
    ):
        dosya_yolu = kok_yol / goreli_yol
        if dosya_yolu.stat().st_size != beklenen_boyut:
            raise ModelGuvenlikHatasi(f"Model dosya boyutu eslesmiyor: {goreli_yol}")
        if dosya_ozetini_hesapla(dosya_yolu) != beklenen_ozet:
            raise ModelGuvenlikHatasi(f"Resmi LFS ozeti eslesmiyor: {goreli_yol}")
    _model_yapilandirmasini_dogrula(kok_yol)
    return manifest


def _model_yapilandirmasini_dogrula(model_yolu: Path) -> None:
    try:
        modul_yapilandirmasi = json.loads(
            (model_yolu / "modules.json").read_text(encoding="utf-8")
        )
        model_yapilandirmasi = json.loads(
            (model_yolu / "config.json").read_text(encoding="utf-8")
        )
        simgelestirici_yapilandirmasi = json.loads(
            (model_yolu / "tokenizer_config.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as hata:
        raise ModelGuvenlikHatasi("Model yapilandirmasi okunamadi") from hata
    modul_turleri = tuple(
        modul.get("type")
        for modul in modul_yapilandirmasi
        if isinstance(modul, dict)
    )
    if modul_turleri != IZINLI_MODEL_MODULLERI:
        raise ModelGuvenlikHatasi("Model beklenmeyen modul turu iceriyor")
    if model_yapilandirmasi.get("architectures") != ["BertModel"]:
        raise ModelGuvenlikHatasi("Model mimarisi beklenen BERT mimarisi degil")
    if model_yapilandirmasi.get("model_type") != "bert":
        raise ModelGuvenlikHatasi("Model turu beklenen BERT turu degil")
    if model_yapilandirmasi.get("hidden_size") != 384:
        raise ModelGuvenlikHatasi("Model gizli boyutu 384 degil")
    if "auto_map" in model_yapilandirmasi:
        raise ModelGuvenlikHatasi("Model uzaktan kod eslemesi iceremez")
    if model_yapilandirmasi.get("trust_remote_code"):
        raise ModelGuvenlikHatasi("Model uzaktan kod calistirma izni iceremez")
    if simgelestirici_yapilandirmasi.get("tokenizer_class") not in {
        "PreTrainedTokenizerFast",
        "XLMRobertaTokenizer",
        "XLMRobertaTokenizerFast",
    }:
        raise ModelGuvenlikHatasi("Tokenizer sinifi izinli degil")
