#!/usr/bin/env python3
"""Colab kurulum yardımcı script'i — klasörleri oluşturur, dosya kontrolü yapar."""
import argparse, os, shutil, sys, json, re

PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GEREKLI_KLASORLER = [
    "config", "src", "scripts", "tests", "data/input",
    "data/kaynaklar/01_mevzuat", "data/kaynaklar/02_resmi_uyds_kilavuzlari",
    "data/kaynaklar/03_modul_dokumanlari", "data/kaynaklar/04_teknik_cozumler",
    "data/kaynaklar/05_onayli_destek_kayitlari", "data/kaynaklar/06_surum_notlari",
]

GEREKLI_DOSYALAR = [
    "veri_ayiklama_v4.1.ipynb", "config/config_v4.yaml", "requirements.txt",
    "src/config.py", "src/document_loader.py", "src/chunking.py",
    "src/embeddings.py", "src/retrieval.py", "src/classify_relevance.py",
    "scripts/build_source_corpus.py", "scripts/evaluate_retrieval.py",
]

TEMIZLENEBILIR = [
    "checkpoints_v4/latest/kaynak_embedding",
    "checkpoints_v4/latest/dogrulama_sonuclari.jsonl",
    "checkpoints_v4/latest/meta.json",
    "checkpoints_v4/latest/benchmark_sonuclari.jsonl",
    "checkpoints_v4/latest/benchmark_meta.json",
]

DOKUNULMAZ = ["data/input", "data/kaynaklar"]


def klasorleri_olustur():
    print("📁 Klasörler kontrol ediliyor...")
    for k in GEREKLI_KLASORLER:
        yol = os.path.join(PROJE_KOKU, k)
        if not os.path.exists(yol):
            os.makedirs(yol, exist_ok=True)
            print(f"   ✅ Oluşturuldu: {k}")
        gk = os.path.join(yol, ".gitkeep")
        if not os.path.exists(gk) and "data/" in k:
            open(gk, "w").write("")
    print("   OK")


def dosyalari_kontrol_et():
    print("\n📄 Dosya kontrolü...")
    eksik = []
    for d in GEREKLI_DOSYALAR:
        yol = os.path.join(PROJE_KOKU, d)
        if os.path.exists(yol):
            print(f"   ✅ {d}")
        else:
            print(f"   ❌ {d}")
            eksik.append(d)
    return eksik


def veri_durumu():
    print("\n📊 Veri durumu...")
    inp = os.path.join(PROJE_KOKU, "data", "input")
    xl = [f for f in os.listdir(inp) if f.endswith((".xlsx", ".xls"))] if os.path.isdir(inp) else []
    print(f"   {'✅' if xl else '⚠️'} Excel: {', '.join(xl) if xl else 'YOK'}")

    kk = os.path.join(PROJE_KOKU, "data", "kaynaklar")
    top = 0
    for i in range(1, 7):
        alt = f"{i:02d}_" + ["mevzuat","resmi_uyds_kilavuzlari","modul_dokumanlari","teknik_cozumler","onayli_destek_kayitlari","surum_notlari"][i-1]
        dy = os.path.join(kk, alt)
        if os.path.isdir(dy):
            ds = [f for f in os.listdir(dy) if not f.startswith(".") and os.path.isfile(os.path.join(dy, f))]
            top += len(ds)
            print(f"   {'✅' if ds else '⚠️'} {alt}/: {len(ds)} belge")
    print(f"   📊 Toplam kaynak belge: {top}")

    env = os.path.join(PROJE_KOKU, "data", "output_v4", "kaynak_envanteri_siniflandirilmis.csv")
    print(f"   {'✅' if os.path.exists(env) else '⚠️'} Sınıflandırılmış envanter: {'var' if os.path.exists(env) else 'YOK'}")

    ckpt = os.path.join(PROJE_KOKU, "checkpoints_v4", "latest", "kaynak_embedding")
    if os.path.isdir(ckpt):
        meta = os.path.join(ckpt, "emb_meta.json")
        if os.path.exists(meta):
            m = json.load(open(meta))
            sv = m.get("siniflandirma_surumu", "yok")
            print(f"   ✅ Checkpoint sürüm: {sv}{' ⚠️ ESKİ!' if sv != '2.0' else ''}")
    else:
        print(f"   ℹ️ Checkpoint yok")


def guvenli_temizlik():
    print("\n🧹 Güvenli temizlik (gerçek veri SİLİNMEZ)...")
    print(f"   🔒 Korunan: {', '.join(DOKUNULMAZ)}")
    s = 0
    for h in TEMIZLENEBILIR:
        yol = os.path.join(PROJE_KOKU, h)
        if os.path.isdir(yol):
            shutil.rmtree(yol); print(f"   🗑️ {h}/"); s += 1
        elif os.path.isfile(yol):
            os.remove(yol); print(f"   🗑️ {h}"); s += 1
    ok = os.path.join(PROJE_KOKU, "data", "output_v4")
    if os.path.isdir(ok):
        for item in os.listdir(ok):
            iy = os.path.join(ok, item)
            if item in ("kaynak_envanteri_siniflandirilmis.csv", "kaynak_envanteri.csv"): continue
            if os.path.isdir(iy) and re.match(r"\d{4}-\d{2}-\d{2}_\d{4}", item):
                shutil.rmtree(iy); print(f"   🗑️ output_v4/{item}/"); s += 1
    print(f"\n   {'✅ ' + str(s) + ' öğe temizlendi' if s else 'ℹ️ Temizlenecek yok'}")


def main():
    parser = argparse.ArgumentParser(description="Colab hazırlık")
    parser.add_argument("--temizle", action="store_true")
    parser.add_argument("--durum", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("  Colab Hazırlık Script'i")
    print("=" * 60)
    print(f"  Proje: {PROJE_KOKU}")

    if args.temizle:
        guvenli_temizlik(); return
    if args.durum:
        veri_durumu(); return

    klasorleri_olustur()
    eksik = dosyalari_kontrol_et()
    veri_durumu()

    if eksik:
        print(f"\n🔴 {len(eksik)} eksik dosya!")
        sys.exit(1)
    print("\n✅ Tüm dosyalar mevcut. Colab'a hazırsınız.")
    print("\n📋 Sıradaki: 1) Excel→data/input 2) Belgeler→data/kaynaklar 3) classify_relevance.py 4) build_source_corpus.py 5) Notebook Run All")


if __name__ == "__main__":
    main()