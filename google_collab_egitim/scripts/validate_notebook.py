#!/usr/bin/env python3
# ============================================================
# validate_notebook.py — Notebook gerçek doğrulama
# ============================================================
"""
veri_ayiklama_v4.1.ipynb için gerçek doğrulama:

  1. nbformat.validate — JSON şema kontrolü
  2. Her kod hücresi ast.parse ile derleme (magic/shell ayrılır)
  3. Notebook'taki `from src.X import Y` cümlelerini gerçek src
     paketinde çözme — import drift'ini yakalar
  4. Zorunlu güvenlik bağlantıları: ortak fonksiyonlar çağrılıyor mu?
  5. Hücre sırası: kullanılan adlar önceki hücrelerde tanımlı mı?

Hata varsa exit code 1 döner.
"""

import ast
import importlib
import json
import os
import sys
import builtins

PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTEBOOK_YOLU = os.path.join(PROJE_KOKU, "veri_ayiklama_v4.1.ipynb")

sys.path.insert(0, PROJE_KOKU)

try:
    import nbformat
except ImportError:
    print("HATA: nbformat kurulu değil (pip install nbformat)")
    sys.exit(1)


hata_sayisi = 0
uyari_sayisi = 0


def hata(mesaj):
    global hata_sayisi
    print(f"  ✗ HATA: {mesaj}")
    hata_sayisi += 1


def uyari(mesaj):
    global uyari_sayisi
    print(f"  ⚠ UYARI: {mesaj}")
    uyari_sayisi += 1


def bilgi(mesaj):
    print(f"  ✓ {mesaj}")


def hucre_python_kaynagi(hucre):
    """Magic/shell satırlarını ayırıp Python kodunu döndürür."""
    source = "".join(hucre.source)
    satirlar = []
    for satir in source.split("\n"):
        stripped = satir.strip()
        if stripped.startswith("!") or stripped.startswith("%"):
            continue
        satirlar.append(satir)
    return "\n".join(satirlar)


def cozulebilir_importlar(kod):
    """AST'den `from MOD import AD` ve `import MOD` düğümlerini çıkarır."""
    sonuc = []
    try:
        agac = ast.parse(kod)
    except SyntaxError:
        return sonuc
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.ImportFrom):
            mod = dugum.module or ""
            for ad in dugum.names:
                sonuc.append((mod, ad.name, dugum.lineno))
        elif isinstance(dugum, ast.Import):
            for ad in dugum.names:
                sonuc.append((None, ad.name if ad.asname is None else ad.name, dugum.lineno))
    return sonuc


def _hedef_adlari(hedef, adlar):
    """Atama hedefinden (tuple/list/starred dahil) adları çıkarır."""
    if isinstance(hedef, ast.Name):
        adlar.add(hedef.id)
    elif isinstance(hedef, (ast.Tuple, ast.List)):
        for el in hedef.elts:
            _hedef_adlari(el, adlar)
    elif isinstance(hedef, ast.Starred):
        _hedef_adlari(hedef.value, adlar)


def tanimlanan_adlar(agac):
    """AST'den hücre içi tanımlanan adları (parametre/unpack/döngü dahil) toplar."""
    adlar = set()
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Assign):
            for hedef in dugum.targets:
                _hedef_adlari(hedef, adlar)
        elif isinstance(dugum, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            _hedef_adlari(dugum.target, adlar)
        elif isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            adlar.add(dugum.name)
            for arg in list(dugum.args.args) + list(dugum.args.posonlyargs) + list(dugum.args.kwonlyargs):
                if arg.arg:
                    adlar.add(arg.arg)
            if dugum.args.vararg:
                adlar.add(dugum.args.vararg.arg)
            if dugum.args.kwarg:
                adlar.add(dugum.args.kwarg.arg)
        elif isinstance(dugum, ast.Import):
            for ad in dugum.names:
                adlar.add((ad.asname or ad.name).split(".")[0])
        elif isinstance(dugum, ast.ImportFrom):
            for ad in dugum.names:
                adlar.add(ad.asname or ad.name)
        elif isinstance(dugum, (ast.For, ast.AsyncFor)):
            _hedef_adlari(dugum.target, adlar)
        elif isinstance(dugum, ast.comprehension):
            _hedef_adlari(dugum.target, adlar)
        elif isinstance(dugum, (ast.With, ast.AsyncWith)):
            for item in dugum.items:
                if item.optional_vars:
                    _hedef_adlari(item.optional_vars, adlar)
        elif isinstance(dugum, ast.ExceptHandler):
            if dugum.name:
                adlar.add(dugum.name)
        elif isinstance(dugum, ast.Global):
            for n in dugum.names:
                adlar.add(n)
    return adlar


def kullanilan_adlar(agac):
    """AST'den Load/Load-benzeri bağlamda kullanılan adları toplar."""
    adlar = set()
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Name) and isinstance(dugum.ctx, ast.Load):
            adlar.add(dugum.id)
    return adlar


