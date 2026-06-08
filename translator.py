"""English ↔ Machine Language Translator - Pure translation, no logic"""
from machine_language import MachineInstruction, Opcode, AgentType

class Translator:
    """
    ONLY translates. No decisions, no logic.
    English → MachineInstruction → English
    """
    
    # Keyword mappings for English → Opcode
    INTENT_MAP = {
        "init": Opcode.INIT,
        "start": Opcode.INIT,
        "boot": Opcode.INIT,
        "initialize": Opcode.INIT,
        
        "spawn": Opcode.SPAWN,
        "create": Opcode.SPAWN,
        "make": Opcode.SPAWN,
        "new": Opcode.SPAWN,
        "build": Opcode.SPAWN,
        
        "kill": Opcode.TERMINATE,
        "terminate": Opcode.TERMINATE,
        "destroy": Opcode.TERMINATE,
        "remove": Opcode.TERMINATE,
        "delete": Opcode.TERMINATE,
        
        "list": Opcode.LIST_AGENTS,
        "show": Opcode.LIST_AGENTS,
        "agents": Opcode.LIST_AGENTS,
        "who": Opcode.LIST_AGENTS,
        
        "task": Opcode.ASSIGN_TASK,
        "run": Opcode.ASSIGN_TASK,
        "execute": Opcode.ASSIGN_TASK,
        "do": Opcode.ASSIGN_TASK,
        
        "status": Opcode.QUERY_AGENT,
        "check": Opcode.QUERY_AGENT,
        "query": Opcode.QUERY_AGENT,
        
        "result": Opcode.QUERY_RESULT,
        "output": Opcode.QUERY_RESULT,
        
        "clone": Opcode.CLONE,
        "copy": Opcode.CLONE,
        "duplicate": Opcode.CLONE,
        
        "ping": Opcode.PING,
        "health": Opcode.PING,
    }
    
    AGENT_TYPE_MAP = {
        "http": AgentType.HTTP_FETCHER,
        "fetcher": AgentType.HTTP_FETCHER,
        "fetch": AgentType.HTTP_FETCHER,
        "request": AgentType.HTTP_FETCHER,
        "api": AgentType.HTTP_FETCHER,
        
        "code": AgentType.CODE_EXECUTOR,
        "executor": AgentType.CODE_EXECUTOR,
        "python": AgentType.CODE_EXECUTOR,
        "script": AgentType.CODE_EXECUTOR,
        "shell": AgentType.CODE_EXECUTOR,
        
        "data": AgentType.DATA_PROCESSOR,
        "processor": AgentType.DATA_PROCESSOR,
        "process": AgentType.DATA_PROCESSOR,
        "filter": AgentType.DATA_PROCESSOR,
        
        "scraper": AgentType.WEB_SCRAPER,
        "scrape": AgentType.WEB_SCRAPER,
        "crawl": AgentType.WEB_SCRAPER,
        
        "calculator": AgentType.CALCULATOR,
        "calc": AgentType.CALCULATOR,
        "math": AgentType.CALCULATOR,
        "calculate": AgentType.CALCULATOR,
        
        "schedule": AgentType.SCHEDULER,
        "scheduler": AgentType.SCHEDULER,
        "timer": AgentType.SCHEDULER,
        "delay": AgentType.SCHEDULER,
    }
    
    def english_to_machine(self, text: str) -> MachineInstruction:
        """Convert English text to MachineInstruction"""
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        # Detect opcode
        opcode = Opcode.PING  # Default
        detected_intent = None
        for word in words:
            if word in self.INTENT_MAP:
                opcode = self.INTENT_MAP[word]
                detected_intent = word
                break
        
        params = {"original_text": text}
        
        # Extract agent type for spawn commands
        if opcode == Opcode.SPAWN:
            agent_type = AgentType.CALCULATOR  # Default
            for word in words:
                if word in self.AGENT_TYPE_MAP:
                    agent_type = self.AGENT_TYPE_MAP[word]
                    break
            params["agent_type"] = int(agent_type)
            params["config"] = {}
        
        # Extract agent_id for task/terminate/query
        for word in words:
            if word.startswith("agent_"):
                params["agent_id"] = word
                break
        
        # Extract task data for ASSIGN_TASK
        if opcode == Opcode.ASSIGN_TASK:
            task = {}
            
            # HTTP fetch
            if "url" in text_lower:
                for w in words:
                    if w.startswith("http"):
                        task["url"] = w
                        task["method"] = "GET"
                        break
            
            # Code execution
            if "code:" in text_lower:
                code_start = text_lower.find("code:") + 5
                code = text[code_start:].strip()
                task["code"] = code
                task["language"] = "python"
            
            # Calculation
            if "calculate:" in text_lower or "calc:" in text_lower:
                marker = "calculate:" if "calculate:" in text_lower else "calc:"
                expr_start = text_lower.find(marker) + len(marker)
                task["expression"] = text[expr_start:].strip()
                task["operation"] = "eval"
            
            params["task"] = task if task else {"description": text}
        
        return MachineInstruction(opcode=opcode, params=params)
    
    def machine_to_english(self, instruction: MachineInstruction) -> str:
        """Convert MachineInstruction response to English"""
        opcode = instruction.opcode
        params = instruction.params
        
        if opcode == Opcode.ACK:
            if "agent_id" in params:
                agent_type = params.get("agent_type", "unknown")
                agent_id = params.get("agent_id", "")
                caps = params.get("capabilities", [])
                return f"✅ Created {agent_type} agent: {agent_id}\n   Capabilities: {', '.join(caps)}"
            if params.get("status") == "TERMINATED":
                return f"🗑️ Terminated agent: {params.get('agent_id', 'unknown')}"
            if "new_agent_id" in params:
                return f"📋 Cloned agent. New ID: {params['new_agent_id']}"
            status = params.get("status", "ready")
            return f"🟢 Acknowledged. System status: {status}"
        
        elif opcode == Opcode.NACK:
            error = params.get("error", "Unknown error")
            agent_id = params.get("agent_id", "")
            return f"❌ Failed: {error}" + (f" (Agent: {agent_id})" if agent_id else "")
        
        elif opcode == Opcode.DATA_RESPONSE:
            if "agents" in params:
                agents = params["agents"]
                count = params.get("total_count", 0)
                if count == 0:
                    return "📋 No agents currently active."
                lines = [f"📋 Active Agents ({count}):"]
                for a in agents:
                    lines.append(f"  • {a['agent_id']} [{a['type']}] - {a['status']}")
                return "\n".join(lines)
            
            if "task_completed" in params:
                if params["task_completed"]:
                    data = params.get("data", {})
                    return f"✅ Task completed in {params['execution_time']:.2f}s\n📦 Result: {json.dumps(data, indent=2) if isinstance(data, dict) else data}"
                else:
                    return f"❌ Task failed: {params.get('error', 'Unknown error')}"
            
            return f"📦 Data: {params}"
        
        elif opcode == Opcode.STATUS_RESPONSE:
            if "agent_id" in params:
                return f"📡 Agent {params['agent_id']}: Type={params.get('type', '?')}, Status={params.get('status', '?')}"
            status = params.get("status", "?")
            count = params.get("agent_count", 0)
            uptime = params.get("uptime", 0)
            return f"🟢 System: {status} | Agents: {count} | Uptime: {uptime:.0f}s"
        
        elif opcode == Opcode.ERROR_RESPONSE:
            return f"⚠️ Error: {params.get('error', 'Unknown')}"
        
        return f"📨 Response: {opcode.name} - {params}"
    
    def translate_roundtrip(self, english: str, factory) -> str:
        """Full translation cycle"""
        # English → Machine
        machine_input = self.english_to_machine(english)
        
        # Machine → Factory → Machine
        machine_output = factory.receive_instruction(machine_input)
        
        # Machine → English
        return self.machine_to_english(machine_output)
