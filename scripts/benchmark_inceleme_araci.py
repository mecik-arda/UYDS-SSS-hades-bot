import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uygulama.cekirdek.veritabani import baglam_yoneticisi
from uygulama.servisler.arama_servisi import AramaServisi
from uygulama.servisler.terim_haritasi import TerimHaritasi
from uygulama.servisler.vektor_servisi import VektorServisi

KOK = Path(__file__).resolve().parent.parent
BENCHMARK_YOLU = KOK / "testler" / "benchmark" / "insan_dogrulamali_benchmark.json"
SONUC_YOLU = KOK / "testler" / "benchmark" / "insan_dogrulama_sonuclari.json"
GOLD_YOLU = KOK / "testler" / "benchmark" / "gold_benchmark_v1.json"
PORT = 8765

KARAR_SECENEKLERI = {
    "tek_dogru": "Tek dogru",
    "birden_fazla_dogru": "Birden fazla dogru",
    "eslesme_yok": "Eslesme yok",
    "belirsiz": "Belirsiz",
    "kismen_dogru": "Kismen dogru",
    "incelemeyi_atla": "Incelemeyi atla",
}

HTML_SAYFA = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Benchmark Inceleme Araci</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#f1f5f9;color:#1e293b;display:flex;min-height:100vh}
.sidebar{width:260px;background:#1e293b;color:white;padding:16px;overflow-y:auto;flex-shrink:0}
.sidebar h2{font-size:1rem;margin-bottom:12px;border-bottom:1px solid #334155;padding-bottom:8px}
.sidebar .stat{font-size:0.82rem;margin:4px 0;display:flex;justify-content:space-between}
.sidebar .stat span{color:#94a3b8}
.filter{margin:12px 0}
.filter select,.filter input{width:100%;padding:6px 8px;margin:4px 0;border:1px solid #475569;background:#334155;color:white;border-radius:4px;font-size:0.8rem}
.main{flex:1;padding:24px;overflow-y:auto}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.topbar h1{font-size:1.2rem}
.topbar .nav{display:flex;gap:8px}
.topbar button{padding:6px 14px;border:1px solid #cbd5e1;background:white;border-radius:6px;cursor:pointer;font-size:0.85rem}
.topbar button:hover{background:#e2e8f0}
.query-box{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-bottom:16px}
.query-box .qid{font-size:0.8rem;color:#64748b;margin-bottom:4px}
.query-box .qtext{font-size:1.05rem;font-weight:500;line-height:1.5}
.candidates{margin-bottom:16px}
.candidate{background:white;border:1px solid #e2e8f0;border-radius:8px;padding:12px 16px;margin:8px 0;cursor:pointer;transition:all .15s}
.candidate:hover{border-color:#3b82f6}
.candidate.selected{border-color:#3b82f6;background:#eff6ff;box-shadow:0 0 0 2px #bfdbfe}
.candidate .c-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.candidate .c-id{font-weight:700;color:#3b82f6;font-size:0.95rem}
.candidate .c-scores{font-size:0.78rem;color:#64748b;display:flex;gap:12px}
.candidate .c-meta{font-size:0.8rem;color:#64748b;margin-bottom:4px}
.candidate .c-body{font-size:0.85rem;line-height:1.5;max-height:80px;overflow:hidden}
.candidate .c-body.expanded{max-height:none}
.candidate .c-expand{font-size:0.78rem;color:#3b82f6;cursor:pointer;margin-top:4px}
.decision{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:16px}
.decision h3{font-size:0.95rem;margin-bottom:10px}
.decision .opts{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.decision .opt{padding:6px 14px;border:1px solid #cbd5e1;border-radius:20px;cursor:pointer;font-size:0.82rem;background:white}
.decision .opt:hover{background:#e2e8f0}
.decision .opt.active{background:#3b82f6;color:white;border-color:#3b82f6}
.decision textarea{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:0.85rem;resize:vertical;min-height:50px}
.decision .manual-id{margin:8px 0;display:flex;gap:8px}
.decision .manual-id input{padding:6px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:0.85rem;flex:1}
.shortcuts{font-size:0.75rem;color:#64748b;margin-top:8px}
.shortcuts kbd{background:#e2e8f0;padding:1px 5px;border-radius:3px;font-size:0.7rem}
.sort-btn{padding:4px 10px;font-size:0.78rem;border:1px solid #cbd5e1;background:white;border-radius:4px;cursor:pointer}
.sort-btn.active{background:#3b82f6;color:white}
</style>
</head>
<body>
<div class="sidebar">
<h2>Ilerleme</h2>
<div class="stat"><span>Toplam</span> <b id="stat-toplam">0</b></div>
<div class="stat"><span>Dogrilanan</span> <b id="stat-dogrulanan">0</b></div>
<div class="stat"><span>Kalan</span> <b id="stat-kalan">0</b></div>
<div class="stat"><span>Tek dogru</span> <b id="stat-tek">0</b></div>
<div class="stat"><span>Birden fazla</span> <b id="stat-cok">0</b></div>
<div class="stat"><span>Eslesme yok</span> <b id="stat-yok">0</b></div>
<div class="stat"><span>Belirsiz</span> <b id="stat-belirsiz">0</b></div>
<div class="stat"><span>Kismen dogru</span> <b id="stat-kismen">0</b></div>
<div class="stat"><span>Atlanan</span> <b id="stat-atla">0</b></div>
<hr style="border-color:#334155;margin:10px 0">
<div class="filter">
<label style="font-size:0.8rem">Filtre</label>
<select id="filtre-karar" onchange="filtrele()">
<option value="">Tumu</option>
<option value="">--- Dogrulanmamis ---</option>
<option value="dogrulanmamis">Sadece dogrulanmamis</option>
<option value="">--- Karar turu ---</option>
<option value="tek_dogru">Tek dogru</option>
<option value="birden_fazla_dogru">Birden fazla dogru</option>
<option value="eslesme_yok">Eslesme yok</option>
<option value="belirsiz">Belirsiz</option>
<option value="kismen_dogru">Kismen dogru</option>
<option value="incelemeyi_atla">Incelemeyi atla</option>
</select>
</div>
<div class="filter">
<label style="font-size:0.8rem">SSS ID ara</label>
<input type="number" id="filtre-sssid" placeholder="ID..." onkeydown="if(event.key==='Enter')sssidAra()">
</div>
<button onclick="kaydet()" style="width:100%;padding:8px;margin:8px 0;background:#22c55e;color:white;border:none;border-radius:6px;cursor:pointer;font-weight:600">Kaydet (Ctrl+S)</button>
</div>
<div class="main">
<div class="topbar">
<h1 id="query-title">Sorgu yukleniyor...</h1>
<div class="nav">
<button onclick="onceki()">&larr; Onceki</button>
<button onclick="sonraki()">Sonraki &rarr;</button>
<span style="font-size:0.85rem;color:#64748b" id="index-info"></span>
</div>
</div>
<div class="query-box">
<div class="qid" id="qid"></div>
<div class="qtext" id="qtext"></div>
</div>
<div class="candidates" id="candidates"></div>
<div class="decision">
<h3>Karar</h3>
<div class="opts" id="karar-opts"></div>
<div class="manual-id">
<input type="text" id="manual-sssid" placeholder="Manuel SSS ID (virgulle ayir)">
<button onclick="manuelEkle()">Ekle</button>
</div>
<textarea id="inceleme-notu" placeholder="Inceleme notu..."></textarea>
<div class="shortcuts">
Klavye: <kbd>1-5</kbd> aday sec | <kbd>N</kbd> eslesme yok | <kbd>B</kbd> belirsiz | <kbd>K</kbd> kismen dogru | <kbd>&larr;&rarr;</kbd> gezin | <kbd>Ctrl+S</kbd> kaydet
</div>
</div>
</div>
<script>
let tumSorgular=[],sonuclar={},aktifIndex=0,seciliAdaylar=[],aktifKarar=null;

async function yukle(){
  let r=await fetch('/api/sorgular');
  tumSorgular=await r.json();
  let r2=await fetch('/api/sonuclar');
  sonuclar=await r2.json();
  guncelleIstatistik();
  filtrele();
}

function guncelleIstatistik(){
  let gorunen=filtreliSorgular();
  let dogrulanan=gorunen.filter(i=>sonuclar[i.id]&&sonuclar[i.id].karar&&sonuclar[i.id].karar!=='incelemeyi_atla').length;
  document.getElementById('stat-toplam').textContent=gorunen.length;
  document.getElementById('stat-kalan').textContent=gorunen.length-dogrulanan;
  document.getElementById('stat-dogrulanan').textContent=dogrulanan;
  document.getElementById('stat-tek').textContent=gorunen.filter(i=>sonuclar[i.id]?.karar==='tek_dogru').length;
  document.getElementById('stat-cok').textContent=gorunen.filter(i=>sonuclar[i.id]?.karar==='birden_fazla_dogru').length;
  document.getElementById('stat-yok').textContent=gorunen.filter(i=>sonuclar[i.id]?.karar==='eslesme_yok').length;
  document.getElementById('stat-belirsiz').textContent=gorunen.filter(i=>sonuclar[i.id]?.karar==='belirsiz').length;
  document.getElementById('stat-kismen').textContent=gorunen.filter(i=>sonuclar[i.id]?.karar==='kismen_dogru').length;
  document.getElementById('stat-atla').textContent=gorunen.filter(i=>sonuclar[i.id]?.karar==='incelemeyi_atla').length;
}

function filtreliSorgular(){
  let f=document.getElementById('filtre-karar').value;
  if(!f)return tumSorgular;
  if(f==='dogrulanmamis')return tumSorgular.filter(i=>!sonuclar[i.id]||!sonuclar[i.id].karar);
  return tumSorgular.filter(i=>sonuclar[i.id]&&sonuclar[i.id].karar===f);
}

function filtrele(){
  aktifIndex=0;goster();guncelleIstatistik();
}

function sssidAra(){
  let sid=parseInt(document.getElementById('filtre-sssid').value);
  if(!sid)return;
  let idx=tumSorgular.findIndex(i=>i.aday_sss_idler&&i.aday_sss_idler.includes(sid));
  if(idx>=0){aktifIndex=idx;goster();}
}

async function goster(){
  let gorunen=filtreliSorgular();
  if(gorunen.length===0){document.getElementById('query-title').textContent='Sorgu yok';return}
  if(aktifIndex<0)aktifIndex=0;
  if(aktifIndex>=gorunen.length)aktifIndex=gorunen.length-1;
  let s=gorunen[aktifIndex];
  document.getElementById('query-title').textContent='Benchmark Inceleme Araci';
  document.getElementById('qid').textContent=`${s.id} | Kayit ${aktifIndex+1}/${gorunen.length}`;
  document.getElementById('qtext').textContent=s.soru;
  document.getElementById('index-info').textContent=`${aktifIndex+1}/${gorunen.length}`;

  let mevcut=sonuclar[s.id]||{};
  seciliAdaylar=[...((mevcut.insan_onayli_sss_idler||[]).filter(id=>mevcut.karar!=='eslesme_yok'&&mevcut.karar!=='belirsiz'&&mevcut.karar!=='incelemeyi_atla'))];
  aktifKarar=mevcut.karar||null;
  document.getElementById('inceleme-notu').value=mevcut.inceleme_notu||'';

  kararDugmeleriniGuncelle();
  adaylariYukle(s);
}

async function adaylariYukle(s){
  let r=await fetch('/api/adaylar?soru='+encodeURIComponent(s.soru));
  let adaylar=await r.json();
  let html='';
  adaylar.forEach((a,i)=>{
    let secili=seciliAdaylar.includes(a.sss_id);
    html+=`<div class="candidate${secili?' selected':''}" onclick="adaySec(${a.sss_id},${i})" id="aday-${i}">
<div class="c-header"><span class="c-id">[${i+1}] SSS #${a.sss_id}</span>
<span class="c-scores"><span>RRF: ${a.rrf_skoru?.toFixed(4)||'-'}</span><span>Reranker: ${(a.yeniden_siralama_skoru||0).toFixed(4)}</span><span>Guven: ${(a.vektor_benzerlik_skoru||0).toFixed(4)}</span></span></div>
<div class="c-meta">Modul: ${a.kaynak_dokuman||'-'} | Sayfa: ${a.kaynak_sayfa||'-'} | Satir: ${a.kaynak_satir||'-'}</div>
<div class="c-body" id="cbody-${i}">${metniTemizle(a.aday_metni).substring(0,300)}</div>
${(a.aday_metni||'').length>300?`<div class="c-expand" onclick="event.stopPropagation();genislet(${i})">Devamini goster...</div>`:''}
</div>`;
  });
  document.getElementById('candidates').innerHTML=html;

  let genisletilmis={};
  window._genislet=genisletilmis;
  window._adayMetinleri={};
  adaylar.forEach((a,i)=>{window._adayMetinleri[i]=a.aday_metni||''});
}

function metniTemizle(t){return(t||'').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function genislet(i){
  let el=document.getElementById('cbody-'+i);
  if(el.classList.contains('expanded')){el.classList.remove('expanded');el.textContent=metniTemizle(window._adayMetinleri[i]).substring(0,300)}
  else{el.classList.add('expanded');el.textContent=metniTemizle(window._adayMetinleri[i])}
}

function adaySec(sssId,index){
  let idx=seciliAdaylar.indexOf(sssId);
  if(idx>=0){seciliAdaylar.splice(idx,1);document.getElementById('aday-'+index)?.classList.remove('selected')}
  else{seciliAdaylar.push(sssId);document.getElementById('aday-'+index)?.classList.add('selected')}
  aktifKarar=seciliAdaylar.length===1?'tek_dogru':seciliAdaylar.length>=2?'birden_fazla_dogru':null;
  kararDugmeleriniGuncelle();
}

function kararSec(karar){
  aktifKarar=karar;
  if(karar==='eslesme_yok'||karar==='belirsiz'||karar==='incelemeyi_atla'){seciliAdaylar=[]}
  kararDugmeleriniGuncelle();
  adaySecimiGuncelle();
}

function kararDugmeleriniGuncelle(){
  let kararlar=['tek_dogru','birden_fazla_dogru','kismen_dogru','eslesme_yok','belirsiz','incelemeyi_atla'];
  let etiketler={tek_dogru:'1-5: Tek Dogru',birden_fazla_dogru:'Birden Fazla',kismen_dogru:'K: Kismen',eslesme_yok:'N: Eslesme Yok',belirsiz:'B: Belirsiz',incelemeyi_atla:'Atla'};
  let html='';
  kararlar.forEach(k=>{html+=`<div class="opt${aktifKarar===k?' active':''}" onclick="kararSec('${k}')">${etiketler[k]}</div>`});
  document.getElementById('karar-opts').innerHTML=html;
}

function adaySecimiGuncelle(){
  document.querySelectorAll('.candidate').forEach(el=>el.classList.remove('selected'));
  seciliAdaylar.forEach(id=>{
    document.querySelectorAll('.candidate').forEach(el=>{if(el.querySelector('.c-id')?.textContent.includes('#'+id))el.classList.add('selected')});
  });
}

function manuelEkle(){
  let val=document.getElementById('manual-sssid').value;
  let ids=val.split(',').map(s=>parseInt(s.trim())).filter(n=>!isNaN(n)&&n>0);
  ids.forEach(id=>{if(!seciliAdaylar.includes(id))seciliAdaylar.push(id)});
  document.getElementById('manual-sssid').value='';
  adaySecimiGuncelle();
}

async function kaydet(){
  if(!aktifKarar){alert('Once bir karar secin');return}
  let gorunen=filtreliSorgular();
  if(gorunen.length===0)return;
  let s=gorunen[aktifIndex];
  let not=document.getElementById('inceleme-notu').value;
  await fetch('/api/kaydet',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:s.id,karar:aktifKarar,insan_onayli_sss_idler:seciliAdaylar,inceleme_notu:not})});
  let r2=await fetch('/api/sonuclar');sonuclar=await r2.json();
  guncelleIstatistik();
}

function sonraki(){aktifIndex++;goster()}
function onceki(){aktifIndex--;goster()}

document.addEventListener('keydown',function(e){
  if(e.ctrlKey&&e.key==='s'){e.preventDefault();kaydet();return}
  if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA'||e.target.tagName==='SELECT')return;
  if(e.key>='1'&&e.key<='5'){let i=parseInt(e.key)-1;let el=document.getElementById('aday-'+i);if(el){let s=el.querySelector('.c-id')?.textContent;let m=s?.match(/#(\d+)/);if(m)adaySec(parseInt(m[1]),i)}}
  else if(e.key==='n'||e.key==='N')kararSec('eslesme_yok');
  else if(e.key==='b'||e.key==='B')kararSec('belirsiz');
  else if(e.key==='k'||e.key==='K')kararSec('kismen_dogru');
  else if(e.key==='ArrowRight')sonraki();
  else if(e.key==='ArrowLeft')onceki();
});

yukle();
</script>
</body>
</html>"""


def _servis_olustur():
    vektor = VektorServisi()
    terim = TerimHaritasi()
    return AramaServisi(vektor, terim, None)


def _benchmark_yukle() -> list[dict]:
    if not BENCHMARK_YOLU.is_file():
        return []
    with BENCHMARK_YOLU.open(encoding="utf-8") as f:
        return json.load(f)["sorgular"]


def _sonuclari_yukle() -> dict:
    if not SONUC_YOLU.is_file():
        return {}
    with SONUC_YOLU.open(encoding="utf-8") as f:
        return json.load(f)


def _sonuclari_kaydet(sonuclar: dict):
    SONUC_YOLU.parent.mkdir(parents=True, exist_ok=True)
    with SONUC_YOLU.open("w", encoding="utf-8") as f:
        json.dump(sonuclar, f, ensure_ascii=False, indent=2)


def _adaylari_getir(servis, soru: str) -> list[dict]:
    try:
        sonuc = servis.ara(soru)
        adaylar = []
        for a in sonuc.adaylar[:5]:
            adaylar.append({
                "sss_id": a.sss_id,
                "rrf_skoru": round(a.rrf_skoru, 6),
                "vektor_benzerlik_skoru": round(a.vektor_benzerlik_skoru, 6) if a.vektor_benzerlik_skoru else None,
                "yeniden_siralama_skoru": round(a.yeniden_siralama_skoru, 6) if a.yeniden_siralama_skoru else None,
                "kaynak_dokuman": a.kaynak_dokuman,
                "kaynak_sayfa": a.kaynak_sayfa,
                "kaynak_satir": a.kaynak_satir,
                "aday_metni": a.aday_metni,
            })
        return adaylar
    except Exception:
        return []


def _karar_dogrula(karar: str, idler: list[int]) -> tuple[bool, str]:
    if karar not in KARAR_SECENEKLERI:
        return False, f"Gecersiz karar: {karar}"
    if karar == "tek_dogru":
        if len(idler) != 1:
            return False, "tek_dogru icin tam 1 ID gerekli"
    elif karar == "birden_fazla_dogru":
        if len(idler) < 2:
            return False, "birden_fazla_dogru icin en az 2 ID gerekli"
    elif karar == "kismen_dogru":
        if len(idler) < 1:
            return False, "kismen_dogru icin en az 1 ID gerekli"
    elif karar in ("eslesme_yok", "belirsiz", "incelemeyi_atla"):
        if len(idler) != 0:
            return False, f"{karar} icin ID listesi bos olmali"
    return True, ""


def _validate() -> dict:
    if not SONUC_YOLU.is_file():
        return {"hata": "Sonuc dosyasi bulunamadi", "gecerli": False}
    sorgular = _benchmark_yukle()
    if not sorgular:
        return {"hata": "Benchmark dosyasi bos", "gecerli": False}
    sonuclar = _sonuclari_yukle()
    hatalar = []
    gorulen_idler = set()
    for s in sorgular:
        sid = s["id"]
        if sid in gorulen_idler:
            hatalar.append(f"Yinelenen ID: {sid}")
        gorulen_idler.add(sid)
        if sid not in sonuclar:
            continue
        kayit = sonuclar[sid]
        if not kayit.get("karar"):
            continue
        karar = kayit["karar"]
        idler = kayit.get("insan_onayli_sss_idler", [])
        gecerli, mesaj = _karar_dogrula(karar, idler)
        if not gecerli:
            hatalar.append(f"{sid}: {mesaj}")
        if not kayit.get("inceleme_tarihi"):
            hatalar.append(f"{sid}: inceleme_tarihi eksik")
        for sss_id in idler:
            with baglam_yoneticisi() as b:
                r = b.execute("SELECT 1 FROM sss_kayitlari WHERE id=?", (sss_id,)).fetchone()
                if not r:
                    hatalar.append(f"{sid}: SSS ID {sss_id} veritabaninda yok")
    return {"gecerli": len(hatalar) == 0, "hata_sayisi": len(hatalar), "hatalar": hatalar[:50]}


def _export() -> dict:
    if not SONUC_YOLU.is_file():
        return {"hata": "Sonuc dosyasi bulunamadi"}
    sorgular = _benchmark_yukle()
    sonuclar = _sonuclari_yukle()
    gold = []
    bilinmeyen = []
    for s in sorgular:
        sid = s["id"]
        if sid not in sonuclar:
            continue
        kayit = sonuclar[sid]
        if not kayit.get("karar") or kayit["karar"] in ("belirsiz", "incelemeyi_atla"):
            continue
        if kayit["karar"] == "eslesme_yok":
            bilinmeyen.append({
                "id": sid,
                "soru": s["soru"],
                "karar": "eslesme_yok",
                "inceleme_notu": kayit.get("inceleme_notu", ""),
            })
            continue
        gecerli, _ = _karar_dogrula(kayit["karar"], kayit.get("insan_onayli_sss_idler", []))
        if not gecerli:
            continue
        gold.append({
            "id": sid,
            "soru": s["soru"],
            "beklenen_sss_id": kayit["insan_onayli_sss_idler"][0] if kayit["karar"] == "tek_dogru" else None,
            "beklenen_sss_idler": kayit["insan_onayli_sss_idler"],
            "karar": kayit["karar"],
            "inceleme_notu": kayit.get("inceleme_notu", ""),
            "inceleme_tarihi": kayit.get("inceleme_tarihi", ""),
        })
    cikti = {
        "aciklama": "Insan dogrulamali altin benchmark seti",
        "toplam": len(gold),
        "bilinmeyen_test_sorgulari": len(bilinmeyen),
        "sorgular": gold,
        "bilinmeyen_sorgulari": bilinmeyen,
    }
    GOLD_YOLU.parent.mkdir(parents=True, exist_ok=True)
    with GOLD_YOLU.open("w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)
    return {"yazildi": str(GOLD_YOLU), "altin_kayit": len(gold), "bilinmeyen": len(bilinmeyen)}


def _fastapi_app():
    from fastapi import FastAPI, Query
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel

    app = FastAPI(title="Benchmark Inceleme Araci", docs_url=None, redoc_url=None)
    servis = _servis_olustur()

    class KayitIstegi(BaseModel):
        id: str
        karar: str
        insan_onayli_sss_idler: list[int]
        inceleme_notu: str = ""

    @app.get("/", response_class=HTMLResponse)
    async def anasayfa():
        return HTMLResponse(HTML_SAYFA)

    @app.get("/api/sorgular")
    async def sorgular():
        return _benchmark_yukle()

    @app.get("/api/sonuclar")
    async def sonuclar():
        return _sonuclari_yukle()

    @app.get("/api/adaylar")
    async def adaylar(soru: str = Query(...)):
        return _adaylari_getir(servis, soru)

    @app.post("/api/kaydet")
    async def kaydet_api(istek: KayitIstegi):
        sonuclar = _sonuclari_yukle()
        sonuclar[istek.id] = {
            "benchmark_id": istek.id,
            "karar": istek.karar,
            "insan_onayli_sss_idler": istek.insan_onayli_sss_idler,
            "inceleme_notu": istek.inceleme_notu,
            "inceleme_tarihi": datetime.now(timezone.utc).isoformat(),
            "inceleyen": "manuel",
            "aday_sss_idler": [],
        }
        sorgular = _benchmark_yukle()
        for s in sorgular:
            if s["id"] == istek.id:
                sonuclar[istek.id]["aday_sss_idler"] = s.get("aday_sss_idler", [])
                break
        _sonuclari_kaydet(sonuclar)
        return {"durum": "kaydedildi"}

    return app


def main():
    import argparse
    import uvicorn

    ayrıştırıcı = argparse.ArgumentParser(description="Benchmark Inceleme Araci")
    ayrıştırıcı.add_argument("--validate", action="store_true")
    ayrıştırıcı.add_argument("--export", action="store_true")
    argumanlar = ayrıştırıcı.parse_args()

    if argumanlar.validate:
        sonuc = _validate()
        print(json.dumps(sonuc, ensure_ascii=False, indent=2))
        return

    if argumanlar.export:
        sonuc = _export()
        print(json.dumps(sonuc, ensure_ascii=False, indent=2))
        return

    print(f"Benchmark Inceleme Araci baslatiliyor: http://127.0.0.1:{PORT}")
    print(f"Benchmark: {BENCHMARK_YOLU}")
    print(f"Sonuclar:  {SONUC_YOLU}")
    uvicorn.run(_fastapi_app(), host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
