from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from .epistemic import EpistemicAnswer
from .memory import Memory
from .world import WorldEngine

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
    body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:0;padding:16px;background:#000;color:#eee}
    input,textarea,button{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:1px solid #333;background:#111;color:#eee;font-size:16px}
    button{background:#0a84ff;border:none;font-weight:600}
    .smallbtn{width:48%;display:inline-block;margin:4px 1%}
    .card{background:#111;padding:12px;margin:8px 0;border-radius:8px;border:1px solid #222}
    small{color:#888}
  </style>
</head>
<body>
  <h2>Worlds Best AI Lab</h2>
  <small>predict → act → remember → learn</small>
  <input id="uid" placeholder="user_id" value="ash">
  <textarea id="txt" rows="3" placeholder="Enter your thought..."></textarea>
  <button onclick="predict()">Predict</button>
  <button onclick="act()">Act</button>
  <button onclick="showMemory()">Show Memory</button>
  <div id="out"></div>
<script>
let lastPrediction = "";
async function predict(){
  const uid=document.getElementById('uid').value;
  const txt=document.getElementById('txt').value;
  lastPrediction = txt;
  const r=await fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt,user_id:uid})});
  const j=await r.json();
  const card = `<div class=card><b>Prediction</b><br>${j.claim}<br><small>uncertainty ${j.uncertainty} | test: ${j.falsifiable_test}</small><br><button class=smallbtn onclick="feedback(true)">Mark True</button><button class=smallbtn onclick="feedback(false)">Mark False</button></div>`;
  document.getElementById('out').innerHTML = card + document.getElementById('out').innerHTML;
}
async function act(){
  const uid=document.getElementById('uid').value;
  const txt=document.getElementById('txt').value;
  const r=await fetch('/act',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt,user_id:uid})});
  const j=await r.json();
  document.getElementById('out').innerHTML='<div class=card><b>Action</b><br>'+j.result+'</div>'+document.getElementById('out').innerHTML;
}
async function showMemory(){
  const uid=document.getElementById('uid').value;
  const r=await fetch('/memory/'+uid);
  const j=await r.json();
  let html='<div class=card><b>Memory ('+j.length+')</b><br>';
  j.slice(0,10).forEach(m=>{html+=m.key+': '+JSON.stringify(m.value).slice(0,80)+'<br>'});
  html+='</div>';
  document.getElementById('out').innerHTML=html+document.getElementById('out').innerHTML;
}
async function feedback(correct){
  const uid=document.getElementById('uid').value;
  await fetch('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:lastPrediction,user_id:uid,correct:correct})});
  document.getElementById('out').innerHTML='<div class=card><small>Feedback saved: '+ (correct?'TRUE':'FALSE') +' for "'+lastPrediction+'"</small></div>'+document.getElementById('out').innerHTML;
}
</script>
</body>
</html>
'''

@app.post("/predict")
def predict(q: Query):
    # 1. predict next state
    prediction = world.predict(q.text)
    # 2. wrap in epistemic layer
    answer = EpistemicAnswer(
        claim=prediction,
        source="world_engine_stub",
        uncertainty=0.7,
        falsifiable_test=f"Check if '{prediction}' holds in real world"
    )
    # 3. store in memory
    memory.add(q.user_id, q.text, answer.model_dump())
    return answer

@app.post("/act")
def act(q: Query):
    result = world.act(q.text)
    memory.add(q.user_id, f"ACT:{q.text}", {"result": result})
    return {"result": result}

@app.post("/feedback")
def give_feedback(fb: Feedback):
    memory.add(fb.user_id, f"FEEDBACK:{fb.text}", {"correct": fb.correct})
    return {"status": "saved", "correct": fb.correct}

@app.get("/memory/{user_id}")
def get_memory(user_id: str):
    return memory.get_all(user_id)