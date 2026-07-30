@echo off
chcp 65001 >nul
title UYDS HadesBot Windows Yoneticisi
color 0A

echo ===================================================
echo    UYDS HadesBot - Windows Baslatma Yoneticisi
echo ===================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python sistemde bulunamadi. Lutfen Python 3.11 yukleyin ve PATH sistem degiskenine ekleyin.
    pause
    exit /b
)

if not exist ".venv\Scripts\python.exe" (
    echo [BILGI] Sanal ortam bulunamadi. Otomatik olarak olusturuluyor...
    python -m venv .venv
    echo [BILGI] Bagimliliklar yukleniyor, bu islem biraz surebilir...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.13.0+cpu
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
)

if not exist ".env" (
    echo [BILGI] .env dosyasi bulunamadi. Ornek dosyadan kopyalaniyor...
    copy .env.example .env
    echo [UYARI] Lutfen acilan dosyada VERITABANI_SIFRELEME_ANAHTARI, JWT_GIZLI_ANAHTARI ve VARSAYILAN_YONETICI_SIFRESI ayarlarini degistirip kaydedin!
    notepad .env
    pause
)

if not exist "veriler" mkdir veriler
if not exist "veriler\es_anlamlilar.json" (
    echo [BILGI] es_anlamlilar.json bulunamadi. Ornek dosyadan kopyalaniyor...
    copy es_anlamlilar.example.json veriler\es_anlamlilar.json
)

:MENU
echo.
echo ---------------------------------------------------
echo Lutfen gerceklestirmek istediginiz islemi secin:
echo ---------------------------------------------------
echo 1) Uygulamayi Yerel Olarak Baslat (Uvicorn / Gelistirme Modu)
echo 2) Excel Dosyasindan SSS Verilerini Ice Aktar
echo 3) Yerel Vektor ve Yeniden Siralama (Cross-Encoder) Modellerini Indir
echo 4) SSS Vektorlerini (Embedding) Olustur
echo 5) Docker Compose ile Konteynerlari Baslat (Arka Planda)
echo 6) Docker Compose Konteynerlarini Durdur
echo 0) Cikis
echo.

set /p secim="Seciminiz: "

if "%secim%"=="1" goto BASLAT
if "%secim%"=="2" goto EXCEL
if "%secim%"=="3" goto MODEL
if "%secim%"=="4" goto VEKTOR
if "%secim%"=="5" goto DOCKER_UP
if "%secim%"=="6" goto DOCKER_DOWN
if "%secim%"=="0" goto CIKIS

echo Gecersiz bir secim yaptiniz.
goto MENU

:BASLAT
echo [BILGI] FastAPI sunucusu baslatiliyor (http://127.0.0.1:8000)...
.venv\Scripts\uvicorn.exe uygulama.ana:uygulama --host 127.0.0.1 --port 8000
goto MENU

:EXCEL
echo [BILGI] Excel veri aktarimi basliyor...
.venv\Scripts\python.exe excel_ice_aktar.py
pause
goto MENU

:MODEL
echo [BILGI] Yerel ana vektor modeli (MiniLM) hazirlaniyor...
.venv\Scripts\python.exe vektor_modelini_hazirla.py
echo [BILGI] Yerel yeniden siralama modeli (Cross-Encoder) hazirlaniyor...
.venv\Scripts\python.exe yeniden_siralama_modelini_hazirla.py
pause
goto MENU

:VEKTOR
echo [BILGI] SSS vektorleri olusturuluyor (Embedding)...
.venv\Scripts\python.exe vektorleri_olustur.py
pause
goto MENU

:DOCKER_UP
echo [BILGI] Docker Compose servisleri derleniyor ve baslatiliyor...
docker compose up -d --build
echo [BILGI] Konteynerlar arka planda baslatildi. Durumlarini 'docker compose ps' ile gorebilirsiniz.
pause
goto MENU

:DOCKER_DOWN
echo [BILGI] Docker Compose servisleri durduruluyor...
docker compose down
pause
goto MENU

:CIKIS
echo [BILGI] Cikis yapiliyor...
exit /b
