# brain.py - Main loop and FastAPI server
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import json
import time
import uuid
import os
from datetime import datetime

from factory import ResearchFactory
from memory import BrainMemory

# Create FastAPI app
app = FastAPI(title="UAI - Self-Evolving Brain")

# Initialize core components
factory = ResearchFactory()
memory = BrainMemory()

# Track active sessions
active_sessions = {}

class UserRequest(BaseModel):
    text: str
    user_id: str = "default"

class HelpRequest(BaseModel):
    info: str
    user_id: str = "default"

class BrainSession:
    """Manages state for each brain processing session"""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.task = None
        self.attempt = 0
        self.max_attempts = 2
        self.status = "idle"
        self.stop_requested = False
        self.help_info = None
        self.current_neuron = None
        
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "task": self.task,
            "attempt": self.attempt,
            "status": self.status,
            "current_neuron": self.current_neuron
        }

async def process_task(session: BrainSession, task: str):
    """Main processing loop with visible failure handling"""
    session.task = task
    session.attempt = 0
    session.stop_requested = False
    
    # Check memory for cached solution first
    cached = await memory.find_solution(task, session.user_id)
    if cached:
        yield json.dumps({
            "attempt": 1,
            "status": "success",
            "message": "Found cached solution in memory",
            "answer": cached["answer"],
            "neuron_used": cached["neuron_name"],
            "from_memory": True
        }) + "\n"
        return
    
    # Try processing with retries
    while session.attempt <= session.max_attempts:
        if session.stop_requested:
            yield json.dumps({
                "attempt": session.attempt,
                "status": "stopped",
                "message": "Processing stopped by user"
            }) + "\n"
            return
            
        session.attempt += 1
        session.status = "processing"
        
        yield json.dumps({
            "attempt": session.attempt,
            "status": "processing",
            "message": f"Processing: '{task}' (Attempt {session.attempt}/{session.max_attempts})"
        }) + "\n"
        
        try:
            # Try to understand and execute
            result = await factory.execute_task({
                "text": task,
                "help_info": session.help_info,
                "user_id": session.user_id
            })
            
            if result.get("success"):
                # Store success in memory
                await memory.store_success(
                    task=task,
                    user_id=session.user_id,
                    neuron_name=result.get("neuron_used", "unknown"),
                    answer=result["answer"]
                )
                
                yield json.dumps({
                    "attempt": session.attempt,
                    "status": "success",
                    "message": "Task completed successfully!",
                    "answer": result["answer"],
                    "neuron_used": result.get("neuron_used"),
                    "log": result.get("log", [])
                }) + "\n"
                return
            else:
                # Failed - start visible failure loop
                error = result.get("error", "Unknown error")
                yield json.dumps({
                    "attempt": session.attempt,
                    "status": "failed",
                    "message": f"Failed: {error}",
                    "error": error
                }) + "\n"
                
                if session.attempt <= session.max_attempts:
                    # STEP 1: Research the failure
                    yield json.dumps({
                        "attempt": session.attempt,
                        "status": "researching",
                        "message": f"Researching: '{error}'..."
                    }) + "\n"
                    
                    research = await factory.research_failure(error, task)
                    
                    yield json.dumps({
                        "attempt": session.attempt,
                        "status": "researching",
                        "message": "Research complete",
                        "research_findings": research.get("summary", "")[:200],
                        "sources": research.get("sources", [])
                    }) + "\n"
                    
                    # STEP 2: Build a neuron to fix it
                    yield json.dumps({
                        "attempt": session.attempt,
                        "status": "building",
                        "message": "Building neuron to fix the issue..."
                    }) + "\n"
                    
                    build_result = await factory.build_fix(error, research, task)
                    
                    if build_result.get("success"):
                        session.current_neuron = build_result["neuron_name"]
                        yield json.dumps({
                            "attempt": session.attempt,
                            "status": "building",
                            "message": f"Neuron built: {build_result['neuron_name']}",
                            "neuron_built": build_result["neuron_name"]
                        }) + "\n"
                        
                        # Store the learning
                        await memory.store_learning(
                            error=error,
                            task=task,
                            research=research,
                            neuron_name=build_result["neuron_name"],
                            success=False
                        )
                        
                        # STEP 3: Retry with new neuron
                        yield json.dumps({
                            "attempt": session.attempt,
                            "status": "retrying",
                            "message": "Retrying with new neuron..."
                        }) + "\n"
                    else:
                        yield json.dumps({
                            "attempt": session.attempt,
                            "status": "failed",
                            "message": "Could not build fix",
                            "error": build_result.get("error")
                        }) + "\n"
                        return
                        
        except Exception as e:
            yield json.dumps({
                "attempt": session.attempt,
                "status": "failed",
                "message": f"Critical error: {str(e)}",
                "error": str(e)
            }) + "\n"
            
            if session.attempt <= session.max_attempts:
                yield json.dumps({
                    "attempt": session.attempt,
                    "status": "retrying",
                    "message": "Retrying after error..."
                }) + "\n"
                await asyncio.sleep(1)
                continue
            else:
                return
    
    # Max attempts reached
    yield json.dumps({
        "attempt": session.attempt,
        "status": "failed",
        "message": "Maximum attempts reached. Please try again or provide help."
    }) + "\n"

