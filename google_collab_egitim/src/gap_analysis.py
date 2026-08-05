#!/usr/bin/env python3
# ============================================================
# gap_analysis.py — Kaynak boşluk analizi raporu
# ============================================================
"""
Excel'deki modül/konu dağılımı ile indirilen kaynakları karşılaştırır,
kapsama durumunu analiz eder ve kaynak_bosluk_analizi.xlsx üretir.
"""

import os
import sys
import json
import pandas as pd
from collections import defaultdict

PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCEL_YOLU = os.path.join(PROJE_KOKU, "google_collab_egitim", "data", "input", "UYDS_SSS_Listesi.xlsx")
ENVANTER_YOLU = os.path.join(PROJE_KOKU, "google_collab_egitim", "data", "output_v4", "kaynak_envanteri.csv")
CIKTI_YOLU = os.path.join(PROJE_KOKU, "google_collab_egitim", "data", "output_v4", "kaynak_bosluk_analizi.xlsx")

# UYDS modül eşleştirmeleri — Excel'deki modüller ile kaynak kategorileri arası
MODUL_ESLEME = {
    "genel": ["mevzuat", "genelgeler", "kanunlar", "khk"],
    "ruhsat": ["mevzuat", "genelgeler", "iskan_mevzuati"],
    "yapi_kayit": ["mevzuat", "iskan_mevzuati", "afet_mevzuati"],
    "denetci": ["mevzuat", "teblig", "genelgeler"],
    "hakedis": ["ihale_mevzuati", "genelgeler"],
    "laboratuvar": ["mevzuat", "teblig", "afet_mevzuati"],
    "personel": ["mevzuat", "genelgeler"],
    "proje": ["proje_mevzuati", "egitim_dokumanlari"],
    "santiye_sefi": ["mevzuat", "genelgeler"],
    "yapi_denetim_kurulusu": ["mevzuat", "teblig"],
    "is_bitirme": ["ihale_mevzuati", "genelgeler"],
    "yetkilendirme": ["mevzuat", "teblig"],
    "seviye_tespit": ["afet_mevzuati", "genelgeler"],
}


def excel_analiz():
    """Excel'deki modül ve konu dağılımını çıkarır."""
    df = pd.read_excel(EXCEL_YOLU)
    modules = df['Unnamed: 1']
    topics = df['Unnamed: 5']

    # Modül dağılımı
    modul_sayac = defaultdict(int)
    modul_konular = defaultdict(list)

    for idx, (modul, konu) in enumerate(zip(modules, topics)):
        if pd.notna(modul) and pd.notna(konu):
            modul_str = str(modul).strip()
            konu_str = str(konu).strip()
            if modul_str and modul_str != "UYDS - SSS LİSTESİ" and modul_str != "Modül":
                modul_sayac[modul_str] += 1
                modul_konular[modul_str].append(konu_str)

    return modul_sayac, modul_konular


def envanter_analiz():
    """Envanter CSV'deki kaynak dağılımını çıkarır."""
    if not os.path.exists(ENVANTER_YOLU):
        return {}, [], 0

    df = pd.read_csv(ENVANTER_YOLU)

    # Modül (kategori) bazında sayım
    modul_kaynak_sayac = defaultdict(int)
    for _, row in df.iterrows():
        modul = str(row.get("modul", ""))
        if modul:
            modul_kaynak_sayac[modul] += 1

    # Tüm dosyalar
    dosyalar = df.to_dict("records")
    toplam = len(df)

    return modul_kaynak_sayac, dosyalar, toplam


def chunk_tahmini(dosya_boyutu_kb):
    """Dosya boyutundan tahmini chunk sayısı çıkarır."""
    # Ortalama 1KB = ~200 kelime = ~250 token
    # Chunk boyutu ~512 token, overlap ~50 token
    # Yani ~470 token/chunk
    # 1KB -> ~250 token -> ~0.5 chunk
    if dosya_boyutu_kb < 1:
        return 0
    return max(1, int(dosya_boyutu_kb * 0.5))


