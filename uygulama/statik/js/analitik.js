function canvasGrafikOlustur(tuvalId, veri, etiketHaritasi) {
    const tuval = document.getElementById(tuvalId);
    if (!tuval || !veri.length) {
        return;
    }
    const ctx = tuval.getContext("2d");
    const genislik = tuval.offsetWidth;
    const yukseklik = tuval.offsetHeight;
    tuval.width = genislik * 2;
    tuval.height = yukseklik * 2;
    ctx.scale(2, 2);
    const merkezX = genislik / 2;
    const merkezY = yukseklik / 2;
    const yaricap = Math.min(merkezX, merkezY) * 0.7;
    const toplam = veri.reduce(function(toplam, oge) { return toplam + (Number(oge.deger) || 0); }, 0);
    if (toplam <= 0) {
        return;
    }
    var baslangicAcisi = -Math.PI / 2;
    var renkler = ["#6366f1", "#8b5cf6", "#d946ef", "#ec4899", "#f43f5e", "#f97316", "#eab308", "#22c55e"];
    veri.forEach(function(oge, indeks) {
        var deger = Number(oge.deger) || 0;
        var dilimAcisi = (deger / toplam) * 2 * Math.PI;
        ctx.beginPath();
        ctx.moveTo(merkezX, merkezY);
        ctx.arc(merkezX, merkezY, yaricap, baslangicAcisi, baslangicAcisi + dilimAcisi);
        ctx.closePath();
        ctx.fillStyle = renkler[indeks % renkler.length];
        ctx.fill();
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2;
        ctx.stroke();
        if (dilimAcisi > 0.3) {
            var etiketAcisi = baslangicAcisi + dilimAcisi / 2;
            var etiketX = merkezX + Math.cos(etiketAcisi) * yaricap * 0.65;
            var etiketY = merkezY + Math.sin(etiketAcisi) * yaricap * 0.65;
            ctx.fillStyle = "#fff";
            ctx.font = "bold 12px system-ui";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            var etiket = etiketHaritasi ? (etiketHaritasi[oge.etiket] || oge.etiket) : oge.etiket;
            ctx.fillText(etiket, etiketX, etiketY);
        }
        baslangicAcisi += dilimAcisi;
    });
}

function yatayCubukGrafikOlustur(tuvalId, veri, etiketHaritasi) {
    var tuval = document.getElementById(tuvalId);
    if (!tuval || !veri.length) {
        return;
    }
    var ctx = tuval.getContext("2d");
    var genislik = tuval.offsetWidth;
    var yukseklik = veri.length * 40 + 20;
    tuval.width = genislik * 2;
    tuval.height = yukseklik * 2;
    ctx.scale(2, 2);
    var enYuksek = Math.max.apply(null, veri.map(function(oge) { return Number(oge.deger) || 0; }));
    if (enYuksek < 1) { enYuksek = 1; }
    veri.forEach(function(oge, indeks) {
        var y = indeks * 40 + 10;
        var genislikYuzdesi = ((Number(oge.deger) || 0) / enYuksek) * (genislik * 0.6);
        ctx.fillStyle = "#6366f1";
        ctx.fillRect(genislik * 0.25, y, genislikYuzdesi, 28);
        ctx.fillStyle = "#1e293b";
        ctx.font = "13px system-ui";
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        var etiket = etiketHaritasi ? (etiketHaritasi[oge.etiket] || oge.etiket) : oge.etiket;
        ctx.fillText(etiket, genislik * 0.23, y + 14);
        ctx.fillStyle = "#fff";
        ctx.textAlign = "left";
        ctx.fillText(String(oge.deger), genislik * 0.25 + genislikYuzdesi + 8, y + 14);
    });
}

function metrikMetniniAyarla(kimlik, metin) {
    var oge = document.getElementById(kimlik);
    if (oge) {
        oge.textContent = String(metin);
    }
}

function karantinaListesiniDoldur(karantinalar) {
    var liste = document.getElementById("karantina-listesi");
    if (!liste) {
        return;
    }
    liste.replaceChildren();
    if (!karantinalar.length) {
        var bos = document.createElement("p");
        bos.textContent = "Karantinada belge bulunmuyor.";
        liste.appendChild(bos);
        return;
    }
    karantinalar.forEach(function(kayit) {
        var satir = document.createElement("div");
        satir.className = "veri-satiri";
        var ad = document.createElement("strong");
        ad.textContent = String(kayit.dosya_adi || "Belge");
        var neden = document.createElement("span");
        neden.textContent = String(kayit.karantina_nedeni || "Bilinmeyen hata");
        satir.append(ad, neden);
        liste.appendChild(satir);
    });
}

