import re

_TC_KIMLIK_KALIBI = re.compile(r"\b[1-9]\d{10}\b")
_IBAN_KALIBI = re.compile(r"\bTR\d{24}\b", re.IGNORECASE)
_TELEFON_KALIBI = re.compile(r"\b05\d{9}\b")
_KREDI_KARTI_KALIBI = re.compile(r"\b\d{16}\b")
_EPOSTA_KALIBI = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)


class PiiMaskeleyici:
    @staticmethod
    def tc_kimlik_maskele(metin: str) -> str:
        return _TC_KIMLIK_KALIBI.sub("***********", metin)

    @staticmethod
    def iban_maskele(metin: str) -> str:
        def _iban_degistirici(eslesme):
            iban = eslesme.group(0)
            return iban[:2] + iban[2:6] + "****" + iban[-4:]

        return _IBAN_KALIBI.sub(_iban_degistirici, metin)

    @staticmethod
    def telefon_maskele(metin: str) -> str:
        return _TELEFON_KALIBI.sub("05*********", metin)

    @staticmethod
    def kredi_karti_maskele(metin: str) -> str:
        def _kart_degistirici(eslesme):
            kart = eslesme.group(0)
            return "****-****-****-" + kart[-4:]

        return _KREDI_KARTI_KALIBI.sub(_kart_degistirici, metin)

    @staticmethod
    def eposta_maskele(metin: str) -> str:
        def _eposta_degistirici(eslesme):
            eposta = eslesme.group(0)
            yerel, alan = eposta.split("@", 1)
            yerel_maske = yerel[0] + "***" if len(yerel) > 1 else "***"
            alan_parcalari = alan.split(".")
            alan_maske = alan_parcalari[0][0] + "***" if alan_parcalari else "***"
            tld = alan_parcalari[-1] if len(alan_parcalari) > 1 else ""
            return yerel_maske + "@" + alan_maske + "." + tld if tld else yerel_maske + "@" + alan_maske

        return _EPOSTA_KALIBI.sub(_eposta_degistirici, metin)

    @staticmethod
    def tumunu_maskele(metin: str) -> str:
        sonuc = metin
        sonuc = PiiMaskeleyici.tc_kimlik_maskele(sonuc)
        sonuc = PiiMaskeleyici.iban_maskele(sonuc)
        sonuc = PiiMaskeleyici.telefon_maskele(sonuc)
        sonuc = PiiMaskeleyici.kredi_karti_maskele(sonuc)
        sonuc = PiiMaskeleyici.eposta_maskele(sonuc)
        return sonuc

    @staticmethod
    def maskeleme_istatistikleri(metin: str) -> dict:
        return {
            "tc_kimlik_sayisi": len(_TC_KIMLIK_KALIBI.findall(metin)),
            "iban_sayisi": len(_IBAN_KALIBI.findall(metin)),
            "telefon_sayisi": len(_TELEFON_KALIBI.findall(metin)),
            "kredi_karti_sayisi": len(_KREDI_KARTI_KALIBI.findall(metin)),
            "eposta_sayisi": len(_EPOSTA_KALIBI.findall(metin)),
        }