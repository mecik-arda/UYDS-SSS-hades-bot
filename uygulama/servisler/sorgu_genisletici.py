import re
from dataclasses import dataclass

from uygulama.servisler.terim_haritasi import (
    TerimHaritasi,
    TerimHaritasiHatasi,
    sorguyu_normalize_et,
)

MAKS_GENISLETME_TERIMI = 15
KISA_SORGU_KELIME_ESIGI = 8
_DOLGU_KELIMELERI = frozenset({
    "nasil", "nedir", "ne", "acaba", "mi", "mu", "mü",
    "kadar", "icin", "ile", "ve", "veya", "bir", "bu", "su", "şu",
    "o", "da", "de", "dir", "dır", "dur", "dür", "tir", "tır",
    "ki", "ise", "gibi", "daha", "en", "cok", "çok", "ama",
    "fakat", "lakin", "ancak", "yani", "sadece", "yalnizca",
    "yali", "her", "tum", "tüm", "bazi", "bazı", "hangi",
    "neden", "niye", "niçin", "nicin", "nerede", "nereye",
    "nereden", "kim", "kimi", "neyle",
    "olur", "olabilir", "yapilir", "edilir",
    "gerekiyor", "gerekir", "lazim", "lazım", "var",
})
_ISTISNA_KELIMELERI = frozenset({
    "ctr", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8",
    "teu", "tact", "edi", "ft", "cd", "3k", "pdks", "kpi",
    "ct", "c&su", "hb", "bl", "awb", "cmr", "ba", "bs",
    "kdv", "tl", "eur", "usd", "mts", "gdl", "t04", "t06",
})
_YAZIM_DUZELTMELERI = {
    "pesronel": "personel",
    "personeli": "personel",
    "calisilmayan": "çalışılmayan",
    "musteri": "müşteri",
    "musteriler": "müşteriler",
    "musterisi": "müşterisi",
    "musterisini": "müşterisini",
    "sirket": "şirket",
    "sirketi": "şirketi",
    "sirketinde": "şirketinde",
    "sirkette": "şirkette",
    "firmasi": "firması",
    "firmasinda": "firmasında",
    "giris": "giriş",
    "girisi": "girişi",
    "girisinde": "girişinde",
    "cikis": "çıkış",
    "cikisi": "çıkışı",
    "cikisinda": "çıkışında",
    "degisikligi": "değişikliği",
    "degisiklik": "değişiklik",
    "olusturma": "oluşturma",
    "olusturulmasi": "oluşturulması",
    "guncelleme": "güncelleme",
    "guncellenmesi": "güncellenmesi",
    "guncellemesi": "güncellemesi",
    "goruntuleme": "görüntüleme",
    "goruntulenmesi": "görüntülenmesi",
    "goruntuleyemiyor": "görüntüleyemiyor",
    "goruntuleyemiyorum": "görüntüleyemiyorum",
    "duzeltme": "düzeltme",
    "duzeltilmesi": "düzeltilmesi",
    "kayit": "kayıt",
    "kaydi": "kaydı",
    "kayitlari": "kayıtları",
    "fisi": "fişi",
    "fisiyle": "fişiyle",
    "islem": "işlem",
    "islemi": "işlemi",
    "islemleri": "işlemleri",
    "yapilamiyor": "yapılamıyor",
    "yapilamiyo": "yapılamıyor",
    "yapamiyoruz": "yapamıyoruz",
    "yapilmiyor": "yapılmıyor",
    "basilamiyor": "basılamıyor",
    "alinamiyor": "alınamıyor",
    "gelmiyor": "gelmiyor",
    "gelmemesi": "gelmemesi",
    "gonderemiyor": "gönderemiyor",
    "gonderelemiyor": "gönderilemiyor",
    "goruntulenemiyor": "görüntülenemiyor",
    "silinemiyor": "silinemiyor",
    "acilamiyor": "açılamıyor",
    "hatasi": "hatası",
    "hatasini": "hatasını",
    "hata": "hata",
    "acil": "acil",
    "destek": "destek",
}
_FTS_OZEL_KARAKTERLERI = re.compile(r'["()\-*]')
_SINIR_ONCESI = r"(?<!\w)"
_SINIR_SONRASI = r"(?!\w)"
_ESLESME_ANAHTARI_CEVIRISI = str.maketrans({"ı": "i"})


