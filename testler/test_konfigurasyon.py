import pytest
from pydantic import ValidationError

from uygulama.cekirdek.konfigurasyon import Konfigurasyon


def konfigurasyon_olustur(**degisiklikler) -> Konfigurasyon:
    degerler = {
        "VERITABANI_SIFRELEME_ANAHTARI": "guvenli_veritabani_anahtari_123456789",
        "JWT_GIZLI_ANAHTARI": "guvenli_jwt_anahtari_123456789012345",
        "VARSAYILAN_YONETICI_SIFRESI": "GuvenliYoneticiSifresi123",
        "ORTAM_PROFILI": "prod",
    }
    degerler.update(degisiklikler)
    return Konfigurasyon(_env_file=None, **degerler)


@pytest.mark.parametrize("guven_esigi", (-0.01, 1.01))
def test_guven_esigi_birim_araligi_disinda_reddedilir(guven_esigi):
    with pytest.raises(ValidationError):
        konfigurasyon_olustur(GUVEN_ESIGI=guven_esigi)


def test_uretimde_izinli_olmayan_deepseek_alani_reddedilir():
    with pytest.raises(ValidationError, match="izinli listede"):
        konfigurasyon_olustur(
            DEEPSEEK_API_ADRESI="https://ornek.invalid/chat/completions"
        )


def test_uretimde_izinli_deepseek_alani_kabul_edilir():
    sonuc = konfigurasyon_olustur(
        DEEPSEEK_API_ADRESI="https://kurum.example/chat/completions",
        DEEPSEEK_IZINLI_ALAN_ADLARI="api.deepseek.com, kurum.example",
    )

    assert sonuc.DEEPSEEK_API_ADRESI == (
        "https://kurum.example/chat/completions"
    )


def test_gelistirmede_yerel_http_adresi_kabul_edilir():
    sonuc = konfigurasyon_olustur(
        ORTAM_PROFILI="dev",
        DEEPSEEK_API_ADRESI="http://127.0.0.1:8080/v1/chat/completions",
    )

    assert sonuc.DEEPSEEK_API_ADRESI.startswith("http://127.0.0.1")


@pytest.mark.parametrize(
    "adres",
    (
        "https://kullanici:sifre@api.deepseek.com/chat/completions",
        "https://api.deepseek.com/chat/completions?anahtar=gizli",
        "https://api.deepseek.com/chat/completions#parca",
    ),
)
def test_deepseek_adresinde_riskli_bilesenler_reddedilir(adres):
    with pytest.raises(ValidationError):
        konfigurasyon_olustur(DEEPSEEK_API_ADRESI=adres)


def test_coklu_worker_yapilandirmasi_reddedilir():
    with pytest.raises(ValidationError):
        konfigurasyon_olustur(UYGULAMA_WORKER_SAYISI=2)


def test_gecersiz_guvenlik_bakim_araligi_reddedilir():
    with pytest.raises(ValidationError):
        konfigurasyon_olustur(GUVENLIK_BAKIM_ARALIGI_SAAT=0)
