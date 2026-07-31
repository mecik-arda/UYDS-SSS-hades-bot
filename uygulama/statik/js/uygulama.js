const Durum = {
    erisimBelirteci: sessionStorage.getItem("hadesbot_erisim") || "",
    yenilemeBelirteci: sessionStorage.getItem("hadesbot_yenileme") || "",
    kullaniciAdi: sessionStorage.getItem("hadesbot_kullanici") || "",
    rol: sessionStorage.getItem("hadesbot_rol") || "",
    oturumId: sessionStorage.getItem("hadesbot_oturum") || "",
    sonSoru: "",
    sonCevap: "",
    sonKaynaklar: []
};

const Elemanlar = {
    govde: document.body,
    girisPenceresi: document.getElementById("giris-penceresi"),
    girisFormu: document.getElementById("giris-formu"),
    girisHatasi: document.getElementById("giris-hatasi"),
    girisDugmesi: document.getElementById("giris-dugmesi"),
    profilAdi: document.getElementById("profil-adi"),
    profilRolu: document.getElementById("profil-rolu"),
    profilAvatar: document.getElementById("profil-avatar"),
    cikisDugmesi: document.getElementById("cikis-dugmesi"),
    durumNoktasi: document.getElementById("durum-noktasi"),
    durumMetni: document.getElementById("durum-metni"),
    uyariBandi: document.getElementById("uyari-bandi"),
    uyariMetni: document.getElementById("uyari-metni"),
    bildirimAlani: document.getElementById("bildirim-alani"),
    yanPanel: document.getElementById("yan-panel"),
    mobilMenu: document.getElementById("mobil-menu"),
    cekmeceOrtusu: document.getElementById("cekmece-ortusu")
};