@dataclass(frozen=True)
class GenisletilmisSorgu:
    fts_sorgusu: str
    genisletilen_terim_sayisi: int
    kullanilan_grup_sayisi: int


class SorguGenisletmeHatasi(ValueError):
    def __init__(self, mesaj: str) -> None:
        super().__init__(mesaj)


class SorguGenisletici:
    def __init__(self, terim_haritasi: TerimHaritasi) -> None:
        self._harita = terim_haritasi
        self._gruplar = self._harita.yukle()
        tum_terimler = []
        for ana_terim, es_anlamlilar in self._gruplar.items():
            for terim in (ana_terim,) + es_anlamlilar:
                tum_terimler.append((terim, ana_terim))
        tum_terimler.sort(key=lambda x: len(x[0]), reverse=True)
        self._sirali_terimler = tum_terimler
        self._yedek_sirali_terimler = [
            (self._eslesme_anahtarini_olustur(terim), ana_terim)
            for terim, ana_terim in tum_terimler
        ]

    def genislet(self, ham_soru: str) -> GenisletilmisSorgu:
        try:
            duzeltilmis_soru = self._yazim_duzelt(ham_soru)
            normalize_soru = (
                sorguyu_normalize_et(duzeltilmis_soru)
                if duzeltilmis_soru.strip()
                else ""
            )
        except TerimHaritasiHatasi as hata:
            raise SorguGenisletmeHatasi("Sorgu gecersiz") from hata
        if not normalize_soru:
            raise SorguGenisletmeHatasi("Sorgu bos veya gecersiz")
        eslesen_araliklar = self._araliklari_bul(normalize_soru)
        if not eslesen_araliklar:
            return self._sadece_orijinal_terimler(normalize_soru)
        fts_parcalari = []
        genisletilen_terim_sayisi = 0
        islenen_ana_terimler: set[str] = set()
        islenen_araliklar = []
        for baslangic, bitis, ana_terim in eslesen_araliklar:
            if ana_terim in islenen_ana_terimler:
                islenen_araliklar.append((baslangic, bitis, ana_terim))
                continue
            grup_terimleri = (ana_terim,) + self._gruplar[ana_terim]
            if genisletilen_terim_sayisi + len(grup_terimleri) > MAKS_GENISLETME_TERIMI:
                continue
            fts_parcalari.append(self._or_grubu_olustur(grup_terimleri))
            genisletilen_terim_sayisi += len(grup_terimleri)
            islenen_ana_terimler.add(ana_terim)
            islenen_araliklar.append((baslangic, bitis, ana_terim))
        kalan_anlamlilar = self._anlamli_kelimeleri_cikar(
            normalize_soru,
            islenen_araliklar,
        )
        fts_parcalari.extend(
            self._fts_kelimesine_donustur(kelime) for kelime in kalan_anlamlilar
        )
        if not fts_parcalari:
            return self._sadece_orijinal_terimler(normalize_soru)
        kalan_anlamli_sayisi = len(kalan_anlamlilar)
        eslesen_grup_sayisi = len(islenen_ana_terimler)
        toplam_anlamli = kalan_anlamli_sayisi + eslesen_grup_sayisi
        kisa_sorgu = toplam_anlamli <= KISA_SORGU_KELIME_ESIGI
        operator = " OR " if kisa_sorgu else " AND "
        return GenisletilmisSorgu(
            fts_sorgusu=operator.join(fts_parcalari),
            genisletilen_terim_sayisi=min(
                genisletilen_terim_sayisi,
                MAKS_GENISLETME_TERIMI,
            ),
            kullanilan_grup_sayisi=len(islenen_ana_terimler),
        )

    def _araliklari_bul(self, metin: str) -> list[tuple[int, int, str]]:
        sonuc = []
        isgal_edilen_konumlar = set()
        self._eslesmeleri_ekle(
            metin,
            self._sirali_terimler,
            isgal_edilen_konumlar,
            sonuc,
        )
        if len(sonuc) < MAKS_GENISLETME_TERIMI:
            self._eslesmeleri_ekle(
                self._eslesme_anahtarini_olustur(metin),
                self._yedek_sirali_terimler,
                isgal_edilen_konumlar,
                sonuc,
            )
        return sonuc

    def _eslesmeleri_ekle(
        self,
        metin: str,
        sirali_terimler: list[tuple[str, str]],
        isgal_edilen_konumlar: set[int],
        sonuc: list[tuple[int, int, str]],
    ) -> None:
        for terim, ana_terim in sirali_terimler:
            desen = _SINIR_ONCESI + re.escape(terim) + _SINIR_SONRASI
            for eslesme in re.finditer(desen, metin):
                baslangic = eslesme.start()
                bitis = eslesme.end()
                aralik = set(range(baslangic, bitis))
                if not aralik & isgal_edilen_konumlar:
                    isgal_edilen_konumlar.update(aralik)
                    sonuc.append((baslangic, bitis, ana_terim))
                    if len(sonuc) >= MAKS_GENISLETME_TERIMI:
                        return

    def _anlamli_kelimeleri_cikar(
        self,
        metin: str,
        islenen_araliklar: list[tuple[int, int, str]],
    ) -> list[str]:
        maskelenmis_metin = list(metin)
        for baslangic, bitis, _ in islenen_araliklar:
            for konum in range(baslangic, bitis):
                maskelenmis_metin[konum] = " "
        kalan = "".join(maskelenmis_metin)
        kelimeler = re.findall(r"\w+", kalan)
        return [
            kelime
            for kelime in kelimeler
            if kelime not in _DOLGU_KELIMELERI
            and (len(kelime) > 1 or kelime.lower() in _ISTISNA_KELIMELERI)
        ]

    def _or_grubu_olustur(self, terimler: tuple[str, ...]) -> str:
        kacirilmis_terimler = [
            self._fts_kelimesine_donustur(terim) for terim in terimler
        ]
        if len(kacirilmis_terimler) == 1:
            return kacirilmis_terimler[0]
        return "(" + " OR ".join(kacirilmis_terimler) + ")"

    def _fts_kelimesine_donustur(self, kelime: str) -> str:
        temiz = _FTS_OZEL_KARAKTERLERI.sub(" ", kelime).strip()
        if not temiz:
            return f'"{kelime}"'
        if " " in temiz:
            return f'"{temiz}"'
        return f'"{temiz}"'

    def _sadece_orijinal_terimler(self, metin: str) -> GenisletilmisSorgu:
        kelimeler = re.findall(r"\w+", metin)
        anlamlilar = [
            kelime
            for kelime in kelimeler
            if kelime not in _DOLGU_KELIMELERI
            and (len(kelime) > 1 or kelime.lower() in _ISTISNA_KELIMELERI)
        ]
        if not anlamlilar:
            raise SorguGenisletmeHatasi("Sorguda anlamli kelime bulunamadi")
        fts_parcalari = [
            self._fts_kelimesine_donustur(kelime) for kelime in anlamlilar
        ]
        kisa_sorgu = len(anlamlilar) <= KISA_SORGU_KELIME_ESIGI
        operator = " OR " if kisa_sorgu else " AND "
        return GenisletilmisSorgu(
            fts_sorgusu=operator.join(fts_parcalari),
            genisletilen_terim_sayisi=0,
            kullanilan_grup_sayisi=0,
        )

    def _eslesme_anahtarini_olustur(self, metin: str) -> str:
        return metin.translate(_ESLESME_ANAHTARI_CEVIRISI)

    def _yazim_duzelt(self, metin: str) -> str:
        kelimeler = re.findall(r"\w+", metin)
        duzeltilmis = metin
        for kelime in kelimeler:
            kucuk = kelime.lower()
            if kucuk in _YAZIM_DUZELTMELERI:
                duzeltilmis = re.sub(
                    r"\b" + re.escape(kelime) + r"\b",
                    _YAZIM_DUZELTMELERI[kucuk],
                    duzeltilmis,
                    count=1,
                )
        return duzeltilmis