from typing import Protocol, runtime_checkable

from uygulama.modeller.semalar import AramaAdayi


@runtime_checkable
class YenidenSiralayiciProtokolu(Protocol):
    def yeniden_sirala(
        self,
        soru: str,
        adaylar: list[AramaAdayi],
    ) -> list[AramaAdayi]:
        raise NotImplementedError
