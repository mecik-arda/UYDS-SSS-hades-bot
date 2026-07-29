import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from uygulama.servisler.yeniden_siralayici import (
    YENIDEN_SIRALAMA_MANIFESTI,
    YENIDEN_SIRALAMA_MODEL_DOSYALARI,
    YENIDEN_SIRALAMA_MODEL_KIMLIGI,
    YENIDEN_SIRALAMA_MODEL_REVIZYONU,
    yeniden_siralama_manifestini_olustur,
    yerel_yeniden_siralama_modelini_dogrula,
)


def argumanlari_al() -> argparse.Namespace:
    ayristirici = argparse.ArgumentParser(
        prog="yeniden_siralama_modelini_hazirla.py",
        description="Sabitlenmis Cross-Encoder modelini guvenli yerel dizine indirir",
    )
    ayristirici.add_argument(
        "--hedef",
        type=Path,
        default=Path(
            os.getenv(
                "YENIDEN_SIRALAMA_MODEL_YOLU",
                "modeller/mmarco-mMiniLMv2-L12-H384-v1",
            )
        ),
    )
    return ayristirici.parse_args()


def ana() -> None:
    argumanlar = argumanlari_al()
    hedef = argumanlar.hedef.expanduser().resolve()
    if hedef.exists():
        raise FileExistsError("Hedef yeniden siralama model dizini zaten mevcut")
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
            repo_id=YENIDEN_SIRALAMA_MODEL_KIMLIGI,
            revision=YENIDEN_SIRALAMA_MODEL_REVIZYONU,
            local_dir=str(gecici_yol),
            allow_patterns=list(YENIDEN_SIRALAMA_MODEL_DOSYALARI),
        )
        gecici_onbellek = gecici_yol / ".cache"
        if gecici_onbellek.exists():
            shutil.rmtree(gecici_onbellek)
        manifest = yeniden_siralama_manifestini_olustur(gecici_yol)
        (gecici_yol / YENIDEN_SIRALAMA_MANIFESTI).write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        yerel_yeniden_siralama_modelini_dogrula(gecici_yol)
        os.replace(gecici_yol, hedef)
    finally:
        if gecici_yol.exists():
            shutil.rmtree(gecici_yol)
    print(
        json.dumps(
            {
                "model_kimligi": YENIDEN_SIRALAMA_MODEL_KIMLIGI,
                "model_revizyonu": YENIDEN_SIRALAMA_MODEL_REVIZYONU,
                "yerel_model_yolu": str(hedef),
                "guvenlik_dogrulamasi": "basarili",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    ana()