@app.on_event("startup")
async def startup_event():
    """Initialize neurons on first startup"""
    print("🧠 UAI Brain starting up...")
    
    # Create neurons directory if it doesn't exist
    os.makedirs("neurons", exist_ok=True)
    
    # Check if neurons already exist
    existing_neurons = [f for f in os.listdir("neurons") if f.endswith(".py")]
    
    if len(existing_neurons) <= 1:  # Only __init__.py or empty
        print("🔧 No neurons found. Building initial neurons...")
        try:
            # Create initial translator
            result = await factory._build_translator("initial setup", {})
            print(f"✅ Created translator: {result['neuron_name']}")
            
            # Create initial capability
            result = await factory._build_capability("search", {})
            print(f"✅ Created capability: {result['neuron_name']}")
            
            print("🧠 Initial neurons created successfully!")
        except Exception as e:
            print(f"⚠️ Neuron init error (non-fatal): {e}")
            print("Brain will still work - neurons will be created on first request")
    else:
        print(f"🧠 Found {len(existing_neurons)} existing neurons")
    
    print("✅ UAI Brain is ready!")
    print(f"📊 Memory system: {'Supabase' if memory.client else 'Local storage'}")

@app.post("/think")
async def think(request: UserRequest):
    """Main endpoint - accepts task and streams progress"""
    session_id = f"{request.user_id}_{int(time.time())}"
    session = BrainSession(request.user_id)
    active_sessions[session_id] = session
    
    return StreamingResponse(
        process_task(session, request.text),
        media_type="application/x-ndjson"
    )

@app.post("/stop")
async def stop(request: UserRequest):
    """Stop current processing for user"""
    stopped = []
    for sid, session in active_sessions.items():
        if session.user_id == request.user_id and session.status != "idle":
            session.stop_requested = True
            stopped.append(session.to_dict())
    
    return {
        "status": "stopped",
        "sessions_stopped": len(stopped),
        "progress": stopped
    }

@app.post("/help")
async def help_guide(request: HelpRequest):
    """Provide additional guidance to the brain"""
    for sid, session in active_sessions.items():
        if session.user_id == request.user_id:
            session.help_info = request.info
            return {
                "status": "help_received",
                "will_retry_with": request.info,
                "current_task": session.task
            }
    
    return {
        "status": "help_received",
        "message": "Help stored for next request"
    }

@app.get("/memory/{user_id}")
async def get_memory(user_id: str):
    """View stored memories for a user"""
    memories = await memory.get_user_memories(user_id)
    return {
        "user_id": user_id, 
        "memories": memories, 
        "count": len(memories)
    }

