"""
FACTORY AI AGENT - The Controller
- Only speaks Machine Language
- THINKS, PLANS, DECIDES
- Creates sub-agents to do work
- Orchestrates everything
- Learns from results
- Has memory via Supabase
"""
import time
from typing import Dict, List, Optional
from machine_language import Packet, OP, TYPE
from sub_agents import create_agent, SubAgent
from memory import Memory

class FactoryAgent:
    """
    THE BRAIN. The Controller.
    Speaks ONLY machine language.
    Makes all decisions about agent creation and task execution.
    """
    
    def __init__(self, memory: Memory):
        self.mem = memory
        self.name = "Factory"
        self.agents: Dict[str, SubAgent] = {}
        self.counter = 0
        self.status = "booting"
        self.started = time.time()
        self.total_tasks = 0
        self.thought_log: List[str] = []
        
        # The Factory's personality/strategy
        self.strategy = "eager"  # eager, cautious, balanced
        
        # Wake up - restore from memory
        self._boot()
    
    def _boot(self):
        """Restore state from memory on startup"""
        state = self.mem.get_state()
        if state:
            self.counter = state.get("counter", 0)
            self.total_tasks = state.get("tasks", 0)
            self.status = "ready"
        
        # Restore all agents
        for a in self.mem.all_agents():
            agent = create_agent(a["id"], a["type"])
            agent.status = a.get("status", "idle")
            agent.runs = a.get("runs", 0)
            self.agents[a["id"]] = agent
        
        self.status = "ready"
        self._think("Factory booted. Restored {} agents from memory.".format(len(self.agents)))
        self._save()
    
    def _think(self, thought: str):
        """The Factory thinks - records its thoughts"""
        self.thought_log.append(f"[{time.strftime('%H:%M:%S')}] {thought}")
        self.mem.save_decision({
            "type": "thought",
            "content": thought,
            "ts": time.time()
        })
        if len(self.thought_log) > 100:
            self.thought_log = self.thought_log[-50:]
    
    def _save(self):
        """Persist state"""
        self.mem.save_state({
            "status": self.status,
            "counter": self.counter,
            "tasks": self.total_tasks,
            "started": self.started,
            "strategy": self.strategy
        })
    
    def receive(self, pkt: Packet) -> Packet:
        """
        THE ONLY ENTRY POINT.
        Receives a machine Packet, THINKS about it,
        executes, returns machine Packet.
        """
        
        # Log what we received
        self._think(f"Received: [{pkt.op}] {pkt.payload}")
        
        # Route to handler
        handlers = {
            OP.INIT: self._handle_init,
            OP.PING: self._handle_ping,
            OP.SPAWN: self._handle_spawn,
            OP.KILL: self._handle_kill,
            OP.CLONE: self._handle_clone,
            OP.TASK: self._handle_task,
            OP.STOP: self._handle_stop,
            OP.LIST: self._handle_list,
            OP.PEEK: self._handle_peek,
            OP.RESULT: self._handle_result,
        }
        
        handler = handlers.get(pkt.op, self._handle_unknown)
        response = handler(pkt)
        
        self._save()
        return response
    
    def _handle_init(self, pkt: Packet) -> Packet:
        self.status = "ready"
        self._think("System initialized")
        return Packet(op=OP.OK, payload={
            "msg": "factory_ready",
            "status": "ready",
            "agents": len(self.agents)
        })
    
    def _handle_ping(self, pkt: Packet) -> Packet:
        return Packet(op=OP.INFO, payload={
            "status": self.status,
            "agents": len(self.agents),
            "tasks": self.total_tasks,
            "uptime": time.time() - self.started,
            "strategy": self.strategy
        })
    
    def _handle_spawn(self, pkt: Packet) -> Packet:
        """Create a new sub-agent - Factory decides what to create"""
        agent_type = pkt.payload.get("type", TYPE.CALC)
        config = pkt.payload.get("config", {})
        
        self.counter += 1
        agent_id = f"ag_{self.counter:05d}"
        
        # Factory THINKS about what it's creating
        self._think(f"Spawning new {agent_type} agent as {agent_id}")
        
        # Create the agent
        agent = create_agent(agent_id, agent_type)
        self.agents[agent_id] = agent
        
        # Save to memory
        self.mem.save_agent(agent_id, {
            "id": agent_id,
            "type": agent_type,
            "status": "idle",
            "caps": agent.caps(),
            "created": time.time(),
            "runs": 0,
            "config": config
        })
        
        self._think(f"Agent {agent_id} ready with capabilities: {agent.caps()}")
        
        return Packet(op=OP.OK, payload={
            "agent_id": agent_id,
            "type": agent_type,
            "caps": agent.caps(),
            "msg": "agent_created"
        })
    
    def _handle_kill(self, pkt: Packet) -> Packet:
        agent_id = pkt.payload.get("agent_id", "")
        if agent_id in self.agents:
            self._think(f"Terminating {agent_id}")
            del self.agents[agent_id]
            self.mem.delete_agent(agent_id)
            return Packet(op=OP.OK, payload={"killed": agent_id})
        return Packet(op=OP.ERR, payload={"msg": f"agent {agent_id} not found"})
    
    def _handle_clone(self, pkt: Packet) -> Packet:
        source = pkt.payload.get("source_id", "")
        if source in self.agents:
            self.counter += 1
            new_id = f"ag_{self.counter:05d}"
            import copy
            self.agents[new_id] = copy.deepcopy(self.agents[source])
            self.agents[new_id].id = new_id
            self._think(f"Cloned {source} → {new_id}")
            
            self.mem.save_agent(new_id, {
                "id": new_id,
                "type": self.agents[new_id].type,
                "status": "idle",
                "caps": self.agents[new_id].caps(),
                "created": time.time(),
                "runs": 0,
                "cloned_from": source
            })
            
            return Packet(op=OP.OK, payload={"cloned": new_id, "source": source})
        return Packet(op=OP.ERR, payload={"msg": f"source {source} not found"})
    
    def _handle_task(self, pkt: Packet) -> Packet:
        """Assign a task to an agent - Factory orchestrates this"""
        agent_id = pkt.payload.get("agent_id", "")
        task = pkt.payload.get("task", {})
        
        # If no specific agent, Factory DECIDES which agent to use
        if not agent_id:
            agent_id = self._decide_agent(task)
            if not agent_id:
                # Factory decides to CREATE a new agent
                self._think("No suitable agent found. Spawning calculator agent.")
                spawn_pkt = Packet(op=OP.SPAWN, payload={"type": TYPE.CALC})
                spawn_result = self._handle_spawn(spawn_pkt)
                agent_id = spawn_result.payload.get("agent_id", "")
                self._think(f"Created {agent_id} to handle the task")
        
        if agent_id not in self.agents:
            return Packet(op=OP.ERR, payload={"msg": f"agent {agent_id} not found"})
        
        agent = self.agents[agent_id]
        self._think(f"Assigning task to {agent_id}: {task}")
        
        # Execute
        result = agent.execute(task)
        self.total_tasks += 1
        
        # Update agent in memory
        self.mem.save_agent(agent_id, {
            "id": agent_id,
            "type": agent.type,
            "status": agent.status,
            "runs": agent.runs,
            "last_result": agent.last_result
        })
        
        if result.get("ok"):
            self._think(f"Task completed by {agent_id} in {result.get('time', 0):.2f}s")
        else:
            self._think(f"Task failed on {agent_id}: {result.get('error')}")
            # Factory LEARNS from failure
            self._learn_from_failure(agent_id, task, result.get("error"))
        
        return Packet(op=OP.DATA, payload={
            "agent": agent_id,
            "ok": result.get("ok"),
            "result": result.get("data"),
            "error": result.get("error"),
            "time": result.get("time", 0)
        })
    
    def _decide_agent(self, task: Dict) -> Optional[str]:
        """Factory's decision-making: which agent to use?"""
        # Find idle agents that match the task type
        for aid, agent in self.agents.items():
            if agent.status == "idle":
                return aid  # Return first available
        return None  # No agent available
    
    def _learn_from_failure(self, agent_id: str, task: Dict, error: str):
        """Factory learns from failures"""
        self._think(f"LEARNING: {agent_id} failed at {task}. Error: {error}")
        # In future: adjust strategy, retry with different agent, etc.
        self.mem.save_decision({
            "type": "failure_learn",
            "agent": agent_id,
            "task": task,
            "error": error,
            "ts": time.time()
        })
    
    def _handle_stop(self, pkt: Packet) -> Packet:
        agent_id = pkt.payload.get("agent_id", "")
        if agent_id in self.agents:
            self.agents[agent_id].status = "idle"
            return Packet(op=OP.OK, payload={"stopped": agent_id})
        return Packet(op=OP.ERR, payload={"msg": "not found"})
    
    def _handle_list(self, pkt: Packet) -> Packet:
        agents = self.mem.all_agents()
        self._think(f"Listing {len(agents)} agents")
        return Packet(op=OP.DATA, payload={"agents": agents})
    
    def _handle_peek(self, pkt: Packet) -> Packet:
        agent_id = pkt.payload.get("agent_id", "")
        data = self.mem.get_agent(agent_id)
        if data:
            return Packet(op=OP.INFO, payload={"agent": data})
        return Packet(op=OP.ERR, payload={"msg": "not found"})
    
    def _handle_result(self, pkt: Packet) -> Packet:
        agent_id = pkt.payload.get("agent_id", "")
        if agent_id in self.agents:
            return Packet(op=OP.DATA, payload={
                "agent": agent_id,
                "result": self.agents[agent_id].last_result
            })
        return Packet(op=OP.ERR, payload={"msg": "not found"})
    
    def _handle_unknown(self, pkt: Packet) -> Packet:
        self._think(f"Unknown opcode received: {pkt.op}")
        return Packet(op=OP.ERR, payload={"msg": f"unknown op: {pkt.op}"})
    
    def get_thoughts(self, limit: int = 20) -> List[str]:
        """Return the Factory's recent thoughts"""
        return self.thought_log[-limit:]