function markdownDonustur(metin) {
    if (!metin) {
        return "";
    }
    let temiz = metin;
    temiz = temiz.replace(/&/g, "&");
    temiz = temiz.replace(/</g, "<");
    temiz = temiz.replace(/>/g, ">");
    temiz = temiz.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    temiz = temiz.replace(/^\* (.*$)/gim, "<li>$1</li>");
    temiz = temiz.replace(/((?:<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");
    temiz = temiz.replace(/\[Kaynak (\d+)\]/g, '<span class="kaynak-rozet">Kaynak $1</span>');
    temiz = temiz.replace(/\n/g, "<br>");
    return temiz;
}

function metinElemani(etiket, sinifAdi, metin) {
    const eleman = document.createElement(etiket);
    if (sinifAdi) {
        eleman.className = sinifAdi;
    }
    eleman.textContent = metin;
    return eleman;
}

function bildirimGoster(mesaj, tur = "bilgi") {
    const bildirim = metinElemani("div", `bildirim ${tur}`, mesaj);
    Elemanlar.bildirimAlani.append(bildirim);
    window.setTimeout(() => bildirim.remove(), 5000);
}

function belirtecleriKaydet(veri, kullaniciAdi) {
    Durum.erisimBelirteci = veri.erisim_belirteci;
    Durum.yenilemeBelirteci = veri.yenileme_belirteci;
    Durum.kullaniciAdi = kullaniciAdi || Durum.kullaniciAdi;
    Durum.rol = veri.rol;
    sessionStorage.setItem("hadesbot_erisim", Durum.erisimBelirteci);
    sessionStorage.setItem("hadesbot_yenileme", Durum.yenilemeBelirteci);
    sessionStorage.setItem("hadesbot_kullanici", Durum.kullaniciAdi);
    sessionStorage.setItem("hadesbot_rol", Durum.rol);
}

function oturumuTemizle() {
    Object.assign(Durum, {
        erisimBelirteci: "",
        yenilemeBelirteci: "",
        kullaniciAdi: "",
        rol: "",
        oturumId: ""
    });
    [
        "hadesbot_erisim",
        "hadesbot_yenileme",
        "hadesbot_kullanici",
        "hadesbot_rol",
        "hadesbot_oturum"
    ].forEach((anahtar) => sessionStorage.removeItem(anahtar));
}

function yoneticiMi() {
    return Durum.rol === "YONETICI";
}

function profilGuncelle() {
    const oturumAcik = Boolean(Durum.erisimBelirteci);
    Elemanlar.profilAdi.textContent = oturumAcik ? Durum.kullaniciAdi : "Oturum kapalı";
    Elemanlar.profilRolu.textContent = oturumAcik ? (yoneticiMi() ? "Yönetici" : "Kullanıcı") : "Giriş gerekli";
    Elemanlar.profilAvatar.textContent = oturumAcik && Durum.kullaniciAdi ? Durum.kullaniciAdi.charAt(0).toLocaleUpperCase("tr-TR") : "K";
    Elemanlar.cikisDugmesi.hidden = !oturumAcik;
    document.querySelectorAll("[data-yonetici-ogesi]").forEach((eleman) => {
        eleman.hidden = !yoneticiMi();
    });
}

async function jsonIstegi(yol, secenekler = {}, yenidenDene = true) {
    const basliklar = new Headers(secenekler.headers || {});
    if (Durum.erisimBelirteci) {
        basliklar.set("Authorization", `Bearer ${Durum.erisimBelirteci}`);
    }
    if (secenekler.body && !basliklar.has("Content-Type")) {
        basliklar.set("Content-Type", "application/json");
    }
    const yanit = await fetch(yol, {...secenekler, headers: basliklar});
    if (yanit.status === 401 && yenidenDene && Durum.yenilemeBelirteci) {
        const yenilendi = await belirteciYenile();
        if (yenilendi) {
            return jsonIstegi(yol, secenekler, false);
        }
    }
    if (!yanit.ok) {
        let mesaj = `İstek tamamlanamadı (${yanit.status})`;
        try {
            const hata = await yanit.json();
            if (typeof hata.detail === "string") {
                mesaj = hata.detail;
            }
        } catch {
            mesaj = `İstek tamamlanamadı (${yanit.status})`;
        }
        throw new Error(mesaj);
    }
    return yanit;
}

async function belirteciYenile() {
    try {
        const yanit = await fetch("/api/v1/kimlik-dogrulama/yenile", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({yenileme_belirteci: Durum.yenilemeBelirteci})
        });
        if (!yanit.ok) {
            throw new Error("Oturum yenilenemedi");
        }
        const veri = await yanit.json();
        belirtecleriKaydet(veri);
        profilGuncelle();
        return true;
    } catch {
        oturumuTemizle();
        profilGuncelle();
        girisPenceresiniAc();
        return false;
    }
}

function girisPenceresiniAc() {
    if (!Elemanlar.girisPenceresi.open) {
        Elemanlar.girisPenceresi.showModal();
    }
}

async function girisYap(olay) {
    olay.preventDefault();
    const formVerisi = new FormData(Elemanlar.girisFormu);
    const kullaniciAdi = String(formVerisi.get("kullanici_adi") || "").trim();
    const sifre = String(formVerisi.get("sifre") || "");
    Elemanlar.girisDugmesi.disabled = true;
    Elemanlar.girisHatasi.textContent = "";
    try {
        const yanit = await fetch("/api/v1/kimlik-dogrulama/giris", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({kullanici_adi: kullaniciAdi, sifre})
        });
        if (!yanit.ok) {
            throw new Error("Kullanıcı adı veya şifre geçersiz");
        }
        const veri = await yanit.json();
        belirtecleriKaydet(veri, kullaniciAdi);
        profilGuncelle();
        Elemanlar.girisPenceresi.close();
        Elemanlar.girisFormu.reset();
        bildirimGoster("Oturum başarıyla açıldı.");
        await sayfaVerisiniYukle();
    } catch (hata) {
        Elemanlar.girisHatasi.textContent = hata.message;
    } finally {
        Elemanlar.girisDugmesi.disabled = false;
    }
}

async function cikisYap() {
    try {
        if (Durum.erisimBelirteci && Durum.yenilemeBelirteci) {
            await jsonIstegi("/api/v1/kimlik-dogrulama/cikis", {
                method: "POST",
                body: JSON.stringify({yenileme_belirteci: Durum.yenilemeBelirteci})
            }, false);
        }
    } catch {
        bildirimGoster("Sunucu oturumu kapatılamadı; yerel oturum temizlendi.", "hata");
    } finally {
        oturumuTemizle();
        profilGuncelle();
        girisPenceresiniAc();
    }
}

async function sistemDurumunuDenetle() {
    try {
        const [saglikYaniti, hazirlikYaniti] = await Promise.all([
            fetch("/api/saglik"),
            fetch("/api/hazirlik")
        ]);
        if (!saglikYaniti.ok || !hazirlikYaniti.ok) {
            throw new Error("Servis hazır değil");
        }
        Elemanlar.durumNoktasi.className = "durum-noktasi basarili";
        Elemanlar.durumMetni.textContent = "Tüm sistemler çalışıyor";
        Elemanlar.uyariMetni.textContent = "Bilgi tabanı hazır. Yanıtlar güven eşiği ve kaynak doğrulamasıyla üretiliyor.";
        const hazirlikMetrigi = document.getElementById("hazirlik-metrigi");
        if (hazirlikMetrigi) {
            hazirlikMetrigi.textContent = "Hazır";
        }
    } catch {
        Elemanlar.durumNoktasi.className = "durum-noktasi hatali";
        Elemanlar.durumMetni.textContent = "Servis kısıtlı";
        Elemanlar.uyariMetni.textContent = "Bilgi tabanı şu anda hazır değil. Bir süre sonra yeniden deneyin.";
    }
}

function mesajiEkle(rol, metin = "") {
    const makale = document.createElement("article");
    makale.className = `mesaj ${rol === "kullanici" ? "kullanici-mesaji" : "asistan-mesaji"}`;
    const avatar = metinElemani("span", "mesaj-avatar", rol === "kullanici" ? "S" : "H");
    avatar.setAttribute("aria-hidden", "true");
    const govde = document.createElement("div");
    govde.className = "mesaj-govdesi";
    govde.append(metinElemani("span", "mesaj-rolu", rol === "kullanici" ? "Siz" : "HadesBot"));
    const paragraf = metinElemani("p", "", metin);
    govde.append(paragraf);
    makale.append(avatar, govde);
    const alan = document.getElementById("mesaj-alani");
    alan.append(makale);
    alan.scrollTop = alan.scrollHeight;
    return paragraf;
}

function kaynaklariGoster(kaynaklar) {
    const liste = document.getElementById("kaynak-listesi");
    liste.replaceChildren();
    if (!kaynaklar.length) {
        liste.append(metinElemani("p", "bos-durum", "Bu yanıt için gösterilebilir kaynak bulunamadı."));
        return;
    }
    kaynaklar.forEach((kaynak, sira) => {
        const rozet = document.createElement("div");
        rozet.className = "kaynak-rozeti";
        const baslik = kaynak.kaynak_dokuman || kaynak.kaynak || `Kurumsal kaynak ${sira + 1}`;
        const detay = kaynak.kaynak_metni || kaynak.kaynak_sayfa || `SSS kaydı ${kaynak.sss_id || sira + 1}`;
        rozet.append(
            metinElemani("strong", "", baslik),
            metinElemani("span", "", detay)
        );
        liste.append(rozet);
    });
}

function guveniGoster(skor) {
    const yuzde = Math.max(0, Math.min(100, Math.round(Number(skor || 0) * 100)));
    document.getElementById("guven-degeri").textContent = `%${yuzde}`;
    document.getElementById("guven-etiketi").textContent = yuzde >= 70 ? "Yüksek güven" : yuzde >= 45 ? "Orta güven" : "Düşük güven";
    document.getElementById("guven-cizgisi").style.width = `${yuzde}%`;
}

function sseBloklariniAyristir(tampon) {
    const bloklar = tampon.split(/\r?\n\r?\n/);
    return {
        tamamlananlar: bloklar.slice(0, -1),
        kalan: bloklar.at(-1) || ""
    };
}

function sseOlayiniOku(blok) {
    let olay = "message";
    const veriSatirlari = [];
    blok.split(/\r?\n/).forEach((satir) => {
        if (satir.startsWith("event:")) {
            olay = satir.slice(6).trim();
        }
        if (satir.startsWith("data:")) {
            veriSatirlari.push(satir.slice(5).trimStart());
        }
    });
    if (!veriSatirlari.length) {
        return null;
    }
    return {olay, veri: JSON.parse(veriSatirlari.join("\n"))};
}

function gecmiseEkle(soru, cevap) {
    const kayitlar = JSON.parse(sessionStorage.getItem("hadesbot_gecmis") || "[]");
    kayitlar.unshift({
        soru: soru.slice(0, 160),
        cevap: cevap.slice(0, 240),
        tarih: new Date().toISOString()
    });
    sessionStorage.setItem("hadesbot_gecmis", JSON.stringify(kayitlar.slice(0, 20)));
}

async function soruGonder(olay) {
    olay.preventDefault();
    const girdi = document.getElementById("soru-girdisi");
    const dugme = document.getElementById("gonder-dugmesi");
    const soru = girdi.value.trim();
    if (!soru || dugme.disabled) {
        return;
    }
    Durum.sonSoru = soru;
    Durum.sonCevap = "";
    Durum.sonKaynaklar = [];
    mesajiEkle("kullanici", soru);
    const cevapParagrafi = mesajiEkle("asistan", "Yanıt hazırlanıyor…");
    girdi.value = "";
    girdi.dispatchEvent(new Event("input"));
    dugme.disabled = true;
    try {
        let yanit = await jsonIstegi("/api/v1/arama", {
            method: "POST",
            headers: {"Accept": "text/event-stream"},
            body: JSON.stringify({
                soru,
                oturum_id: Durum.oturumId || null
            })
        });
        if (!yanit.body) {
            throw new Error("Canlı yanıt akışı başlatılamadı");
        }
        const okuyucu = yanit.body.getReader();
        const metinCozucu = new TextDecoder();
        let tampon = "";
        let cevap = "";
        while (true) {
            const {value, done} = await okuyucu.read();
            tampon += metinCozucu.decode(value || new Uint8Array(), {stream: !done});
            const ayrisim = sseBloklariniAyristir(tampon);
            tampon = ayrisim.kalan;
            ayrisim.tamamlananlar.forEach((blok) => {
                const veri = sseOlayiniOku(blok);
                if (!veri) {
                    return;
                }
                if (veri.olay === "oturum") {
                    Durum.oturumId = String(veri.veri.oturum_id || "");
                    sessionStorage.setItem("hadesbot_oturum", Durum.oturumId);
                }
                if (veri.olay === "meta") {
                    Durum.sonKaynaklar = Array.isArray(veri.veri.kaynaklar) ? veri.veri.kaynaklar : [];
                    guveniGoster(veri.veri.guven_skoru);
                    kaynaklariGoster(Durum.sonKaynaklar);
                }
                if (veri.olay === "parca") {
                    cevap += String(veri.veri.metin || "");
                    cevapParagrafi.innerHTML = markdownDonustur(cevap);
                }
                if (veri.olay === "hata") {
                    throw new Error(String(veri.veri.mesaj || "Yanıt üretilemedi"));
                }
            });
            if (done) {
                break;
            }
        }
        if (!cevap) {
            cevapParagrafi.textContent = "Bu soru için yeterli güvene sahip bir yanıt bulunamadı.";
        }
        Durum.sonCevap = cevapParagrafi.textContent;
        gecmiseEkle(soru, Durum.sonCevap);
    } catch (hata) {
        cevapParagrafi.textContent = hata.message;
        bildirimGoster(hata.message, "hata");
    } finally {
        dugme.disabled = false;
        girdi.focus();
    }
}

function sohbetiSifirla() {
    Durum.oturumId = "";
    sessionStorage.removeItem("hadesbot_oturum");
    const alan = document.getElementById("mesaj-alani");
    Array.from(alan.children).forEach((eleman, sira) => {
        if (sira > 0) {
            eleman.remove();
        }
    });
    kaynaklariGoster([]);
    guveniGoster(0);
}

function sohbetiHazirla() {
    const form = document.getElementById("soru-formu");
    if (!form) {
        return;
    }
    const girdi = document.getElementById("soru-girdisi");
    const sayac = document.getElementById("karakter-sayaci");
    form.addEventListener("submit", soruGonder);
    girdi.addEventListener("input", () => {
        sayac.textContent = String(girdi.value.length);
        girdi.style.height = "auto";
        girdi.style.height = `${Math.min(girdi.scrollHeight, 160)}px`;
    });
    girdi.addEventListener("keydown", (olay) => {
        if (olay.key === "Enter" && !olay.shiftKey) {
            olay.preventDefault();
            form.requestSubmit();
        }
    });
    document.querySelectorAll("[data-hizli-soru]").forEach((dugme) => {
        dugme.addEventListener("click", () => {
            girdi.value = dugme.dataset.hizliSoru;
            girdi.dispatchEvent(new Event("input"));
            form.requestSubmit();
        });
    });
    document.getElementById("yeni-sohbet").addEventListener("click", sohbetiSifirla);
}

function listeBosDurumu(liste, mesaj) {
    liste.replaceChildren(metinElemani("p", "bos-durum", mesaj));
}

function veriSatiriOlustur(baslik, aciklama, rozet) {
    const satir = document.createElement("article");
    satir.className = "veri-satiri";
    const metin = document.createElement("div");
    metin.append(
        metinElemani("h3", "", baslik),
        metinElemani("p", "", aciklama)
    );
    satir.append(metin, metinElemani("span", "durum-rozeti", rozet));
    return satir;
}

async function yoneticiVerisiniYukle() {
    if (!yoneticiMi()) {
        return;
    }
    const geriListe = document.getElementById("geri-bildirim-listesi");
    const cevapsizListe = document.getElementById("cevapsiz-sorgu-listesi");
    if (!geriListe || !cevapsizListe) {
        return;
    }
    try {
        const [geriYaniti, cevapsizYaniti] = await Promise.all([
            jsonIstegi("/api/v1/yonetici/geri-bildirimler?sayfa=1&sayfa_basina=20"),
            jsonIstegi("/api/v1/yonetici/cevapsiz-sorgular?sayfa=1&sayfa_basina=20")
        ]);
        const geriVerisi = await geriYaniti.json();
        const cevapsizVerisi = await cevapsizYaniti.json();
        document.getElementById("bekleyen-metrigi").textContent = String(geriVerisi.toplam);
        document.getElementById("cevapsiz-metrigi").textContent = String(cevapsizVerisi.toplam);
        geriListe.replaceChildren();
        cevapsizListe.replaceChildren();
        geriVerisi.bildirimler.forEach((bildirim) => {
            geriListe.append(veriSatiriOlustur(
                bildirim.kullanici_sorusu,
                `Puan ${bildirim.puan}/5 · Kayıt ${bildirim.id}`,
                "BEKLEMEDE"
            ));
        });
        cevapsizVerisi.sorgular.forEach((sorgu) => {
            const guven = sorgu.guven_skoru === null ? "ölçülmedi" : `%${Math.round(sorgu.guven_skoru * 100)}`;
            cevapsizListe.append(veriSatiriOlustur(
                sorgu.kullanici_sorusu,
                `${sorgu.kullanici_adi || "Bilinmeyen kullanıcı"} · Güven ${guven}`,
                sorgu.cevaplandi_mi ? "DÜŞÜK GÜVEN" : "CEVAPSIZ"
            ));
        });
        if (!geriVerisi.bildirimler.length) {
            listeBosDurumu(geriListe, "Bekleyen geri bildirim bulunmuyor.");
        }
        if (!cevapsizVerisi.sorgular.length) {
            listeBosDurumu(cevapsizListe, "Cevapsız veya düşük güvenli sorgu bulunmuyor.");
        }
    } catch (hata) {
        listeBosDurumu(geriListe, hata.message);
        listeBosDurumu(cevapsizListe, hata.message);
        bildirimGoster(hata.message, "hata");
    }
}

function kategoriGrafiginiOlustur(kategoriler) {
    const grafik = document.getElementById("kategori-grafigi");
    grafik.replaceChildren();
    if (!kategoriler.length) {
        listeBosDurumu(grafik, "Kategori verisi bulunmuyor.");
        return;
    }
    const enYuksek = Math.max(...kategoriler.map((kategori) => Number(kategori.adet || 0)), 1);
    kategoriler.forEach((kategori) => {
        const satir = document.createElement("div");
        satir.className = "grafik-satiri";
        const cizgi = document.createElement("div");
        cizgi.className = "grafik-cizgisi";
        const dolgu = document.createElement("span");
        dolgu.style.width = `${Math.max(3, Number(kategori.adet || 0) / enYuksek * 100)}%`;
        cizgi.append(dolgu);
        satir.append(
            metinElemani("span", "grafik-etiketi", String(kategori.kategori || "Kategorisiz")),
            cizgi,
            metinElemani("span", "grafik-degeri", String(kategori.adet || 0))
        );
        grafik.append(satir);
    });
}

async function analitikVerisiniYukle() {
    if (!yoneticiMi() || !document.getElementById("toplam-soru")) {
        return;
    }
    try {
        const yanit = await jsonIstegi("/api/v1/analitik");
        const veri = await yanit.json();
        document.getElementById("toplam-soru").textContent = String(veri.toplam_soru_sayisi);
        document.getElementById("toplam-geri-bildirim").textContent = String(veri.toplam_geri_bildirim_sayisi);
        document.getElementById("ortalama-puan").textContent = Number(veri.ortalama_puan).toLocaleString("tr-TR", {maximumFractionDigits: 2});
        document.getElementById("bekleyen-onay").textContent = String(veri.bekleyen_onay_sayisi);
        kategoriGrafiginiOlustur(veri.en_cok_sorulan_kategoriler || []);
        const liste = document.getElementById("analitik-cevapsiz-listesi");
        liste.replaceChildren();
        (veri.cevapsiz_kalan_sorular || []).forEach((sorgu) => {
            const guven = sorgu.guven_skoru === null ? "ölçülmedi" : `%${Math.round(sorgu.guven_skoru * 100)}`;
            liste.append(veriSatiriOlustur(
                String(sorgu.kullanici_sorusu),
                new Date(sorgu.olusturulma_tarihi).toLocaleString("tr-TR"),
                guven
            ));
        });
        if (!veri.cevapsiz_kalan_sorular.length) {
            listeBosDurumu(liste, "Cevapsız soru bulunmuyor.");
        }
    } catch (hata) {
        bildirimGoster(hata.message, "hata");
    }
}

async function sayfaVerisiniYukle() {
    if (!Durum.erisimBelirteci) {
        return;
    }
    const sayfa = Elemanlar.govde.dataset.sayfa;
    if ((sayfa === "yonetici" || sayfa === "analitik") && !yoneticiMi()) {
        window.location.replace("/");
        return;
    }
    if (sayfa === "yonetici") {
        await yoneticiVerisiniYukle();
    }
    if (sayfa === "analitik") {
        await analitikVerisiniYukle();
    }
}

function gecmisPaneliniDoldur() {
    const liste = document.getElementById("gecmis-listesi");
    const kayitlar = JSON.parse(sessionStorage.getItem("hadesbot_gecmis") || "[]");
    liste.replaceChildren();
    kayitlar.forEach((kayit) => {
        const oge = document.createElement("article");
        oge.className = "gecmis-ogesi";
        oge.append(
            metinElemani("strong", "", String(kayit.soru)),
            metinElemani("small", "", new Date(kayit.tarih).toLocaleString("tr-TR"))
        );
        liste.append(oge);
    });
    if (!kayitlar.length) {
        listeBosDurumu(liste, "Bu tarayıcı oturumunda henüz soru sorulmadı.");
    }
}

function cekmeceyiAc(ad) {
    document.querySelectorAll(".yan-cekmece").forEach((panel) => {
        panel.hidden = true;
    });
    const panel = document.getElementById(`${ad}-paneli`);
    if (!panel) {
        return;
    }
    if (ad === "gecmis") {
        gecmisPaneliniDoldur();
    }
    panel.hidden = false;
    Elemanlar.cekmeceOrtusu.hidden = false;
    panel.querySelector("button").focus();
}

function cekmeceleriKapat() {
    document.querySelectorAll(".yan-cekmece").forEach((panel) => {
        panel.hidden = true;
    });
    Elemanlar.cekmeceOrtusu.hidden = true;
}

function ayarlariHazirla() {
    const kompakt = document.getElementById("kompakt-gorunum");
    const hareket = document.getElementById("hareket-azalt");
    kompakt.checked = localStorage.getItem("hadesbot_kompakt") === "1";
    hareket.checked = localStorage.getItem("hadesbot_hareket_azalt") === "1";
    Elemanlar.govde.classList.toggle("kompakt", kompakt.checked);
    Elemanlar.govde.classList.toggle("hareket-azalt", hareket.checked);
    kompakt.addEventListener("change", () => {
        localStorage.setItem("hadesbot_kompakt", kompakt.checked ? "1" : "0");
        Elemanlar.govde.classList.toggle("kompakt", kompakt.checked);
    });
    hareket.addEventListener("change", () => {
        localStorage.setItem("hadesbot_hareket_azalt", hareket.checked ? "1" : "0");
        Elemanlar.govde.classList.toggle("hareket-azalt", hareket.checked);
    });
}

function temelEtkilesimleriHazirla() {
    document.querySelector(`[data-nav="${Elemanlar.govde.dataset.sayfa}"]`)?.setAttribute("aria-current", "page");
    Elemanlar.girisFormu.addEventListener("submit", girisYap);
    Elemanlar.cikisDugmesi.addEventListener("click", cikisYap);
    Elemanlar.mobilMenu.addEventListener("click", () => {
        const acik = Elemanlar.yanPanel.classList.toggle("acik");
        Elemanlar.mobilMenu.setAttribute("aria-expanded", String(acik));
    });
    document.querySelectorAll("[data-panel-ac]").forEach((dugme) => {
        dugme.addEventListener("click", () => cekmeceyiAc(dugme.dataset.panelAc));
    });
    document.querySelectorAll("[data-panel-kapat]").forEach((dugme) => {
        dugme.addEventListener("click", cekmeceleriKapat);
    });
    Elemanlar.cekmeceOrtusu.addEventListener("click", cekmeceleriKapat);
    document.getElementById("uyari-kapat").addEventListener("click", () => {
        Elemanlar.uyariBandi.hidden = true;
    });
    document.getElementById("yonetici-yenile")?.addEventListener("click", yoneticiVerisiniYukle);
    document.addEventListener("keydown", (olay) => {
        if (olay.key === "Escape") {
            cekmeceleriKapat();
            Elemanlar.yanPanel.classList.remove("acik");
        }
    });
}

async function uygulamayiBaslat() {
    temelEtkilesimleriHazirla();
    ayarlariHazirla();
    sohbetiHazirla();
    profilGuncelle();
    await sistemDurumunuDenetle();
    if (!Durum.erisimBelirteci) {
        girisPenceresiniAc();
        return;
    }
    await sayfaVerisiniYukle();
}

uygulamayiBaslat();
