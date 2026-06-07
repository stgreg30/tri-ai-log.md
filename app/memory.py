import os
from supabase import create_client, Client

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
            client.table("memories").insert({
                "user_id": user_id,
                "key": key,
                "value": value
            }).execute()
        except Exception as e:
            print("memory add error:", e)

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
            return [{"key": r["key"], "value": r["value"], "ts": r["ts"]} for r in res.data]
        except Exception as e:
            print("memory get error:", e)
            return []