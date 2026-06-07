from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import re
import httpx
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

@app.get("/", response_class=HTMLResponse)
def home():
    return '''
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Worlds Best AI Lab</title>
  <style>
    body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:0;padding:0;background:#000;color:#eee;display:flex;flex-direction:column;height:100vh}
    header{padding:12px 16px;border-bottom:1px solid #222}
    #out{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}
  .card{background:#111;padding:12px;border-radius:12px;border:1px solid #222;white-space:pre-wrap;max-width:85%}
  .user{align-self:flex-end;background:#0a84ff;border:none}
  .ai{align-self:flex-start}
    footer{padding:12px;border-top:1px solid #222}
    input,textarea,button{width:100%;padding:12px;margin:6px 0;border-radius:10px;border:1px solid #333;background:#111;color:#eee;font-size:16px}
    button{background:#0a84ff;border:none;font-weight:600}
  .row{display:flex;gap:6px}
  .row button{width:50%}
  .smallbtn{width:32%;display:inline-block;margin:4px 0.5%;padding:8px;font-size:14px}
    small{color:#888}
  </style>
</head>
<body>
  <header><b>Worlds Best AI Lab</b> <small>predict → act → remember → learn</small></header>
  <div id="out"></div>
  <footer>
    <input id="uid" placeholder="user_id" value="ash">
    <textarea id="txt" rows="2" placeholder="Enter your thought... (use 'then' to chain)"></textarea>
    <div class="row">
      <button onclick="predict()">Predict</button>
      <button onclick="act()">Act</button>
    </div>
    <div class="row">
      <button onclick="startVoice()">🎤 Voice</button>
      <button onclick="document.getElementById('img').click()">📷 Image</button>
    </div>
    <button onclick="showMemory()" style="background:#333">Show Memory</button>
    <input type="file" id="img" accept="image/*" style="display:none" onchange="uploadImg()">
  </footer>
<script>
let lastPrediction = ""; let lastTest = "";
function addCard(html, cls){ const d=document.createElement('div'); d.className='card '+cls; d.innerHTML=html; document.getElementById('out').appendChild(d); document.getElementById('out').scrollTop=999999; }

async function predict(){
  const uid=document.getElementById('uid').value;
  const txt=document.getElementById('txt').value;
  if(!txt.trim()) return;
  lastPrediction = txt.trim();
  addCard(txt,'user');
  document.getElementById('txt').value='';
  const r=await fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt,user_id:uid})});
  const j=await r.json();
  lastTest = j.falsifiable_test;
  let auto = j.auto_result? `<br><b>Auto Test:</b> ${j.auto_result.slice(0,200)}` : '';
  let learned = j.learned? ' <small style="color:#0f0">[LEARNED]</small>' : '';
  const html = `<b>Prediction${learned}</b><br>${j.claim}<br><small>uncertainty ${j.uncertainty}</small>${auto}<br><button class=smallbtn onclick="runTest()">Run Test</button><button class=smallbtn onclick="feedback(true)">True</button><button class=smallbtn onclick="feedback(false)">False</button>`;
  addCard(html,'ai');
}
async function act(){
  const uid=document.getElementById('uid').value;
  const txt=document.getElementById('txt').value;
  if(!txt.trim()) return;
  addCard(txt,'user');
  document.getElementById('txt').value='';
  const r=await fetch('/act',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt,user_id:uid})});
  const j=await r.json();
  addCard('<b>Action</b><br>'+j.result,'ai');
}
async function uploadImg(){
  const f=document.getElementById('img').files[0]; if(!f) return;
  const uid=document.getElementById('uid').value;
  const fd=new FormData(); fd.append('file',f); fd.append('user_id',uid);
  addCard('📷 Uploading...','user');
  const r=await fetch('/upload',{method:'POST',body:fd});
  const j=await r.json();
  addCard('<b>Image Text</b><br>'+j.text,'ai');
  document.getElementById('txt').value = j.text.slice(0,200);
}
function startVoice(){
  const rec = new (window.SpeechRecognition||window.webkitSpeechRecognition)();
  rec.lang='en-US'; rec.start();
  addCard('🎤 Listening...','ai');
  rec.onresult = e=>{ document.getElementById('txt').value = e.results[0][0].transcript; predict(); };
}
async function runTest(){
  const uid=document.getElementById('uid').value;
  const r=await fetch('/act',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:lastTest,user_id:uid})});
  const j=await r.json(); addCard('<b>Test Result</b><br>'+j.result,'ai');
}
async function showMemory(){
  const uid=document.getElementById('uid').value;
  const r=await fetch('/memory/'+uid); const j=await r.json();
  let html='<b>Memory ('+j.length+')</b><br>'; j.slice(0,15).forEach(m=>{html+=m.key+': '+JSON.stringify(m.value).slice(0,80)+'<br>'}); addCard(html,'ai');
}
async function feedback(correct){
  const uid=document.getElementById('uid').value;
  const r = await fetch('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:lastPrediction,user_id:uid,correct:correct})});
  const j = await r.json(); let html = '<small>Feedback: '+ (correct?'TRUE':'FALSE') +'</small>'; if(j.correction){ html += '<br><b style="color:#0f0">Auto-correction:</b> '+ j.correction.claim; } addCard(html,'ai');
}
</script>
</body>
</html>
'''