@app.get("/neurons")
async def list_neurons():
    """List all built neurons"""
    neurons = await factory.list_neurons()
    return {
        "neurons": neurons, 
        "count": len(neurons)
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    neurons_count = len([f for f in os.listdir("neurons") if f.endswith(".py")])
    return {
        "status": "healthy",
        "neurons": neurons_count,
        "memory": "supabase" if memory.client else "local"
    }

@app.get("/")
async def root():
    """Serve the chat interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>UAI - Self-Evolving Brain</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Courier New', monospace; 
                background: #0a0a0a; 
                color: #00ff00; 
                height: 100vh;
                display: flex;
                flex-direction: column;
            }
            #header {
                background: #111;
                padding: 20px;
                border-bottom: 2px solid #00ff00;
                text-align: center;
            }
            #header h1 { color: #00ff00; font-size: 24px; margin-bottom: 5px; }
            #header p { color: #008800; font-size: 14px; }
            #log {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                background: #000;
            }
            .log-entry {
                margin: 10px 0;
                padding: 10px;
                border-left: 3px solid;
                background: #0a0a0a;
                animation: slideIn 0.3s ease;
            }
            @keyframes slideIn {
                from { opacity: 0; transform: translateX(-10px); }
                to { opacity: 1; transform: translateX(0); }
            }
            .log-entry.success { border-color: #00ff00; }
            .log-entry.failed { border-color: #ff0000; }
            .log-entry.researching { border-color: #ffaa00; }
            .log-entry.building { border-color: #00aaff; }
            .log-entry.retrying { border-color: #ff00ff; }
            .log-entry.stopped { border-color: #888888; }
            .log-entry.processing { border-color: #ffffff; }
            .timestamp { color: #666; font-size: 12px; }
            .status { font-weight: bold; }
            #controls {
                background: #111;
                padding: 20px;
                border-top: 2px solid #00ff00;
                display: flex;
                gap: 10px;
            }
            #input {
                flex: 1;
                padding: 10px;
                background: #000;
                border: 1px solid #00ff00;
                color: #00ff00;
                font-family: inherit;
                font-size: 16px;
            }
            #input:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            button {
                padding: 10px 20px;
                background: #003300;
                border: 1px solid #00ff00;
                color: #00ff00;
                cursor: pointer;
                font-family: inherit;
                font-size: 16px;
                transition: all 0.3s;
                white-space: nowrap;
            }
            button:hover:not(:disabled) { 
                background: #004400; 
                transform: scale(1.05); 
            }
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            button.stop { background: #330000; border-color: #ff0000; color: #ff0000; }
            button.stop:hover:not(:disabled) { background: #440000; }
            button.help { background: #003333; border-color: #00aaff; color: #00aaff; }
            button.help:hover:not(:disabled) { background: #004444; }
            .answer-block {
                margin-top: 10px;
                padding: 15px;
                background: #0a0a0a;
                border: 1px solid #00ff00;
                border-radius: 5px;
                white-space: pre-wrap;
                font-family: monospace;
                max-height: 300px;
                overflow-y: auto;
            }
            .info-bar {
                display: flex;
                justify-content: space-between;
                padding: 5px 20px;
                background: #111;
                color: #666;
                font-size: 12px;
                border-bottom: 1px solid #333;
            }
            .status-dot {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-right: 5px;
                background: #00ff00;
            }
            @media (max-width: 768px) {
                #controls {
                    flex-wrap: wrap;
                }
                button {
                    padding: 10px;
                    font-size: 14px;
                }
            }
        </style>
    </head>
    <body>
        <div id="header">
            <h1>🧠 UAI - Self-Evolving Brain</h1>
            <p>Visible failure loop | Auto-research | Self-building neurons</p>
        </div>
        <div class="info-bar">
            <span><span class="status-dot" id="statusDot"></span>Status: <span id="brainStatus">Ready</span></span>
            <span>User: <span id="userId">...</span></span>
            <span>Neurons: <span id="neuronCount">0</span></span>
        </div>
        <div id="log"></div>
        <div id="controls">
            <input type="text" id="input" placeholder="Ask anything - try 'code a webpage' or 'wetin dey'..." />
            <button onclick="sendMessage()" id="sendBtn">▶ Send</button>
            <button class="stop" onclick="stopProcess()" id="stopBtn">■ Stop</button>
            <button class="help" onclick="provideHelp()">💡 Help</button>
        </div>
        
        <script>
            let currentController = null;
            const userId = 'user_' + Math.random().toString(36).substr(2, 9);
            
            document.getElementById('userId').textContent = userId;
            
            // Load initial stats
            async function loadStats() {
                try {
                    const [neuronsRes, healthRes] = await Promise.all([
                        fetch('/neurons'),
                        fetch('/health')
                    ]);
                    const neurons = await neuronsRes.json();
                    const health = await healthRes.json();
                    
                    document.getElementById('neuronCount').textContent = neurons.count;
                    document.getElementById('brainStatus').textContent = health.status;
                    document.getElementById('statusDot').style.background = '#00ff00';
                } catch (e) {
                    document.getElementById('neuronCount').textContent = '?';
                    document.getElementById('brainStatus').textContent = 'Connecting...';
                    document.getElementById('statusDot').style.background = '#ffaa00';
                }
            }
            loadStats();
            
            function addLog(entry) {
                const log = document.getElementById('log');
                const div = document.createElement('div');
                div.className = 'log-entry ' + (entry.status || 'processing');
                const time = new Date().toLocaleTimeString();
                
                let html = `<span class="timestamp">[${time}]</span>`;
                html += `<span class="status">[${(entry.status || 'processing').toUpperCase()}]</span>`;
                html += `<span>${entry.message || ''}</span>`;
                
                if (entry.answer) {
                    html += `<div class="answer-block">${escapeHtml(entry.answer)}</div>`;
                }
                if (entry.neuron_built) {
                    html += `<div style="color:#00aaff;margin-top:5px;">🔧 New neuron: ${entry.neuron_built}</div>`;
                }
                if (entry.research_findings) {
                    html += `<div style="color:#ffaa00;margin-top:5px;">📚 ${entry.research_findings}</div>`;
                }
                if (entry.error) {
                    html += `<div style="color:#ff0000;margin-top:5px;">❌ ${entry.error}</div>`;
                }
                if (entry.from_memory) {
                    html += `<div style="color:#00ff00;margin-top:5px;">💾 Retrieved from memory!</div>`;
                }
                
                div.innerHTML = html;
                log.appendChild(div);
                log.scrollTop = log.scrollHeight;
                
                // Update neuron count if a neuron was built
                if (entry.neuron_built) {
                    loadStats();
                }
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            async function sendMessage() {
                const input = document.getElementById('input');
                const sendBtn = document.getElementById('sendBtn');
                const text = input.value.trim();
                if (!text) return;
                
                input.value = '';
                input.disabled = true;
                sendBtn.disabled = true;
                document.getElementById('brainStatus').textContent = 'Processing...';
                document.getElementById('statusDot').style.background = '#ffaa00';
                
                addLog({status: 'processing', message: `You: ${text}`});
                
                try {
                    currentController = new AbortController();
                    const response = await fetch('/think', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({text, user_id: userId}),
                        signal: currentController.signal
                    });
                    
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    
                    while (true) {
                        const {done, value} = await reader.read();
                        if (done) break;
                        
                        const chunk = decoder.decode(value);
                        const lines = chunk.split('\\n').filter(line => line.trim());
                        
                        for (const line of lines) {
                            try {
                                const data = JSON.parse(line);
                                addLog(data);
                                
                                if (data.status === 'success' || data.status === 'failed') {
                                    document.getElementById('brainStatus').textContent = 'Ready';
                                    document.getElementById('statusDot').style.background = '#00ff00';
                                }
                            } catch (e) {
                                console.error('Parse error:', e);
                            }
                        }
                    }
                } catch (error) {
                    if (error.name !== 'AbortError') {
                        addLog({status: 'failed', message: 'Connection error', error: error.message});
                    }
                } finally {
                    input.disabled = false;
                    sendBtn.disabled = false;
                    input.focus();
                    document.getElementById('brainStatus').textContent = 'Ready';
                    document.getElementById('statusDot').style.background = '#00ff00';
                }
            }
            
            async function stopProcess() {
                if (currentController) {
                    currentController.abort();
                    currentController = null;
                }
                try {
                    await fetch('/stop', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user_id: userId, text: ''})
                    });
                    addLog({status: 'stopped', message: '⏹ Process stopped by user'});
                } catch (error) {
                    console.error('Stop error:', error);
                }
                document.getElementById('input').disabled = false;
                document.getElementById('sendBtn').disabled = false;
                document.getElementById('input').focus();
                document.getElementById('brainStatus').textContent = 'Ready';
                document.getElementById('statusDot').style.background = '#00ff00';
            }
            
            async function provideHelp() {
                const help = prompt('Provide guidance to help the brain:\\n\\nExamples:\\n- "use Tailwind CSS"\\n- "this is Nigerian Pidgin"\\n- "search for recent data"');
                if (!help) return;
                
                try {
                    const response = await fetch('/help', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({info: help, user_id: userId})
                    });
                    const data = await response.json();
                    addLog({status: 'building', message: `💡 Help provided: "${help}"`});
                } catch (error) {
                    console.error('Help error:', error);
                }
            }
            
            document.getElementById('input').addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
            
            // Focus input on load
            document.getElementById('input').focus();
            
            // Welcome message
            setTimeout(() => {
                addLog({
                    status: 'success', 
                    message: '🧠 UAI Brain is ready! Try: "code a webpage", "wetin dey", or "what is AI"'
                });
            }, 500);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)