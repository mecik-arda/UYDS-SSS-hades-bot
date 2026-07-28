from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class IstekGovdesiBoyutMiddleware:
    def __init__(
        self,
        uygulama: ASGIApp,
        maksimum_boyut: int,
        dosya_yukleme_maksimum_boyutu: int,
        dosya_yukleme_yollari: set[str],
    ) -> None:
        self.uygulama = uygulama
        self.maksimum_boyut = maksimum_boyut
        self.dosya_yukleme_maksimum_boyutu = dosya_yukleme_maksimum_boyutu
        self.dosya_yukleme_yollari = dosya_yukleme_yollari

    async def __call__(self, kapsam: Scope, al: Receive, gonder: Send) -> None:
        if kapsam["type"] != "http":
            await self.uygulama(kapsam, al, gonder)
            return

        istek_yolu = kapsam.get("path", "")
        izin_verilen_boyut = (
            self.dosya_yukleme_maksimum_boyutu
            if istek_yolu in self.dosya_yukleme_yollari
            else self.maksimum_boyut
        )
        basliklar = dict(kapsam.get("headers", []))
        icerik_uzunlugu = basliklar.get(b"content-length")
        if icerik_uzunlugu is not None:
            try:
                bildirilen_boyut = int(icerik_uzunlugu)
                if bildirilen_boyut < 0:
                    await self._gecersiz_uzunluk_hatasi_gonder(kapsam, gonder)
                    return
                if bildirilen_boyut > izin_verilen_boyut:
                    await self._boyut_hatasi_gonder(
                        kapsam,
                        gonder,
                        izin_verilen_boyut,
                    )
                    return
            except ValueError:
                await self._gecersiz_uzunluk_hatasi_gonder(kapsam, gonder)
                return

        mesajlar: list[Message] = []
        toplam_boyut = 0
        daha_fazla_govde_var = True
        while daha_fazla_govde_var:
            mesaj = await al()
            if mesaj["type"] == "http.disconnect":
                return
            govde = mesaj.get("body", b"")
            toplam_boyut += len(govde)
            if toplam_boyut > izin_verilen_boyut:
                await self._boyut_hatasi_gonder(
                    kapsam,
                    gonder,
                    izin_verilen_boyut,
                )
                return
            mesajlar.append(mesaj)
            daha_fazla_govde_var = mesaj.get("more_body", False)

        mesaj_indeksi = 0

        async def sinirli_al() -> Message:
            nonlocal mesaj_indeksi
            if mesaj_indeksi < len(mesajlar):
                mesaj = mesajlar[mesaj_indeksi]
                mesaj_indeksi += 1
                return mesaj
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.uygulama(kapsam, sinirli_al, gonder)

    async def _boyut_hatasi_gonder(
        self,
        kapsam: Scope,
        gonder: Send,
        izin_verilen_boyut: int,
    ) -> None:
        yanit = JSONResponse(
            status_code=413,
            content={
                "detay": "Istek govdesi izin verilen boyutu asiyor",
                "maksimum_boyut": izin_verilen_boyut,
            },
        )
        await yanit(kapsam, self._bos_istek_al, gonder)

    async def _gecersiz_uzunluk_hatasi_gonder(
        self,
        kapsam: Scope,
        gonder: Send,
    ) -> None:
        yanit = JSONResponse(
            status_code=400,
            content={"detay": "Gecersiz Content-Length basligi"},
        )
        await yanit(kapsam, self._bos_istek_al, gonder)

    async def _bos_istek_al(self) -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}
