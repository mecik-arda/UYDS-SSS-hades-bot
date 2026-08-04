# ============================================================
# v4.1 src paketi — UYDS SSS Cevap Doğrulama Sistemi
# ============================================================
"""
HadesBot UYDS SSS Cevap Doğrulama Pipeline v4.1.0

Modüller:
  - config        : YAML tabanlı konfigürasyon yönetimi
  - document_loader : Çok formatlı belge okuyucu (PDF, DOCX, TXT, MD, XLSX, CSV, JSON, JSONL)
  - chunking      : Tokenizer tabanlı belge bölümleme
  - source_inventory : Kaynak envanteri ve SHA-256 hash yönetimi
  - utils         : Genel yardımcı fonksiyonlar
  - embeddings    : Sentence-transformer embedding'leri
  - retrieval     : Dense/Bibrit RAG kaynak getirici
  - prompt_builder: Token kontrollü prompt oluşturucu
  - validator     : LLM çıktı doğrulama
  - checkpoint    : JSONL tabanlı sonuç kalıcılığı
  - reporting     : Çıktı ve rapor üretimi
"""

__version__ = "4.1.0"