function analitikListeyiDoldur(kimlik, kayitlar, baslikAlani, detayOlusturucu, bosMesaj) {
    var liste = document.getElementById(kimlik);
    if (!liste) {
        return;
    }
    liste.replaceChildren();
    if (!kayitlar.length) {
        var bos = document.createElement("p");
        bos.className = "bos-durum";
        bos.textContent = bosMesaj;
        liste.appendChild(bos);
        return;
    }
    kayitlar.forEach(function(kayit) {
        var satir = document.createElement("div");
        satir.className = "veri-satiri";
        var govde = document.createElement("div");
        var baslik = document.createElement("h3");
        baslik.textContent = String(kayit[baslikAlani] || "—");
        var detay = document.createElement("p");
        detay.textContent = detayOlusturucu(kayit);
        govde.append(baslik, detay);
        satir.appendChild(govde);
        liste.appendChild(satir);
    });
}

async function belgeSurumleriniYukle(basliklar, dosyaYolu) {
    var sorgu = dosyaYolu ? "?dosya_yolu=" + encodeURIComponent(dosyaYolu) : "";
    var yanit = await fetch("/api/v1/analitik/belge-surumleri" + sorgu, {headers: basliklar});
    if (!yanit.ok) {
        return;
    }
    var veri = await yanit.json();
    analitikListeyiDoldur(
        "belge-surum-listesi",
        veri.surumler || [],
        "dosya_adi",
        function(kayit) {
            return "Sürüm " + kayit.surum + " · " + (kayit.aktif ? "Aktif" : "Arşiv") + " · " + kayit.islenme_durumu;
        },
        "Belge sürümü bulunmuyor."
    );
}

async function gelismisAnalitikVerileriniYukle(basliklar) {
    var yanitlar = await Promise.all([
        fetch("/api/v1/analitik/parca-istatistikleri", {headers: basliklar}),
        fetch("/api/v1/analitik/sorgu-trendi", {headers: basliklar}),
        fetch("/api/v1/analitik/yetim-kavramlar", {headers: basliklar})
    ]);
    if (yanitlar[0].ok) {
        var parcalar = await yanitlar[0].json();
        analitikListeyiDoldur(
            "parca-istatistik-listesi",
            parcalar.turler || [],
            "parca_turu",
            function(kayit) { return kayit.adet + " parça · Ortalama " + kayit.ortalama_token + " token"; },
            "Yapısal parça bulunmuyor."
        );
    }
    if (yanitlar[1].ok) {
        var trend = await yanitlar[1].json();
        analitikListeyiDoldur(
            "sorgu-trendi-listesi",
            trend.gunler || [],
            "tarih",
            function(kayit) { return kayit.toplam + " sorgu · " + kayit.cevaplanan + " cevaplandı"; },
            "Son 30 günde sorgu bulunmuyor."
        );
    }
    if (yanitlar[2].ok) {
        var yetimler = await yanitlar[2].json();
        analitikListeyiDoldur(
            "yetim-kavram-listesi",
            yetimler.kavramlar || [],
            "etiket",
            function(kayit) { return "Kavram " + kayit.id + " · Bağlantı bekliyor"; },
            "Bağlantısız kavram bulunmuyor."
        );
    }
    await belgeSurumleriniYukle(basliklar, "");
}

async function dokumanRaporunuIndir() {
    var belirtec = sessionStorage.getItem("hadesbot_erisim");
    var yanit = await fetch("/api/v1/analitik/rapor/dokuman", {
        headers: {"Authorization": "Bearer " + belirtec}
    });
    if (!yanit.ok) {
        window.dispatchEvent(new CustomEvent("hadesbot:analitik-hatasi", {detail: "Rapor indirilemedi"}));
        return;
    }
    var veri = await yanit.json();
    var nesneAdresi = URL.createObjectURL(new Blob([JSON.stringify(veri, null, 2)], {type: "application/json"}));
    var baglanti = document.createElement("a");
    baglanti.href = nesneAdresi;
    baglanti.download = "hadesbot-dokuman-analitik.json";
    baglanti.click();
    URL.revokeObjectURL(nesneAdresi);
}

