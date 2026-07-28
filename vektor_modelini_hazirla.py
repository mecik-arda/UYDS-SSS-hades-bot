import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from uygulama.servisler.model_guvenligi import (
    GUVENILIR_MODEL_DOSYALARI,
    GUVENILIR_MODEL_KIMLIGI,
    GUVENILIR_MODEL_REVIZYONU,
    MODEL_GUVENLIK_MANIFESTI,
    model_manifestini_olustur,
    yerel_modeli_dogrula,
)


def argumanlari_al() -> argparse.Namespace:
    ayristirici = argparse.ArgumentParser(
        prog="vektor_modelini_hazirla.py",
        description="Sabitlenmis ve guvenilir vektor modelini yerel dizine indirir",
    )
    ayristirici.add_argument(
        "--hedef",
        type=Path,
        default=Path(
            os.getenv(
                "VEKTOR_MODEL_YOLU",
                "modeller/paraphrase-multilingual-MiniLM-L12-v2",
            )
        ),
    )
    return ayristirici.parse_args()


def ana() -> None:
    argumanlar = argumanlari_al()
    hedef = argumanlar.hedef.expanduser().resolve()
    if hedef.exists():
        raise FileExistsError("Hedef model dizini zaten mevcut")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import snapshot_download
    except ImportError as hata:
        raise RuntimeError("huggingface-hub kutuphanesi kurulu degil") from hata
    gecici_yol = Path(
        tempfile.mkdtemp(
            prefix=f"{hedef.name}.hazirlaniyor.",
            dir=hedef.parent,
        )
    )
    try:
        snapshot_download(
            repo_id=GUVENILIR_MODEL_KIMLIGI,
            revision=GUVENILIR_MODEL_REVIZYONU,
            local_dir=str(gecici_yol),
            allow_patterns=list(GUVENILIR_MODEL_DOSYALARI),
        )
        gecici_onbellek = gecici_yol / ".cache"
        if gecici_onbellek.exists():
            shutil.rmtree(gecici_onbellek)
        manifest = model_manifestini_olustur(gecici_yol)
        (gecici_yol / MODEL_GUVENLIK_MANIFESTI).write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        yerel_modeli_dogrula(gecici_yol)
        os.replace(gecici_yol, hedef)
    finally:
        if gecici_yol.exists():
            shutil.rmtree(gecici_yol)
    print(
        json.dumps(
            {
                "model_kimligi": GUVENILIR_MODEL_KIMLIGI,
                "model_revizyonu": GUVENILIR_MODEL_REVIZYONU,
                "yerel_model_yolu": str(hedef),
                "vektor_boyutu": 384,
                "guvenlik_dogrulamasi": "basarili",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    ana()
