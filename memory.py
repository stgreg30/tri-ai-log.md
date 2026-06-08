# memory.py - Supabase memory system
import os
from datetime import datetime
from typing import Dict, Any, List
import httpx
import json

class BrainMemory:
    def __init__(self):
        # Use Supabase if configured, otherwise use local storage
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_key = os.getenv("SUPABASE_KEY", "")
        self.local_memory = []
        
        if self.supabase_url and self.supabase_key:
            self.client = httpx.AsyncClient(
                base_url=self.supabase_url,
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}"
                }
            )
        else:
            self.client = None
            print("⚠️  No Supabase configured, using local memory storage")
    
    async def store_success(self, task: str, user_id: str, neuron_name: str, answer: str):
        """Store successful task execution"""
        memory = {
            "type": "success",
            "task": task,
            "user_id": user_id,
            "neuron_name": neuron_name,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        }
        await self._save(memory)
    
    async def store_learning(self, error: str, task: str, research: Dict, neuron_name: str, success: bool):
        """Store learning from failure"""
        memory = {
            "type": "learning",
            "error": error,
            "task": task,
            "research_summary": research.get("summary", ""),
            "neuron_name": neuron_name,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        await self._save(memory)
    
    async def find_solution(self, task: str, user_id: str) -> Dict:
        """Try to find cached solution for task"""
        if self.client:
            try:
                response = await self.client.get(
                    f"/rest/v1/brain_memory",
                    params={
                        "task": f"eq.{task}",
                        "type": "eq.success",
                        "order": "timestamp.desc",
                        "limit": "1"
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        return data[0]
            except Exception as e:
                print(f"Supabase query error: {e}")
        
        # Check local memory
        for memory in reversed(self.local_memory):
            if memory.get("task") == task and memory.get("type") == "success":
                return memory
        
        return None
    
    async def get_user_memories(self, user_id: str) -> List[Dict]:
        """Get all memories for a user"""
        if self.client:
            try:
                response = await self.client.get(
                    f"/rest/v1/brain_memory",
                    params={
                        "user_id": f"eq.{user_id}",
                        "order": "timestamp.desc",
                        "limit": "50"
                    }
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                print(f"Supabase query error: {e}")
        
        # Return local memories
        return [m for m in self.local_memory if m.get("user_id") == user_id]
    
    async def _save(self, memory: Dict):
        """Save memory to Supabase or local storage"""
        if self.client:
            try:
                response = await self.client.post(
                    "/rest/v1/brain_memory",
                    json=memory
                )
                if response.status_code not in [200, 201]:
                    print(f"Supabase save error: {response.text}")
                    self.local_memory.append(memory)
            except Exception as e:
                print(f"Supabase connection error: {e}")
                self.local_memory.append(memory)
        else:
            self.local_memory.append(memory)
        
        # Keep local memory manageable
        if len(self.local_memory) > 1000:
            self.local_memory = self.local_memory[-500:]
    
    async def setup_supabase(self):
        """Create necessary tables in Supabase if they don't exist"""
        if not self.client:
            return
        
        # This would need to be run once to set up the schema
        # For now, we'll just log that Supabase is configured
        print("✅ Supabase memory system configured")
        
        # The SQL to run in Supabase dashboard:
        sql = """
        CREATE TABLE IF NOT EXISTS brain_memory (
            id SERIAL PRIMARY KEY,
            type VARCHAR(50),
            task TEXT,
            user_id VARCHAR(100),
            neuron_name VARCHAR(200),
            answer TEXT,
            error TEXT,
            research_summary TEXT,
            success BOOLEAN,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_task_type ON brain_memory(task, type);
        CREATE INDEX IF NOT EXISTS idx_user_id ON brain_memory(user_id);
        """
        print("Run this SQL in your Supabase dashboard:")
        print(sql)
