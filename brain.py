# brain.py - Main loop and FastAPI server
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import json
import time
import uuid
from datetime import datetime
import os

from factory import ResearchFactory
from memory import BrainMemory

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
    
    # Check memory for cached solution
    cached = await memory.find_solution(task, session.user_id)
    if cached:
        yield json.dumps({
            "attempt": 1,
            "status": "success",
            "message": "Found cached solution",
            "answer": cached["answer"],
            "neuron_used": cached["neuron_name"],
            "from_memory": True
        }) + "\n"
        return
    
    # Try processing
    while session.attempt <= session.max_attempts:
        if session.stop_requested:
            yield json.dumps({
                "attempt": session.attempt,
                "status": "stopped",
                "message": "Stopped by user"
            }) + "\n"
            return
            
        session.attempt += 1
        session.status = "processing"
        
        yield json.dumps({
            "attempt": session.attempt,
            "status": "processing",
            "message": f"Attempting to process: '{task}'"
        }) + "\n"
        
        try:
            # Try to understand and execute
            result = await factory.execute_task({
                "text": task,
                "help_info": session.help_info,
                "user_id": session.user_id
            })
            
            if result.get("success"):
                # Store in memory
                await memory.store_success(
                    task=task,
                    user_id=session.user_id,
                    neuron_name=result.get("neuron_used", "unknown"),
                    answer=result["answer"]
                )
                
                yield json.dumps({
                    "attempt": session.attempt,
                    "status": "success",
                    "message": "Task completed successfully",
                    "answer": result["answer"],
                    "neuron_used": result.get("neuron_used"),
                    "log": result.get("log", [])
                }) + "\n"
                return
            else:
                # Failure detected
                error = result.get("error", "Unknown error")
                yield json.dumps({
                    "attempt": session.attempt,
                    "status": "failed",
                    "message": f"Failed: {error}",
                    "error": error
                }) + "\n"
                
                if session.attempt <= session.max_attempts:
                    # Research the failure
                    yield json.dumps({
                        "attempt": session.attempt,
                        "status": "researching",
                        "message": f"Researching: {error}"
                    }) + "\n"
                    
                    research = await factory.research_failure(error, task)
                    
                    yield json.dumps({
                        "attempt": session.attempt,
                        "status": "researching",
                        "message": "Research complete",
                        "research_findings": research.get("summary"),
                        "sources": research.get("sources", [])
                    }) + "\n"
                    
                    # Build fix
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
                        
                        # Will retry in next loop iteration
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
                    "message": "Retrying after critical error..."
                }) + "\n"
                await asyncio.sleep(1)  # Brief pause before retry
                continue
            else:
                return
    
    yield json.dumps({
        "attempt": session.attempt,
        "status": "failed",
        "message": "Max attempts reached"
    }) + "\n"

@app.post("/think")
async def think(request: UserRequest):
    """Main endpoint for brain processing"""
    session_id = f"{request.user_id}_{int(time.time())}"
    session = BrainSession(request.user_id)
    active_sessions[session_id] = session
    
    return StreamingResponse(
        process_task(session, request.text),
        media_type="application/x-ndjson"
    )

@app.post("/stop")
async def stop(request: UserRequest):
    """Stop current processing"""
    # Find and stop active sessions for user
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
    """Provide help to guide the brain"""
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
        "message": "No active session found, but help stored for next request"
    }

@app.get("/memory/{user_id}")
async def get_memory(user_id: str):
    """View stored memories for a user"""
    memories = await memory.get_user_memories(user_id)
    return {"user_id": user_id, "memories": memories}

@app.get("/neurons")
async def list_neurons():
    """List all built neurons"""
    neurons = await factory.list_neurons()
    return {"neurons": neurons}

@app.get("/")
async def root():
    """Serve the chat interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>UAI - Self-Evolving Brain</title>
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
            #header h1 { color: #00ff00; font-size: 24px; }
            #header p { color: #008800; font-size: 14px; margin-top: 5px; }
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
            }
            .log-entry.success { border-color: #00ff00; }
            .log-entry.failed { border-color: #ff0000; }
            .log-entry.researching { border-color: #ffaa00; }
            .log-entry.building { border-color: #00aaff; }
            .log-entry.retrying { border-color: #ff00ff; }
            .log-entry.stopped { border-color: #888888; }
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
            button {
                padding: 10px 20px;
                background: #003300;
                border: 1px solid #00ff00;
                color: #00ff00;
                cursor: pointer;
                font-family: inherit;
                font-size: 16px;
            }
            button:hover { background: #004400; }
            button.stop { background: #330000; border-color: #ff0000; color: #ff0000; }
            button.stop:hover { background: #440000; }
            button.help { background: #003333; border-color: #00aaff; color: #00aaff; }
            button.help:hover { background: #004444; }
        </style>
    </head>
    <body>
        <div id="header">
            <h1>🧠 UAI - Self-Evolving Brain</h1>
            <p>Visible failure loop | Auto-research | Self-building neurons</p>
        </div>
        <div id="log"></div>
        <div id="controls">
            <input type="text" id="input" placeholder="Ask anything..." />
            <button onclick="sendMessage()">Send</button>
            <button class="stop" onclick="stopProcess()">Stop</button>
            <button class="help" onclick="provideHelp()">Help</button>
        </div>
        
        <script>
            let currentController = null;
            const userId = 'user_' + Math.random().toString(36).substr(2, 9);
            
            function addLog(entry) {
                const log = document.getElementById('log');
                const div = document.createElement('div');
                div.className = 'log-entry ' + entry.status;
                const time = new Date().toLocaleTimeString();
                div.innerHTML = `
                    <span class="timestamp">[${time}]</span>
                    <span class="status">[${entry.status.toUpperCase()}]</span>
                    <span>${entry.message || ''}</span>
                    ${entry.answer ? '<div style="margin-top:10px;padding:10px;background:#0a0a0a;">' + entry.answer + '</div>' : ''}
                    ${entry.neuron_built ? '<div style="color:#00aaff;">🔧 Built: ' + entry.neuron_built + '</div>' : ''}
                    ${entry.error ? '<div style="color:#ff0000;">❌ ' + entry.error + '</div>' : ''}
                `;
                log.appendChild(div);
                log.scrollTop = log.scrollHeight;
            }
            
            async function sendMessage() {
                const input = document.getElementById('input');
                const text = input.value.trim();
                if (!text) return;
                
                input.value = '';
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
                            } catch (e) {
                                console.error('Parse error:', e);
                            }
                        }
                    }
                } catch (error) {
                    if (error.name !== 'AbortError') {
                        addLog({status: 'failed', message: 'Connection error', error: error.message});
                    }
                }
            }
            
            async function stopProcess() {
                if (currentController) {
                    currentController.abort();
                }
                try {
                    const response = await fetch('/stop', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user_id: userId, text: ''})
                    });
                    const data = await response.json();
                    addLog({status: 'stopped', message: 'Process stopped by user'});
                } catch (error) {
                    console.error('Stop error:', error);
                }
            }
            
            async function provideHelp() {
                const help = prompt('Enter help/guidance for the brain:');
                if (!help) return;
                
                try {
                    const response = await fetch('/help', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({info: help, user_id: userId})
                    });
                    const data = await response.json();
                    addLog({status: 'building', message: `Help provided: ${help}`});
                } catch (error) {
                    console.error('Help error:', error);
                }
            }
            
            // Handle Enter key
            document.getElementById('input').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
