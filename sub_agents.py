"""Sub-agents with REAL capabilities - HTTP calls, code execution, etc."""
import time
import json
import subprocess
import tempfile
import os
from typing import Dict, Any, List
from machine_language import AgentType

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

class SubAgent:
    """Base agent with real execution capabilities"""
    
    def __init__(self, agent_id: str, agent_type: AgentType, config: Dict = None):
        self.id = agent_id
        self.agent_type = agent_type
        self.config = config or {}
        self.status = "IDLE"
        self.created_at = time.time()
        self.last_result = None
        self.execution_count = 0
    
    def get_capabilities(self) -> List[str]:
        """Override in subclasses"""
        return ["basic_execution"]
    
    def execute_task(self, task_data: Dict) -> Dict:
        """Execute a task and return results"""
        self.status = "RUNNING"
        start_time = time.time()
        
        try:
            result_data = self._execute(task_data)
            self.status = "IDLE"
            self.last_result = result_data
            self.execution_count += 1
            
            return {
                "success": True,
                "data": result_data,
                "execution_time": time.time() - start_time,
                "error": None
            }
        except Exception as e:
            self.status = "ERROR"
            return {
                "success": False,
                "data": None,
                "execution_time": time.time() - start_time,
                "error": str(e)
            }
    
    def _execute(self, task_data: Dict) -> Any:
        """Override in subclasses"""
        return {"message": "Base agent executed", "task": task_data}
    
    def cancel_task(self):
        self.status = "IDLE"


class HTTPFetcherAgent(SubAgent):
    """Makes real HTTP requests"""
    
    def __init__(self, agent_id: str, agent_type: AgentType, config: Dict = None):
        super().__init__(agent_id, agent_type, config)
    
    def get_capabilities(self):
        return ["http_get", "http_post", "fetch_json", "check_status"]
    
    def _execute(self, task_data: Dict) -> Any:
        if not requests:
            return {"error": "requests library not available"}
        
        url = task_data.get("url", "")
        method = task_data.get("method", "GET").upper()
        headers = task_data.get("headers", {})
        body = task_data.get("body", None)
        timeout = task_data.get("timeout", 10)
        
        if not url:
            return {"error": "No URL provided"}
        
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=body, timeout=timeout)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=timeout)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        result = {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "url": resp.url,
        }
        
        try:
            result["body"] = resp.json()
        except:
            result["body"] = resp.text[:5000]  # Truncate long responses
        
        return result


class WebScraperAgent(SubAgent):
    """Scrapes web pages"""
    
    def get_capabilities(self):
        return ["scrape_page", "extract_links", "extract_text", "extract_tables"]
    
    def _execute(self, task_data: Dict) -> Any:
        if not requests or not BeautifulSoup:
            return {"error": "requests or beautifulsoup4 not available"}
        
        url = task_data.get("url", "")
        extract_type = task_data.get("extract", "text")
        selector = task_data.get("selector", "body")
        
        resp = requests.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        if extract_type == "text":
            elements = soup.select(selector)
            return {"text": [el.get_text(strip=True) for el in elements]}
        elif extract_type == "links":
            links = soup.find_all('a')
            return {"links": [{"href": l.get('href'), "text": l.get_text(strip=True)} for l in links[:100]]}
        elif extract_type == "html":
            return {"html": str(soup.select_one(selector))}
        
        return {"data": "extraction complete"}


