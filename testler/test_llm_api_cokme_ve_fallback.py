import pytest
from fastapi.testclient import TestClient

from uygulama.ana import uygulama


@pytest.fixture
def istemci():
    return TestClient(uygulama)


class TestLLMAPIFallback:
    def test_saglik_kontrolu_calisir(self, istemci):
        yanit = istemci.get("/api/saglik")
        assert yanit.status_code == 200