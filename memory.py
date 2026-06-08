import os
import json
from datetime import datetime
from typing import Dict, Any, List

class BrainMemory:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_key = os.getenv("SUPABASE_KEY", "")
        self.local_memory = []
        self.client = None
        
        if self.supabase_url and self.supabase_key:
            try:
                import httpx
                self.client = httpx.AsyncClient(
                    base_url=self.supabase_url,
                    headers={"apikey": self.supabase_key, "Authorization": f"Bearer {self.supabase_key}"}
                )
                print("Using Supabase memory")
            except:
                print("Using local memory")
        else:
            print("Using local memory (no Supabase configured)")
    
    async def store_success(self, task: str, user_id: str, neuron_name: str, answer: str):
        memory = {"type": "success", "task": task, "user_id": user_id, "neuron_name": neuron_name, "answer": answer, "timestamp": datetime.now().isoformat()}
        self.local_memory.append(memory)
        if len(self.local_memory) > 1000:
            self.local_memory = self.local_memory[-500:]
    
    async def store_learning(self, error: str, task: str, research: Dict, neuron_name: str, success: bool):
        memory = {"type": "learning", "error": error, "task": task, "neuron_name": neuron_name, "success": success, "timestamp": datetime.now().isoformat()}
        self.local_memory.append(memory)
    
    async def find_solution(self, task: str, user_id: str) -> Dict:
        for memory in reversed(self.local_memory):
            if memory.get("task") == task and memory.get("type") == "success":
                return memory
        return None
    
    async def get_user_memories(self, user_id: str) -> List[Dict]:
        return [m for m in self.local_memory if m.get("user_id") == user_id][-50:]