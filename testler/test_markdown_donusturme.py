import re


def _markdown_donustur(metin):
    if not metin:
        return ""
    temiz = metin
    temiz = temiz.replace("&", "&amp;")
    temiz = temiz.replace("<", "&lt;")
    temiz = temiz.replace(">", "&gt;")
    temiz = temiz.replace('"', "&quot;")
    temiz = temiz.replace("'", "&#39;")
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

    def test_html_etiketleri_kodlanir(self):
        sonuc = _markdown_donustur(
            '<img src="gecersiz" onerror="alert(1)">'
        )
        assert "<img" not in sonuc
        assert "&lt;img" in sonuc
        assert "&quot;gecersiz&quot;" in sonuc

    def test_markdown_icindeki_html_kodlanir(self):
        sonuc = _markdown_donustur("**<script>alert('x')</script>**")
        assert sonuc.startswith("<strong>&lt;script&gt;")
        assert "<script>" not in sonuc


def test_uygulama_betigi_gercek_html_kacisini_icerir():
    from pathlib import Path

    betik = Path("uygulama/statik/js/uygulama.js").read_text(
        encoding="utf-8"
    )
    assert 'replace(/&/g, "&amp;")' in betik
    assert 'replace(/</g, "&lt;")' in betik
    assert 'replace(/>/g, "&gt;")' in betik
