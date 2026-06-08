"""The Machine Language - What the Factory AI speaks"""
from dataclasses import dataclass, field
from typing import Dict, Any
import hashlib, time

# Machine opcodes
class OP:
    INIT = "INIT"
    PING = "PING"
    SPAWN = "SPAWN"
    KILL = "KILL"
    CLONE = "CLONE"
    TASK = "TASK"
    STOP = "STOP"
    LIST = "LIST"
    PEEK = "PEEK"
    RESULT = "RESULT"
    OK = "OK"
    ERR = "ERR"
    DATA = "DATA"
    INFO = "INFO"
    PLAN = "PLAN"      # Factory shares its plan
    THINK = "THINK"    # Factory is thinking
    LEARN = "LEARN"    # Factory learned something

# Agent types
class TYPE:
    HTTP = "HTTP"
    CODE = "CODE"
    SCRAPE = "SCRAPE"
    CALC = "CALC"
    TIMER = "TIMER"
    DATA = "DATA"

@dataclass
class Packet:
    """A machine language packet"""
    op: str
    payload: Dict = field(default_factory=dict)
    id: str = ""
    ts: float = 0.0
    
    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(f"{time.time()}{self.op}".encode()).hexdigest()[:8]
        if not self.ts:
            self.ts = time.time()
    
    def to_dict(self):
        return {"op": self.op, "payload": self.payload, "id": self.id, "ts": self.ts}
    
    @classmethod
    def from_dict(cls, d):
        return cls(op=d["op"], payload=d.get("payload", {}), id=d.get("id", ""), ts=d.get("ts", 0))