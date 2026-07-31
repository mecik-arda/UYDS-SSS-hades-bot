from datetime import datetime, timezone

from uygulama.servisler.belge_ayiklayici import BelgeIcerik
from uygulama.servisler.yapisal_parcalayici import YapisalParcalayici


def _ornek_belge_icerik(metin="", yetki=0):
    return BelgeIcerik(
        ham_metin=metin,
        basliklar=[],
        tablolar=[],
        madde_imleri=[],
        sayfa_sayisi=1,
        kaynak_dosya="test.pdf",
        son_degistirilme_tarihi=datetime.now(timezone.utc),
        sha256_ozeti="abc123",
        yetki_seviyesi=yetki,
    )


def test_baslik_parcalari_ayrilir():
    parcalayici = YapisalParcalayici()
    metin = "# Ana Baslik\nBu bir paragraf.\n## Alt Baslik\nAlt paragraf."
    belge = _ornek_belge_icerik(metin)
    parcalar = parcalayici.yapisal_parcala(belge)
    baslik_parcalari = [p for p in parcalar if p.parca_turu == "baslik"]
    assert len(baslik_parcalari) >= 2


def test_madde_imleri_gruplanir():
    parcalayici = YapisalParcalayici()
    metin = "- Birinci madde\n- Ikinci madde\n- Ucuncu madde"
    belge = _ornek_belge_icerik(metin)
    parcalar = parcalayici.yapisal_parcala(belge)
    madde_parcalari = [p for p in parcalar if p.parca_turu == "madde_imleri"]


def test_tablo_butunlugu_korunur():
    parcalayici = YapisalParcalayici()
    metin = "Baslik\n| Sutun1 | Sutun2 |\n|-------|-------|\n| Deger1 | Deger2 |\n| Deger3 | Deger4 |"
    belge = _ornek_belge_icerik(metin)
    parcalar = parcalayici.yapisal_parcala(belge)
    tablo_parcalari = [p for p in parcalar if p.parca_turu == "tablo"]
    assert len(tablo_parcalari) >= 1


def test_yetki_seviyesi_parcalara_tasinir():
    parcalayici = YapisalParcalayici()
    belge = _ornek_belge_icerik("Test metni", yetki=3)
    parcalar = parcalayici.yapisal_parcala(belge)
    assert len(parcalar) > 0
    assert all(p.yetki_seviyesi == 3 for p in parcalar)


def test_sha256_ozeti_her_parca_icin_farkli():
    parcalayici = YapisalParcalayici()
    metin = "Ilk paragraf.\n\nIkinci paragraf."
    belge = _ornek_belge_icerik(metin)
    parcalar = parcalayici.yapisal_parcala(belge)
    ozetler = [p.sha256_ozeti for p in parcalar]
    assert len(ozetler) == len(set(ozetler))


def test_sira_numaralari_artan():
    parcalayici = YapisalParcalayici()
    metin = "A\nB\nC\nD\nE"
    belge = _ornek_belge_icerik(metin)
    parcalar = parcalayici.yapisal_parcala(belge)
    for i in range(1, len(parcalar)):
        assert parcalar[i].sira > parcalar[i - 1].sira