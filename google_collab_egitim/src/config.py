# ============================================================
# v4.1 Config Modülü — YAML tabanlı konfigürasyon yönetimi
# ============================================================
"""
UYDS SSS Cevap Doğrulama sistemi için merkezi konfigürasyon modülü.

Tüm eşik değerleri, model isimleri ve yol tanımları bu modülden yönetilir.
Colab ve lokal ortamda çalışabilir.
"""

import os
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

# ============================================================
# Sabit Sürüm Bilgileri
# ============================================================
PIPELINE_SURUMU = "4.1.0"
PROMPT_SURUMU = "4.1.0"
KURAL_SETI_SURUMU = "2026-08-04.1"
CHUNK_ALGORITMA_SURUMU = "1.0"
RETRIEVAL_ALGORITMA_SURUMU = "1.0"

# ============================================================
# Dizin Keşfi (Colab / Lokal adaptif)
# ============================================================


def _kesfet_dizinler() -> dict:
    """Colab veya lokal ortama göre proje dizinlerini belirler."""
    CALISMA_DIZINI = "/content"
    DRIVE_DIZINI = "/content/drive/MyDrive"

    # Önce Drive'ı dene (Colab)
    aday = os.path.join(DRIVE_DIZINI, "google_collab_egitim")
    if os.path.isdir(aday):
        NOTEBOOK_DIZINI = aday
        KOK_DIZIN = DRIVE_DIZINI
        COLAB_MU = True
    else:
        # Drive yoksa lokal çalışma dizininden proje kökünü bul
        NOTEBOOK_DIZINI = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        KOK_DIZIN = NOTEBOOK_DIZINI
        COLAB_MU = False

    # Alt dizinler
    KAYNAK_DIZINI = os.path.join(NOTEBOOK_DIZINI, "data", "kaynaklar")
    INPUT_DIZINI = os.path.join(NOTEBOOK_DIZINI, "data", "input")
    CIKTI_DIZINI = os.path.join(
        NOTEBOOK_DIZINI, "data", "output_v4",
        datetime.now().strftime("%Y-%m-%d_%H%M")
    )
    CKPT_DIZINI = os.path.join(NOTEBOOK_DIZINI, "checkpoints_v4", "latest")
    CONFIG_DIZINI = os.path.join(NOTEBOOK_DIZINI, "config")

    return {
        "calisma": CALISMA_DIZINI,
        "kok": KOK_DIZIN,
        "notebook": NOTEBOOK_DIZINI,
        "kaynak": KAYNAK_DIZINI,
        "input": INPUT_DIZINI,
        "cikti": CIKTI_DIZINI,
        "ckpt": CKPT_DIZINI,
        "config": CONFIG_DIZINI,
        "colab_mu": COLAB_MU,
    }


DIZINLER = _kesfet_dizinler()

# Kolay erişim kısayolları
KAYNAK_DIZINI = DIZINLER["kaynak"]
INPUT_DIZINI = DIZINLER["input"]
CIKTI_DIZINI = DIZINLER["cikti"]
CKPT_DIZINI = DIZINLER["ckpt"]
CONFIG_DIZINI = DIZINLER["config"]
COLAB_MU = DIZINLER["colab_mu"]

# ============================================================
# Config Dosyası Yükleme
# ============================================================


