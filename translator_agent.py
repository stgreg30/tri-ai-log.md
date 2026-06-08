"""Translator AI Agent - Learns English↔Machine translation over time"""
import re, json, time
from typing import Dict, List, Tuple
from machine_language import Packet, OP, TYPE
from memory import Memory

class TranslatorAgent:
    """
    An AI agent that translates English to Machine and Machine to English.
    Learns from every translation to get better.
    Stores training data in Supabase.
    """
    
    def __init__(self, memory: Memory):
        self.mem = memory
        self.training_examples: List[Dict] = []
        self._load_training()
        self._init_patterns()
    
    def _load_training(self):
        """Load past training from memory"""
        self.training_examples = self.mem.get_training(limit=200)
        # Extract patterns from training
        self.learned_patterns = {}
        for ex in self.training_examples:
            key = ex.get("intent", "")
            if key:
                if key not in self.learned_patterns:
                    self.learned_patterns[key] = []
                self.learned_patterns[key].append(ex)
    
    def _init_patterns(self):
        """Base patterns - these improve over time"""
        self.patterns = {
            # Intent → (confidence, opcode, type_hint)
            "init": [
                (0.9, OP.INIT, None),
                (0.8, OP.PING, None),
            ],
            "spawn": [
                (0.95, OP.SPAWN, None),
            ],
            "kill": [
                (0.9, OP.KILL, None),
            ],
            "list": [
                (0.95, OP.LIST, None),
            ],
            "task": [
                (0.9, OP.DO, None),
            ],
            "peek": [
                (0.85, OP.PEEK, None),
            ],
            "clone": [
                (0.9, OP.CLONE, None),
            ],
            "ping": [
                (0.9, OP.PING, None),
            ],
        }
        
        self.agent_types = {
            "http": (0.9, TYPE.HTTP),
            "fetch": (0.85, TYPE.HTTP),
            "request": (0.8, TYPE.HTTP),
            "api": (0.8, TYPE.HTTP),
            "code": (0.9, TYPE.CODE),
            "python": (0.85, TYPE.CODE),
            "executor": (0.85, TYPE.CODE),
            "shell": (0.8, TYPE.CODE),
            "script": (0.8, TYPE.CODE),
            "scrape": (0.9, TYPE.SCRAPE),
            "scraper": (0.9, TYPE.SCRAPE),
            "crawl": (0.8, TYPE.SCRAPE),
            "calculator": (0.9, TYPE.CALC),
            "calc": (0.9, TYPE.CALC),
            "math": (0.8, TYPE.CALC),
            "timer": (0.9, TYPE.TIMER),
            "scheduler": (0.85, TYPE.TIMER),
            "delay": (0.8, TYPE.TIMER),
            "data": (0.8, TYPE.DATA),
            "processor": (0.8, TYPE.DATA),
        }
    
    def english_to_packet(self, text: str) -> Tuple[Packet, Dict]:
        """
        Translate English to Machine Packet.
        Returns (packet, metadata_for_learning)
        """
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        # Step 1: Detect intent
        detected_intent = None
        best_confidence = 0
        detected_op = OP.PING
        
        for intent, options in self.patterns.items():
            if intent in text_lower:
                for conf, op, hint in options:
                    if conf > best_confidence:
                        best_confidence = conf
                        detected_op = op
                        detected_intent = intent
        
        # Check learned patterns
        for intent, examples in self.learned_patterns.items():
            if intent in text_lower:
                avg_conf = sum(e.get("confidence", 0.5) for e in examples) / len(examples)
                if avg_conf > best_confidence:
                    best_confidence = avg_conf
                    detected_op = examples[0].get("opcode", OP.PING)
                    detected_intent = intent
        
        payload = {"raw_text": text}
        
        # Step 2: Extract agent type for spawn
        if detected_op == OP.SPAWN:
            agent_type = TYPE.CALC  # Default
            type_conf = 0.5
            for type_word, (conf, atype) in self.agent_types.items():
                if type_word in text_lower and conf > type_conf:
                    agent_type = atype
                    type_conf = conf
            payload["type"] = agent_type
        
        # Step 3: Extract agent ID
        for word in words:
            if word.startswith("ag_"):
                payload["id"] = word
                break
        
        # Step 4: Extract task data
        if detected_op == OP.DO:
            task = {}
            
            # URL detection
            for word in words:
                if word.startswith("http"):
                    task["url"] = word
                    task["method"] = "GET"
                    break
            
            # Code block detection
            if "```" in text or "code:" in text_lower:
                code = text
                if "```" in text:
                    parts = text.split("```")
                    if len(parts) >= 2:
                        code = parts[1]
                        if "\n" in code:
                            code = "\n".join(code.split("\n")[1:])
                elif "code:" in text_lower:
                    code = text[text_lower.find("code:")+5:].strip()
                task["code"] = code
                task["lang"] = "python"
            
            # Expression
            if "calc:" in text_lower or "calculate:" in text_lower:
                marker = "calc:" if "calc:" in text_lower else "calculate:"
                task["expr"] = text[text_lower.find(marker)+len(marker):].strip()
            
            # Selector for scrape
            if "selector:" in text_lower:
                task["selector"] = text[text_lower.find("selector:")+9:].strip().split()[0]
            
            payload["task"] = task if task else {"raw": text}
        
        # Step 5: Extract source for clone
        if detected_op == OP.CLONE:
            for word in words:
                if word.startswith("ag_"):
                    payload["from"] = word
                    break
        
        pkt = Packet(op=detected_op, payload=payload)
        
        # Metadata for learning
        learn_meta = {
            "intent": detected_intent,
            "confidence": best_confidence,
            "opcode": detected_op,
            "text": text,
            "words": words,
            "extracted_id": payload.get("id", payload.get("from", "")),
        }
        
        return pkt, learn_meta
    
    def packet_to_english(self, pkt: Packet) -> str:
        """Translate Machine Packet to English"""
        op = pkt.op
        p = pkt.payload
        
        if op == OP.OK:
            if "id" in p:
                caps = p.get("caps", [])
                return f"✅ Agent spawned: {p['id']}\n   Type: {p.get('type', '?')}\n   Can: {', '.join(caps)}"
            if "killed" in p:
                return f"🗑️ Terminated: {p['killed']}"
            if "new" in p:
                return f"📋 Cloned: {p['new']} (from {p.get('cloned_from', '?')})"
            if "status" in p:
                return f"🟢 System ready. Agents: {p.get('agents', 0)}"
            return f"✅ Done: {p}"
        
        elif op == OP.ERR:
            msg = p.get("msg", "error")
            aid = p.get("id", "")
            return f"❌ Error: {msg}" + (f" ({aid})" if aid else "")
        
        elif op == OP.DAT:
            if "agents" in p:
                agents = p["agents"]
                if not agents:
                    return "📋 No agents active. Create one with: create a calculator agent"
                lines = [f"📋 {p.get('count', len(agents))} Agents:"]
                for a in agents:
                    caps = a.get("caps", [])
                    lines.append(f"  • {a['id']} [{a.get('type', '?')}] - {a.get('status', '?')}")
                    if caps:
                        lines.append(f"    ↳ {', '.join(caps)}")
                return "\n".join(lines)
            
            if "ok" in p:
                if p["ok"]:
                    return f"✅ Task done in {p.get('time', 0):.2f}s\n📦 Result: {json.dumps(p.get('data'), indent=2)}"
                return f"❌ Task failed: {p.get('error', '?')}"
            
            if "last" in p:
                return f"📦 Last result: {json.dumps(p.get('last'), indent=2)}"
            
            return f"📦 Data: {json.dumps(p, indent=2)}"
        
        elif op == OP.INF:
            if "agent" in p:
                a = p["agent"]
                return f"📡 {a['id']}: type={a.get('type','?')} status={a.get('status','?')} runs={a.get('runs',0)}"
            return f"ℹ️ Status: {p.get('status','?')} | Agents: {p.get('agents','?')} | Runs: {p.get('runs','?')}"
        
        return f"📨 [{op}] {p}"
    
    def learn(self, english: str, pkt: Packet, success: bool, feedback: str = ""):
        """
        Learn from this translation to improve future ones.
        Called after every translation.
        """
        # Record translation
        record = {
            "id": pkt.id,
            "english": english,
            "opcode": pkt.op,
            "payload": pkt.payload,
            "success": success,
            "feedback": feedback,
            "ts": time.time()
        }
        self.mem.save_translation(record)
        
        # If successful, reinforce the patterns
        if success:
            intent = self._extract_intent(english)
            if intent:
                training = {
                    "id": pkt.id,
                    "intent": intent,
                    "english": english,
                    "opcode": pkt.op,
                    "confidence": 0.9,
                    "ts": time.time()
                }
                self.mem.save_training(training)
                
                # Update learned patterns
                if intent not in self.learned_patterns:
                    self.learned_patterns[intent] = []
                self.learned_patterns[intent].append(training)
                # Keep only recent
                self.learned_patterns[intent] = self.learned_patterns[intent][-20:]
        
        # If failed, lower confidence
        elif feedback:
            intent = self._extract_intent(english)
            if intent and intent in self.learned_patterns:
                for ex in self.learned_patterns[intent]:
                    ex["confidence"] = max(0.1, ex.get("confidence", 0.5) - 0.1)
    
    def _extract_intent(self, text: str) -> str:
        """Extract the intent keyword from text"""
        text_lower = text.lower()
        for intent in ["init", "spawn", "create", "kill", "terminate", "list",
                        "task", "run", "execute", "peek", "check", "clone",
                        "ping", "health", "status"]:
            if intent in text_lower:
                return intent
        return ""
    
    def get_stats(self) -> Dict:
        """Get translator learning stats"""
        translations = self.mem.get_translations(1000)
        training = self.mem.get_training(1000)
        return {
            "total_translations": len(translations),
            "training_examples": len(training),
            "learned_patterns": len(self.learned_patterns),
            "recent_success_rate": sum(1 for t in translations[-20:] if t.get("success")) / max(len(translations[-20:]), 1)
        }
