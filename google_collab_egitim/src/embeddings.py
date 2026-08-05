# ============================================================
# v4.1 Embeddings — Kaynak ve sorgu vektörleştirme
# ============================================================
"""
Sentence-transformer ile chunk ve sorgu embedding'leri oluşturur.
Checkpoint ile yeniden kullanımı destekler.
"""

import json
import os
import pickle
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def _torchcodec_kaldir() -> None:
    """
    torchcodec sentence-transformers metin embedding'i için gereksizdir;
    Colab'da sistem FFmpeg'i (libavutil) ile çakışıp SentenceTransformer
    yüklenirken patlar. Paket kuruluysa sessizce kaldırır.
    """
    try:
        import importlib.metadata as _md
        _md.version("torchcodec")
    except Exception:
        return
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "torchcodec"],
            capture_output=True,
            check=False,
        )
        sys.modules.pop("torchcodec", None)
        print("   🧹 torchcodec kaldırıldı (FFmpeg çakışmasını önlemek için).")
    except Exception:
        pass


def embedding_modeli_yukle(
    model_adi: str, cihaz: str = "cuda"
):
    """SentenceTransformer modelini yükler."""
    import torch
    _torchcodec_kaldir()
    from sentence_transformers import SentenceTransformer

    if cihaz == "cuda" and not torch.cuda.is_available():
        print("⚠️ CUDA yok, CPU kullanılıyor.")
        cihaz = "cpu"

    return SentenceTransformer(model_adi, device=cihaz, trust_remote_code=False)


def kaynak_embedding_olustur(
    chunk_metinleri: List[str],
    model,
    batch_size: int = 2,
    normalize: bool = True,
) -> np.ndarray:
    """
    Chunk metinlerinden embedding vektörleri oluşturur.

    Returns:
        (n_chunks, embedding_dim) numpy array (normalize edilmiş)
    """
    try:
        vektorler = model.encode(
            chunk_metinleri,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
    except (RuntimeError, Exception) as e:
        # GPU OOM → batch_size=1 ile dene
        print(f"   ⚠️ Batch {batch_size} hata: {e}. batch_size=1 deneniyor...")
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        vektorler = model.encode(
            chunk_metinleri,
            batch_size=1,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
    return vektorler


def soru_embedding_olustur(
    soru_metinleri: List[str],
    model_adi: str,
    batch_size: int = 2,
    cihaz: str = "cpu",
) -> np.ndarray:
    """
    Soru metinleri için embedding oluşturur.
    Bellek tasarrufu için CPU'da çalışır.
    """
    _torchcodec_kaldir()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_adi, device=cihaz, trust_remote_code=False)
    vektorler = model.encode(
        soru_metinleri,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    del model
    import gc
    gc.collect()
    return vektorler


def embedding_checkpoint_kaydet(
    ckpt_dizini: str,
    kaynak_vektorler: np.ndarray,
    tum_parcalar: List[Dict[str, Any]],
    kaynak_dizin_hash: str,
    embedding_model: str,
    chunk_boyut: int,
    chunk_overlap: int,
    chunk_algoritma_surumu: str,
    siniflandirilmis_envanter_hash: str = "",
    ilgililik_filtresi: Optional[List[str]] = None,
    siniflandirma_surumu: str = "",
) -> None:
    """Embedding'leri ve metadatasını checkpoint'e kaydeder."""
    alt_dizin = os.path.join(ckpt_dizini, "kaynak_embedding")
    os.makedirs(alt_dizin, exist_ok=True)

    vektor_yolu = os.path.join(alt_dizin, "kaynak_vektorler.npy")
    parcalar_yolu = os.path.join(alt_dizin, "parcalar.pkl")
    meta_yolu = os.path.join(alt_dizin, "emb_meta.json")

    np.save(vektor_yolu, kaynak_vektorler)
    with open(parcalar_yolu, "wb") as f:
        pickle.dump(tum_parcalar, f)

    meta = {
        "kaynak_dizin_hash": kaynak_dizin_hash,
        "embedding_model": embedding_model,
        "chunk_boyut": chunk_boyut,
        "chunk_overlap": chunk_overlap,
        "chunk_algoritma_surumu": chunk_algoritma_surumu,
    }
    if siniflandirilmis_envanter_hash:
        meta["siniflandirilmis_envanter_hash"] = siniflandirilmis_envanter_hash
    if ilgililik_filtresi is not None:
        meta["ilgililik_filtresi"] = ilgililik_filtresi
    if siniflandirma_surumu:
        meta["siniflandirma_surumu"] = siniflandirma_surumu

    with open(meta_yolu, "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"   💾 Embedding checkpoint: {len(tum_parcalar)} parça, {kaynak_vektorler.shape}")


def embedding_checkpoint_yukle(
    ckpt_dizini: str,
    kaynak_dizin_hash: str,
    embedding_model: str,
    chunk_boyut: int,
    chunk_overlap: int,
    chunk_algoritma_surumu: str,
    siniflandirilmis_envanter_hash: Optional[str] = None,
    ilgililik_filtresi: Optional[List[str]] = None,
    siniflandirma_surumu: Optional[str] = None,
) -> Optional[Tuple[np.ndarray, List[Dict[str, Any]]]]:
    """
    Embedding checkpoint'ini yükler. Meta uyuşmazsa None döner.

    Returns:
        (kaynak_vektorler, tum_parcalar) veya None
    """
    alt_dizin = os.path.join(ckpt_dizini, "kaynak_embedding")
    vektor_yolu = os.path.join(alt_dizin, "kaynak_vektorler.npy")
    parcalar_yolu = os.path.join(alt_dizin, "parcalar.pkl")
    meta_yolu = os.path.join(alt_dizin, "emb_meta.json")

    if not all(os.path.exists(p) for p in [vektor_yolu, parcalar_yolu, meta_yolu]):
        return None

    try:
        with open(meta_yolu, "r") as f:
            meta = json.load(f)

        checks = [
            meta.get("kaynak_dizin_hash") == kaynak_dizin_hash,
            meta.get("embedding_model") == embedding_model,
            meta.get("chunk_boyut") == chunk_boyut,
            meta.get("chunk_overlap") == chunk_overlap,
            meta.get("chunk_algoritma_surumu") == chunk_algoritma_surumu,
        ]
        if not all(checks):
            return None

        # Opsiyonel envanter/ilgililik hash kontrolü
        if siniflandirilmis_envanter_hash is not None:
            if meta.get("siniflandirilmis_envanter_hash") != siniflandirilmis_envanter_hash:
                print("   ⚠️ Sınıflandırılmış envanter değişmiş, checkpoint geçersiz.")
                return None
        if ilgililik_filtresi is not None:
            if meta.get("ilgililik_filtresi") != ilgililik_filtresi:
                print("   ⚠️ İlgililik filtresi değişmiş, checkpoint geçersiz.")
                return None
        if siniflandirma_surumu is not None:
            if meta.get("siniflandirma_surumu") != siniflandirma_surumu:
                print("   ⚠️ Sınıflandırma sürümü değişmiş, checkpoint geçersiz.")
                return None

        kaynak_vektorler = np.load(vektor_yolu)
        with open(parcalar_yolu, "rb") as f:
            tum_parcalar = pickle.load(f)

        print(f"🔄 Embedding checkpoint yüklendi: {len(tum_parcalar)} parça, {kaynak_vektorler.shape}")
        return kaynak_vektorler, tum_parcalar
    except Exception as e:
        print(f"   ⚠️ Embedding checkpoint okunamadı: {e}")
        return None