def _config_yukle() -> dict:
    """config_v4.yaml dosyasını yükler."""
    config_yolu = os.path.join(CONFIG_DIZINI, "config_v4.yaml")
    if not os.path.exists(config_yolu):
        # Lokal fallback: proje kökü altında config/
        fallback = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config", "config_v4.yaml"
        )
        if os.path.exists(fallback):
            config_yolu = fallback
        else:
            raise FileNotFoundError(
                f"Config dosyası bulunamadı: {config_yolu} "
                f"(fallback: {fallback})"
            )
    with open(config_yolu, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


_HAM_CONFIG = _config_yukle()


def cfg(bolum: str, alt_bolum: str, anahtar: str, default: Any = None) -> Any:
    """Config'ten iç içe değer okur. Bulamazsa default döner."""
    try:
        return _HAM_CONFIG[bolum][alt_bolum][anahtar]
    except (KeyError, TypeError):
        return default


# ============================================================
# Türetilmiş Sabitler (Config'ten okunur)
# ============================================================

# Embedding modeli
EMBEDDING_MODEL = cfg(
    "v4", "embedding", "model",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
EMBEDDING_BATCH = cfg("v4", "embedding", "batch_size", 2)
SORU_EMB_BATCH = cfg("v4", "embedding", "soru_batch_size", 2)

# LLM Modelleri
BIRINCIL_MODEL = cfg("v4", "model", "birincil", "Qwen/Qwen3-32B-AWQ")
YEDEK_MODEL = cfg("v4", "model", "yedek", "Qwen/Qwen2.5-32B-Instruct-AWQ")

# Chunk parametreleri
CHUNK_BOYUT_TOKEN = cfg("v4", "chunk", "token_boyut", 110)
CHUNK_OVERLAP_TOKEN = cfg("v4", "chunk", "token_overlap", 25)

# vLLM parametreleri
MAX_MODEL_LEN = cfg("v4", "vllm", "max_model_len", 4096)
GPU_MEM_UTIL = cfg("v4", "vllm", "gpu_memory_utilization", 0.75)
BATCH_BUYUKLUK = cfg("v4", "vllm", "batch_size", 4)
MAX_NEW_TOKENS = cfg("v4", "sampling", "max_tokens", 256)
GUVENLIK_PAYI = 50

# Prompt token limiti
PROMPT_TOKEN_LIMIT = MAX_MODEL_LEN - MAX_NEW_TOKENS - GUVENLIK_PAYI

# RAG parametreleri
RAG_TOP_K = cfg("v4", "rag", "top_k", 10)
RAG_SON_K = cfg("v4", "rag", "son_k", 3)
RAG_MIN_SKOR = cfg("v4", "rag", "min_skor", 0.3)

# Güven eşiği
GUVEN_ESIK = cfg("v4", "guven", "esik", 0.85)

# Checkpoint
CKPT_ARALIK = cfg("v4", "checkpoint", "aralik", 100)

# Sampling
TEMPERATURE = cfg("v4", "sampling", "temperature", 0.2)
TOP_P = cfg("v4", "sampling", "top_p", 0.9)

# ============================================================
# Hash Fonksiyonları (Bütünlük kontrolü)
# ============================================================


def dosya_hashi(dosya_yolu: str, blok: int = 65536) -> str:
    """Bir dosyanın SHA-256 hash'ini döndürür."""
    if not os.path.isfile(dosya_yolu):
        raise FileNotFoundError(f"Dosya bulunamadı: {dosya_yolu}")
    h = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        for blk in iter(lambda: f.read(blok), b""):
            h.update(blk)
    return h.hexdigest()


def dizin_hashi(dizin_yolu: str) -> str:
    """Bir dizindeki tüm dosyaların birleşik SHA-256 hash'ini döndürür."""
    h = hashlib.sha256()
    if not os.path.isdir(dizin_yolu):
        return h.hexdigest()
    for kok, _, dosyalar in sorted(os.walk(dizin_yolu)):
        for df in sorted(dosyalar):
            if df.startswith("."):
                continue
            try:
                h.update(dosya_hashi(os.path.join(kok, df)).encode())
            except Exception:
                pass
    return h.hexdigest()


def config_hashi() -> str:
    """Mevcut config'in SHA-256 hash'ini döndürür."""
    return hashlib.sha256(
        json.dumps(_HAM_CONFIG, sort_keys=True).encode()
    ).hexdigest()[:16]


CONFIG_HASH = config_hashi()


# ============================================================
# Dizin Oluşturma
# ============================================================
def dizinleri_hazirla() -> None:
    """Gerekli tüm çıktı ve checkpoint dizinlerini oluşturur."""
    for d in [CIKTI_DIZINI, CKPT_DIZINI]:
        os.makedirs(d, exist_ok=True)
    # Embedding alt dizini
    os.makedirs(os.path.join(CKPT_DIZINI, "kaynak_embedding"), exist_ok=True)


# ============================================================
# Config Özeti (Log/Debug için)
# ============================================================
def config_ozeti() -> str:
    """İnsan tarafından okunabilir config özeti döndürür."""
    satirlar = [
        f"Pipeline: v{PIPELINE_SURUMU} | Prompt: {PROMPT_SURUMU}",
        f"Birincil Model: {BIRINCIL_MODEL}",
        f"Yedek Model: {YEDEK_MODEL}",
        f"Embedding: {EMBEDDING_MODEL}",
        f"Chunk: {CHUNK_BOYUT_TOKEN}/{CHUNK_OVERLAP_TOKEN} token | Algo v{CHUNK_ALGORITMA_SURUMU}",
        f"RAG: top-{RAG_TOP_K} -> son-{RAG_SON_K} | min_skor={RAG_MIN_SKOR}",
        f"vLLM: max_model_len={MAX_MODEL_LEN} | gpu_mem={GPU_MEM_UTIL} | batch={BATCH_BUYUKLUK}",
        f"Prompt limit: {PROMPT_TOKEN_LIMIT} token | max_new={MAX_NEW_TOKENS}",
        f"Güven eşiği: {GUVEN_ESIK} | Sıcaklık: {TEMPERATURE}",
        f"Config hash: {CONFIG_HASH}",
        f"Colab: {'Evet' if COLAB_MU else 'Hayır'}",
    ]
    return "\n".join(satirlar)