async function grafikVerileriniYukle() {
    var belirtec = sessionStorage.getItem("hadesbot_erisim");
    if (!belirtec) {
        return;
    }
    var basliklar = {
        "Authorization": "Bearer " + belirtec,
        "Content-Type": "application/json"
    };
    try {
        var belgeYaniti = await fetch("/api/v1/analitik/belge-dagilimi", {headers: basliklar});
        if (belgeYaniti.ok) {
            var belgeVerisi = await belgeYaniti.json();
            if (belgeVerisi.formata_gore) {
                var formataGore = Object.keys(belgeVerisi.formata_gore).map(function(anahtar) {
                    return {etiket: anahtar, deger: belgeVerisi.formata_gore[anahtar]};
                });
                canvasGrafikOlustur("belge-dagilim-grafigi", formataGore, {});
            }
            if (belgeVerisi.yetkiye_gore) {
                var yetkiyeGore = Object.keys(belgeVerisi.yetkiye_gore).map(function(anahtar) {
                    return {etiket: "Seviye " + anahtar, deger: belgeVerisi.yetkiye_gore[anahtar]};
                });
                yatayCubukGrafikOlustur("yetki-dagilim-grafigi", yetkiyeGore, {});
            }
        }
        var kavramYaniti = await fetch("/api/v1/analitik/kavram-bulutu", {headers: basliklar});
        if (kavramYaniti.ok) {
            var kavramVerisi = await kavramYaniti.json();
            if (kavramVerisi.kavramlar && kavramVerisi.kavramlar.length) {
                yatayCubukGrafikOlustur("kavram-bulutu-grafigi", kavramVerisi.kavramlar, {});
            }
        }
        var grafYaniti = await fetch("/api/v1/analitik/graf-istatistik", {headers: basliklar});
        if (grafYaniti.ok) {
            var grafVerisi = await grafYaniti.json();
            var dugumMetrigi = document.getElementById("graf-dugum-metrigi");
            var iliskiMetrigi = document.getElementById("graf-iliski-metrigi");
            if (dugumMetrigi) { dugumMetrigi.textContent = String(grafVerisi.dugum_sayisi || 0); }
            if (iliskiMetrigi) { iliskiMetrigi.textContent = String(grafVerisi.iliski_sayisi || 0); }
        }
        var senkroYaniti = await fetch("/api/v1/analitik/senkronizasyon-durumu", {headers: basliklar});
        if (senkroYaniti.ok) {
            var senkroVerisi = await senkroYaniti.json();
            metrikMetniniAyarla("senkro-durum-metrigi", senkroVerisi.aktif ? "Aktif" : "Pasif");
            metrikMetniniAyarla("senkro-bekleyen-metrigi", String(senkroVerisi.bekleyen_belge || 0) + " bekleyen belge");
        }
        var vektorYaniti = await fetch("/api/v1/analitik/vektor-durumu", {headers: basliklar});
        if (vektorYaniti.ok) {
            var vektorVerisi = await vektorYaniti.json();
            metrikMetniniAyarla("vektor-toplam-metrigi", vektorVerisi.toplam_vektor || 0);
            metrikMetniniAyarla("vektor-eksik-metrigi", String(vektorVerisi.eksik_vektor || 0) + " eksik vektör");
        }
        var karantinaYaniti = await fetch("/api/v1/analitik/karantina", {headers: basliklar});
        if (karantinaYaniti.ok) {
            var karantinaVerisi = await karantinaYaniti.json();
            karantinaListesiniDoldur(karantinaVerisi.karantinalar || []);
        }
        await gelismisAnalitikVerileriniYukle(basliklar);
    } catch (hata) {
        var durumMetrigi = document.getElementById("senkro-durum-metrigi");
        if (durumMetrigi) {
            durumMetrigi.textContent = "Yuklenemedi";
        }
        window.dispatchEvent(new CustomEvent("hadesbot:analitik-hatasi", {detail: String(hata)}));
    }
}

document.addEventListener("DOMContentLoaded", function() {
    if (document.body.dataset.sayfa === "analitik") {
        var surumFormu = document.getElementById("belge-surum-formu");
        surumFormu.addEventListener("submit", async function(olay) {
            olay.preventDefault();
            var belirtec = sessionStorage.getItem("hadesbot_erisim");
            await belgeSurumleriniYukle(
                {"Authorization": "Bearer " + belirtec},
                document.getElementById("belge-yolu").value.trim()
            );
        });
        document.getElementById("dokuman-raporu-indir").addEventListener("click", dokumanRaporunuIndir);
        grafikVerileriniYukle();
    }
});