def main():
    print("=" * 60)
    print("  Kaynak Boşluk Analizi")
    print("=" * 60)

    # Excel analiz
    print("\n📊 Excel analizi yapılıyor...")
    modul_sayac, modul_konular = excel_analiz()
    print(f"   {len(modul_sayac)} benzersiz modül tespit edildi")
    print(f"   Toplam kayıt: {sum(modul_sayac.values())}")

    # Envanter analiz
    print("\n📋 Envanter analizi yapılıyor...")
    kaynak_sayac, kaynak_dosyalar, toplam_kaynak = envanter_analiz()
    print(f"   {toplam_kaynak} kaynak belge envanterde")

    # Boşluk analizi
    print("\n🔍 Boşluk analizi yapılıyor...")

    satirlar = []
    for modul, excel_sayi in sorted(modul_sayac.items(), key=lambda x: -x[1]):
        # Bu modül için eşleşen kaynak kategorilerini bul
        modul_lower = modul.lower()

        # Doğrudan eşleşme
        eslesen_kategoriler = []
        for anahtar, kategoriler in MODUL_ESLEME.items():
            if anahtar in modul_lower or any(k in modul_lower for k in [anahtar.replace("_", " ")]):
                eslesen_kategoriler.extend(kategoriler)

        # Eşleşme yoksa genel kategorileri kullan
        if not eslesen_kategoriler:
            eslesen_kategoriler = ["mevzuat", "genelgeler"]

        # Benzersiz kategoriler
        eslesen_kategoriler = list(set(eslesen_kategoriler))

        # Bu kategorilerdeki kaynak sayısı
        bulunan_kaynak = 0
        bulunan_chunk = 0
        en_iyi_kaynak = ""
        en_iyi_guven = "E"

        for kategori in eslesen_kategoriler:
            for kaynak in kaynak_dosyalar:
                if str(kaynak.get("modul", "")) == kategori:
                    bulunan_kaynak += 1
                    boyut_kb = float(kaynak.get("dosya_boyutu", 0)) / 1024
                    bulunan_chunk += chunk_tahmini(boyut_kb)

                    if not en_iyi_kaynak:
                        en_iyi_kaynak = str(kaynak.get("baslik", ""))[:50]
                        en_iyi_guven = str(kaynak.get("guven_sinifi", "E"))

        # Kapsama durumu
        if bulunan_kaynak == 0:
            kapsama = "hic_kaynak_yok"
        elif bulunan_kaynak < 3 and excel_sayi > 20:
            kapsama = "yetersiz"
        elif bulunan_kaynak < 5:
            kapsama = "kismen_yeterli"
        else:
            kapsama = "yeterli"

        # Eksik belge önerisi
        if kapsama == "hic_kaynak_yok":
            eksik_oneri = f"Kurum içi UYDS {modul} modülü dokümanı gerekiyor"
            onerilen_sorgu = f'site:gov.tr UYDS "{modul}" filetype:pdf'
        elif kapsama == "yetersiz":
            eksik_oneri = f"{modul} modülü için ek kılavuz/teknik doküman gerekiyor"
            onerilen_sorgu = f'site:yapiisleri.csb.gov.tr "{modul}" filetype:pdf'
        elif kapsama == "kismen_yeterli":
            eksik_oneri = f"{modul} modülü kapsamı kısmen yeterli, güncel sürüm notları eklenebilir"
            onerilen_sorgu = f'site:csb.gov.tr UYDS {modul} duyuru'
        else:
            eksik_oneri = "Mevcut kaynaklar yeterli görünüyor"
            onerilen_sorgu = ""

        # Konu örnekleri
        konu_ornekleri = modul_konular.get(modul, [])[:3]
        konu_str = " | ".join(konu_ornekleri)

        satirlar.append({
            "modul": modul,
            "konu": konu_str,
            "excel_kayit_sayisi": excel_sayi,
            "bulunan_kaynak_sayisi": bulunan_kaynak,
            "bulunan_chunk_tahmini": bulunan_chunk,
            "en_iyi_kaynak": en_iyi_kaynak,
            "guven_sinifi": en_iyi_guven,
            "kapsama_durumu": kapsama,
            "eksik_belge_onerisi": eksik_oneri,
            "onerilen_arama_sorgusu": onerilen_sorgu,
        })

    # DataFrame oluştur
    df_sonuc = pd.DataFrame(satirlar)

    # Excel'e kaydet
    df_sonuc.to_excel(CIKTI_YOLU, index=False, sheet_name="Bosluk_Analizi")
    print(f"\n✅ Boşluk analizi kaydedildi: {CIKTI_YOLU}")

    # Özet
    print("\n" + "=" * 60)
    print("  BOŞLUK ANALİZİ ÖZETİ")
    print("=" * 60)

    kapsama_dagilim = df_sonuc["kapsama_durumu"].value_counts()
    print("\nKapsama durumu dağılımı:")
    for durum, sayi in kapsama_dagilim.items():
        print(f"  {durum}: {sayi}")

    toplam_excel = df_sonuc["excel_kayit_sayisi"].sum()
    toplam_kaynak = df_sonuc["bulunan_kaynak_sayisi"].sum()
    toplam_chunk = df_sonuc["bulunan_chunk_tahmini"].sum()

    print(f"\nToplam Excel kaydı: {toplam_excel}")
    print(f"Toplam bulunan kaynak: {toplam_kaynak}")
    print(f"Tahmini toplam chunk: {toplam_chunk}")

    # Eksik modüller
    eksik_moduller = df_sonuc[df_sonuc["kapsama_durumu"] == "hic_kaynak_yok"]["modul"].tolist()
    if eksik_moduller:
        print(f"\n⚠️ Kaynak bulunamayan modüller ({len(eksik_moduller)}):")
        for m in eksik_moduller[:10]:
            print(f"   - {m}")

    # Yetersiz modüller
    yetersiz_moduller = df_sonuc[df_sonuc["kapsama_durumu"] == "yetersiz"]["modul"].tolist()
    if yetersiz_moduller:
        print(f"\n⚠️ Kaynakları yetersiz modüller ({len(yetersiz_moduller)}):")
        for m in yetersiz_moduller[:10]:
            print(f"   - {m}")

    return len(satirlar)


if __name__ == "__main__":
    main()