class CodeExecutorAgent(SubAgent):
    """Executes Python code in a sandboxed subprocess"""
    
    def get_capabilities(self):
        return ["execute_python", "execute_shell", "run_script"]
    
    def _execute(self, task_data: Dict) -> Any:
        language = task_data.get("language", "python")
        code = task_data.get("code", "")
        
        if not code:
            return {"error": "No code provided"}
        
        if language == "python":
            return self._execute_python(code)
        elif language == "shell":
            return self._execute_shell(code)
        else:
            return {"error": f"Unsupported language: {language}"}
    
    def _execute_python(self, code: str) -> Dict:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            result = subprocess.run(
                ['python3', temp_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out (30s limit)"}
        finally:
            os.unlink(temp_path)
    
    def _execute_shell(self, command: str) -> Dict:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out (30s limit)"}


class DataProcessorAgent(SubAgent):
    """Processes and transforms data"""
    
    def get_capabilities(self):
        return ["filter", "sort", "aggregate", "transform", "validate"]
    
    def _execute(self, task_data: Dict) -> Any:
        operation = task_data.get("operation", "filter")
        data = task_data.get("data", [])
        
        if operation == "filter":
            key = task_data.get("key", "")
            value = task_data.get("value", "")
            filtered = [item for item in data if str(item.get(key, "")) == str(value)]
            return {"filtered_data": filtered, "count": len(filtered)}
        
        elif operation == "sort":
            key = task_data.get("key", "")
            reverse = task_data.get("reverse", False)
            sorted_data = sorted(data, key=lambda x: x.get(key, ""), reverse=reverse)
            return {"sorted_data": sorted_data}
        
        elif operation == "count":
            return {"count": len(data)}
        
        elif operation == "unique":
            key = task_data.get("key", "")
            seen = set()
            unique = []
            for item in data:
                val = item.get(key, "")
                if val not in seen:
                    seen.add(val)
                    unique.append(item)
            return {"unique_data": unique, "count": len(unique)}
        
        return {"error": f"Unknown operation: {operation}"}


class CalculatorAgent(SubAgent):
    """Performs calculations"""
    
    def get_capabilities(self):
        return ["calculate", "convert", "statistics"]
    
    def _execute(self, task_data: Dict) -> Any:
        operation = task_data.get("operation", "eval")
        expression = task_data.get("expression", "")
        
        if operation == "eval":
            # Safe math evaluation
            import math
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("_")
            }
            allowed_names.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})
            
            try:
                result = eval(expression, {"__builtins__": {}}, allowed_names)
                return {"result": result, "expression": expression}
            except Exception as e:
                return {"error": str(e)}
        
        elif operation == "statistics":
            numbers = task_data.get("numbers", [])
            if not numbers:
                return {"error": "No numbers provided"}
            return {
                "sum": sum(numbers),
                "mean": sum(numbers) / len(numbers),
                "min": min(numbers),
                "max": max(numbers),
                "count": len(numbers)
            }
        
        return {"error": f"Unknown operation: {operation}"}


class SchedulerAgent(SubAgent):
    """Handles delayed/timed tasks"""
    
    def get_capabilities(self):
        return ["schedule", "delay", "repeat"]
    
    def _execute(self, task_data: Dict) -> Any:
        action = task_data.get("action", "delay")
        delay_seconds = task_data.get("delay", 1)
        message = task_data.get("message", "")
        
        if action == "delay":
            time.sleep(min(delay_seconds, 60))  # Max 60 second delay
            return {"message": f"Delayed {delay_seconds}s: {message}"}
        
        elif action == "timestamp":
            return {"timestamp": time.time(), "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        
        return {"error": f"Unknown action: {action}"}


def create_agent(agent_id: str, agent_type: AgentType, config: Dict = None) -> SubAgent:
    """Factory function to create the right agent type"""
    agent_map = {
        AgentType.HTTP_FETCHER: HTTPFetcherAgent,
        AgentType.CODE_EXECUTOR: CodeExecutorAgent,
        AgentType.DATA_PROCESSOR: DataProcessorAgent,
        AgentType.WEB_SCRAPER: WebScraperAgent,
        AgentType.CALCULATOR: CalculatorAgent,
        AgentType.SCHEDULER: SchedulerAgent,
    }
    
    agent_class = agent_map.get(agent_type, SubAgent)
    return agent_class(agent_id, agent_type, config)
