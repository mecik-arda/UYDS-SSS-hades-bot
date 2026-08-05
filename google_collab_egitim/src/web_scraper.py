import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
from datetime import datetime
import hashlib
import pandas as pd
from pathlib import Path

class UYDSScraper:
    MAX_DOSYA_BOYUTU = 200 * 1024 * 1024

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.downloaded_urls = set()
        self.results = []
        
    def search_google(self, query, max_results=10):
        """Google'da arama yapar ve sonuçları döner"""
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={max_results}&lr=lang_tr"
        try:
            response = self.session.get(search_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            
            for g in soup.find_all('div', class_='g'):
                anchor = g.find('a')
                if anchor and anchor.get('href'):
                    link = anchor['href']
                    if link.startswith('/url?q='):
                        link = link.split('/url?q=')[1].split('&')[0]
                    
                    # Sadece güvenilir sitelerden gelen linkleri al
                    if any(domain in link for domain in ['.gov.tr', 'csb.gov.tr', 'yapiisleri.csb.gov.tr', 'resmigazete.gov.tr', 'mevzuat.gov.tr']):
                        title_elem = g.find('h3')
                        title = title_elem.text if title_elem else "Başlık bulunamadı"
                        
                        links.append({
                            'url': link,
                            'title': title,
                            'query_used': query
                        })
            
            return links
        except Exception as e:
            print(f"Arama yapılırken hata oluştu: {e}")
            return []
    
    def is_valid_pdf_url(self, url):
        """PDF bağlantısı olup olmadığını kontrol eder"""
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()
        
        # URL'de PDF içerdiğini belirten parametreler
        if 'filetype:pdf' in url.lower():
            return True
            
        # Dosya uzantısı kontrolü
        if path.endswith('.pdf'):
            return True
            
        # Content-Type başlığı kontrolü için HEAD isteği
        try:
            head_response = self.session.head(url, timeout=10)
            content_type = head_response.headers.get('Content-Type', '').lower()
            if 'application/pdf' in content_type:
                return True
        except Exception:
            pass
            
        return False
    
    def download_file(self, url, destination_folder, filename=None):
        """Belirtilen URL'den dosya indirir"""
        try:
            # URL'nin gerçekten erişilebilir olup olmadığını kontrol et
            response = self.session.head(url, timeout=10)
            if response.status_code != 200:
                print(f"URL erişilemez (status: {response.status_code}): {url}")
                return None
                
            # MIME türü kontrolü
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' in content_type:
                print(f"HTML sayfası, dosya değil: {url}")
                return None
            
            # Dosya indirme
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Dosya uzantısı belirleme
            if not filename:
                parsed_url = urllib.parse.urlparse(url)
                path_parts = parsed_url.path.split('/')
                
                # URL'deki son parça dosya adı olabilir
                if path_parts and '.' in path_parts[-1]:
                    filename = path_parts[-1]
                elif 'application/pdf' in content_type:
                    filename = f"{hashlib.md5(url.encode()).hexdigest()[:8]}.pdf"
                else:
                    print(f"Bilinmeyen dosya türü: {url}")
                    return None
            
            # Güvenli dosya adı oluşturma
            filename = "".join(c for c in filename if c.isalnum() or c in "._- ").rstrip()
            filepath = os.path.join(destination_folder, filename)
            
            # Dosya adı benzersiz yapma
            counter = 1
            original_filepath = filepath
            while os.path.exists(filepath):
                name, ext = os.path.splitext(original_filepath)
                filepath = f"{name}_{counter}{ext}"
                counter += 1
            
            # Content-Length ön kontrolü
            content_length = response.headers.get('Content-Length')
            if content_length:
                try:
                    boyut = int(content_length)
                    if boyut > self.MAX_DOSYA_BOYUTU:
                        print(f"Dosya boyut sinirini asti ({boyut} > {self.MAX_DOSYA_BOYUTU}): {url}")
                        return None
                except (ValueError, TypeError):
                    pass

            # Dosyayı kaydetme
            toplam = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    toplam += len(chunk)
                    if toplam > self.MAX_DOSYA_BOYUTU:
                        f.close()
                        try:
                            os.remove(filepath)
                        except Exception:
                            pass
                        print(f"Dosya boyut sinirini asti ({toplam} > {self.MAX_DOSYA_BOYUTU}): {url}")
                        return None
                    f.write(chunk)
            
            # SHA256 checksum
            sha256_hash = hashlib.sha256()
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            return {
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'size': os.path.getsize(filepath),
                'sha256': sha256_hash.hexdigest(),
                'url': url
            }
        except Exception as e:
            print(f"Dosya indirme hatası: {e} - {url}")
            return None
    
    def categorize_document(self, url, title, query_used):
        """Belgeyi uygun kategoriye yerleştirir"""
        title_lower = title.lower()
        query_lower = query_used.lower()
        
        # Klasör belirleme
        if any(term in query_lower for term in ['kanun', 'yönetmelik', 'tebliğ', 'genelge', 'resmigazete']):
            folder = '01_mevzuat'
        elif any(term in query_lower for term in ['kılavuz', 'kullanıcı işlemleri', 'modül kılavuzu', 'eğitim']):
            folder = '02_resmi_uyds_kilavuzlari'
        elif any(term in query_lower for term in ['hakediş', 'laboratuvar', 'personel', 'denetçi', 'ruhsat', 'yapı kayıt', 'proje', 'şantiye']):
            if 'hakediş' in query_lower:
                folder = '03_modul_dokumanlari/hakedis'
            elif 'laboratuvar' in query_lower:
                folder = '03_modul_dokumanlari/laboratuvar'
            elif 'personel' in query_lower:
                folder = '03_modul_dokumanlari/personel'
            elif 'denetçi' in query_lower:
                folder = '03_modul_dokumanlari/denetci'
            elif 'ruhsat' in query_lower:
                folder = '03_modul_dokumanlari/ruhsat'
            elif 'yapı kayıt' in query_lower:
                folder = '03_modul_dokumanlari/yapi_kayit'
            elif 'proje' in query_lower:
                folder = '03_modul_dokumanlari/proje'
            elif 'şantiye' in query_lower:
                folder = '03_modul_dokumanlari/santiye_sefi'
            else:
                folder = '03_modul_dokumanlari'
        elif any(term in query_lower for term in ['hata', 'çözüm', 'teknik']):
            folder = '04_teknik_cozumler'
        elif any(term in query_lower for term in ['destek', 'kayıt']):
            folder = '05_onayli_destek_kayitlari'
        elif any(term in query_lower for term in ['sürüm', 'versiyon', 'duyuru']):
            folder = '06_surum_notlari'
        else:
            folder = '99_inceleme_bekleyenler'
        
        # Klasör yoksa oluştur
        full_path = f"../data/kaynaklar/{folder}"
        os.makedirs(full_path, exist_ok=True)
        
        return full_path, folder
    
    def assign_trust_score(self, url):
        """Belgeye güven puanı atar (A-E arası)"""
        if any(domain in url for domain in ['resmigazete.gov.tr', 'mevzuat.gov.tr']):
            return 'A'  # Kanun, yönetmelik, Resmî Gazete
        elif any(domain in url for domain in ['csb.gov.tr', 'yapiisleri.csb.gov.tr']):
            return 'B'  # Bakanlık veya resmî kurum kılavuzu
        elif '.gov.tr' in url:
            return 'C'  # Resmî kurum duyurusu veya il müdürlüğü rehberi
        elif 'belgeler.yapiisleri.csb.gov.tr' in url:
            return 'D'  # Kurum içi, izinli ve uzman onaylı teknik belge
        else:
            return 'E'  # Güvenilirliği henüz doğrulanmamış aday kaynak
    
    def process_search_results(self, search_terms):
        """Arama sonuçlarını işler ve dosyaları indirir"""
        for i, term in enumerate(search_terms):
            print(f"Arama {i+1}/{len(search_terms)}: {term}")
            
            results = self.search_google(term, max_results=5)
            print(f"  {len(results)} sonuç bulundu")
            
            for result in results:
                url = result['url']
                title = result['title']
                
                if url in self.downloaded_urls:
                    print(f"    Zaten indirilmiş: {url}")
                    continue
                
                print(f"    Kontrol ediliyor: {url}")
                
                # PDF mi diye kontrol et
                if self.is_valid_pdf_url(url):
                    # Kategoriye göre klasör belirle
                    dest_folder, category = self.categorize_document(url, title, term)
                    
                    # Dosyayı indir
                    file_info = self.download_file(url, dest_folder)
                    
                    if file_info:
                        # Güven puanı ata
                        trust_score = self.assign_trust_score(url)
                        
                        # Metadata oluştur
                        metadata = {
                            'url': url,
                            'title': title,
                            'category': category,
                            'trust_score': trust_score,
                            'file_path': file_info['filepath'],
                            'file_name': file_info['filename'],
                            'file_size': file_info['size'],
                            'sha256': file_info['sha256'],
                            'download_date': datetime.now().isoformat(),
                            'query_used': term
                        }
                        
                        self.results.append(metadata)
                        self.downloaded_urls.add(url)
                        
                        print(f"      ✓ İndirildi: {file_info['filename']} [{trust_score}]")
                    else:
                        print(f"      ✗ İndirme başarısız: {url}")
                else:
                    print(f"      ! PDF değil: {url}")

def main():
    scraper = UYDSScraper()
    
    # Arama terimlerini doğrudan tanımla
    search_terms = [
        'UYDS kullanım kılavuzu filetype:pdf',
        'Ulusal Yapı Denetim Sistemi kullanım kılavuzu',
        'UYDS eğitim dokümanı filetype:pdf',
        'UYDS kullanıcı işlemleri',
        'UYDS modül kılavuzu',
        'UYDS hata çözümü',
        'UYDS yetkilendirme',
        'UYDS hakediş işlemleri',
        'UYDS yapı kayıt işlemleri',
        'UYDS denetçi işlemleri',
        'UYDS laboratuvar modülü',
        'UYDS personel işlemleri',
        'UYDS proje müellifi işlemleri',
        'UYDS ruhsat işlemleri',
        'UYDS seviye tespit tutanağı',
        'UYDS iş bitirme işlemleri',
        'UYDS yapı denetim kuruluşu işlemleri',
        'UYDS şantiye şefi işlemleri',
        'Yapı Denetimi Uygulama Yönetmeliği',
        '4708 sayılı Yapı Denetimi Hakkında Kanun',
        'yapı denetimi genelge filetype:pdf',
        'yapı denetimi tebliğ filetype:pdf',
        'UYDS duyuru',
        'UYDS sürüm notları',
        'site:csb.gov.tr UYDS',
        'site:yapiisleri.csb.gov.tr UYDS',
        'site:gov.tr "Ulusal Yapı Denetim Sistemi"'
    ]
    
    print(f"Toplam {len(search_terms)} arama terimi yüklendi")
    
    # Arama ve indirme işlemini başlat
    scraper.process_search_results(search_terms)
    
    # Sonuçları CSV olarak kaydet
    if scraper.results:
        df = pd.DataFrame(scraper.results)
        df.to_csv("google_collab_egitim/data/output_v4/kaynak_envanteri.csv", index=False, encoding='utf-8-sig')
        print(f"\nToplam {len(scraper.results)} belge indirildi ve envanter kaydedildi.")
    else:
        print("\nHiçbir belge indirilemedi.")

if __name__ == "__main__":
    main()