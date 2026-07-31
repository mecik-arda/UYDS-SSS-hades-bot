import re


def _markdown_donustur(metin):
    if not metin:
        return ""
    temiz = metin
    temiz = temiz.replace("&", r"&")
    temiz = temiz.replace("<", r"<")
    temiz = temiz.replace(">", r">")
    temiz = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", temiz)
    temiz = re.sub(r"^\* (.*$)", r"<li>\1</li>", temiz, flags=re.M)
    temiz = re.sub(r"((?:<li>.*</li>\n?)+)", r"<ul>\1</ul>", temiz)
    temiz = re.sub(
        r"\[Kaynak (\d+)\]",
        r'<span class="kaynak-rozet">Kaynak \1</span>',
        temiz,
    )
    temiz = temiz.replace("\n", "<br>")
    return temiz


class TestMarkdownDonusturme:
    def test_kalin_vurgu(self):
        sonuc = _markdown_donustur("Bu **onemli** bir mesajdir")
        assert "<strong>onemli</strong>" in sonuc

    def test_liste_maddesi(self):
        sonuc = _markdown_donustur("* Birinci madde")
        assert "<li>Birinci madde</li>" in sonuc

    def test_kaynak_rozeti(self):
        sonuc = _markdown_donustur("Bkz. [Kaynak 5]")
        assert '<span class="kaynak-rozet">Kaynak 5</span>' in sonuc

    def test_satir_sonu(self):
        sonuc = _markdown_donustur("birinci\nikinci")
        assert "<br>" in sonuc

    def test_bos_metin(self):
        sonuc = _markdown_donustur("")
        assert sonuc == ""

    def test_birden_fazla_donusum(self):
        sonuc = _markdown_donustur("**Baslik**\n* Madde 1\n* Madde 2")
        assert "<strong>Baslik</strong>" in sonuc
        assert "<li>Madde 1</li>" in sonuc
        assert "<li>Madde 2</li>" in sonuc

    def test_birden_fazla_kaynak_rozeti(self):
        sonuc = _markdown_donustur("[Kaynak 1] ve [Kaynak 3] referanslari")
        assert '<span class="kaynak-rozet">Kaynak 1</span>' in sonuc
        assert '<span class="kaynak-rozet">Kaynak 3</span>' in sonuc

    def test_duz_metin_degismez(self):
        sonuc = _markdown_donustur("Normal bir metin, hicbir ozel isaret yok.")
        assert sonuc == "Normal bir metin, hicbir ozel isaret yok."