@app.post("/upload")
async def upload(file: UploadFile = File(...), user_id: str = Form("default")):
    content = await file.read()
    try:
        # Free OCR.space API (works without install)
        r = httpx.post(
            "https://api.ocr.space/parse/image",
            files={"file": (file.filename, content, file.content_type)},
            data={"apikey": "helloworld", "language": "eng"},
            timeout=20.0
        )
        data = r.json()
        text = data["ParsedResults"][0]["ParsedText"] if data.get("ParsedResults") else ""
    except Exception as e:
        text = f"OCR failed: {e}"

    memory.add(user_id, f"IMAGE:{file.filename}", {"text": text})
    return {"text": text.strip() or "[no text found]"}

@app.post("/predict")
def predict(q: Query):
    text_norm = q.text.strip()
    if ' then ' in text_norm.lower():
        steps = re.split(r'\s+then\s+', q.text, flags=re.IGNORECASE)
        chain_results = []; last_summary = ""; last_url = ""
        for step in steps:
            step_proc = step
            if 'city mentioned' in step.lower():
                city = None
                if last_url and 'wikipedia.org/wiki/' in last_url:
                    city = last_url.split('/wiki/')[-1].replace('_',' ')
                if not city and last_summary:
                    stop = {'Summary','Wikipedia','Main','Jump','Content','Article'}
                    for m in re.finditer(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b', last_summary):
                        if m.group(1) not in stop: city = m.group(1); break
                if city: step_proc = re.sub(r'city mentioned', city, step, flags=re.IGNORECASE)
            pred, test = world.predict(step_proc.strip())
            if step_proc.lower().startswith('summarize'):
                url_match = re.search(r'https?://\S+', step_proc)
                if url_match: last_url = url_match.group(0)
                last_summary = pred
            chain_results.append(f"→ {step_proc}:\n{pred}")
            memory.add(q.user_id, step_proc, {"claim": pred})
        final_claim = "\n\n".join(chain_results)
        answer = EpistemicAnswer(claim=final_claim, source="chain", uncertainty=0.2, falsifiable_test="# chain")
        memory.add(q.user_id, text_norm, answer.model_dump())
        result = answer.model_dump(); result["auto_result"] = None; result["learned"] = False
        return result

    past = memory.get_all(q.user_id)
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
        prediction, test_code = world.predict(text_norm)
        feedbacks = [m for m in past if m["key"] == f"FEEDBACK:{text_norm}"]
        uncertainty = round(0.7 * (1 - sum(1 for f in feedbacks if f["value"].get("correct"))/len(feedbacks)) + 0.1, 2) if feedbacks else 0.7
        source = "world_engine_v1"

    answer = EpistemicAnswer(claim=prediction, source=source, uncertainty=uncertainty, falsifiable_test=test_code)
    memory.add(q.user_id, text_norm, answer.model_dump())
    auto_result = None
    if test_code and not test_code.startswith("#"):
        auto_result = world.act(test_code)
        memory.add(q.user_id, f"ACT:{test_code[:80]}", {"result": auto_result})
    result = answer.model_dump(); result["auto_result"] = auto_result; result["learned"] = bool(learned_answer)
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
        if new_pred!= last_pred and not new_pred.startswith("Simulated future for:"):
            corr = EpistemicAnswer(claim=new_pred, source="auto_correction", uncertainty=0.5, falsifiable_test=test_code)
            memory.add(fb.user_id, text_norm, corr.model_dump())
            auto_res = world.act(test_code) if test_code and not test_code.startswith("#") else None
            correction = {"claim": new_pred, "auto_result": auto_res}
    return {"status": "saved", "correction": correction}

@app.get("/memory/{user_id}")
def get_memory(user_id: str):
    return memory.get_all(user_id)