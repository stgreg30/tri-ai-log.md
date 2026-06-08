"""The Factory - Main AI Controller. Speaks ONLY machine language."""
import time
from typing import Dict, List
from machine_language import MachineInstruction, Opcode, AgentType
from sub_agents import SubAgent, create_agent

class Factory:
    """
    THE MAIN CONTROLLER
    - Receives MachineInstruction
    - Processes it
    - Returns MachineInstruction
    - NEVER sees or uses English
    """
    
    def __init__(self):
        self.agents: Dict[str, SubAgent] = {}
        self.agent_counter = 0
        self.system_status = "BOOTING"
        self.start_time = time.time()
        self.execution_log: List[Dict] = []
    
    def receive_instruction(self, instruction: MachineInstruction) -> MachineInstruction:
        """THE ONLY ENTRY POINT. Machine in, machine out."""
        self._log(f"RECEIVED: {instruction.opcode.name}", instruction)
        
        handler_map = {
            Opcode.INIT: self._handle_init,
            Opcode.SHUTDOWN: self._handle_shutdown,
            Opcode.PING: self._handle_ping,
            Opcode.SPAWN: self._handle_spawn,
            Opcode.TERMINATE: self._handle_terminate,
            Opcode.CLONE: self._handle_clone,
            Opcode.ASSIGN_TASK: self._handle_assign_task,
            Opcode.CANCEL_TASK: self._handle_cancel_task,
            Opcode.LIST_AGENTS: self._handle_list_agents,
            Opcode.QUERY_AGENT: self._handle_query_agent,
            Opcode.QUERY_RESULT: self._handle_query_result,
        }
        
        handler = handler_map.get(instruction.opcode, self._handle_unknown)
        response = handler(instruction)
        self._log(f"RESPONSE: {response.opcode.name}", response)
        return response
    
    def _handle_init(self, instr: MachineInstruction) -> MachineInstruction:
        self.system_status = "READY"
        return MachineInstruction(
            opcode=Opcode.ACK,
            params={
                "status": self.system_status,
                "uptime": time.time() - self.start_time,
                "agent_count": len(self.agents)
            }
        )
    
    def _handle_shutdown(self, instr: MachineInstruction) -> MachineInstruction:
        self.agents.clear()
        self.system_status = "SHUTDOWN"
        return MachineInstruction(
            opcode=Opcode.ACK,
            params={"status": "SHUTDOWN_COMPLETE"}
        )
    
    def _handle_ping(self, instr: MachineInstruction) -> MachineInstruction:
        return MachineInstruction(
            opcode=Opcode.STATUS_RESPONSE,
            params={
                "status": self.system_status,
                "agent_count": len(self.agents),
                "uptime": time.time() - self.start_time
            }
        )
    
    def _handle_spawn(self, instr: MachineInstruction) -> MachineInstruction:
        agent_type_val = instr.params.get("agent_type", int(AgentType.CALCULATOR))
        agent_type = AgentType(agent_type_val)
        config = instr.params.get("config", {})
        
        self.agent_counter += 1
        agent_id = f"agent_{self.agent_counter:06d}"
        
        agent = create_agent(agent_id, agent_type, config)
        self.agents[agent_id] = agent
        
        return MachineInstruction(
            opcode=Opcode.ACK,
            params={
                "agent_id": agent_id,
                "agent_type": agent_type.name,
                "agent_type_code": int(agent_type),
                "status": "SPAWNED",
                "capabilities": agent.get_capabilities()
            }
        )
    
    def _handle_terminate(self, instr: MachineInstruction) -> MachineInstruction:
        agent_id = instr.params.get("agent_id", "")
        if agent_id in self.agents:
            del self.agents[agent_id]
            return MachineInstruction(
                opcode=Opcode.ACK,
                params={"agent_id": agent_id, "status": "TERMINATED"}
            )
        return MachineInstruction(
            opcode=Opcode.NACK,
            params={"error": "AGENT_NOT_FOUND", "agent_id": agent_id}
        )
    
    def _handle_clone(self, instr: MachineInstruction) -> MachineInstruction:
        source_id = instr.params.get("source_agent_id", "")
        if source_id in self.agents:
            self.agent_counter += 1
            new_id = f"agent_{self.agent_counter:06d}"
            import copy
            self.agents[new_id] = copy.deepcopy(self.agents[source_id])
            self.agents[new_id].id = new_id
            return MachineInstruction(
                opcode=Opcode.ACK,
                params={"new_agent_id": new_id, "cloned_from": source_id}
            )
        return MachineInstruction(
            opcode=Opcode.NACK,
            params={"error": "SOURCE_NOT_FOUND", "agent_id": source_id}
        )
    
    def _handle_assign_task(self, instr: MachineInstruction) -> MachineInstruction:
        agent_id = instr.params.get("agent_id", "")
        task_data = instr.params.get("task", {})
        
        if agent_id not in self.agents:
            return MachineInstruction(
                opcode=Opcode.NACK,
                params={"error": "AGENT_NOT_FOUND", "agent_id": agent_id}
            )
        
        agent = self.agents[agent_id]
        result = agent.execute_task(task_data)
        
        return MachineInstruction(
            opcode=Opcode.DATA_RESPONSE,
            params={
                "agent_id": agent_id,
                "task_completed": result.get("success", False),
                "data": result.get("data", None),
                "error": result.get("error", None),
                "execution_time": result.get("execution_time", 0)
            }
        )
    
    def _handle_cancel_task(self, instr: MachineInstruction) -> MachineInstruction:
        agent_id = instr.params.get("agent_id", "")
        if agent_id in self.agents:
            self.agents[agent_id].cancel_task()
            return MachineInstruction(
                opcode=Opcode.ACK,
                params={"agent_id": agent_id, "status": "CANCELLED"}
            )
        return MachineInstruction(
            opcode=Opcode.NACK,
            params={"error": "AGENT_NOT_FOUND"}
        )
    
    def _handle_list_agents(self, instr: MachineInstruction) -> MachineInstruction:
        agents_data = []
        for aid, agent in self.agents.items():
            agents_data.append({
                "agent_id": aid,
                "type": agent.agent_type.name,
                "type_code": int(agent.agent_type),
                "status": agent.status,
                "created_at": agent.created_at,
                "capabilities": agent.get_capabilities()
            })
        
        return MachineInstruction(
            opcode=Opcode.DATA_RESPONSE,
            params={
                "agents": agents_data,
                "total_count": len(agents_data)
            }
        )
    
    def _handle_query_agent(self, instr: MachineInstruction) -> MachineInstruction:
        agent_id = instr.params.get("agent_id", "")
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            return MachineInstruction(
                opcode=Opcode.STATUS_RESPONSE,
                params={
                    "agent_id": agent_id,
                    "type": agent.agent_type.name,
                    "status": agent.status,
                    "config": agent.config,
                    "capabilities": agent.get_capabilities(),
                    "created_at": agent.created_at
                }
            )
        return MachineInstruction(
            opcode=Opcode.NACK,
            params={"error": "AGENT_NOT_FOUND"}
        )
    
    def _handle_query_result(self, instr: MachineInstruction) -> MachineInstruction:
        agent_id = instr.params.get("agent_id", "")
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            return MachineInstruction(
                opcode=Opcode.DATA_RESPONSE,
                params={
                    "agent_id": agent_id,
                    "last_result": agent.last_result
                }
            )
        return MachineInstruction(
            opcode=Opcode.NACK,
            params={"error": "AGENT_NOT_FOUND"}
        )
    
    def _handle_unknown(self, instr: MachineInstruction) -> MachineInstruction:
        return MachineInstruction(
            opcode=Opcode.ERROR_RESPONSE,
            params={"error": "UNKNOWN_OPCODE", "received": instr.opcode.name}
        )
    
    def _log(self, message: str, instruction: MachineInstruction):
        self.execution_log.append({
            "time": time.time(),
            "message": message,
            "instruction_id": instruction.instruction_id,
            "opcode": instruction.opcode.name
        })
        if len(self.execution_log) > 1000:
            self.execution_log = self.execution_log[-500:]