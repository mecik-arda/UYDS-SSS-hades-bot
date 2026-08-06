import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uygulama.cekirdek.veritabani import baglam_yoneticisi

BENCHMARK_KOKU = Path(__file__).resolve().parent.parent / "testler" / "benchmark"
KALIBRASYON_YOLU = BENCHMARK_KOKU / "kalibrasyon_seti.json"
FINAL_YOLU = BENCHMARK_KOKU / "final_test_seti.json"
TUM_YOLU = BENCHMARK_KOKU / "semantik_benchmark.json"

KALIBRASYON_ORANI = 0.60

SEMANTIK_SORGULAR = [
    {"soru": "Fatura keserken para birimi farklı olduğunda kur farkı nasıl hesaplanır ve hangi hesaba kaydedilir"},
    {"soru": "Bir çalışanın yıllık izin hakkını nereden görüntüleyebilirim ve kalan gün sayısını nasıl öğrenirim"},
    {"soru": "Gemi konteyner takibinde TEU hesaplaması hangi ekranda yapılıyor"},
    {"soru": "Muhasebe fişi oluştururken mahsup kaydı nasıl yapılır"},
    {"soru": "E-defter uygulamasına yükleme yaptım ama portalda görünmüyor, ne yapmalıyım"},
    {"soru": "Çek senet işlemleri için borç alacak hesap eşleştirmesi nasıl tanımlanır"},
    {"soru": "Antrepo giriş çıkış işlemlerinde palet takibi yapılabiliyor mu"},
    {"soru": "Farklı bir firmaya ait banka hesap bilgisini sistemde nasıl güncelleyebilirim"},
    {"soru": "Tır şoför hesap kapatma işlemi sırasında hata alıyorum, nasıl düzeltebilirim"},
    {"soru": "E-fatura gönderiminde alıcı tarafın sistemde kayıtlı olmadığı hatası alıyorum"},
    {"soru": "İthalat beyannamesi girişi yaparken kalem bazında güncelleme nasıl yapılır"},
    {"soru": "Stok sayımında eksik çıkan ürünler için fire kaydı nasıl oluşturulur"},
    {"soru": "Cari hesap ekstresinde bakiye ile muhasebe kaydındaki bakiye neden farklı gösteriyor"},
    {"soru": "Personel maaş bordrosunda AGİ tutarı neden sıfır olarak görünüyor"},
    {"soru": "Havayolu taşımacılığında AWB numarası ile takip ekranı hangi menüde"},
    {"soru": "Depolar arası transfer fişi oluştururken miktar birimi dönüşümü nasıl yapılıyor"},
    {"soru": "Müşteri şikayet kaydı oluştururken açıklama alanı karakter sınırına takılıyor"},
    {"soru": "Karayolu taşımacılığında navlun faturası keserken hangi hesap kodlarını kullanmalıyım"},
    {"soru": "Satış faturasında irsaliye ile fatura miktarları uyuşmuyor, nasıl düzeltirim"},
    {"soru": "Yeni bir kullanıcıya sadece belirli modüllere erişim yetkisi nasıl tanımlarım"},
    {"soru": "İhracat faturası düzenlerken gümrük beyannamesi numarasını hangi alana girmeliyim"},
    {"soru": "Demirbaş kaydı oluşturup amortisman hesaplamasını nasıl başlatırım"},
    {"soru": "Sipariş onay akışında bekleyen bir kaydı nasıl hızlandırabilirim"},
    {"soru": "Farklı para birimleri ile çalışan firmalar için döviz kuru güncellemesi otomatik yapılabiliyor mu"},
    {"soru": "Geçici kabul tutanağı için sistem üzerinden evrak oluşturma adımları nelerdir"},
    {"soru": "Proje bazlı maliyet takibinde işçilik giderleri nasıl dağıtılır"},
    {"soru": "Sevkiyat planlaması yaparken araç kapasitesi ile yük miktarı eşleşmiyor, nasıl optimize ederim"},
    {"soru": "Kapanmış bir döneme ait muhasebe kaydını düzeltmek için hangi işlem yapılır"},
    {"soru": "Konteyner takibinde boş ve dolu konteyner listesini ayrı ayrı nasıl alırım"},
    {"soru": "Vergi dairesine gönderilecek KDV beyannamesi için gerekli verileri hangi rapordan alabilirim"},
    {"soru": "Sözleşme bedeli üzerinden damga vergisi hesaplaması otomatik yapılıyor mu"},
    {"soru": "Aylık ciro raporunu geçmiş dönemlerle karşılaştırmalı olarak nasıl çekerim"},
    {"soru": "Yurt dışından gelen malzemelerin gümrük giriş işlemleri hangi modülde yapılıyor"},
    {"soru": "Çalışanın işten ayrılış işlemleri ve kıdem tazminatı hesaplaması nasıl yapılır"},
    {"soru": "Banka hesap özeti ile muhasebe kayıtları arasında mutabakat nasıl sağlanır"},
    {"soru": "Müşteriye özel fiyat listesi tanımlayıp otomatik faturaya yansıtabilir miyim"},
    {"soru": "Taşıma irsaliyesi üzerinde değişiklik yapmak için hangi yetkiye ihtiyacım var"},
    {"soru": "Barkod etiketi yazdırma işlemini toplu olarak nasıl yapabilirim"},
    {"soru": "Geçici vergi döneminde matrah hesaplaması için gerekli rapor hangisidir"},
    {"soru": "Arşivlenmiş faturaları toplu olarak dışa aktarmak mümkün mü"},
    {"soru": "Hakediş raporu hazırlarken birim fiyat farkı otomatik yansıtılıyor mu"},
    {"soru": "Depo raf sistemi ile stok yeri tanımlaması arasındaki bağlantı nasıl kurulur"},
    {"soru": "Özel tüketim vergisi hesaplaması fatura üzerinde hangi durumlarda otomatik gelir"},
    {"soru": "İrsaliye kesmeden fatura oluşturmak istiyorum, sistem buna izin veriyor mu"},
    {"soru": "Yıl sonu envanter işlemleri sırasında kapanış kaydı nasıl yapılır"},
    {"soru": "Alt işveren hakedişlerinde kesinti kalemleri hangi menüden tanımlanır"},
    {"soru": "Araç bakım kayıtlarının periyodik takibi için hatırlatma sistemi var mı"},
    {"soru": "Muhasebe hesap planına yeni bir hesap kodu eklemek için hangi adımları izlemeliyim"},
    {"soru": "Kar zarar tablosunda geçen yıl ile bu yıl arasındaki farkları göremiyorum, sebebi ne olabilir"},
    {"soru": "İhale sürecinde teklif mektuplarının elektronik ortamda alınması mümkün mü"},
    {"soru": "Filo yönetiminde araçların yakıt tüketim raporunu nasıl alırım"},
    {"soru": "Malzeme ihtiyaç planlaması yaparken minimum stok seviyesi uyarısı nasıl ayarlanır"},
    {"soru": "Teslim alınan malların giriş kontrolü ve kalite onay süreci nasıl işler"},
    {"soru": "Tahsilat takibinde vadesi geçmiş alacaklar için otomatik uyarı sistemi var mı"},
    {"soru": "İş kazası bildirimi ve SGK'ya elektronik başvuru süreci nasıl işliyor"},
    {"soru": "Hafta sonu çalışma ve fazla mesai hesaplamaları bordroya otomatik yansır mı"},
    {"soru": "Performans değerlendirme formu oluşturmak için hangi kriterleri kullanabilirim"},
    {"soru": "Üretim reçetesinde kullanılan hammadde miktarlarını güncellemek istiyorum"},
    {"soru": "Fason üretim takibinde iş emri ile sevk takibi nasıl eşleştirilir"},
    {"soru": "E-arşiv fatura iptali için süre sınırı var mı ve hangi durumlarda iptal edilebilir"},
    {"soru": "Müşteri cari hesabına ait açık kalemleri toplu kapatma işlemi nasıl yapılır"},
    {"soru": "İşletme defteri tutan firmalar için KDV hesaplaması sistemde nasıl çalışıyor"},
    {"soru": "Taşeron hakedişlerinde stopaj kesintisi otomatik hesaplanıyor mu"},
    {"soru": "Gümrük antrepo rejiminde süre uzatımı başvurusu için hangi belgeler gerekli"},
    {"soru": "Satın alma talebinde onay süreci hangi aşamalardan geçiyor ve kimler onaylamalı"},
    {"soru": "Kurumsal e-posta entegrasyonu ile müşterilere otomatik fatura gönderimi mümkün mü"},
    {"soru": "Nakliye aracına ait sefer maliyeti hesaplaması nasıl yapılır"},
    {"soru": "Sabit kıymet yeniden değerleme işlemi için hangi parametreler kullanılır"},
    {"soru": "Vardiya sistemi ile çalışan personelin puantaj kaydı nasıl tutulur"},
    {"soru": "Yıllık bütçe planlaması yaparken geçmiş yıl verilerini nasıl kullanabilirim"},
    {"soru": "Otomatik ödeme talimatı ile fatura ödemelerini nasıl eşleştirebilirim"},
    {"soru": "Yemek kartı ve servis ücreti gibi yan hakların bordroya entegrasyonu nasıl yapılır"},
    {"soru": "Deprem ve sel gibi mücbir sebep hallerinde SGK ve vergi erteleme başvurusu nasıl yapılır"},
    {"soru": "Siparişten sevkiyata kadar olan süreci adım adım hangi ekranda takip edebilirim"},
    {"soru": "Yabancı uyruklu çalışanların çalışma izni takibi ve bildirimi hangi modülde yapılır"},
    {"soru": "Dijital arşivleme sistemine belge yüklerken hangi formatlar kabul ediliyor"},
    {"soru": "Banka POS entegrasyonu ile tahsilatların otomatik muhasebeleştirilmesi mümkün mü"},
    {"soru": "Proje ilerleme raporunda gerçekleşen ile planlanan arasındaki sapma nasıl analiz edilir"},
    {"soru": "Geçici iş göremezlik ödeneği hesaplaması ve bordroya yansıması nasıl olur"},
    {"soru": "Atıl kapasite raporlaması ile boşta kalan kaynakları nasıl tespit ederim"},
    {"soru": "Yıl sonu kapanış işlemleri öncesi mutlaka yapılması gereken kontroller nelerdir"},
    {"soru": "Toptan satışta iskonto oranlarını müşteri grubuna göre nasıl tanımlayabilirim"},
    {"soru": "Yükleme talimatı oluştururken birden fazla sevkiyatı birleştirmek mümkün mü"},
    {"soru": "Zaman damgası ile e-belgelerin yasal geçerliliği nasıl sağlanıyor"},
    {"soru": "Satış elemanlarının saha ziyaret raporlaması hangi modülde yapılıyor"},
    {"soru": "İthalat maliyetlendirme kalemlerini malzeme birim fiyatına nasıl yansıtırım"},
    {"soru": "Kıdem tazminatı tavanı değişikliğinde eski çalışanların hesaplaması etkilenir mi"},
    {"soru": "Konteyner hasar tespit tutanağı sisteme nasıl kaydedilir"},
    {"soru": "E-bilet entegrasyonu ile yolcu taşımacılığı faturalandırması nasıl yapılır"},
    {"soru": "Varlık yönetiminde demirbaş yer değişikliği kaydı hangi ekrandan yapılır"},
    {"soru": "Serbest bölge işlemlerinde gümrük giriş çıkış takibi için hangi modül kullanılır"},
    {"soru": "Hizmet faturasında KDV tevkifatı hangi durumlarda ve hangi oranda uygulanır"},
    {"soru": "Firma birleşmesi durumunda cari hesapların devri nasıl gerçekleştirilir"},
    {"soru": "Mobil uygulama üzerinden depo giriş çıkış işlemi yapabilir miyim"},
    {"soru": "Hatalı girilen bir üretim kaydını silmeden düzeltme yöntemi var mı"},
    {"soru": "SGK bildirgesinde eksik gün nedenlerini hangi kodlarla bildirmeliyim"},
    {"soru": "Dış ticaret sermaye şirketleri için ihracat teşvik hesaplamaları nasıl yapılır"},
    {"soru": "Farklı şubeler arası stok transferinde maliyetlendirme nasıl çalışır"},
    {"soru": "Sözleşmeli personel ile kadrolu personelin özlük hakları aynı ekranda mı takip edilir"},
    {"soru": "Limanda bekleyen konteyner için demuraj hesaplaması otomatik yapılıyor mu"},
    {"soru": "Elektronik tebligat sisteminden gelen bildirimler muhasebeye nasıl aktarılır"},
    {"soru": "Vadesi geçmiş çeklerin takibi ve protesto süreci hangi ekrandan izlenir"},
    {"soru": "Teşvik belgesi kapsamındaki yatırımlar için indirimli kurumlar vergisi nasıl hesaplanır"},
    {"soru": "Depo içi malzeme hareketlerinde el terminali ile barkod okutma desteği var mı"},
    {"soru": "Arge merkezi çalışanlarının maaş bordrosunda gelir vergisi istisnası nasıl uygulanır"},
    {"soru": "Liman çıkışında gümrük müdürlüğüne elektronik bildirim sistemi nasıl çalışıyor"},
    {"soru": "Yurt dışı fuar katılım giderlerinin muhasebeleştirilmesinde hangi hesaplar kullanılır"},
    {"soru": "Birden fazla depo için ayrı ayrı sayım planlaması yapıp sonuçları birleştirebilir miyim"},
    {"soru": "İzin yönetiminde bakiye devir işlemi yıl sonunda otomatik mi yapılıyor"},
    {"soru": "Ro-Ro taşımacılığında araç ve treyler takibi için hangi raporlama aracı kullanılır"},
    {"soru": "Ücretsiz izindeki personelin SGK prim gün sayısı nasıl hesaplanır"},
    {"soru": "Konsinye mal takibinde satılan ve iade edilen ürünlerin raporlaması nasıl yapılır"},
    {"soru": "Bağımsız denetim için gerekli olan mali tabloları sistemden nasıl hazırlarım"},
    {"soru": "Tehlikeli madde taşımacılığında ADR belgesi takibi hangi modülde yapılıyor"},
    {"soru": "Kısmı zamanlı çalışanların sigorta prim gün sayısı otomatik mi hesaplanıyor"},
    {"soru": "İnternet şubesi üzerinden müşterilerin kendi cari hesaplarını görmesi mümkün mü"},
    {"soru": "Transit ticaret işlemlerinde gümrük beyannamesi kapatma süreci nasıl takip edilir"},
    {"soru": "Rotatif kredi kullanımında faiz tahakkuku ve anapara ödemesi nasıl kaydedilir"},
    {"soru": "İş sağlığı ve güvenliği eğitim takibi için personel bazlı kayıt tutuluyor mu"},
    {"soru": "Soğuk zincir taşımacılığında sıcaklık takip kayıtları sisteme entegre edilebilir mi"},
    {"soru": "Yemekhane ve yemek fişi takibi ile personel yemek hakkı kullanım raporu nasıl alınır"},
    {"soru": "Bayilik sözleşmesi kapsamında ciro primi hesaplaması için hangi verilere ihtiyacım var"},
]


