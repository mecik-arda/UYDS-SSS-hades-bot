import os
from contextlib import contextmanager
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl


def veritabani_kilit_yolunu_al(veritabani_yolu: Path) -> Path:
    return veritabani_yolu.parent / f".{veritabani_yolu.name}.kilit"


@contextmanager
def surecler_arasi_veritabani_kilidi(
    veritabani_yolu: Path,
    paylasimli: bool,
):
    kilit_yolu = veritabani_kilit_yolunu_al(veritabani_yolu)
    kilit_yolu.parent.mkdir(parents=True, exist_ok=True)
    with kilit_yolu.open("a+b") as kilit_dosyasi:
        kilit_dosyasi.seek(0, os.SEEK_END)
        if kilit_dosyasi.tell() == 0:
            kilit_dosyasi.write(b"\0")
            kilit_dosyasi.flush()
        kilit_dosyasi.seek(0)
        if os.name == "nt":
            kilit_turu = msvcrt.LK_RLCK if paylasimli else msvcrt.LK_LOCK
            msvcrt.locking(kilit_dosyasi.fileno(), kilit_turu, 1)
        else:
            kilit_turu = fcntl.LOCK_SH if paylasimli else fcntl.LOCK_EX
            fcntl.flock(kilit_dosyasi.fileno(), kilit_turu)
        try:
            yield
        finally:
            kilit_dosyasi.seek(0)
            if os.name == "nt":
                msvcrt.locking(kilit_dosyasi.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(kilit_dosyasi.fileno(), fcntl.LOCK_UN)
