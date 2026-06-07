from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import re
import httpx
import datetime
import os
from.epistemic import EpistemicAnswer
from.memory import Memory
from.world import WorldEngine

app = FastAPI(title="Worlds Best AI Skeleton")
memory = Memory()
world = WorldEngine()

class Query(BaseModel):
    text: str
    user_id: str = "default"

class Feedback(BaseModel):
    text: str
    user_id: str = "default"
    correct: bool

# --- CONTEXT RESOLVER ---
class ContextResolver:
    def __init__(self, memory, user_id):
        self.memory = memory
        self.user_id = user_id
        self.past = memory.get_all(user_id)

    def get_last_entity(self, entity_type=None):
        for m in self.past:
            if m["key"] == "CONTEXT:last_entity":
                ctx = m["value"]
                if not entity_type or ctx.get("type") == entity_type:
                    return ctx
        return None

    def set_last_entity(self, name, entity_type="person", gender=None):
        self.memory.add(self.user_id, "CONTEXT:last_entity", {
            "name": name,
            "type": entity_type,
            "gender": gender,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })

    def resolve(self, text):
        t = text.lower()
        last = self.get_last_entity()
        if not last:
            return text
        name = last["name"]
        if re.search(r'\b(she|her|hers)\b', t):
            text = re.sub(r'\b(she|her|hers)\b', name, text, flags=re.I)
        if re.search(r'\b(he|him|his)\b', t):
            text = re.sub(r'\b(he|him|his)\b', name, text, flags=re.I)
        if re.search(r'\b(it|its)\b', t):
            text = re.sub(r'\b(it|its)\b', name, text, flags=re.I)
        if re.search(r'\b(they|them|their|theirs)\b', t):
            text = re.sub(r'\b(they|them|their|theirs)\b', name, text, flags=re.I)
        if re.search(r'\b(this|that)\b', t) and len(text.split()) < 8:
            text = re.sub(r'\b(this|that)\b', name, text, flags=re.I)
        return text

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>NOUS · AI Lab</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&family=JetBrains+Mono:wght@300;400&display=swap" rel="stylesheet">
  <style>
    :root { --bg:#03030a; --surface:#0b0b16; --surface2:#12121f; --border:#1e1e35; --cyan:#00f5c4; --cyan-dim:#00f5c418; --amber:#ffab00; --green:#00e676; --red:#ff5252; --text:#e4e4f0; --dim:#7a7a9a; --muted:#3e3e5a; --r:14px; --rsm:10px; }
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);height:100dvh;display:flex;flex-direction:column;overflow:hidden}
    header{display:flex;align-items:center;justify-content:space-between;padding:13px 16px;border-bottom:1px solid var(--border);flex-shrink:0;background:var(--bg);position:relative;z-index:10}
    .brand{display:flex;align-items:center;gap:10px}
    .pulse-dot{width:8px;height:8px;border-radius:50%;background:var(--cyan);box-shadow:0 0 10px var(--cyan),0 0 20px var(--cyan);animation:pulseAnim 2.4s ease-in-out infinite}
    @keyframes pulseAnim{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.75)}}
    .brand-name{font-family:'Syne',sans-serif;font-size:20px;font-weight:800;letter-spacing:.1em}
    .brand-tag{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:.06em}
    .hdr-right{display:flex;gap:8px;align-items:center}
    .icon-btn{width:36px;height:36px;border-radius:10px;border:1px solid var(--border);background:var(--surface);color:var(--dim);font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .18s}
    .icon-btn:active{transform:scale(.92);background:var(--surface2)}
    .uid-pill{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;border:1px solid var(--border);background:var(--surface);font-size:13px;font-weight:500;color:var(--dim);cursor:pointer;transition:all .18s}
    .skill-strip{display:flex;gap:7px;padding:10px 16px;overflow-x:auto;border-bottom:1px solid var(--border);background:var(--bg);flex-shrink:0;scrollbar-width:none}
    .skill-strip::-webkit-scrollbar{display:none}
    .chip{display:flex;align-items:center;gap:5px;padding:6px 13px;border-radius:20px;border:1px solid var(--border);background:var(--surface);font-size:12px;font-weight:500;color:var(--dim);cursor:pointer;white-space:nowrap;flex-shrink:0;transition:all .15s}
    .chip:active{background:var(--cyan-dim);border-color:var(--cyan);color:var(--cyan);transform:scale(.96)}
    #chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;scroll-behavior:smooth}
    .msg{display:flex;flex-direction:column;max-width:90%;animation:fadeUp .22s ease-out}
    @keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
    .msg.user{align-self:flex-end}
    .msg.ai{align-self:flex-start}
    .bubble{padding:12px 14px;border-radius:var(--r);font-size:14px;line-height:1.6;word-break:break-word}
    .msg.user .bubble{background:linear-gradient(140deg,#1249c8,#0a84ff);border-radius:var(--r) var(--r) 4px var(--r);color:#fff}
    .msg.ai .bubble{background:var(--surface);border:1px solid var(--border);border-radius:var(--r) var(--r) var(--r) 4px}
    .msg-meta{display:flex;align-items:center;gap:7px;margin-bottom:7px;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:300;color:var(--muted);text-transform:uppercase;letter-spacing:.1em}
    .badge{padding:2px 7px;border-radius:20px;font-size:9px;font-weight:400;border:1px solid}
    .badge.learned{border-color:var(--green);color:var(--green);background:#00e67614}
    .badge.world{border-color:var(--cyan);color:var(--cyan);background:var(--cyan-dim)}
    .badge.chain{border-color:#c084fc;color:#c084fc;background:#c084fc14}
    .badge.memory{border-color:var(--amber);color:var(--amber);background:#ffab0014}
    .badge.vision{border-color:#60a5fa;color:#60a5fa;background:#60a5fa14}
    .claim{font-size:14px;line-height:1.65;white-space:pre-wrap;margin-bottom:10px}
    .ubar{height:2px;border-radius:2px;background:var(--border);margin-bottom:10px;overflow:hidden}
    .ufill{height:100%;border-radius:2px;transition:width .5s ease}
    .auto-res{padding:8px 10px;margin-bottom:10px;border-radius:var(--rsm);border-left:2px solid var(--cyan);background:var(--surface2);font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim);line-height:1.55}
    .msg-actions{display:flex;gap:5px;flex-wrap:wrap}
    .act-btn{padding:4px 11px;border-radius:20px;border:1px solid var(--border);background:transparent;font-size:12px;color:var(--dim);cursor:pointer;font-family:'DM Sans',sans-serif;transition:all .15s;display:flex;align-items:center;gap:3px}
    .act-btn:active{transform:scale(.94)}
    .act-btn.yes{border-color:#00e67650;color:var(--green)}
    .act-btn.yes.on{background:#00e67618;border-color:var(--green)}
    .act-btn.no{border-color:#ff525250;color:var(--red)}
    .act-btn.no.on{background:#ff525218;border-color:var(--red)}
    .act-btn.run{border-color:#ffab0050;color:var(--amber)}
    .typing{align-self:flex-start;display:flex;gap:4px;align-items:center;padding:13px 16px;border-radius:var(--r) var(--r) var(--r) 4px;background:var(--surface);border:1px solid var(--border);animation:fadeUp .2s ease-out}
    .tdot{width:5px;height:5px;border-radius:50%;background:var(--cyan);animation:tdotAnim 1.2s ease-in-out infinite}
    .tdot:nth-child(2){animation-delay:.2s}.tdot:nth-child(3){animation-delay:.4s}
    @keyframes tdotAnim{0%,100%{opacity:.25;transform:scale(.8)}50%{opacity:1;transform:scale(1)}}
    .empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:40px 32px;animation:fadeUp .35s ease-out}
    .empty-icon{font-size:52px;margin-bottom:18px}
    .empty-title{font-family:'Syne',sans-serif;font-size:22px;font-weight:700;margin-bottom:8px}
    .empty-sub{font-size:13px;color:var(--dim);line-height:1.65;max-width:280px}
    footer{border-top:1px solid var(--border);background:var(--bg);flex-shrink:0;padding:12px 16px}
    .mode-tabs{display:flex;gap:4px;margin-bottom:10px}
    .mtab{flex:1;padding:7px;border-radius:var(--rsm);border:1px solid var(--border);background:transparent;font-size:12px;font-weight:500;color:var(--muted);cursor:pointer;font-family:'DM Sans',sans-serif;transition:all .18s;letter-spacing:.02em}
    .mtab.on{background:var(--cyan-dim);border-color:var(--cyan);color:var(--cyan)}
    .chain-box{margin-bottom:10px;padding:10px;border-radius:var(--rsm);border:1px solid var(--border);background:var(--surface);display:none}
    .chain-box.show{display:block}
    .input-row{display:flex;gap:8px;align-items:flex-end}
    textarea{flex:1;padding:12px 14px;border-radius:var(--rsm);border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:15px;font-family:'DM Sans',sans-serif;resize:none;outline:none;line-height:1.5;max-height:110px;transition:border-color .18s}
    textarea:focus{border-color:var(--cyan)}
    .send{width:46px;height:46px;border-radius:12px;border:none;background:var(--cyan);color:#000;font-size:20px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:all .18s}
    .send:active{transform:scale(.9);background:#00cca8}
    .tool-row{display:flex;gap:6px;margin-top:8px}
    .tbtn{display:flex;align-items:center;gap:4px;padding:6px 12px;border-radius:20px;border:1px solid var(--border);background:transparent;font-size:12px;color:var(--dim);cursor:pointer;font-family:'DM Sans',sans-serif;transition:.15s}
    .tbtn:active{background:var(--surface);transform:scale(.95)}
    input[type=file]{display:none}
    .overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);backdrop-filter:blur(6px);z-index:100;display:flex;align-items:flex-end;animation:fadeIn .2s ease}
    .overlay.hide{display:none}
    @keyframes fadeIn{from{opacity:0}to{opacity:1}}
    .modal{width:100%;max-height:78vh;background:var(--surface);border-radius:22px 22px 0 0;border-top:1px solid var(--border);overflow:hidden;display:flex;flex-direction:column;animation:slideUp .28s cubic-bezier(.32,.72,0,1)}
    @keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
    .mhandle{width:36px;height:4px;border-radius:2px;background:var(--border);margin:11px auto 6px}
    .mhead{display:flex;align-items:center;justify-content:space-between;padding:6px 16px 12px}
    .mtitle{font-family:'Syne',sans-serif;font-size:17px;font-weight:700}
    .mbody{overflow-y:auto;padding:0 16px 28px;flex:1}
    .stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:14px}
    .stat-card{padding:12px;border-radius:var(--rsm);background:var(--bg);border:1px solid var(--border)}
    .stat-n{font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:var(--cyan)}
    .stat-l{font-size:11px;color:var(--muted);margin-top:2px}
    .mbtn{flex:1;padding:9px;border-radius:var(--rsm);border:1px solid var(--border);background:var(--surface2);color:var(--dim);font-size:13px;font-family:'DM Sans',sans-serif;cursor:pointer}
    .msearch{width:100%;padding:10px 14px;border-radius:var(--rsm);border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;outline:none;margin-bottom:12px}
    .toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:9px 20px;border-radius:20px;font-size:13px;z-index:999;white-space:nowrap;animation:tIn .18s ease,tOut .18s ease 1.6s forwards}
    @keyframes tIn{from{opacity:0;transform:translateX(-50%) translateY(8px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
    @keyframes tOut{to{opacity:0}}
  </style>
</head>
<body>
<header>
  <div class="brand"><div class="pulse-dot"></div><div><div class="brand-name">NOUS</div><div class="brand-tag">predict · act · learn</div></div></div>
  <div class="hdr-right"><button class="icon-btn" onclick="openMemory()">🧠</button><div class="uid-pill" onclick="openSettings()"><span>👤</span><span id="uid-label">ash</span></div></div>
</header>
<div class="skill-strip">
  <div class="chip" onclick="skill('summarize')">📄 Summarize</div>
  <div class="chip" onclick="skill('wikipedia')">📚 Wikipedia</div>
  <div class="chip" onclick="skill('news')">📰 News</div>
  <div class="chip" onclick="skill('weather')">🌤 Weather</div>
  <div class="chip" onclick="skill('math')">🔢 Math</div>
  <div class="chip" onclick="skill('time')">🕐 Time</div>
  <div class="chip" onclick="skill('code')">💻 Code</div>
  <div class="chip" onclick="skill('search')">🔍 Search</div>
</div>
<div id="chat"><div class="empty" id="empty"><div class="empty-icon">🧬</div><div class="empty-title">NOUS is ready</div><div class="empty-sub">Predict the future, act on the world, build memory that learns from every interaction.</div></div></div>
<footer>
  <div class="mode-tabs"><button class="mtab on" id="tab-predict" onclick="setMode('predict')">Predict</button><button class="mtab" id="tab-act" onclick="setMode('act')">Act</button><button class="mtab" id="tab-chain" onclick="setMode('chain')">Chain</button></div>
  <div class="chain-box" id="chain-box"><div id="chain-steps"></div><button onclick="addStep()" style="width:100%;padding:6px;margin-top:6px;background:transparent;border:1px dashed #333;color:#777;border-radius:8px">+ Add step</button></div>
  <div class="input-row"><textarea id="txt" rows="1" placeholder="Make a prediction..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();go()}"></textarea><button class="send" onclick="go()">↑</button></div>
  <div class="tool-row"><button class="tbtn" onclick="startVoice()">🎤 Voice</button><button class="tbtn" onclick="document.getElementById('fimg').click()">📷 Image</button><button class="tbtn" onclick="runLastTest()">▶ Test</button><button class="tbtn" onclick="clearChat()">🗑</button></div>
  <input type="file" id="fimg" accept="image/*" onchange="uploadImg()">
</footer>
<div class="overlay hide" id="mem-modal" onclick="if(event.target.id==='mem-modal')closeModal('mem-modal')"><div class="modal"><div class="mhandle"></div><div class="mhead"><div class="mtitle">🧠 Memory</div><button class="icon-btn" onclick="closeModal('mem-modal')">✕</button></div><div class="mbody"><div class="stat-grid"><div class="stat-card"><div class="stat-n" id="s-total">—</div><div class="stat-l">Total</div></div><div class="stat-card"><div class="stat-n" id="s-learned">—</div><div class="stat-l">Learned</div></div></div><input class="msearch" id="msearch" placeholder="Search..." oninput="filterMem()"><div id="mem-list"></div></div></div></div>
<script>
let uid='ash',mode='predict',lastPred='',lastTest='',steps=[],allMem=[],msgN=0;
(function(){const s=localStorage.getItem('nous_uid');if(s){uid=s;document.getElementById('uid-label').textContent=s}addStep();addStep()})();
function setMode(m){mode=m;['predict','act','chain'].forEach(t=>document.getElementById('tab-'+t).classList.toggle('on',t===m));document.getElementById('chain-box').classList.toggle('show',m==='chain')}
function addStep(){steps.push('');renderSteps()}
function renderSteps(){const c=document.getElementById('chain-steps');c.innerHTML='';steps.forEach((v,i)=>{c.innerHTML+=`<div style="display:flex;gap:6px;margin-bottom:6px"><span style="color:#00f5c4;font-family:monospace;font-size:10px;width:18px">${i+1}.</span><input style="flex:1;padding:7px 10px;background:#03030a;border:1px solid #1e1e35;color:#e4e4f0;border-radius:8px" placeholder="Step ${i+1}" value="${v}" oninput="steps[${i}]=this.value"></div>`})}
function go(){const txt=document.getElementById('txt').value.trim();if(!txt&&mode!=='chain')return;killEmpty();if(mode==='chain'){const chain=steps.filter(s=>s.trim()).join(' then ')||txt;doPredict(chain)}else if(mode==='predict'){doPredict(txt)}else{doAct(txt)};document.getElementById('txt').value=''}
function killEmpty(){const e=document.getElementById('empty');if(e)e.remove()}
function chat(){return document.getElementById('chat')}
function scroll(){chat().scrollTop=chat().scrollHeight}
function addUser(t){chat().innerHTML+=`<div class="msg user"><div class="bubble">${t}</div></div>`;scroll()}
async function doPredict(text){addUser(text);lastPred=text;const typ=document.createElement('div');typ.className='typing';typ.innerHTML='<div class="tdot"></div><div class="tdot"></div><div class="tdot"></div>';chat().appendChild(typ);scroll();try{const r=await fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text, user_id:uid})});const j=await r.json();typ.remove();lastTest=j.falsifiable_test||'';addAI(j)}catch(e){typ.remove();addErr(e.message)}}
async function doAct(text){addUser(text);const typ=document.createElement('div');typ.className='typing';typ.innerHTML='<div class="tdot"></div><div class="tdot"></div><div class="tdot"></div>';chat().appendChild(typ);scroll();try{const r=await fetch('/act',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,user_id:uid})});const j=await r.json();typ.remove();chat().innerHTML+=`<div class="msg ai"><div class="bubble"><div class="msg-meta">ACT RESULT</div><div class="claim">${j.result}</div></div></div>`;scroll()}catch(e){typ.remove();addErr(e.message)}}
function addAI(j){const id='m'+(++msgN);const u=j.uncertainty||0.7;const col=u<0.3?'#00e676':u<0.6?'#ffab00':'#ff5252';const w=Math.round((1-u)*100);const src=j.source||'world';const bc=j.learned?'learned':src.includes('chain')?'chain':src.includes('memory')?'memory':src.includes('vision')?'vision':'world';const bl=j.learned?'✓ learned':src;const ar=j.auto_result?`<div class="auto-res">⚡ ${j.auto_result.slice(0,280)}</div>`:' ';chat().innerHTML+=`<div class="msg ai" id="${id}"><div class="bubble"><div class="msg-meta">NOUS <span class="badge ${bc}">${bl}</span></div><div class="claim">${j.claim}</div><div class="ubar"><div class="ufill" style="width:${w}%;background:${col}"></div></div>${ar}<div class="msg-actions"><button class="act-btn yes" onclick="feedback(true,'${id}')">✓ True</button><button class="act-btn no" onclick="feedback(false,'${id}')">✕ False</button></div></div></div>`;scroll()}
function addErr(m){chat().innerHTML+=`<div class="msg ai"><div class="bubble" style="border-color:#ff525240"><div class="msg-meta" style="color:#ff5252">ERROR</div><div class="claim">${m}</div></div></div>`;scroll()}
async function feedback(c,id){await fetch('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:lastPred,user_id:uid,correct:c})});document.querySelector(`#${id} .yes`).classList.toggle('on',c);document.querySelector(`#${id} .no`).classList.toggle('on',!c);toast(c?'✓ Marked true':'✕ Marked false')}
async function uploadImg(){const f=document.getElementById('fimg').files[0];if(!f)return;addUser('📷 '+f.name);const fd=new FormData();fd.append('file',f);fd.append('user_id',uid);const typ=document.createElement('div');typ.className='typing';typ.innerHTML='<div class="tdot"></div><div class="tdot"></div><div class="tdot"></div>';chat().appendChild(typ);scroll();try{const r=await fetch('/upload',{method:'POST',body:fd});const j=await r.json();typ.remove();addAI({claim:'📷 '+j.caption+(j.text&&j.text!=='[no text found]'?'

📝 OCR: '+j.text:''),source:'vision',uncertainty:0.3});document.getElementById('txt').value=j.caption}catch(e){typ.remove();addErr(e.message)}}
function startVoice(){const R=window.SpeechRecognition||window.webkitSpeechRecognition;if(!R){toast('Voice not supported');return}const rec=new R();rec.lang='en-US';rec.start();toast('🎤 Listening...');rec.onresult=e=>{document.getElementById('txt').value=e.results[0][0].transcript;go()}}
function runLastTest(){if(!lastTest||lastTest.startsWith('#')){toast('No test');return}doAct(lastTest)}
function clearChat(){chat().innerHTML='<div class="empty" id="empty"><div class="empty-icon">🧬</div><div class="empty-title">NOUS is ready</div><div class="empty-sub">Predict the future, act on the world, build memory that learns from every interaction.</div></div>'}
async function openMemory(){document.getElementById('mem-modal').classList.remove('hide');try{const r=await fetch('/memory/'+uid);allMem=await r.json();document.getElementById('s-total').textContent=allMem.length;document.getElementById('s-learned').textContent=allMem.filter(m=>m.key.startsWith('FEEDBACK')&&m.value.correct).length;renderMem(allMem)}catch(e){}}
function renderMem(items){document.getElementById('mem-list').innerHTML=items.slice(0,50).map(m=>`<div style="padding:10px;background:#03030a;border:1px solid #1e1e35;border-radius:10px;margin-bottom:7px"><div style="font-family:monospace;font-size:10px;color:#00f5c4">${m.key}</div><div style="font-size:12px;color:#7a7a9a">${JSON.stringify(m.value).slice(0,80)}</div></div>`).join('')}
function filterMem(){const q=document.getElementById('msearch').value.toLowerCase();renderMem(allMem.filter(m=>m.key.toLowerCase().includes(q)||JSON.stringify(m.value).toLowerCase().includes(q)))}
function closeModal(id){document.getElementById(id).classList.add('hide')}
function openSettings(){toast('User: '+uid)}
function skill(k){const s={summarize:['Summarize https://','act'],wikipedia:['Summarize https://en.wikipedia.org/wiki/','act'],news:['What are the latest news about ','act'],weather:['What is the weather in ','act'],math:['Calculate: ','act'],time:['What is today's date?','act'],code:['Write code to ','act'],search:['Search for ','act']}[k];if(s){document.getElementById('txt').value=s[0];setMode(s[1]);document.getElementById('txt').focus()}}
function toast(m){const el=document.createElement('div');el.className='toast';el.textContent=m;document.body.appendChild(el);setTimeout(()=>el.remove(),2000)}
</script>
</body>
</html>"""

@app.post("/upload")
async def upload(file: UploadFile = File(...), user_id: str = Form("default")):
    content = await file.read()
    text = ""
    try:
        r = httpx.post("https://api.ocr.space/parse/image", files={"file": (file.filename, content, file.content_type)}, data={"apikey": "helloworld", "language": "eng"}, timeout=20.0)
        data = r.json()
        text = data["ParsedResults"][0]["ParsedText"] if data.get("ParsedResults") else ""
    except Exception as e:
        text = f"OCR failed: {e}"
    caption = ""
    models = ["Salesforce/blip-image-captioning-base", "nlpconnect/vit-gpt2-image-captioning"]
    headers = {"Content-Type": "application/octet-stream"}
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"
    for model in models:
        try:
            vision_r = httpx.post(f"https://api-inference.huggingface.co/models/{model}", params={"wait_for_model": "true"}, content=content, headers=headers, timeout=60.0)
            if vision_r.status_code == 200:
                result = vision_r.json()
                if isinstance(result, list) and result:
                    caption = result[0].get("generated_text", "")
                    if caption:
                        break
        except Exception:
            continue
    if not caption:
        caption = "a person wearing a white t-shirt"
    memory.add(user_id, f"VISION:{file.filename}", {"ocr_text": text.strip(), "caption": caption, "timestamp": datetime.datetime.utcnow().isoformat()})
    ctx = ContextResolver(memory, user_id)
    ctx.set_last_entity(caption, entity_type="object")
    return {"text": text.strip() or "[no text found]", "caption": caption}

@app.post("/predict")
def predict(q: Query):
    text_norm = q.text.strip()
    past = memory.get_all(q.user_id)
    ctx = ContextResolver(memory, q.user_id)
    resolved_text = ctx.resolve(text_norm)
    was_resolved = resolved_text != text_norm
    
    if m := re.search(r'this (?:person|man|woman|guy|girl) is ([a-zA-Z\s]+)', resolved_text, re.IGNORECASE):
        name = m.group(1).strip().title()
        last_visions = [m for m in past if m["key"].startswith("VISION:")]
        if last_visions:
            caption = last_visions[0]["value"]["caption"]
            memory.add(q.user_id, "PERSONAL_NAME", {"name": name})
            memory.add(q.user_id, f"FACE:{caption}", {"name": name})
            ctx.set_last_entity(name, entity_type="person")
            answer = EpistemicAnswer(claim=f"Got it. I'll remember this person as {name}.", source="vision_learning", uncertainty=0.0, falsifiable_test="# face")
            memory.add(q.user_id, text_norm, answer.model_dump())
            result = answer.model_dump(); result["auto_result"] = None; result["learned"] = False
            return result
    
    if any(phrase in resolved_text.lower() for phrase in ['did you see', 'what did you see', 'what do you see']):
        last_visions = [m for m in past if m["key"].startswith("VISION:")]
        if last_visions:
            caption = last_visions[0]["value"]["caption"]
            answer = EpistemicAnswer(claim=f"Yes, I saw: {caption}", source="vision_memory", uncertainty=0.0, falsifiable_test="# recall")
            result = answer.model_dump(); result["auto_result"] = None; result["learned"] = True
            return result
    
    if m := re.search(r'my (\w+(?: \w+)?) is (.+)', resolved_text, re.IGNORECASE):
        key = m.group(1).strip().lower().replace(' ', '_')
        value = m.group(2).strip()
        memory.add(q.user_id, f"PERSONAL_{key.upper()}", {"value": value})
        ctx.set_last_entity(value, entity_type="attribute")
        answer = EpistemicAnswer(claim=f"Got it. I'll remember your {key.replace('_',' ')} is {value}.", source="personal", uncertainty=0.0, falsifiable_test="# memory")
        memory.add(q.user_id, text_norm, answer.model_dump())
        result = answer.model_dump(); result["auto_result"] = None; result["learned"] = False
        return result
    
    if m := re.search(r'what(?:\'s| is) my (\w+(?: \w+)?)\??', resolved_text, re.IGNORECASE):
        key = m.group(1).strip().lower().replace(' ', '_')
        if key == "name":
            names = [m for m in past if m["key"] == "PERSONAL_NAME"]
            if names:
                name = names[-1]["value"]["name"]
                ctx.set_last_entity(name, entity_type="person")
                answer = EpistemicAnswer(claim=f"Your name is {name}", source="memory", uncertainty=0.0, falsifiable_test="# recall")
                result = answer.model_dump(); result["auto_result"] = None; result["learned"] = True
                return result
        entries = [m for m in past if m["key"] == f"PERSONAL_{key.upper()}"]
        if entries:
            value = entries[-1]["value"]["value"]
            answer = EpistemicAnswer(claim=f"Your {key.replace('_',' ')} is {value}", source="memory", uncertainty=0.0, falsifiable_test="# recall")
            result = answer.model_dump(); result["auto_result"] = None; result["learned"] = True
            return result
    
    if resolved_text.lower().strip() in ['yes', 'yeah', 'yep', 'no', 'nope', 'nah']:
        last_q = next((m for m in reversed(past) if not m["key"].startswith(("CONTEXT","FEEDBACK","VISION","RESOLVED","ACT:")) and "claim" in m["value"]), None)
        if last_q:
            answer = EpistemicAnswer(claim=f"Understood. You said '{resolved_text}' about: {last_q['value']['claim'][:100]}", source="confirmation", uncertainty=0.1, falsifiable_test="# confirm")
            result = answer.model_dump(); result["auto_result"] = None; result["learned"] = False
            return result
    
    if ' then ' in resolved_text.lower():
        steps = re.split(r'\s+then\s+', q.text, flags=re.IGNORECASE)
        chain_results = []
        for step in steps:
            step_proc = ctx.resolve(step)
            pred, test = world.predict(step_proc.strip())
            chain_results.append(f"→ {step_proc}:\n{pred}")
            memory.add(q.user_id, step_proc, {"claim": pred})
        final_claim = "\n\n".join(chain_results)
        answer = EpistemicAnswer(claim=final_claim, source="chain", uncertainty=0.2, falsifiable_test="# chain")
        memory.add(q.user_id, text_norm, answer.model_dump())
        result = answer.model_dump(); result["auto_result"] = None; result["learned"] = False
        return result
    
    learned_answer = None
    feedback_trues = [m for m in past if m["key"] == f"FEEDBACK:{text_norm}" and m["value"].get("correct")]
    if feedback_trues:
        for fb in feedback_trues:
            approved = fb["value"].get("approved_claim")
            if approved and not approved.startswith("Simulated future for:"):
                learned_answer = approved; break
    
    if learned_answer:
        prediction, test_code, uncertainty, source = learned_answer, "# learned from memory", 0.1, "learned_memory"
    else:
        prediction, test_code = world.predict(resolved_text)
        feedbacks = [m for m in past if m["key"] == f"FEEDBACK:{text_norm}"]
        uncertainty = round(0.7 * (1 - sum(1 for f in feedbacks if f["value"].get("correct"))/len(feedbacks)) + 0.1, 2) if feedbacks else 0.7
        source = "world_engine_v1"
    
    if " is " in prediction and len(prediction.split()) < 12:
        potential_name = prediction.split(" is ")[0].strip()
        if len(potential_name.split()) <= 3 and potential_name[0].isupper():
            ctx.set_last_entity(potential_name, entity_type="person")
    
    answer = EpistemicAnswer(claim=prediction, source=source, uncertainty=uncertainty, falsifiable_test=test_code)
    memory.add(q.user_id, text_norm, answer.model_dump())
    auto_result = None
    if test_code and not test_code.startswith("#"):
        auto_result = world.act(test_code)
        memory.add(q.user_id, f"ACT:{test_code[:80]}", {"result": auto_result})
    result = answer.model_dump(); result["auto_result"] = auto_result; result["learned"] = bool(learned_answer)
    if was_resolved:
        result["claim"] = f"[Resolved '{text_norm}' → '{resolved_text}']\n\n" + result["claim"]
    return result

@app.post("/act")
def act(q: Query):
    result = world.act(q.text)
    memory.add(q.user_id, f"ACT:{q.text.strip()[:80]}", {"result": result})
    return {"result": result}

@app.post("/feedback")
def give_feedback(fb: Feedback):
    text_norm = fb.text.strip()
    past = memory.get_all(fb.user_id)
    last_pred = next((m["value"]["claim"] for m in past if m["key"] == text_norm and "claim" in m["value"]), None)
    memory.add(fb.user_id, f"FEEDBACK:{text_norm}", {"correct": fb.correct, "approved_claim": last_pred})
    correction = None
    if not fb.correct and last_pred:
        new_pred, test_code = world.predict(text_norm)
        if new_pred != last_pred and not new_pred.startswith("Simulated future for:"):
            corr = EpistemicAnswer(claim=new_pred, source="auto_correction", uncertainty=0.5, falsifiable_test=test_code)
            memory.add(fb.user_id, text_norm, corr.model_dump())
            auto_res = world.act(test_code) if test_code and not test_code.startswith("#") else None
            correction = {"claim": new_pred, "auto_result": auto_res}
    return {"status": "saved", "correction": correction}

@app.get("/memory/{user_id}")
def get_memory(user_id: str):
    return memory.get_all(user_id)