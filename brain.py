from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
import asyncio
import json
import time
import os
from datetime import datetime

from factory import ResearchFactory
from memory import BrainMemory

app = FastAPI(title="UAI Brain")
factory = ResearchFactory()
memory = BrainMemory()
active_sessions = {}

class UserRequest(BaseModel):
    text: str
    user_id: str = "default"

class HelpRequest(BaseModel):
    info: str
    user_id: str = "default"

class BrainSession:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.task = None
        self.attempt = 0
        self.max_attempts = 2
        self.status = "idle"
        self.stop_requested = False
        self.help_info = None
        self.current_neuron = None

async def process_task(session, task):
    session.task = task
    session.attempt = 0
    
    cached = await memory.find_solution(task, session.user_id)
    if cached:
        yield json.dumps({"attempt": 1, "status": "success", "message": "Found in memory", "answer": cached["answer"], "neuron_used": cached["neuron_name"], "from_memory": True}) + "\n"
        return
    
    while session.attempt <= session.max_attempts:
        if session.stop_requested:
            yield json.dumps({"attempt": session.attempt, "status": "stopped", "message": "Stopped"}) + "\n"
            return
            
        session.attempt += 1
        session.status = "processing"
        
        yield json.dumps({"attempt": session.attempt, "status": "processing", "message": f"Processing: {task} (Attempt {session.attempt}/{session.max_attempts})"}) + "\n"
        
        try:
            result = await factory.execute_task({"text": task, "help_info": session.help_info, "user_id": session.user_id})
            
            if result.get("success"):
                await memory.store_success(task=task, user_id=session.user_id, neuron_name=result.get("neuron_used", "unknown"), answer=result["answer"])
                yield json.dumps({"attempt": session.attempt, "status": "success", "message": "Done!", "answer": result["answer"], "neuron_used": result.get("neuron_used")}) + "\n"
                return
            else:
                error = result.get("error", "Unknown error")
                yield json.dumps({"attempt": session.attempt, "status": "failed", "message": f"Failed: {error}", "error": error}) + "\n"
                
                if session.attempt <= session.max_attempts:
                    yield json.dumps({"attempt": session.attempt, "status": "researching", "message": "Researching..."}) + "\n"
                    research = await factory.research_failure(error, task)
                    yield json.dumps({"attempt": session.attempt, "status": "researching", "message": "Research done", "research_findings": research.get("summary", "")[:200]}) + "\n"
                    
                    yield json.dumps({"attempt": session.attempt, "status": "building", "message": "Building AI agent..."}) + "\n"
                    build_result = await factory.build_fix(error, research, task)
                    
                    if build_result.get("success"):
                        session.current_neuron = build_result.get("agent_name", build_result.get("neuron_name"))
                        yield json.dumps({"attempt": session.attempt, "status": "building", "message": f"Agent built: {session.current_neuron}", "neuron_built": session.current_neuron}) + "\n"
                        await memory.store_learning(error=error, task=task, research=research, neuron_name=session.current_neuron, success=False)
                        yield json.dumps({"attempt": session.attempt, "status": "retrying", "message": "Retrying..."}) + "\n"
                    else:
                        yield json.dumps({"attempt": session.attempt, "status": "failed", "message": "Build failed", "error": build_result.get("error")}) + "\n"
                        return
        except Exception as e:
            yield json.dumps({"attempt": session.attempt, "status": "failed", "message": f"Error: {str(e)}", "error": str(e)}) + "\n"
            if session.attempt <= session.max_attempts:
                await asyncio.sleep(1)
                continue
            return
    
    yield json.dumps({"attempt": session.attempt, "status": "failed", "message": "Max attempts reached"}) + "\n"

@app.on_event("startup")
async def startup():
    print("UAI Brain starting...")
    os.makedirs("neurons", exist_ok=True)
    os.makedirs("agents", exist_ok=True)
    
    existing = []
    for d in ["neurons", "agents"]:
        if os.path.exists(d):
            existing.extend([f for f in os.listdir(d) if f.endswith(".py")])
    
    if len(existing) <= 1:
        try:
            r1 = await factory._build_universal_agent("init", {})
            print(f"Created: {r1.get('agent_name')}")
            r2 = await factory._build_research_agent("search", {})
            print(f"Created: {r2.get('agent_name')}")
        except Exception as e:
            print(f"Init error: {e}")
    
    print("UAI Brain ready!")

@app.post("/think")
async def think(request: UserRequest):
    session = BrainSession(request.user_id)
    active_sessions[f"{request.user_id}_{int(time.time())}"] = session
    return StreamingResponse(process_task(session, request.text), media_type="application/x-ndjson")

@app.post("/stop")
async def stop(request: UserRequest):
    for sid, s in active_sessions.items():
        if s.user_id == request.user_id:
            s.stop_requested = True
    return {"status": "stopped"}

@app.post("/help")
async def help_guide(request: HelpRequest):
    for sid, s in active_sessions.items():
        if s.user_id == request.user_id:
            s.help_info = request.info
            return {"status": "help_received", "info": request.info}
    return {"status": "help_received"}

@app.get("/memory/{user_id}")
async def get_memory(user_id: str):
    memories = await memory.get_user_memories(user_id)
    return {"user_id": user_id, "memories": memories, "count": len(memories)}

@app.get("/neurons")
async def list_neurons():
    neurons = await factory.list_neurons()
    return {"neurons": neurons, "count": len(neurons)}

@app.get("/health")
async def health():
    count = 0
    for d in ["neurons", "agents"]:
        if os.path.exists(d):
            count += len([f for f in os.listdir(d) if f.endswith(".py")])
    return {"status": "healthy", "agents": count}

