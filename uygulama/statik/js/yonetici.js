const YoneticiDurumu = {
    geriBildirimSayfasi: 1,
    cevapsizSayfasi: 1,
    sssSayfasi: 1,
    sssAramasi: "",
    seciliSssId: null,
    sayfaBasina: 10
};

function yoneticiMetinElemani(etiket, sinifAdi, metin) {
    const eleman = document.createElement(etiket);
    if (sinifAdi) {
        eleman.className = sinifAdi;
    }
    eleman.textContent = String(metin);
    return eleman;
}

function sayfalamaOlustur(kimlik, sayfa, toplam, degistir) {
    const alan = document.getElementById(kimlik);
    if (!alan) {
        return;
    }
    alan.replaceChildren();
    const toplamSayfa = Math.max(1, Math.ceil(toplam / YoneticiDurumu.sayfaBasina));
    const onceki = yoneticiMetinElemani("button", "ikincil-dugme", "Önceki");
    onceki.type = "button";
    onceki.disabled = sayfa <= 1;
    onceki.addEventListener("click", () => degistir(sayfa - 1));
    const bilgi = yoneticiMetinElemani("span", "sayfa-bilgisi", `${sayfa} / ${toplamSayfa}`);
    const sonraki = yoneticiMetinElemani("button", "ikincil-dugme", "Sonraki");
    sonraki.type = "button";
    sonraki.disabled = sayfa >= toplamSayfa;
    sonraki.addEventListener("click", () => degistir(sayfa + 1));
    alan.append(onceki, bilgi, sonraki);
}

async function imzaliYoneticiIstegi(yol, veri = null) {
    const govde = veri === null ? "" : JSON.stringify(veri);
    const imzaYaniti = await jsonIstegi("/api/v1/yonetici/islem-imzasi", {
        method: "POST",
        body: JSON.stringify({hedef_yol: yol, govde})
    });
    const imza = await imzaYaniti.json();
    const basliklar = {
        "X-UYDS-Zaman": imza.zaman,
        "X-UYDS-Nonce": imza.nonce,
        "X-UYDS-Imza": imza.imza
    };
    return jsonIstegi(yol, {
        method: "POST",
        headers: basliklar,
        body: govde || undefined
    });
}

function geriBildirimKartiOlustur(kayit) {
    const kart = document.createElement("article");
    kart.className = "inceleme-karti";
    const baslik = document.createElement("div");
    baslik.className = "inceleme-basligi";
    baslik.append(
        yoneticiMetinElemani("strong", "", `Kayıt ${kayit.id}`),
        yoneticiMetinElemani("span", "durum-rozeti", `${kayit.puan}/5`)
    );
    const soru = yoneticiMetinElemani("p", "inceleme-sorusu", kayit.kullanici_sorusu);
    const cevap = yoneticiMetinElemani("p", "inceleme-cevabi", kayit.verilen_cevap);
    const form = document.createElement("div");
    form.className = "inceleme-eylemleri";
    const sssGirdisi = document.createElement("input");
    sssGirdisi.type = "number";
    sssGirdisi.min = "1";
    sssGirdisi.className = "sss-secim";
    sssGirdisi.placeholder = "Doğru SSS kayıt no";
    sssGirdisi.value = kayit.secili_sss_id || kayit.sss_id || YoneticiDurumu.seciliSssId || "";
    const onayla = yoneticiMetinElemani("button", "birincil-dugme", "Onayla ve öğren");
    onayla.type = "button";
    onayla.addEventListener("click", async () => {
        const sssId = Number(sssGirdisi.value);
        if (!Number.isInteger(sssId) || sssId < 1) {
            bildirimGoster("Onay için geçerli bir SSS kayıt numarası seçin.", "hata");
            return;
        }
        await geriBildirimKarariVer(kayit.id, "ONAYLA", sssId, onayla);
    });
    const reddet = yoneticiMetinElemani("button", "tehlikeli-dugme", "Reddet");
    reddet.type = "button";
    reddet.addEventListener("click", async () => {
        await geriBildirimKarariVer(kayit.id, "REDDET", null, reddet);
    });
    form.append(sssGirdisi, onayla, reddet);
    kart.append(baslik, soru, cevap);
    if (kayit.yorum) {
        kart.append(yoneticiMetinElemani("p", "ikincil-metin", kayit.yorum));
    }
    kart.append(form);
    return kart;
}

async function geriBildirimKarariVer(kayitId, islem, sssId, dugme) {
    if (islem === "REDDET" && !window.confirm("Bu geri bildirimi reddetmek istediğinize emin misiniz?")) {
        return;
    }
    dugme.disabled = true;
    try {
        await imzaliYoneticiIstegi("/api/v1/yonetici/geri-bildirim/onay", {
            geri_bildirim_id: kayitId,
            islem,
            secili_sss_id: sssId
        });
        bildirimGoster(islem === "ONAYLA" ? "Geri bildirim öğrenme havuzuna alındı." : "Geri bildirim reddedildi.");
        await geriBildirimleriYukle();
    } catch (hata) {
        bildirimGoster(hata.message, "hata");
    } finally {
        dugme.disabled = false;
    }
}

