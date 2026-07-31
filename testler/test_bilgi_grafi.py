from uygulama.servisler.bilgi_grafi import BilgiGrafi, GrafIliskisi


def test_tfidf_kavram_cikar_bos_metin():
    grafi = BilgiGrafi()
    assert grafi._tfidf_kavram_cikar("") == []


def test_tfidf_kavram_cikar_tekrarlayan():
    grafi = BilgiGrafi()
    sonuc = grafi._tfidf_kavram_cikar(
        "fatura fatura fatura odeme belge sistem modul"
    )
    assert "fatura" in sonuc


def test_tfidf_kavram_cikar_stop_kelimeler():
    grafi = BilgiGrafi()
    sonuc = grafi._tfidf_kavram_cikar("bir icin ile bu kadar")
    assert sonuc == []


def test_graf_insa_et_jaccard():
    grafi = BilgiGrafi()
    belgeler = {
        "belge1": ["fatura", "odeme", "sistem"],
        "belge2": ["fatura", "modul", "kullanici"],
    }
    iliskiler = grafi.graf_insa_et(belgeler)
    assert len(iliskiler) == 1
    assert iliskiler[0].iliski_turu == "ortak_kavram"


def test_graf_skor_hesapla():
    grafi = BilgiGrafi()
    sorgu = ["fatura", "odeme"]
    belgeler = {
        "belge1": ["fatura", "odeme", "sistem"],
        "belge2": ["modul", "kullanici"],
    }
    skorlar = grafi.graf_skor_hesapla(sorgu, belgeler)
    assert len(skorlar) == 1
    assert "belge1" in skorlar


def test_komsuluk_ekle_ve_bul():
    grafi = BilgiGrafi()
    grafi.komsuluk_ekle("a", "b")
    grafi.komsuluk_ekle("b", "c")
    komsular = grafi.komsulari_bul("a", derinlik=2)
    assert "b" in komsular
    assert "c" in komsular
    assert "a" not in komsular