print("=" * 60)
print("  Notebook Doğrulama (nbformat + compile + import çözme)")
print("=" * 60)

# 1. nbformat.validate
try:
    nb = nbformat.read(NOTEBOOK_YOLU, as_version=4)
    changes, nb = nbformat.validator.normalize(nb)
    nbformat.validate(nb)
    bilgi("nbformat.validate geçti")
except nbformat.ValidationError as e:
    hata(f"nbformat şema hatası: {e}")
    sys.exit(1)
except Exception as e:
    hata(f"notebook okunamadı: {e}")
    sys.exit(1)

hucreler = nb.cells
kod_hucreleri = [c for c in hucreler if c.cell_type == "code"]
md_hucreleri = [c for c in hucreler if c.cell_type == "markdown"]
bilgi(f"{len(hucreler)} hücre ({len(kod_hucreleri)} kod, {len(md_hucreleri)} markdown)")

if len(kod_hucreleri) < 8:
    hata(f"kod hücresi az: {len(kod_hucreleri)}")

# 2. Her hücreyi derle + import çöz + tanım/kullanım topla
tum_kaynak = ""
tanımlanan = set()
uyarildi = set()
ipython_istisnalar = {
    "get_ipython", "display", "In", "Out", "_", "__", "___",
    "np", "pd",
}

for i, c in enumerate(kod_hucreleri):
    cid = c.metadata.get("id", f"hücre_{i}")
    kod = hucre_python_kaynagi(c)
    if not kod.strip():
        continue
    try:
        agac = ast.parse(kod)
    except SyntaxError as e:
        hata(f"[{cid}] SyntaxError: {e}")
        continue

    tum_kaynak += kod + "\n"

    for mod, ad, satir in cozulebilir_importlar(kod):
        if mod and mod.startswith("src."):
            try:
                paket = importlib.import_module(mod)
            except Exception as e:
                hata(f"[{cid}] import çözülemedi: from {mod} import {ad} ({e})")
                continue
            if not hasattr(paket, ad):
                hata(f"[{cid}] {mod}.{ad} kaynakta yok — import drift'i")

    hucre_tanim = tanimlanan_adlar(agac)
    hucre_kullan = kullanilan_adlar(agac)

    kullanilmadan_once = hucre_kullan - hucre_tanim - tanımlanan - ipython_istisnalar
    for ad in sorted(kullanilmadan_once):
        if ad in dir(builtins):
            continue
        if ad.startswith("_"):
            continue
        if ad in uyarildi:
            continue
        uyarildi.add(ad)
        uyari(f"'{ad}' hiçbir hücrede tanımlanmamış olabilir (ilk kullanım: {cid})")

    tanımlanan |= hucre_tanim

# 3. Zorunlu güvenlik bağlantıları — notebook'un ortak kodu kullandığını kanıtla
ZORUNLU_IMPORTLAR = {
    "from src.source_validation import": "ortak güvenlik kapısı",
    "from src.excel_format import": "ortak excel format modülü",
    "from src.ocr_helpers import": "ortak ocr yardımcıları",
}
for iban, aciklama in ZORUNLU_IMPORTLAR.items():
    if iban not in tum_kaynak:
        hata(f"zorunlu import yok: {iban} ({aciklama})")
    else:
        bilgi(f"zorunlu import var: {iban}")

ZORUNLU_CAGRILAR = [
    "dogrudan_kaynaklari_dogrula",
    "excel_formatini_tespit_et",
    "hedef_yolu_bul",
    "checkpoint_kaydet",
]
for cagri in ZORUNLU_CAGRILAR:
    if cagri + "(" not in tum_kaynak:
        hata(f"zorunlu çağrı yok: {cagri}()")

# 4. Smoke kalite kapısı eşiği
for esik in ["0.05", "0.80"]:
    if esik not in tum_kaynak:
        uyari(f"smoke eşik değeri ({esik}) kaynakta yok")

print()
print(f"Özet: {hata_sayisi} hata, {uyari_sayisi} uyarı")
sys.exit(0 if hata_sayisi == 0 else 1)