async function geriBildirimleriYukle() {
    const liste = document.getElementById("geri-bildirim-listesi");
    const yanit = await jsonIstegi(`/api/v1/yonetici/geri-bildirimler?sayfa=${YoneticiDurumu.geriBildirimSayfasi}&sayfa_basina=${YoneticiDurumu.sayfaBasina}`);
    const veri = await yanit.json();
    document.getElementById("bekleyen-metrigi").textContent = String(veri.toplam);
    liste.replaceChildren();
    veri.bildirimler.forEach((kayit) => liste.append(geriBildirimKartiOlustur(kayit)));
    if (!veri.bildirimler.length) {
        liste.append(yoneticiMetinElemani("p", "bos-durum", "Bekleyen geri bildirim bulunmuyor."));
    }
    sayfalamaOlustur("geri-bildirim-sayfalama", YoneticiDurumu.geriBildirimSayfasi, veri.toplam, async (sayfa) => {
        YoneticiDurumu.geriBildirimSayfasi = sayfa;
        await geriBildirimleriYukle();
    });
}

async function cevapsizSorgulariYukle() {
    const liste = document.getElementById("cevapsiz-sorgu-listesi");
    const yanit = await jsonIstegi(`/api/v1/yonetici/cevapsiz-sorgular?sayfa=${YoneticiDurumu.cevapsizSayfasi}&sayfa_basina=${YoneticiDurumu.sayfaBasina}`);
    const veri = await yanit.json();
    document.getElementById("cevapsiz-metrigi").textContent = String(veri.toplam);
    liste.replaceChildren();
    veri.sorgular.forEach((kayit) => {
        const kart = document.createElement("article");
        kart.className = "veri-satiri";
        const govde = document.createElement("div");
        govde.append(
            yoneticiMetinElemani("h3", "", kayit.kullanici_sorusu),
            yoneticiMetinElemani("p", "", `${kayit.kullanici_adi || "Bilinmeyen kullanıcı"} · ${new Date(kayit.olusturulma_tarihi).toLocaleString("tr-TR")}`)
        );
        const guven = kayit.guven_skoru === null ? "Ölçülmedi" : `%${Math.round(kayit.guven_skoru * 100)}`;
        kart.append(govde, yoneticiMetinElemani("span", "durum-rozeti", guven));
        liste.append(kart);
    });
    if (!veri.sorgular.length) {
        liste.append(yoneticiMetinElemani("p", "bos-durum", "Cevapsız sorgu bulunmuyor."));
    }
    sayfalamaOlustur("cevapsiz-sayfalama", YoneticiDurumu.cevapsizSayfasi, veri.toplam, async (sayfa) => {
        YoneticiDurumu.cevapsizSayfasi = sayfa;
        await cevapsizSorgulariYukle();
    });
}

function sssKartiOlustur(kayit) {
    const kart = document.createElement("article");
    kart.className = "veri-satiri";
    const govde = document.createElement("div");
    govde.append(
        yoneticiMetinElemani("h3", "", kayit.soru),
        yoneticiMetinElemani("p", "", `Kayıt ${kayit.id} · ${kayit.kategori} · ${kayit.modul || "Modül belirtilmemiş"}`)
    );
    const sec = yoneticiMetinElemani("button", "ikincil-dugme", "Doğru kayıt olarak seç");
    sec.type = "button";
    sec.addEventListener("click", () => {
        YoneticiDurumu.seciliSssId = kayit.id;
        document.querySelectorAll(".sss-secim").forEach((girdi) => {
            if (!girdi.value) {
                girdi.value = String(kayit.id);
            }
        });
        bildirimGoster(`SSS kayıt ${kayit.id} seçildi.`);
    });
    kart.append(govde, sec);
    return kart;
}

async function sssKayitlariniYukle() {
    const liste = document.getElementById("sss-listesi");
    const sorgu = new URLSearchParams({
        sayfa: String(YoneticiDurumu.sssSayfasi),
        sayfa_basina: String(YoneticiDurumu.sayfaBasina)
    });
    if (YoneticiDurumu.sssAramasi) {
        sorgu.set("arama", YoneticiDurumu.sssAramasi);
    }
    const yanit = await jsonIstegi(`/api/v1/sss?${sorgu.toString()}`);
    const veri = await yanit.json();
    liste.replaceChildren();
    veri.kayitlar.forEach((kayit) => liste.append(sssKartiOlustur(kayit)));
    if (!veri.kayitlar.length) {
        liste.append(yoneticiMetinElemani("p", "bos-durum", "Eşleşen SSS kaydı bulunamadı."));
    }
    sayfalamaOlustur("sss-sayfalama", YoneticiDurumu.sssSayfasi, veri.toplam, async (sayfa) => {
        YoneticiDurumu.sssSayfasi = sayfa;
        await sssKayitlariniYukle();
    });
}

