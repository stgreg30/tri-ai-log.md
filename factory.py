# factory.py - Research and neuron building
import httpx
import asyncio
import os
import json
import re
from typing import Dict, Any, List
from datetime import datetime
import subprocess
import sys
import importlib.util

class ResearchFactory:
    def __init__(self):
        self.neurons_dir = "neurons"
        os.makedirs(self.neurons_dir, exist_ok=True)
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def research_failure(self, error: str, task: str) -> Dict[str, Any]:
        """Research failure using DuckDuckGo and other free APIs"""
        try:
            # Search for error resolution
            search_query = f"{error} {task} how to fix"
            research_data = await self._search_web(search_query)
            
            # Also search for task understanding
            task_query = f"what does {task} mean"
            task_data = await self._search_web(task_query)
            
            return {
                "summary": research_data.get("summary", ""),
                "sources": research_data.get("sources", []),
                "suggested_fix": self._extract_solution(research_data, task_data),
                "task_understanding": task_data.get("summary", ""),
                "raw_research": research_data
            }
        except Exception as e:
            return {
                "summary": f"Research failed: {str(e)}",
                "sources": [],
                "suggested_fix": "Manual intervention needed",
                "error": str(e)
            }
    
    async def _search_web(self, query: str) -> Dict[str, Any]:
        """Search using DuckDuckGo Instant Answer API"""
        try:
            # Try DuckDuckGo Instant Answer API (no key needed)
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }
            
            response = await self.client.get(url, params=params)
            data = response.json()
            
            summary = data.get("AbstractText", "")
            sources = []
            
            if data.get("AbstractURL"):
                sources.append(data["AbstractURL"])
            
            # Get related topics
            related = []
            for topic in data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and "Text" in topic:
                    related.append(topic["Text"])
            
            if not summary and related:
                summary = " | ".join(related)
            
            # Fallback: try Wikipedia API
            if not summary:
                wiki_data = await self._search_wikipedia(query)
                if wiki_data:
                    summary = wiki_data.get("extract", "")
                    if wiki_data.get("url"):
                        sources.append(wiki_data["url"])
            
            return {
                "summary": summary or f"No results found for: {query}",
                "sources": sources,
                "related": related
            }
        except Exception as e:
            return {"summary": f"Search error: {str(e)}", "sources": [], "related": []}
    
    async def _search_wikipedia(self, query: str) -> Dict[str, Any]:
        """Fallback to Wikipedia API"""
        try:
            # Search for page
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json"
            }
            response = await self.client.get(search_url, params=params)
            data = response.json()
            
            if data.get("query", {}).get("search"):
                page_title = data["query"]["search"][0]["title"]
                
                # Get page extract
                extract_params = {
                    "action": "query",
                    "prop": "extracts",
                    "exintro": 1,
                    "explaintext": 1,
                    "titles": page_title,
                    "format": "json"
                }
                extract_response = await self.client.get(search_url, params=extract_params)
                extract_data = extract_response.json()
                
                pages = extract_data.get("query", {}).get("pages", {})
                for page_id, page in pages.items():
                    return {
                        "extract": page.get("extract", ""),
                        "url": f"https://en.wikipedia.org/wiki/{page_title}"
                    }
        except Exception:
            pass
        return {}
    
    def _extract_solution(self, research: Dict, task_research: Dict) -> str:
        """Extract potential solution from research data"""
        solutions = []
        
        if research.get("summary"):
            solutions.append(research["summary"])
        
        if task_research.get("summary"):
            solutions.append(task_research["summary"])
        
        # Look for code examples or implementation hints
        combined = " ".join(solutions)
        
        if "code" in combined.lower() or "function" in combined.lower():
            return "Implement as code execution function"
        elif "api" in combined.lower():
            return "Implement as API call function"
        elif "search" in combined.lower():
            return "Implement as search function"
        else:
            return "Implement as general processing function"
    
    async def build_fix(self, error: str, research: Dict, task: str) -> Dict[str, Any]:
        """Build neuron based on failure type"""
        neuron_type = self._determine_neuron_type(error, research)
        
        try:
            if neuron_type == "translator":
                return await self._build_translator(task, research)
            elif neuron_type == "capability":
                return await self._build_capability(task, research)
            elif neuron_type == "retry":
                return await self._build_retry(task, research)
            else:
                return await self._build_general(task, research)
        except Exception as e:
            return {
                "success": False,
                "error": f"Neuron build failed: {str(e)}",
                "neuron_type": neuron_type
            }
    
    def _determine_neuron_type(self, error: str, research: Dict) -> str:
        """Determine what type of neuron to build"""
        error_lower = error.lower()
        
        if any(word in error_lower for word in ["understand", "parse", "don't know", "cannot interpret"]):
            return "translator"
        elif any(word in error_lower for word in ["not found", "missing", "no capability", "cannot execute"]):
            return "capability"
        elif any(word in error_lower for word in ["timeout", "api error", "connection", "network"]):
            return "retry"
        else:
            return "general"
    
    async def _build_translator(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build translator neuron"""
        neuron_name = f"translator_{int(datetime.now().timestamp())}"
        code = f'''
"""Auto-generated Translator Neuron"""
import asyncio
import httpx

async def fire(task: dict) -> dict:
    """Translate user input to machine-readable format"""
    text = task.get("text", "").lower()
    
    # Research-based translations
    if "code" in text or "build" in text or "create" in text:
        if "webpage" in text or "website" in text:
            return {{
                "intent": "generate_code",
                "type": "html",
                "language": "html",
                "confidence": 0.9,
                "understood_as": "Generate HTML webpage"
            }}
        elif "app" in text or "application" in text:
            return {{
                "intent": "generate_code",
                "type": "application",
                "confidence": 0.85,
                "understood_as": "Generate application code"
            }}
        else:
            return {{
                "intent": "generate_code",
                "type": "general",
                "confidence": 0.7,
                "understood_as": "Generate code"
            }}
    
    elif "what is" in text or "who is" in text or "define" in text:
        return {{
            "intent": "search_knowledge",
            "query": text,
            "confidence": 0.9,
            "understood_as": "Search for information"
        }}
    
    elif "how to" in text or "tutorial" in text:
        return {{
            "intent": "get_tutorial",
            "topic": text,
            "confidence": 0.9,
            "understood_as": "Get tutorial/guide"
        }}
    
    elif "wetin" in text or "how far" in text:
        return {{
            "intent": "greeting",
            "meaning": "How are you?",
            "language": "pidgin",
            "confidence": 0.9,
            "understood_as": "Nigerian Pidgin greeting"
        }}
    
    # Fallback: search web for meaning
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={{"q": f"what does '{{text}}' mean", "format": "json"}}
            )
            data = response.json()
            abstract = data.get("AbstractText", "")
            
            return {{
                "intent": "search_knowledge",
                "query": text,
                "confidence": 0.4,
                "understood_as": abstract or "Unknown query",
                "research": abstract
            }}
    except:
        return {{
            "intent": "unknown",
            "query": text,
            "confidence": 0.2,
            "understood_as": "Could not understand"
        }}
'''
        return await self._save_neuron(neuron_name, code)
    
    async def _build_capability(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build capability neuron to execute tasks"""
        neuron_name = f"capability_{int(datetime.now().timestamp())}"
        
        # Analyze what capability is needed
        task_lower = task.lower()
        
        if "webpage" in task_lower or "html" in task_lower:
            code = f'''
"""Auto-generated Capability Neuron - HTML Generator"""
import asyncio

async def fire(task: dict) -> dict:
    """Generate HTML webpage"""
    help_info = task.get("help_info", "")
    framework = "vanilla"
    
    if "tailwind" in help_info.lower():
        framework = "tailwind"
    elif "bootstrap" in help_info.lower():
        framework = "bootstrap"
    
    if framework == "tailwind":
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Page</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <header class="text-center mb-12">
            <h1 class="text-4xl font-bold text-gray-800 mb-4">Welcome</h1>
            <p class="text-xl text-gray-600">Auto-generated webpage with Tailwind CSS</p>
        </header>
        <main class="max-w-4xl mx-auto">
            <div class="bg-white rounded-lg shadow-lg p-8 mb-8">
                <h2 class="text-2xl font-semibold mb-4">About This Page</h2>
                <p class="text-gray-700 mb-4">This webpage was automatically generated by the UAI Brain.</p>
                <button class="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 transition">
                    Get Started
                </button>
            </div>
        </main>
    </div>
</body>
</html>"""
    else:
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Page</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f0f0; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        p {{ color: #666; line-height: 1.6; }}
        .btn {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
        .btn:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome</h1>
        <p>This webpage was automatically generated by the UAI Brain.</p>
        <button class="btn">Get Started</button>
    </div>
</body>
</html>"""
    
    return {{
        "success": True,
        "result": html,
        "format": "html",
        "framework_used": framework
    }}
'''
        elif "search" in task_lower or "find" in task_lower:
            code = f'''
"""Auto-generated Capability Neuron - Search"""
import httpx

async def fire(task: dict) -> dict:
    """Search for information"""
    query = task.get("text", "")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.duckduckgo.com/",
            params={{"q": query, "format": "json"}}
        )
        data = response.json()
        
        result = {{
            "success": True,
            "answer": data.get("AbstractText", "No information found"),
            "source": data.get("AbstractURL", ""),
            "related": [t.get("Text", "") for t in data.get("RelatedTopics", [])[:3] if isinstance(t, dict)]
        }}
        return result
'''
        else:
            code = f'''
"""Auto-generated General Capability Neuron"""
import httpx

async def fire(task: dict) -> dict:
    """General task execution"""
    text = task.get("text", "")
    
    # Try to search and provide information
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.duckduckgo.com/",
            params={{"q": text, "format": "json"}}
        )
        data = response.json()
        
        return {{
            "success": True,
            "answer": data.get("AbstractText", f"I processed: {{text}}"),
            "source": data.get("AbstractURL", ""),
            "method": "web_search"
        }}
'''
        
        return await self._save_neuron(neuron_name, code)
    
    async def _build_retry(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build retry neuron with better error handling"""
        neuron_name = f"retry_{int(datetime.now().timestamp())}"
        code = f'''
"""Auto-generated Retry Neuron"""
import asyncio
import httpx
from typing import Dict, Any

async def fire(task: dict) -> dict:
    """Execute with retry logic"""
    max_retries = 3
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            # Add timeout and better error handling
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={{"q": task.get("text", ""), "format": "json"}}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {{
                        "success": True,
                        "answer": data.get("AbstractText", "Success"),
                        "attempt": attempt + 1
                    }}
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay * (2 ** attempt))
                        continue
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(base_delay * (2 ** attempt))
                continue
            return {{
                "success": False,
                "error": f"Failed after {{max_retries}} attempts: {{str(e)}}"
            }}
    
    return {{"success": False, "error": "Max retries exceeded"}}
'''
        return await self._save_neuron(neuron_name, code)
    
    async def _build_general(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build general purpose neuron"""
        neuron_name = f"general_{int(datetime.now().timestamp())}"
        code = f'''
"""Auto-generated General Neuron"""
async def fire(task: dict) -> dict:
    """General processing neuron"""
    return {{
        "success": True,
        "answer": f"Processed: {{task.get('text', '')}}",
        "method": "general_processing"
    }}
'''
        return await self._save_neuron(neuron_name, code)
    
    async def _save_neuron(self, name: str, code: str) -> Dict[str, Any]:
        """Save neuron to file and test it"""
        filepath = os.path.join(self.neurons_dir, f"{name}.py")
        
        # Clean up code indentation
        code = code.strip()
        
        with open(filepath, "w") as f:
            f.write(code)
        
        # Test the neuron
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Test fire function
            test_result = await module.fire({"text": "test", "help_info": ""})
            
            return {
                "success": True,
                "neuron_name": name,
                "filepath": filepath,
                "test_result": str(test_result)[:100],
                "code": code
            }
        except Exception as e:
            # If test fails, still save but mark as untested
            return {
                "success": True,
                "neuron_name": name,
                "filepath": filepath,
                "test_error": str(e),
                "code": code
            }
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Try to execute task using existing neurons"""
        # First, try to understand the task
        try:
            # Look for translator neurons
            translators = [f for f in os.listdir(self.neurons_dir) if f.startswith("translator_")]
            
            if translators:
                # Use most recent translator
                latest = sorted(translators)[-1]
                filepath = os.path.join(self.neurons_dir, latest)
                
                spec = importlib.util.spec_from_file_location(latest, filepath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                understanding = await module.fire(task)
                
                # If confidence is high, execute
                if understanding.get("confidence", 0) > 0.3:
                    # Look for capability neurons
                    capabilities = [f for f in os.listdir(self.neurons_dir) if f.startswith("capability_")]
                    
                    if capabilities:
                        latest_cap = sorted(capabilities)[-1]
                        cap_path = os.path.join(self.neurons_dir, latest_cap)
                        
                        cap_spec = importlib.util.spec_from_file_location(latest_cap, cap_path)
                        cap_module = importlib.util.module_from_spec(cap_spec)
                        cap_spec.loader.exec_module(cap_module)
                        
                        result = await cap_module.fire(task)
                        
                        return {
                            "success": True,
                            "answer": result.get("result") or result.get("answer", "Task completed"),
                            "neuron_used": f"{latest},{latest_cap}",
                            "understanding": understanding,
                            "log": ["Understood task", "Executed with capability neuron"]
                        }
                    
                    return {
                        "success": False,
                        "error": f"No capability for '{understanding.get('intent')}'",
                        "understanding": understanding
                    }
                
                return {
                    "success": False,
                    "error": f"Cannot parse '{task.get('text')}'",
                    "understanding": understanding
                }
            
            return {
                "success": False,
                "error": f"No translator available for '{task.get('text')}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}"
            }
    
    async def list_neurons(self) -> List[Dict]:
        """List all built neurons"""
        neurons = []
        for filename in os.listdir(self.neurons_dir):
            if filename.endswith(".py"):
                filepath = os.path.join(self.neurons_dir, filename)
                with open(filepath, "r") as f:
                    code = f.read()
                neurons.append({
                    "name": filename.replace(".py", ""),
                    "filepath": filepath,
                    "size": len(code),
                    "created": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                })
        return sorted(neurons, key=lambda x: x["created"], reverse=True)
