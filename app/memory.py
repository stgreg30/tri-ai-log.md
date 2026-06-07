import os
from supabase import create_client, Client
import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

class Memory:
    def add(self, user_id: str, key: str, value: dict):
        if not client:
            return
        try:
            # add timestamp in code for reliability
            payload = {
                "user_id": user_id,
                "key": key,
                "value": value,
                "ts": datetime.datetime.utcnow().isoformat()
            }
            client.table("memories").insert(payload).execute()
        except Exception as e:
            print(f"memory add error [{key}]:", e)

    def get_all(self, user_id: str):
        if not client:
            return []
        try:
            res = client.table("memories") \
               .select("key,value,ts") \
               .eq("user_id", user_id) \
               .order("ts", desc=True) \
               .limit(200) \
               .execute()
            return [{"key": r["key"], "value": r["value"], "ts": r.get("ts")} for r in res.data]
        except Exception as e:
            print("memory get error:", e)
            return []

    def get_latest(self, user_id: str, key: str):
        """Fast lookup for personal memory - new for tonight"""
        if not client:
            return None
        try:
            res = client.table("memories") \
               .select("value") \
               .eq("user_id", user_id) \
               .eq("key", key) \
               .order("ts", desc=True) \
               .limit(1) \
               .execute()
            return res.data[0]["value"] if res.data else None
        except Exception as e:
            print(f"memory get_latest error [{key}]:", e)
            return None