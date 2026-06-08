"""Sub-agents that the Factory creates and controls"""
import time, subprocess, tempfile, os
from typing import Dict, Any

try: import requests
except: requests = None
try: from bs4 import BeautifulSoup
except: BeautifulSoup = None

class SubAgent:
    def __init__(self, agent_id: str, agent_type: str):
        self.id = agent_id
        self.type = agent_type
        self.status = "idle"
        self.created = time.time()
        self.runs = 0
        self.last_result = None
    
    def caps(self):
        return ["execute"]
    
    def execute(self, task: Dict) -> Dict:
        self.status = "running"
        start = time.time()
        try:
            result = self._run(task)
            self.status = "idle"
            self.last_result = result
            self.runs += 1
            return {"ok": True, "data": result, "time": time.time() - start}
        except Exception as e:
            self.status = "error"
            return {"ok": False, "error": str(e), "time": time.time() - start}
    
    def _run(self, task: Dict) -> Any:
        return {"msg": "base agent"}

class HTTPAgent(SubAgent):
    def caps(self): return ["http_get", "http_post"]
    def _run(self, task):
        if not requests: return {"error": "requests not installed"}
        url = task.get("url", "https://httpbin.org/get")
        method = task.get("method", "GET").upper()
        if method == "GET":
            r = requests.get(url, timeout=10)
        elif method == "POST":
            r = requests.post(url, json=task.get("body", {}), timeout=10)
        else:
            return {"error": f"unsupported: {method}"}
        try: body = r.json()
        except: body = r.text[:2000]
        return {"status": r.status_code, "body": body}

class CodeAgent(SubAgent):
    def caps(self): return ["run_python", "run_shell"]
    def _run(self, task):
        code = task.get("code", "")
        lang = task.get("lang", "python")
        if not code: return {"error": "no code"}
        
        if lang == "python":
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                path = f.name
            try:
                r = subprocess.run(["python3", path], capture_output=True, text=True, timeout=30)
                return {"stdout": r.stdout, "stderr": r.stderr, "code": r.returncode}
            except subprocess.TimeoutExpired:
                return {"error": "timeout 30s"}
            finally: os.unlink(path)
        
        elif lang == "shell":
            try:
                r = subprocess.run(code, shell=True, capture_output=True, text=True, timeout=30)
                return {"stdout": r.stdout, "stderr": r.stderr, "code": r.returncode}
            except subprocess.TimeoutExpired:
                return {"error": "timeout 30s"}
        return {"error": "bad lang"}

class ScrapeAgent(SubAgent):
    def caps(self): return ["scrape", "extract_links"]
    def _run(self, task):
        if not requests or not BeautifulSoup: return {"error": "missing deps"}
        url = task.get("url", "")
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        sel = task.get("selector", "body")
        if task.get("extract") == "links":
            links = soup.find_all("a")[:30]
            return {"links": [{"href": a.get("href"), "text": a.get_text(strip=True)} for a in links]}
        return {"text": soup.select_one(sel).get_text(strip=True)[:2000] if soup.select_one(sel) else "not found"}

class CalcAgent(SubAgent):
    def caps(self): return ["calculate", "statistics"]
    def _run(self, task):
        import math
        expr = task.get("expr", "2+2")
        safe = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        safe.update(abs=abs, round=round, min=min, max=max, sum=sum, len=len)
        try:
            return {"result": eval(expr, {"__builtins__": {}}, safe)}
        except Exception as e:
            return {"error": str(e)}

class TimerAgent(SubAgent):
    def caps(self): return ["delay", "timestamp"]
    def _run(self, task):
        if task.get("action") == "delay":
            s = min(task.get("seconds", 1), 60)
            time.sleep(s)
            return {"delayed": s}
        return {"ts": time.time()}

def create_agent(agent_id: str, agent_type: str) -> SubAgent:
    m = {
        "HTTP": HTTPAgent, "CODE": CodeAgent, "SCRAPE": ScrapeAgent,
        "CALC": CalcAgent, "TIMER": TimerAgent, "DATA": SubAgent
    }
    cls = m.get(agent_type, SubAgent)
    return cls(agent_id, agent_type)