import hashlib
from collections import defaultdict
from dataclasses import dataclass, field

from uygulama.cekirdek.gunlukleyici import gunlukleyici
from uygulama.cekirdek.konfigurasyon import konfigurasyon


@dataclass(frozen=True)
class GrafDugumu:
    etiket: str
    dugum_turu: str
    ozellikler: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GrafIliskisi:
    kaynak: str
    hedef: str
    iliski_turu: str
    agirlik: float = 1.0


@dataclass(frozen=True)
class GrafAramaSonucu:
    dugumler: list[GrafDugumu]
    iliskiler: list[GrafIliskisi]
    skor_bonusu: float


class BilgiGrafi:
    def __init__(self) -> None:
        self._komsuluk = defaultdict(set)

    def kavram_cikar(
        self,
        metin: str,
    ) -> list[str]:
        if not konfigurasyon.GRAF_AKTIF:
            return []
        strateji = konfigurasyon.GRAF_KAVRAM_STRATEJISI
        if strateji == "hafif":
            return self._tfidf_kavram_cikar(metin)
        if strateji == "ner":
            return self._ner_kavram_cikar(metin)
        return []

    def _tfidf_kavram_cikar(self, metin: str) -> list[str]:
        kelimeler = metin.lower().split()
        siklik = {}
        for kelime in kelimeler:
            temiz = "".join(
                karakter
                for karakter in kelime
                if karakter.isalnum() or karakter == "_"
            )
            if len(temiz) < 3 or temiz in {
                "bir",
                "icin",
                "ile",
                "bu",
                "da",
                "de",
                "ve",
                "veya",
                "ise",
                "ama",
                "fakat",
                "gibi",
                "kadar",
                "sonra",
                "once",
            }:
                continue
            siklik[temiz] = siklik.get(temiz, 0) + 1
        if not siklik:
            return []
        en_yuksek = max(siklik.values())
        return [
            kelime
            for kelime, sayi in sorted(
                siklik.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
            if sayi >= max(2, en_yuksek * 0.3)
        ]

    def _ner_kavram_cikar(self, metin: str) -> list[str]:
        return []

    def graf_insa_et(
        self,
        belge_kavramlari: dict[str, list[str]],
    ) -> list[GrafIliskisi]:
        iliskiler = []
        belgeler = list(belge_kavramlari.keys())
        for idx, belge_a in enumerate(belgeler):
            for belge_b in belgeler[idx + 1:]:
                ortak = set(belge_kavramlari[belge_a]) & set(
                    belge_kavramlari[belge_b]
                )
                if ortak:
                    jaccard = len(ortak) / len(
                        set(belge_kavramlari[belge_a])
                        | set(belge_kavramlari[belge_b])
                    )
                    iliskiler.append(
                        GrafIliskisi(
                            kaynak=belge_a,
                            hedef=belge_b,
                            iliski_turu="ortak_kavram",
                            agirlik=round(jaccard, 4),
                        )
                    )
        return iliskiler

    def graf_skor_hesapla(
        self,
        sorgu_kavramlari: list[str],
        belge_kavramlari: dict[str, list[str]],
    ) -> dict[str, float]:
        skorlar = {}
        for belge, kavramlar in belge_kavramlari.items():
            ortak = set(sorgu_kavramlari) & set(kavramlar)
            if ortak:
                skorlar[belge] = len(ortak) / len(
                    set(sorgu_kavramlari) | set(kavramlar)
                )
        return skorlar

    def komsuluk_ekle(
        self,
        kaynak: str,
        hedef: str,
    ) -> None:
        self._komsuluk[kaynak].add(hedef)
        self._komsuluk[hedef].add(kaynak)

    def komsulari_bul(
        self,
        dugum: str,
        derinlik: int = 1,
    ) -> set[str]:
        if derinlik < 1:
            return set()
        ziyaret = {dugum}
        seviye = [dugum]
        for _ in range(derinlik):
            sonraki_seviye = []
            for dugum_adi in seviye:
                for komsu in self._komsuluk.get(dugum_adi, set()):
                    if komsu not in ziyaret:
                        ziyaret.add(komsu)
                        sonraki_seviye.append(komsu)
            seviye = sonraki_seviye
            if not seviye:
                break
        ziyaret.discard(dugum)
        return ziyaret
