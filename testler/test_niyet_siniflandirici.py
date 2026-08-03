import json

from uygulama.cekirdek.konfigurasyon import konfigurasyon
from uygulama.servisler.niyet_siniflandirici import NiyetSiniflandirici


def eylem_dosyasini_yaz(tmp_path, eylemler):
    eylem_yolu = tmp_path / "niyet_eylemleri.json"
    eylem_yolu.write_text(
        json.dumps({"eylemler": eylemler}),
        encoding="utf-8",
    )
    return eylem_yolu


def test_normal_kullanici_ifadesi_yuksek_guvenle_eslesir(tmp_path, monkeypatch):
    eylem_yolu = eylem_dosyasini_yaz(
        tmp_path,
        [
            {
                "niyet_adi": "sifre_sifirla",
                "buton_metni": "Sifremi Sifirla",
                "hedef_url": "/sifre-sifirla",
                "anahtar_kelimeler": ["sifre", "sifremi", "parola"],
                "kaliplar": ["sifre.*sifirla"],
            }
        ],
    )
    monkeypatch.setattr(konfigurasyon, "NIYET_SINIFLANDIRMA_AKTIF", True)
    monkeypatch.setattr(konfigurasyon, "NIYET_GUVEN_ESIGI", 0.80)
    siniflandirici = NiyetSiniflandirici(str(eylem_yolu))

    sonuc = siniflandirici.siniflandir("Sifremi sifirlamak istiyorum")

    assert sonuc.eslesme_var_mi is True
    assert sonuc.eslesmeler[0].niyet_adi == "sifre_sifirla"
    assert sonuc.eslesmeler[0].guven_skoru == 1.0


def test_guvensiz_ve_eksik_eylemler_yuklenmez(tmp_path, monkeypatch):
    eylem_yolu = eylem_dosyasini_yaz(
        tmp_path,
        [
            {
                "niyet_adi": "guvensiz",
                "buton_metni": "Ac",
                "hedef_url": "javascript:alert(1)",
                "anahtar_kelimeler": ["ac"],
            },
            {
                "niyet_adi": "eksik",
                "hedef_url": "/eksik",
                "anahtar_kelimeler": ["eksik"],
            },
        ],
    )
    monkeypatch.setattr(konfigurasyon, "NIYET_SINIFLANDIRMA_AKTIF", True)
    siniflandirici = NiyetSiniflandirici(str(eylem_yolu))

    assert siniflandirici.siniflandir("ac eksik").eslesme_var_mi is False
