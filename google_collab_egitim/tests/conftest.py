# ============================================================
# Pytest conftest — ortak fixtures
# ============================================================
import os
import sys
import tempfile

import pytest

# src modülünü path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def temp_dir():
    """Geçici dizin fixture'ı."""
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def ornek_chunklar():
    """Test için örnek chunk listesi."""
    return [
        {
            "chunk_id": 0,
            "dokuman": "test_kilavuz.pdf",
            "sayfa": 5,
            "metin": "Hakediş onay işlemi için önce belge kontrolü yapılır.",
            "kaynak_tipi": "resmi_kilavuz",
            "modul": "Hakediş",
        },
        {
            "chunk_id": 1,
            "dokuman": "test_kilavuz.pdf",
            "sayfa": 6,
            "metin": "Belge eksikse sistem hata verir ve işlem durdurulur.",
            "kaynak_tipi": "resmi_kilavuz",
            "modul": "Hakediş",
        },
        {
            "chunk_id": 2,
            "dokuman": "ihale_mevzuat.pdf",
            "sayfa": 12,
            "metin": "İhale sürecinde teklif zarfları komisyon tarafından açılır.",
            "kaynak_tipi": "mevzuat",
            "modul": "İhale",
        },
    ]


@pytest.fixture
def ornek_sonuc():
    """Test için örnek doğrulama sonucu."""
    return {
        "karar": "dogru",
        "guven": 0.95,
        "kaynak_idleri": [0, 1],
        "dayanak": "Kaynaklar cevabı tam olarak destekliyor.",
        "eksik_veya_hata": "",
        "duzeltilmis_cevap": "",
        "_islem_hatasi": False,
        "_kayit_no": 0,
        "_veri_indeksi": 0,
        "_kaynak_dokumanlari": "test_kilavuz.pdf",
        "_rag_maks_skor": 0.85,
    }


@pytest.fixture
def ornek_mesaj():
    """Test için örnek chat mesajı."""
    return [
        {"role": "system", "content": "Sen bir doğrulama uzmanısın."},
        {"role": "user", "content": "Bu soruyu değerlendir."},
    ]


@pytest.fixture
def ornek_vektor_parcalar():
    """Test retrieval için 3 parçalı örnek veri seti."""
    import numpy as np
    vektorler = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float32)
    vektorler = vektorler / np.linalg.norm(vektorler, axis=1, keepdims=True)
    parcalar = [
        {"chunk_id": 0, "dokuman": "a.pdf", "sayfa": 1, "metin": "Hakediş onayı."},
        {"chunk_id": 1, "dokuman": "a.pdf", "sayfa": 2, "metin": "Belge kontrolü."},
        {"chunk_id": 2, "dokuman": "b.pdf", "sayfa": 5, "metin": "İhale süreci."},
    ]
    return vektorler, parcalar
