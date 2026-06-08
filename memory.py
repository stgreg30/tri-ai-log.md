"""Supabase Memory - Shared brain for all AI agents"""
import os
from typing import Dict, List, Optional
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

class Memory:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "")
        self.key = os.getenv("SUPABASE_ANON_KEY", "")
        self.client = None
        self.local = {}
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                print("✅ Supabase connected")
            except Exception as e:
                print(f"⚠️ Supabase error: {e}")
    
    # ========== TRANSLATOR MEMORY ==========
    def save_translation_pair(self, english: str, machine: Dict, success: bool):
        """Translator learns from each translation"""
        if not self.client:
            self.local[f"trans_{len(self.local)}"] = {"en": english, "ml": machine, "ok": success}
            return
        try:
            self.client.table("translations").insert({
                "english": english,
                "machine": machine,
                "success": success
            }).execute()
        except: pass
    
    def get_translation_history(self, limit: int = 100) -> List[Dict]:
        if not self.client:
            return list(self.local.values())[-limit:]
        try:
            r = self.client.table("translations").select("*").order("created_at", desc=True).limit(limit).execute()
            return r.data or []
        except: return []
    
    # ========== FACTORY BRAIN MEMORY ==========
    def save_decision(self, decision: Dict):
        """Factory records its decisions to learn from"""
        if not self.client:
            self.local[f"dec_{len(self.local)}"] = decision
            return
        try:
            self.client.table("decisions").insert(decision).execute()
        except: pass
    
    def get_decisions(self, limit: int = 50) -> List[Dict]:
        if not self.client:
            return [v for k, v in self.local.items() if k.startswith("dec_")][-limit:]
        try:
            r = self.client.table("decisions").select("*").order("created_at", desc=True).limit(limit).execute()
            return r.data or []
        except: return []
    
    # ========== AGENT STORAGE ==========
    def save_agent(self, agent_id: str, data: Dict):
        if not self.client:
            self.local[f"agent_{agent_id}"] = data
            return
        try:
            existing = self.client.table("agents").select("id").eq("id", agent_id).execute()
            if existing.data:
                self.client.table("agents").update(data).eq("id", agent_id).execute()
            else:
                self.client.table("agents").insert({"id": agent_id, **data}).execute()
        except: pass
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        if not self.client:
            return self.local.get(f"agent_{agent_id}")
        try:
            r = self.client.table("agents").select("*").eq("id", agent_id).execute()
            return r.data[0] if r.data else None
        except: return None
    
    def all_agents(self) -> List[Dict]:
        if not self.client:
            return [v for k, v in self.local.items() if k.startswith("agent_")]
        try:
            r = self.client.table("agents").select("*").order("created_at", desc=False).execute()
            return r.data or []
        except: return []
    
    def delete_agent(self, agent_id: str):
        if not self.client:
            self.local.pop(f"agent_{agent_id}", None)
            return
        try:
            self.client.table("agents").delete().eq("id", agent_id).execute()
        except: pass
    
    # ========== FACTORY STATE ==========
    def save_state(self, state: Dict):
        if not self.client:
            self.local["factory_state"] = state
            return
        try:
            self.client.table("factory_state").upsert({"id": "main", **state}).execute()
        except: pass
    
    def get_state(self) -> Dict:
        if not self.client:
            return self.local.get("factory_state", {})
        try:
            r = self.client.table("factory_state").select("*").eq("id", "main").execute()
            return r.data[0] if r.data else {}
        except: return {}
    
    # ========== CONVERSATION HISTORY ==========
    def save_message(self, msg: Dict):
        if not self.client:
            key = f"msg_{msg.get('ts', 0)}"
            self.local[key] = msg
            return
        try:
            self.client.table("messages").insert(msg).execute()
        except: pass
    
    def get_messages(self, limit: int = 50) -> List[Dict]:
        if not self.client:
            msgs = [v for k, v in self.local.items() if k.startswith("msg_")]
            return sorted(msgs, key=lambda x: x.get("ts", 0))[-limit:]
        try:
            r = self.client.table("messages").select("*").order("ts", desc=True).limit(limit).execute()
            return list(reversed(r.data)) if r.data else []
        except: return []
