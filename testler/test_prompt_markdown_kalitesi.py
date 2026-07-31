from uygulama.servisler.deepseek_servisi import _SISTEM_TALIMATI


class TestPromptMarkdownKalitesi:
    def test_prompt_markdown_talimati_icerir(self):
        assert "Markdown" in _SISTEM_TALIMATI

    def test_prompt_kalin_vurgu_ornegi_icerir(self):
        assert "**kalin**" in _SISTEM_TALIMATI

    def test_prompt_liste_ornegi_icerir(self):
        assert "* madde" in _SISTEM_TALIMATI.lower()