@app.get("/")
async def root():
    html = """<!DOCTYPE html>
<html>
<head>
    <title>UAI Brain</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Courier New',monospace;background:#0a0a0a;color:#00ff00;height:100vh;display:flex;flex-direction:column}
        #header{background:#111;padding:20px;border-bottom:2px solid #00ff00;text-align:center}
        #header h1{color:#00ff00;font-size:24px}
        #header p{color:#008800;font-size:14px}
        #log{flex:1;overflow-y:auto;padding:20px;background:#000}
        .log-entry{margin:10px 0;padding:10px;border-left:3px solid;background:#0a0a0a}
        .success{border-color:#00ff00}
        .failed{border-color:#ff0000}
        .researching{border-color:#ffaa00}
        .building{border-color:#00aaff}
        .retrying{border-color:#ff00ff}
        .stopped{border-color:#888}
        .processing{border-color:#fff}
        .timestamp{color:#666;font-size:12px}
        .status{font-weight:bold}
        #controls{background:#111;padding:20px;border-top:2px solid #00ff00;display:flex;gap:10px}
        #input{flex:1;padding:10px;background:#000;border:1px solid #00ff00;color:#00ff00;font-family:inherit;font-size:16px}
        button{padding:10px 20px;background:#003300;border:1px solid #00ff00;color:#00ff00;cursor:pointer;font-family:inherit;font-size:16px}
        button:hover{background:#004400}
        .stop{background:#300;border-color:#f00;color:#f00}
        .stop:hover{background:#400}
        .help{background:#033;border-color:#0af;color:#0af}
        .help:hover{background:#044}
        .answer-block{margin-top:10px;padding:15px;background:#0a0a0a;border:1px solid #00ff00;border-radius:5px;white-space:pre-wrap;max-height:400px;overflow-y:auto}
        .info-bar{display:flex;justify-content:space-between;padding:5px 20px;background:#111;color:#666;font-size:12px}
        @media(max-width:768px){#controls{flex-wrap:wrap}button{padding:10px;font-size:14px}}
    </style>
</head>
<body>
    <div id="header"><h1>UAI - Self-Evolving Brain</h1><p>Auto-research | Self-building AI agents</p></div>
    <div class="info-bar"><span>Status: <span id="brainStatus">Ready</span></span><span>Agents: <span id="agentCount">0</span></span></div>
    <div id="log"></div>
    <div id="controls">
        <input type="text" id="input" placeholder="Ask anything..." />
        <button onclick="send()" id="sendBtn">Send</button>
        <button class="stop" onclick="stop()">Stop</button>
        <button class="help" onclick="help()">Help</button>
    </div>
    <script>
        let controller = null;
        const uid = 'u_'+Math.random().toString(36).substr(2,9);
        
        fetch('/health').then(r=>r.json()).then(d=>document.getElementById('agentCount').textContent=d.agents);
        
        function addLog(e){
            const log=document.getElementById('log');
            const div=document.createElement('div');
            div.className='log-entry '+(e.status||'processing');
            const t=new Date().toLocaleTimeString();
            let h='<span class="timestamp">['+t+']</span><span class="status">['+(e.status||'processing').toUpperCase()+']</span> '+e.message;
            if(e.answer)h+='<div class="answer-block">'+e.answer.replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</div>';
            if(e.neuron_built)h+='<div style="color:#0af">New agent: '+e.neuron_built+'</div>';
            if(e.error)h+='<div style="color:#f00">'+e.error+'</div>';
            div.innerHTML=h;
            log.appendChild(div);
            log.scrollTop=log.scrollHeight;
            if(e.neuron_built)fetch('/health').then(r=>r.json()).then(d=>document.getElementById('agentCount').textContent=d.agents);
        }
        
        async function send(){
            const inp=document.getElementById('input');
            const btn=document.getElementById('sendBtn');
            const text=inp.value.trim();
            if(!text)return;
            inp.value='';inp.disabled=true;btn.disabled=true;
            document.getElementById('brainStatus').textContent='Processing...';
            addLog({status:'processing',message:'You: '+text});
            try{
                controller=new AbortController();
                const res=await fetch('/think',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,user_id:uid}),signal:controller.signal});
                const reader=res.body.getReader();
                const decoder=new TextDecoder();
                while(true){
                    const {done,value}=await reader.read();
                    if(done)break;
                    const lines=decoder.decode(value).split('\\n').filter(l=>l.trim());
                    for(const l of lines)try{addLog(JSON.parse(l))}catch(e){}
                }
            }catch(e){if(e.name!=='AbortError')addLog({status:'failed',message:'Error',error:e.message})}
            inp.disabled=false;btn.disabled=false;inp.focus();
            document.getElementById('brainStatus').textContent='Ready';
        }
        
        async function stop(){
            if(controller){controller.abort();controller=null}
            await fetch('/stop',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid,text:''})});
            addLog({status:'stopped',message:'Stopped'});
            document.getElementById('input').disabled=false;
            document.getElementById('sendBtn').disabled=false;
            document.getElementById('brainStatus').textContent='Ready';
        }
        
        async function help(){
            const h=prompt('Guide the brain:');
            if(!h)return;
            await fetch('/help',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({info:h,user_id:uid})});
            addLog({status:'building',message:'Help: '+h});
        }
        
        document.getElementById('input').addEventListener('keypress',e=>{if(e.key==='Enter')send()});
        document.getElementById('input').focus();
        addLog({status:'success',message:'UAI Brain ready! Ask me anything!'});
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)