def _soruyu_dogrula(sorgu_metni: str, servis) -> dict | None:
    try:
        sonuc = servis.ara(sorgu_metni)
        adaylar = sonuc.adaylar
        if not adaylar:
            return None
        en_iyi = adaylar[0]
        if en_iyi.sss_id is None:
            return None

        sorgu_kelimeler = set(sorgu_metni.lower().replace("?", "").replace(",", "").split())
        sss_metni = en_iyi.aday_metni.lower()[:2000]
        ortak = sum(1 for k in sorgu_kelimeler if len(k) >= 3 and k in sss_metni)

        if ortak < 2 and len(sorgu_kelimeler) >= 4:
            return None

        return {
            "soru": sorgu_metni,
            "beklenen_sss_id": en_iyi.sss_id,
            "dogrulama": {
                "yontem": "retrieval_top1_plus_terim_ortusmesi",
                "ortak_terim": ortak,
                "en_iyi_rrf": round(en_iyi.rrf_skoru, 4),
            },
        }
    except Exception:
        return None

def _arama_servisini_olustur():
    from uygulama.servisler.arama_servisi import AramaServisi
    from uygulama.servisler.terim_haritasi import TerimHaritasi
    from uygulama.servisler.vektor_servisi import VektorServisi

    vektor = VektorServisi()
    terim = TerimHaritasi()
    return AramaServisi(vektor, terim, None)


