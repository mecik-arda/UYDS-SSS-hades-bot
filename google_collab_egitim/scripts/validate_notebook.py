"""
Notebook validasyon script'i — JSON geçerliliği, hücre sözdizimi,
güvenlik kontrolleri, checkpoint_kaydet çağrısı, smoke kalite kapısı,
doğrudan belge karşılaştırması kontrollerini yapar.
"""
import json
import os
import sys
import re
import ast


PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTEBOOK_YOLU = os.path.join(PROJE_KOKU, "veri_ayiklama_v4.1.ipynb")

ZORUNLU_KONTROLLER = [
    "checkpoint_kaydet",
    "hata_orani > 0.05",
    "ky_orani > 0.80",
    "dogrudan_ilgili",
    "RuntimeError",
    "SystemExit",
    "classify_relevance.py",
]

hata_sayisi = 0


def hata(mesaj):
    global hata_sayisi
    print(f"  HATA: {mesaj}")
    hata_sayisi += 1


def bilgi(mesaj):
    print(f"  {mesaj}")


print("=" * 60)
print("  Notebook Validasyonu")
print("=" * 60)

print(f"\nNotebook: {NOTEBOOK_YOLU}")

try:
    with open(NOTEBOOK_YOLU, "r", encoding="utf-8") as f:
        nb = json.load(f)
    bilgi(f"JSON geçerli")
except Exception as e:
    hata(f"JSON hatası: {e}")
    sys.exit(1)

cells = nb.get("cells", [])
kod_hucresi = [c for c in cells if c["cell_type"] == "code"]
md_hucresi = [c for c in cells if c["cell_type"] == "markdown"]
bilgi(f"Hücre: {len(cells)} toplam ({len(kod_hucresi)} kod, {len(md_hucresi)} markdown)")

if len(kod_hucresi) < 8:
    hata(f"Kod hücresi sayısı düşük: {len(kod_hucresi)}")

tum_kod = ""
for i, c in enumerate(kod_hucresi):
    cid = c["metadata"].get("id", f"hücre_{i}")
    source = "".join(c["source"])

    python_satirlar = []
    for satir in source.split("\n"):
        stripped = satir.strip()
        if stripped.startswith("!") or stripped.startswith("%"):
            continue
        python_satirlar.append(satir)
    temiz_kod = "\n".join(python_satirlar)

    if not temiz_kod.strip():
        continue

    try:
        ast.parse(temiz_kod)
    except SyntaxError as e:
        hata(f"[{cid}] SyntaxError: {e}")

    tum_kod += temiz_kod + "\n"

for anahtar in ZORUNLU_KONTROLLER:
    if anahtar not in tum_kod:
        hata(f"Zorunlu kontrol bulunamadı: '{anahtar}'")

if "def pdf_metin_uzunlugu" in tum_kod and "gecici.unlink(missing_ok=True)" in tum_kod:
    bilgi("OCR .g_gecici temizliği: var")
else:
    hata("OCR .g_gecici temizliği: EKSİK")

nbformat = nb.get("nbformat", 0)
nbformat_minor = nb.get("nbformat_minor", 0)
bilgi(f"nbformat: {nbformat}.{nbformat_minor}")

print(f"\nSonuç: {'BASARILI' if hata_sayisi == 0 else f'{hata_sayisi} HATA'}")
sys.exit(0 if hata_sayisi == 0 else 1)