function durumListesiniDoldur(kimlik, veriler) {
    const alan = document.getElementById(kimlik);
    alan.replaceChildren();
    Object.entries(veriler).forEach(([anahtar, deger]) => {
        const satir = document.createElement("div");
        satir.className = "durum-satiri";
        const etiket = anahtar.replaceAll("_", " ");
        const gorunenDeger = Array.isArray(deger) ? deger.join(", ") : typeof deger === "boolean" ? (deger ? "Aktif" : "Pasif") : String(deger);
        satir.append(
            yoneticiMetinElemani("span", "", etiket),
            yoneticiMetinElemani("strong", "", gorunenDeger)
        );
        alan.append(satir);
    });
}

async function isletimDurumunuYukle() {
    const yanit = await jsonIstegi("/api/v1/yonetici/isletim-durumu");
    const veri = await yanit.json();
    durumListesiniDoldur("arama-durumu", veri.arama);
    durumListesiniDoldur("belge-durumu", veri.belgeler);
    durumListesiniDoldur("otomasyon-durumu", veri.otomasyon);
    durumListesiniDoldur("veri-yonetimi-durumu", veri.veri_yonetimi);
}

async function indeksleriYenidenOlustur(dugme) {
    if (!window.confirm("FTS ve tüm yerel vektör indeksleri yeniden oluşturulsun mu?")) {
        return;
    }
    dugme.disabled = true;
    try {
        const yanit = await imzaliYoneticiIstegi("/api/v1/yonetici/yeniden-indeksle");
        const veri = await yanit.json();
        bildirimGoster(`${veri.fts_kayit_sayisi} FTS kaydı ve ${veri.uretilen_vektor_sayisi} vektör işlendi.`);
    } catch (hata) {
        bildirimGoster(hata.message, "hata");
    } finally {
        dugme.disabled = false;
    }
}

async function senkronizasyonuCalistir(tur, dugme) {
    if (tur === "tam" && !window.confirm("Tüm belge kaynakları yeniden taransın mı?")) {
        return;
    }
    dugme.disabled = true;
    try {
        const yanit = await imzaliYoneticiIstegi("/api/v1/yonetici/senkronizasyon", {tur});
        const veri = await yanit.json();
        bildirimGoster(`${veri.islenen_belge_sayisi} belge ve ${veri.yeni_parca_sayisi} yeni parça işlendi.`);
    } catch (hata) {
        bildirimGoster(hata.message, "hata");
    } finally {
        dugme.disabled = false;
    }
}

async function epostaRaporuGonder(dugme) {
    dugme.disabled = true;
    try {
        const yanit = await imzaliYoneticiIstegi("/api/v1/yonetici/eposta-raporu/gonder");
        const veri = await yanit.json();
        bildirimGoster(veri.mesaj);
    } catch (hata) {
        bildirimGoster(hata.message, "hata");
    } finally {
        dugme.disabled = false;
    }
}

async function yoneticiMerkeziniYukle() {
    if (document.body.dataset.sayfa !== "yonetici" || !yoneticiMi()) {
        return;
    }
    try {
        await Promise.all([
            geriBildirimleriYukle(),
            cevapsizSorgulariYukle(),
            sssKayitlariniYukle(),
            isletimDurumunuYukle()
        ]);
    } catch (hata) {
        bildirimGoster(hata.message, "hata");
    }
}

function yoneticiEtkilesimleriniHazirla() {
    const aramaFormu = document.getElementById("sss-arama-formu");
    aramaFormu.addEventListener("submit", async (olay) => {
        olay.preventDefault();
        YoneticiDurumu.sssAramasi = document.getElementById("sss-arama").value.trim();
        YoneticiDurumu.sssSayfasi = 1;
        await sssKayitlariniYukle();
    });
    document.getElementById("yonetici-yenile").addEventListener("click", yoneticiMerkeziniYukle);
    const indeksDugmesi = document.getElementById("yeniden-indeksle");
    indeksDugmesi.addEventListener("click", () => indeksleriYenidenOlustur(indeksDugmesi));
    document.querySelectorAll("[data-senkronizasyon]").forEach((dugme) => {
        dugme.addEventListener("click", () => senkronizasyonuCalistir(dugme.dataset.senkronizasyon, dugme));
    });
    const epostaDugmesi = document.getElementById("eposta-raporu-gonder");
    epostaDugmesi.addEventListener("click", () => epostaRaporuGonder(epostaDugmesi));
}

document.addEventListener("DOMContentLoaded", async () => {
    if (document.body.dataset.sayfa === "yonetici") {
        yoneticiEtkilesimleriniHazirla();
        await yoneticiMerkeziniYukle();
    }
});

document.addEventListener("hadesbot:oturum-acildi", yoneticiMerkeziniYukle);
