import sqlite3, json, os

class Memory:
    def __init__(self, path="memory.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("CREATE TABLE IF NOT EXISTS mem (user_id TEXT, key TEXT, value TEXT)")

    def add(self, user_id, key, value):
        self.conn.execute("INSERT INTO mem VALUES (?,?,?)", (user_id, key, json.dumps(value)))
        self.conn.commit()

    def get_all(self, user_id):
        rows = self.conn.execute("SELECT key, value FROM mem WHERE user_id=?", (user_id,)).fetchall()
        return [{"key": k, "value": json.loads(v)} for k,v in rows]
