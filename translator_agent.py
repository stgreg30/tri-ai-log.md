"""
TRANSLATOR AI AGENT
- Knows English AND Machine language
- ONLY translates - no decisions about what to do
- Learns from every translation to get better
- Has memory of past translations
"""
import time as time_module
from typing import Dict
from machine_language import Packet, OP, TYPE
from memory import Memory

class TranslatorAgent:
    def __init__(self, memory: Memory):
        self.mem = memory
        self.name = "Translator"
        self.translation_count = 0
        self.learned_patterns = {}
        self._load_training()
        self._init_patterns()
    
    def _load_training(self):
        """Load past training from memory"""
        self.training_examples = self.mem.get_training(limit=200)
        self.learned_patterns = {}
        for ex in self.training_examples:
            key = ex.get("intent", "")
            if key:
                if key not in self.learned_patterns:
                    self.learned_patterns[key] = []
                self.learned_patterns[key].append(ex)
    
    def _init_patterns(self):
        """Base translation patterns"""
        self.patterns = {
            "init": [(0.9, OP.INIT, None), (0.8, OP.PING, None)],
            "spawn": [(0.95, OP.SPAWN, None)],
            "kill": [(0.9, OP.KILL, None)],
            "list": [(0.95, OP.LIST, None)],
            "task": [(0.9, OP.TASK, None)],
            "peek": [(0.85, OP.PEEK, None)],
            "clone": [(0.9, OP.CLONE, None)],
            "ping": [(0.9, OP.PING, None)],
        }
        
        self.agent_types = {
            "http": (0.9, TYPE.HTTP), "fetch": (0.85, TYPE.HTTP),
            "request": (0.8, TYPE.HTTP), "api": (0.8, TYPE.HTTP),
            "code": (0.9, TYPE.CODE), "python": (0.85, TYPE.CODE),
            "executor": (0.85, TYPE.CODE), "shell": (0.8, TYPE.CODE),
            "script": (0.8, TYPE.CODE), "scrape": (0.9, TYPE.SCRAPE),
            "scraper": (0.9, TYPE.SCRAPE), "crawl": (0.8, TYPE.SCRAPE),
            "calculator": (0.9, TYPE.CALC), "calc": (0.9, TYPE.CALC),
            "math": (0.8, TYPE.CALC), "timer": (0.9, TYPE.TIMER),
            "scheduler": (0.85, TYPE.TIMER), "delay": (0.8, TYPE.TIMER),
            "data": (0.8, TYPE.DATA), "processor": (0.8, TYPE.DATA),
        }
        
        self.en_to_op = {
            "init": OP.INIT, "start": OP.INIT, "boot": OP.INIT, "begin": OP.INIT,
            "ping": OP.PING, "health": OP.PING, "alive": OP.PING,
            "spawn": OP.SPAWN, "create": OP.SPAWN, "make": OP.SPAWN,
            "build": OP.SPAWN, "new": OP.SPAWN, "add": OP.SPAWN,
            "kill": OP.KILL, "terminate": OP.KILL, "destroy": OP.KILL,
            "remove": OP.KILL, "delete": OP.KILL, "drop": OP.KILL,
            "clone": OP.CLONE, "copy": OP.CLONE, "duplicate": OP.CLONE,
            "task": OP.TASK, "run": OP.TASK, "execute": OP.TASK,
            "do": OP.TASK, "tell": OP.TASK, "instruct": OP.TASK,
            "calculate": OP.TASK, "fetch": OP.TASK, "scrape": OP.TASK,
            "stop": OP.STOP, "cancel": OP.STOP, "halt": OP.STOP,
            "list": OP.LIST, "show": OP.LIST, "display": OP.LIST,
            "agents": OP.LIST, "who": OP.LIST,
            "peek": OP.PEEK, "check": OP.PEEK, "status": OP.PEEK,
            "inspect": OP.PEEK, "query": OP.PEEK,
            "result": OP.RESULT, "output": OP.RESULT, "last": OP.RESULT,
        }
    
    def translate_to_machine(self, english: str) -> Packet:
        """English → Machine Packet"""
        text = english.lower().strip()
        words = text.split()
        
        # Detect operation
        op = OP.PING
        detected_keyword = ""
        for word in words:
            if word in self.en_to_op:
                op = self.en_to_op[word]
                detected_keyword = word
                break
        
        for phrase, mapped_op in self.en_to_op.items():
            if phrase in text and len(phrase) > len(detected_keyword):
                op = mapped_op
                detected_keyword = phrase
        
        payload = {"english": english}
        
        # SPAWN - extract agent type
        if op == OP.SPAWN:
            agent_type = TYPE.CALC
            for word in words:
                if word in self.agent_types:
                    agent_type = self.agent_types[word][1]
                    break
            payload["type"] = agent_type
            payload["config"] = {}
        
        # TASK - extract agent and task details
        elif op == OP.TASK:
            for word in words:
                if word.startswith("ag_"):
                    payload["agent_id"] = word
                    break
            
            task = {}
            for word in words:
                if word.startswith("http"):
                    task["url"] = word
                    break
            
            if "```" in english:
                parts = english.split("```")
                if len(parts) >= 2:
                    code = parts[1]
                    if code.startswith("python"): code = code[6:]
                    elif code.startswith("bash"): code = code[4:]
                    task["code"] = code.strip()
                    task["lang"] = "python"
            
            for marker in ["calc:", "calculate:", "expr:", "solve:"]:
                if marker in text:
                    expr = text.split(marker, 1)[1].strip().split("\n")[0]
                    task["expr"] = expr
                    break
            
            if "selector:" in text:
                task["selector"] = text.split("selector:", 1)[1].strip().split()[0]
            
            payload["task"] = task if task else {"command": english}
        
        # KILL, PEEK, RESULT, STOP - extract agent_id
        elif op in [OP.KILL, OP.PEEK, OP.RESULT, OP.STOP]:
            for word in words:
                if word.startswith("ag_"):
                    payload["agent_id"] = word
                    break
        
        # CLONE - extract source_id
        elif op == OP.CLONE:
            for word in words:
                if word.startswith("ag_"):
                    payload["source_id"] = word
                    break
        
        pkt = Packet(op=op, payload=payload)
        self.mem.save_translation_pair(english, pkt.to_dict(), True)
        self.translation_count += 1
        return pkt
    
    def translate_to_english(self, pkt: Packet) -> str:
        """Machine Packet → English"""
        import json
        op = pkt.op
        p = pkt.payload
        
        if op == OP.OK:
            if "agent_id" in p:
                agent_type = p.get("type", "unknown")
                caps = p.get("caps", [])
                msg = f"✅ Created new {agent_type} agent: {p['agent_id']}"
                if caps:
                    msg += f"\n   It can: {', '.join(caps)}"
                return msg
            if "killed" in p:
                return f"🗑️ Agent {p['killed']} has been terminated."
            if "cloned" in p:
                return f"📋 Cloned {p.get('source', '?')} → {p['cloned']}"
            if "stopped" in p:
                return f"⏹️ Stopped agent: {p['stopped']}"
            return f"✅ Done: {p.get('msg', 'ok')}"
        
        elif op == OP.ERR:
            return f"❌ Error: {p.get('msg', 'something went wrong')}"
        
        elif op == OP.DATA:
            if "agents" in p:
                agents = p["agents"]
                if not agents:
                    return "📋 No active agents. Create one with: create a calculator agent"
                msg = f"📋 Active Agents ({len(agents)}):"
                for a in agents:
                    msg += f"\n  • {a['id']} [{a.get('type', '?')}] - {a.get('status', 'idle')}"
                return msg
            
            if "result" in p:
                return f"📦 Result:\n{json.dumps(p['result'], indent=2)}"
            
            if "ok" in p:
                if p["ok"]:
                    data = p.get("data", {})
                    return f"✅ Task done in {p.get('time', 0):.2f}s\n📦 Result: {json.dumps(data, indent=2)}"
                return f"❌ Task failed: {p.get('error', '?')}"
            
            return f"📦 {json.dumps(p, indent=2)}"
        
        elif op == OP.INFO:
            if "agent" in p:
                a = p["agent"]
                return f"📡 {a['id']}: type={a.get('type','?')} status={a.get('status','?')} runs={a.get('runs',0)}"
            return f"ℹ️ Factory is {p.get('status','?')} | {p.get('agents',0)} agents | {p.get('tasks',0)} tasks"
        
        elif op == OP.PLAN:
            return f"🧠 Factory plan: {p.get('plan', '')}"
        
        elif op == OP.THINK:
            return f"🤔 Factory thinking: {p.get('thought', '')}"
        
        elif op == OP.LEARN:
            return f"🧠 Factory learned: {p.get('insight', '')}"
        
        return f"📨 Machine response [{op}]: {json.dumps(p)}"
    
    def learn(self, english: str, pkt: Packet, success: bool, feedback: str = ""):
        """Learn from this translation to improve future ones"""
        record = {
            "id": pkt.id, "english": english, "opcode": pkt.op,
            "payload": pkt.payload, "success": success,
            "feedback": feedback, "ts": time_module.time()
        }
        self.mem.save_translation_pair(english, pkt.to_dict(), success)
        
        if success:
            intent = self._extract_intent(english)
            if intent:
                training = {
                    "id": pkt.id, "intent": intent, "english": english,
                    "opcode": pkt.op, "confidence": 0.9, "ts": time_module.time()
                }
                self.mem.save_training(training)
                if intent not in self.learned_patterns:
                    self.learned_patterns[intent] = []
                self.learned_patterns[intent].append(training)
                self.learned_patterns[intent] = self.learned_patterns[intent][-20:]
    
    def _extract_intent(self, text: str) -> str:
        text_lower = text.lower()
        for intent in ["init", "spawn", "create", "kill", "terminate", "list",
                        "task", "run", "execute", "peek", "check", "clone",
                        "ping", "health", "status"]:
            if intent in text_lower:
                return intent
        return ""
    
    def get_stats(self) -> Dict:
        translations = self.mem.get_translation_history(1000)
        training = self.mem.get_training(1000)
        return {
            "total_translations": len(translations),
            "training_examples": len(training),
            "learned_patterns": len(self.learned_patterns),
            "recent_success_rate": sum(1 for t in translations[-20:] if t.get("success")) / max(len(translations[-20:]), 1)
        }