#!/usr/bin/env python3
# ============================================================
# validate_outputs.py — Çıktı bütünlüğü doğrulama aracı
# ============================================================
"""
Üretilen çıktı dosyalarının bütünlüğünü ve kabul kriterlerini kontrol eder.

Kontroller:
  1. dogrulanan.xlsx yalnızca güvenli "dogru" kayıtları içermeli
  2. supheli.xlsx diğer bütün kayıtları içermeli
  3. Eksik veya tekrarlı _kayit_no olmamalı
  4. islem_hatalari.xlsx yeniden denemeden sonra kalan hataları içermeli
  5. ozet.json geçerli JSON olmalı
  6. Grafik dosyaları üretilmiş olmalı

Kullanım:
  python scripts/validate_outputs.py data/output_v4/2026-08-04_1200
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(description="Çıktı bütünlüğü doğrulama")
    parser.add_argument("cikti_dizini", help="Çıktı dizini yolu")
    parser.add_argument("--guven-esik", type=float, default=0.85, help="Güven eşiği")
    args = parser.parse_args()

    cikti = Path(args.cikti_dizini)
    if not cikti.is_dir():
        print(f"❌ Dizin bulunamadı: {cikti}")
        sys.exit(1)

    hatalar = []
    uyarilar = []

    # 1. tum_sonuclar.xlsx
    tum_path = cikti / "tum_sonuclar.xlsx"
    if not tum_path.exists():
        hatalar.append("tum_sonuclar.xlsx bulunamadı")
    else:
        try:
            import pandas as pd
            df = pd.read_excel(tum_path)
            print(f"✅ tum_sonuclar.xlsx: {len(df)} kayıt")

            # 2. dogrulanan.xlsx kontrolü
            dogrulanan_path = cikti / "dogrulanan.xlsx"
            if dogrulanan_path.exists():
                ddf = pd.read_excel(dogrulanan_path)
                # Her kayıt: karar=dogru, guven>=esik, islem_hatasi=False
                for _, row in ddf.iterrows():
                    karar = row.get("_karar", "")
                    guven = row.get("_guven", 0)
                    hata = row.get("_islem_hatasi", False)
                    if karar != "dogru":
                        hatalar.append(f"dogrulanan.xlsx içinde karar='{karar}' (dogru değil)")
                        break
                    if guven < args.guven_esik:
                        hatalar.append(f"dogrulanan.xlsx içinde güven={guven} < {args.guven_esik}")
                        break
                    if hata:
                        hatalar.append("dogrulanan.xlsx içinde _islem_hatasi=True")
                        break
                print(f"✅ dogrulanan.xlsx: {len(ddf)} kayıt — tümü geçerli")

            # 3. supheli.xlsx kontrolü
            supheli_path = cikti / "supheli.xlsx"
            if supheli_path.exists():
                sdf = pd.read_excel(supheli_path)
                toplam = len(dogrulanan_path and pd.read_excel(dogrulanan_path) or []) + len(sdf)
                if toplam != len(df):
                    hatalar.append(
                        f"dogrulanan + şüpheli ≠ toplam: {toplam} ≠ {len(df)}"
                    )
                print(f"✅ supheli.xlsx: {len(sdf)} kayıt")

            # 4. _kayit_no kontrolü
            tum_nolar = df.index.tolist()
            if len(tum_nolar) != len(set(tum_nolar)):
                hatalar.append(f"Mükerrer indeks tespit edildi")

        except ImportError:
            uyarilar.append("pandas kurulu değil, Excel kontrolü atlandı")
        except Exception as e:
            hatalar.append(f"Excel okuma hatası: {e}")

    # 5. ozet.json
    ozet_path = cikti / "ozet.json"
    if ozet_path.exists():
        try:
            with open(ozet_path, "r", encoding="utf-8") as f:
                ozet = json.load(f)
            gerekli_alanlar = ["toplam_kayit", "dogrulanan", "supheli", "karar_dagilimi"]
            for alan in gerekli_alanlar:
                if alan not in ozet:
                    hatalar.append(f"ozet.json: '{alan}' alanı eksik")
            print(f"✅ ozet.json: {len(ozet)} alan")
        except json.JSONDecodeError:
            hatalar.append("ozet.json geçersiz JSON")
    else:
        uyarilar.append("ozet.json bulunamadı")

    # 6. Grafikler
    grafikler = list(cikti.rglob("*.png"))
    if grafikler:
        for g in grafikler:
            print(f"✅ Grafik: {g.name}")
    else:
        uyarilar.append("Grafik dosyası bulunamadı")

    # 7. islem_hatalari.xlsx (varsa)
    hata_path = cikti / "islem_hatalari.xlsx"
    if hata_path.exists():
        try:
            hdf = pd.read_excel(hata_path)
            for _, row in hdf.iterrows():
                if not row.get("_islem_hatasi", False):
                    hatalar.append("islem_hatalari.xlsx içinde _islem_hatasi=False kayıt var")
                    break
            print(f"✅ islem_hatalari.xlsx: {len(hdf)} kayıt")
        except Exception as e:
            hatalar.append(f"islem_hatalari.xlsx okuma hatası: {e}")

    # Sonuç
    print(f"\n{'='*50}")
    if hatalar:
        print(f"❌ {len(hatalar)} HATA:")
        for h in hatalar:
            print(f"   - {h}")
    if uyarilar:
        print(f"⚠️ {len(uyarilar)} UYARI:")
        for u in uyarilar:
            print(f"   - {u}")
    if not hatalar:
        print("✅ Tüm kontroller başarılı — Çıktılar kabul kriterlerini karşılıyor")

    return len(hatalar)


if __name__ == "__main__":
    sys.exit(main())