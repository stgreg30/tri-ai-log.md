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
   .smallbtn{width:32%;display:inline-block;margin:4px 0.5%}
   .card{background:#111;padding:12px;margin:8px 0;border-radius:8px;border:1px solid #222;white-space:pre-wrap}
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
let lastTest = "";
async function predict(){
  const uid=document.getElementById('uid').value;
  const txt=document.getElementById('txt').value;
  lastPrediction = txt.trim();
  const r=await fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt,user_id:uid})});
  const j=await r.json();
  lastTest = j.falsifiable_test;
  let auto = j.auto_result? `<br><b>Auto Test Result:</b> ${j.auto_result}` : '';
  let learned = j.learned? ' <small style="color:#0f0">[LEARNED]</small>' : '';
  const card = `<div class=card><b>Prediction${learned}</b><br>${j.claim}<br><small>uncertainty ${j.uncertainty} | test: ${j.falsifiable_test}</small>${auto}<br><button class=smallbtn onclick="runTest()">Run Test</button><button class=smallbtn onclick="feedback(true)">Mark True</button><button class=smallbtn onclick="feedback(false)">Mark False</button></div>`;
  document.getElementById('out').innerHTML = card + document.getElementById('out').innerHTML;
}
async function act(){
  const uid=document.getElementById('uid').value;
  const txt=document.getElementById('txt').value;
  const r=await fetch('/act',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt,user_id:uid})});
  const j=await r.json();
  document.getElementById('out').innerHTML='<div class=card><b>Action</b><br>'+j.result+'</div>'+document.getElementById('out').innerHTML;
}
async function runTest(){
  const uid=document.getElementById('uid').value;
  const r=await fetch('/act',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:lastTest,user_id:uid})});
  const j=await r.json();
  document.getElementById('out').innerHTML='<div class=card><b>Test Result</b><br>'+j.result+'</div>'+document.getElementById('out').innerHTML;
}
async function showMemory(){
  const uid=document.getElementById('uid').value;
  const r=await fetch('/memory/'+uid);
  const j=await r.json();
  let html='<div class=card><b>Memory ('+j.length+')</b><br>';
  j.slice(0,15).forEach(m=>{html+=m.key+': '+JSON.stringify(m.value).slice(0,80)+'<br>'});
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
    text_norm = q.text.strip()
    past = memory.get_all(q.user_id)

    # --- PATH 3: LEARNING (only good answers) ---
    learned_answer = None
    feedback_trues = [m for m in past if m["key"] == f"FEEDBACK:{text_norm}" and m["value"].get("correct")]

    if feedback_trues:
        # Prefer the claim you explicitly approved
        for fb in reversed(feedback_trues):
            approved = fb["value"].get("approved_claim")
            if approved and not approved.startswith("Simulated future for:"):
                learned_answer = approved
                break
        # Fallback for old feedback without approved_claim
        if not learned_answer:
            preds = [m for m in reversed(past) if m["key"] == text_norm and "claim" in m["value"]]
            for p in preds:
                claim = p["value"]["claim"]
                if not claim.startswith("Simulated future for:"):
                    learned_answer = claim
                    break

    if learned_answer:
        prediction = learned_answer
        test_code = "# learned from memory"
        uncertainty = 0.1
        source = "learned_memory"
    else:
        prediction, test_code = world.predict(text_norm)
        feedbacks = [m for m in past if m["key"] == f"FEEDBACK:{text_norm}"]
        if feedbacks:
            correct = sum(1 for f in feedbacks if f["value"].get("correct"))
            uncertainty = round(0.7 * (1 - correct/len(feedbacks)) + 0.1, 2)
        else:
            uncertainty = 0.7
        source = "world_engine_v1"

    answer = EpistemicAnswer(
        claim=prediction,
        source=source,
        uncertainty=uncertainty,
        falsifiable_test=test_code
    )
    memory.add(q.user_id, text_norm, answer.model_dump())

    # PATH 1: auto-run test
    auto_result = None
    if test_code and not test_code.startswith("#"):
        auto_result = world.act(test_code)
        memory.add(q.user_id, f"ACT:{test_code[:80]}", {"result": auto_result})

    result = answer.model_dump()
    result["auto_result"] = auto_result
    result["learned"] = bool(learned_answer)
    return result

@app.post("/act")
def act(q: Query):
    result = world.act(q.text)
    memory.add(q.user_id, f"ACT:{q.text.strip()[:80]}", {"result": result})
    return {"result": result}

@app.post("/feedback")
def give_feedback(fb: Feedback):
    # store which exact prediction you approved
    past = memory.get_all(fb.user_id)
    last_pred = next((m["value"]["claim"] for m in reversed(past) if m["key"] == fb.text.strip() and "claim" in m["value"]), None)
    memory.add(fb.user_id, f"FEEDBACK:{fb.text.strip()}", {"correct": fb.correct, "approved_claim": last_pred})
    return {"status": "saved"}

@app.get("/memory/{user_id}")
def get_memory(user_id: str):
    return memory.get_all(user_id)