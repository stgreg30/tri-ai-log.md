"""Pure machine language definitions - No English allowed here"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import hashlib
import time
from enum import IntEnum

class Opcode(IntEnum):
    """Machine operation codes - The ONLY language the Factory speaks"""
    # System
    INIT = 0x01
    SHUTDOWN = 0x02
    PING = 0x03
    
    # Agent lifecycle
    SPAWN = 0x10
    TERMINATE = 0x11
    CLONE = 0x12
    
    # Task management
    ASSIGN_TASK = 0x20
    CANCEL_TASK = 0x21
    
    # Queries
    LIST_AGENTS = 0x30
    QUERY_AGENT = 0x31
    QUERY_RESULT = 0x32
    
    # Responses
    ACK = 0x40
    NACK = 0x41
    DATA_RESPONSE = 0x42
    STATUS_RESPONSE = 0x43
    ERROR_RESPONSE = 0x44

class AgentType(IntEnum):
    """Types of sub-agents the Factory can create"""
    HTTP_FETCHER = 0x50      # Makes HTTP requests
    CODE_EXECUTOR = 0x51     # Runs Python code in sandbox
    DATA_PROCESSOR = 0x52    # Processes/transforms data
    FILE_HANDLER = 0x53      # File operations
    SCHEDULER = 0x54         # Timed task execution
    WEB_SCRAPER = 0x55       # Scrapes web pages
    CALCULATOR = 0x56        # Math operations
    TEXT_PROCESSOR = 0x57    # Text manipulation

@dataclass
class MachineInstruction:
    """Atomic machine instruction packet"""
    opcode: Opcode
    params: Dict[str, Any] = field(default_factory=dict)
    instruction_id: str = ""
    parent_id: str = ""
    timestamp: float = 0.0
    
    def __post_init__(self):
        if not self.instruction_id:
            raw = f"{time.time()}{self.opcode}{hashlib.md5(str(self.params).encode()).hexdigest()}"
            self.instruction_id = hashlib.sha256(raw.encode()).hexdigest()[:12]
        if not self.timestamp:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict:
        return {
            "opcode": int(self.opcode),
            "opcode_name": self.opcode.name,
            "params": self.params,
            "id": self.instruction_id,
            "parent": self.parent_id,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MachineInstruction':
        return cls(
            opcode=Opcode(data["opcode"]),
            params=data.get("params", {}),
            instruction_id=data.get("id", ""),
            parent_id=data.get("parent", ""),
            timestamp=data.get("timestamp", 0.0)
        )
