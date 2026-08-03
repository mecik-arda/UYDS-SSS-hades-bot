# HadesBot Proje Kuralları

## Kodlama

- Üretilen kodlarda yorum satırı, satır içi yorum, çok satırlı yorum, docstring veya devre dışı bırakılmış kod kullanma.
- Kod kendini açıklamalı; açıklayıcı Türkçe değişken, fonksiyon, sınıf, modül, tablo, sütun ve endpoint isimleri kullan.
- Yer tutucu, eksik mantık, TODO veya çalışmayacak örnek kod bırakma.
- Yeni kod üretirken mevcut mimariyi ve proje içindeki adlandırma düzenini koru.

## Dokümantasyon

- Medium veya sınırlı Markdown desteği olan içeriklerde Markdown tablosu kullanma.
- Teknik, bilimsel ve güvenlik içeriklerinde profesyonel ve emojisiz dil kullan.
- Kullanıcı açıkça istemedikçe teknik metinlerde sembol ve emoji kullanma.

## Güvenlik ve Veri

- Gerçek sırları, API anahtarlarını, parolaları, tokenları, özel anahtarları veya kurumsal verileri kaynak koda yazma.
- Gerçek `.env`, `sirlar/`, veritabanı, Excel, SQLite, vektör, model, yedek ve log dosyalarını Git’e ekleme.
- Commit veya push öncesi takip edilen dosyalarda secret ve hassas dosya taraması yap.
- Bir sırın sızdığı tespit edilirse ilgili sağlayıcıda derhal iptal edilmesini ve yenilenmesini bildir.
- Ofansif güvenlik framework’lerini uygulamanın bağımlılıklarına veya kaynak koduna ekleme.
- Güvenlik testlerini uygulamadan bağımsız, kontrollü black-box test süreci olarak yürüt.

## Embedding ve Vektörler

- Varsayılan embedding yöntemi yerel model olmalı.
- Model kimliği, sabit revizyonu, tokenizer sürümü, pooling yöntemi ve vektör boyutunu kaydet.
- Model veya vektör yapılandırması değişirse aktif içerikleri yeni sürüm altında yeniden vektörle.
- Eski ve yeni vektör sürümlerini doğrulama tamamlanmadan karıştırma.
- Yeniden vektörlemeyi atomik geçiş ve geri dönüş imkânı ile tamamla.
- Yeni embedding modelini temsili Türkçe sorgularla ölçmeden üretime alma.
- Harici embedding veya LLM kullanılıyorsa verinin dış sağlayıcıya aktarılabileceğini açıkça belirt.

## Kod Denetimi

- Denetime başlamadan önce varsa `hata_duzeltme_kaydi.md` dosyasını tamamen oku.
- Bulguları hata, performans, güvenlik ve gerektiğinde kod kalitesi başlıklarıyla önceliklendir.
- Her bulguda konumu, nedeni ve somut çözümü belirt.
- Güvenlik bulgularını kritik, yüksek, orta veya düşük olarak sınıflandır.
- Spekülasyonu bulgu olarak sunma; doğrulanamayan noktaları varsayım olarak belirt.

## Git İşlemleri

- Testleri çalıştırmadan değişiklikleri tamamlanmış kabul etme.
- Kullanıcı açıkça onay vermeden `git commit` veya `git push` çalıştırma.
- Commit veya push öncesi değişiklik özetini ve test sonucunu kullanıcıya sun.