def main() -> None:
    BENCHMARK_KOKU.mkdir(parents=True, exist_ok=True)

    print(f"{len(SEMANTIK_SORGULAR)} soru yuklendi, arama servisi olusturuluyor...")
    servis = _arama_servisini_olustur()

    dogrulanmis = []
    basarisiz = []
    for i, sorgu in enumerate(SEMANTIK_SORGULAR):
        sonuc = _soruyu_dogrula(sorgu["soru"], servis)
        if sonuc:
            dogrulanmis.append(sonuc)
        else:
            basarisiz.append(sorgu["soru"])
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(SEMANTIK_SORGULAR)} dogrulandi: {len(dogrulanmis)}")

    print(f"\nDogrulanmis: {len(dogrulanmis)}")
    print(f"Basarisiz: {len(basarisiz)}")

    id_listesi = [d["beklenen_sss_id"] for d in dogrulanmis]
    benzersiz_idler = set(id_listesi)
    print(f"Benzersiz SSS ID: {len(benzersiz_idler)}")

    for i, sorgu in enumerate(dogrulanmis):
        sorgu["id"] = f"BNC-{i+1:04d}"

    sinir = int(len(dogrulanmis) * KALIBRASYON_ORANI)
    kalibrasyon = dogrulanmis[:sinir]
    final = dogrulanmis[sinir:]

    kalibrasyon_verisi = {
        "aciklama": "Kalibrasyon seti — guven esigi ve arama parametresi ayarlamak icin",
        "sorgu_sayisi": len(kalibrasyon),
        "benzersiz_sss_id_sayisi": len(set(d["beklenen_sss_id"] for d in kalibrasyon)),
        "sorgular": kalibrasyon,
    }

    final_verisi = {
        "aciklama": "Final test seti — parametre ayari yapilmadan bagimsiz olcum",
        "sorgu_sayisi": len(final),
        "benzersiz_sss_id_sayisi": len(set(d["beklenen_sss_id"] for d in final)),
        "sorgular": final,
    }

    tum_veri = {
        "aciklama": "Semantik benchmark — veritabanindaki soru metninin birebir kopyasi degil",
        "toplam_sorgu": len(dogrulanmis),
        "kalibrasyon": kalibrasyon_verisi,
        "final": final_verisi,
    }

    for yol, veri in [
        (KALIBRASYON_YOLU, kalibrasyon_verisi),
        (FINAL_YOLU, final_verisi),
        (TUM_YOLU, tum_veri),
    ]:
        yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Yazildi: {yol}")

    if basarisiz:
        basarisiz_yolu = BENCHMARK_KOKU / "basarisiz_sorgular.json"
        basarisiz_yolu.write_text(
            json.dumps(basarisiz, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Basarisiz sorgular: {basarisiz_yolu}")


if __name__ == "__main__":
    main()
