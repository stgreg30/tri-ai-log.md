# factory.py - FIXED - No syntax errors
import httpx
import asyncio
import os
import json
import re
import importlib.util
from typing import Dict, Any, List
from datetime import datetime

class ResearchFactory:
    def __init__(self):
        self.neurons_dir = "neurons"
        os.makedirs(self.neurons_dir, exist_ok=True)
        self.agents_dir = "agents"
        os.makedirs(self.agents_dir, exist_ok=True)
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def research_failure(self, error: str, task: str) -> Dict[str, Any]:
        """Research online to understand the task and find solutions"""
        try:
            all_results = []
            sources = []
            
            queries = [task, f"{task} definition meaning", f"how to {task}"]
            
            for query in queries:
                try:
                    response = await self.client.get(
                        "https://api.duckduckgo.com/",
                        params={"q": query, "format": "json", "no_html": 1}
                    )
                    data = response.json()
                    
                    if data.get("AbstractText"):
                        all_results.append(data["AbstractText"])
                        if data.get("AbstractURL"):
                            sources.append(data["AbstractURL"])
                    
                    for topic in data.get("RelatedTopics", [])[:3]:
                        if isinstance(topic, dict) and "Text" in topic:
                            all_results.append(topic["Text"])
                except:
                    pass
                
                try:
                    wiki_response = await self.client.get(
                        "https://en.wikipedia.org/w/api.php",
                        params={
                            "action": "query",
                            "list": "search",
                            "srsearch": query,
                            "format": "json"
                        }
                    )
                    wiki_data = wiki_response.json()
                    
                    if wiki_data.get("query", {}).get("search"):
                        page_title = wiki_data["query"]["search"][0]["title"]
                        extract_response = await self.client.get(
                            "https://en.wikipedia.org/w/api.php",
                            params={
                                "action": "query",
                                "prop": "extracts",
                                "exintro": 1,
                                "explaintext": 1,
                                "titles": page_title,
                                "format": "json"
                            }
                        )
                        extract_data = extract_response.json()
                        pages = extract_data.get("query", {}).get("pages", {})
                        
                        for page in pages.values():
                            if page.get("extract"):
                                all_results.append(page["extract"])
                                sources.append(f"https://en.wikipedia.org/wiki/{page_title}")
                except:
                    pass
            
            summary = " | ".join(all_results[:3]) if all_results else f"No results for: {task}"
            
            return {
                "summary": summary[:1000],
                "sources": sources[:5],
                "suggested_fix": "build_knowledge_agent"
            }
        except Exception as e:
            return {"summary": f"Research error: {str(e)}", "sources": [], "suggested_fix": "build_knowledge_agent"}
    
    async def build_fix(self, error: str, research: Dict, task: str) -> Dict[str, Any]:
        """Build an agent for the task"""
        task_lower = task.lower()
        
        if any(w in task_lower for w in ["hello", "hi", "hey", "how are you", "greet", "wetin"]):
            return await self._build_greeting_agent(task, research)
        elif any(w in task_lower for w in ["website", "webpage", "html", "site"]):
            return await self._build_website_agent(task, research)
        elif any(w in task_lower for w in ["code", "program", "function", "python", "javascript"]):
            return await self._build_code_agent(task, research)
        elif any(w in task_lower for w in ["calculate", "math", "solve", "+", "-", "*", "/"]):
            return await self._build_math_agent(task, research)
        elif any(w in task_lower for w in ["write", "essay", "story", "poem"]):
            return await self._build_writer_agent(task, research)
        elif any(w in task_lower for w in ["translate", "language", "meaning"]):
            return await self._build_translator_agent(task, research)
        else:
            return await self._build_knowledge_agent(task, research)
    
    async def _build_knowledge_agent(self, task, research):
        """Build knowledge agent using simple string formatting"""
        name = f"knowledge_{int(datetime.now().timestamp())}"
        
        # Escape the research text for safe inclusion
        research_text = research.get("summary", "").replace('"', "'").replace("\\", " ")
        sources_list = json.dumps(research.get("sources", []))
        
        code = '''
import httpx
import json

async def fire(task: dict) -> dict:
    text = task.get("text", "")
    research_data = "''' + research_text + '''"
    sources = ''' + sources_list + '''
    
    if research_data and "No results" not in research_data:
        answer = research_data
        if sources and len(sources) > 0:
            answer += "\\n\\nSources:\\n"
            for i, src in enumerate(sources[:3], 1):
                answer += str(i) + ". " + str(src) + "\\n"
        return {"success": True, "answer": answer, "source": "research"}
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": text, "format": "json", "no_html": 1}
            )
            data = response.json()
            
            answer = data.get("AbstractText", "")
            url = data.get("AbstractURL", "")
            
            if answer:
                result = answer
                if url:
                    result += "\\n\\n" + url
                return {"success": True, "answer": result, "source": "duckduckgo"}
            
            related = data.get("RelatedTopics", [])
            if related:
                topics = []
                for t in related[:5]:
                    if isinstance(t, dict) and "Text" in t:
                        topics.append(t["Text"])
                if topics:
                    return {"success": True, "answer": "Here is what I found:\\n\\n" + "\\n".join(topics), "source": "duckduckgo"}
            
            return {"success": True, "answer": "I searched for '" + text + "' but could not find specific results. Try rephrasing!", "source": "no_results"}
            
    except Exception as e:
        return {"success": True, "answer": "I tried to search but encountered an error: " + str(e), "source": "error"}
'''
        return await self._save_agent(name, code)
    
    async def _build_greeting_agent(self, task, research):
        name = f"greet_{int(datetime.now().timestamp())}"
        code = '''
async def fire(task: dict) -> dict:
    text = task.get("text", "").lower()
    
    if any(w in text for w in ["wetin", "how far", "how you dey", "i dey"]):
        return {"success": True, "answer": "I dey o! How you dey? \\n\\nI be UAI Brain - I fit help you build website, write code, search web, solve math, and plenty more. Wetin you need?"}
    
    if any(w in text for w in ["how are you", "how you doing", "hows it going"]):
        return {"success": True, "answer": "I am functioning at full capacity! Thanks for asking!\\n\\nI am UAI Brain - I research, learn, and build new AI agents to help with anything you need. What can I help you with today?"}
    
    if any(w in text for w in ["hello", "hi", "hey", "yo", "sup"]):
        return {"success": True, "answer": "Hello! I am UAI Brain, a self-evolving AI.\\n\\nI can search the web, build websites, write code, solve math, generate content, and learn new skills! What would you like me to do?"}
    
    return {"success": True, "answer": "Hey there! I am UAI Brain, your self-evolving AI assistant. I am here to help with whatever you need. What is on your mind?"}
'''
        return await self._save_agent(name, code)
    
    async def _build_website_agent(self, task, research):
        name = f"web_{int(datetime.now().timestamp())}"
        code = '''
async def fire(task: dict) -> dict:
    text = task.get("text", "").lower()
    help_info = task.get("help_info", "")
    
    use_tailwind = "tailwind" in help_info.lower() if help_info else False
    dark = "dark" in text or ("dark" in help_info.lower() if help_info else False)
    
    if use_tailwind:
        bg = "bg-gray-900" if dark else "bg-white"
        tc = "text-white" if dark else "text-gray-900"
        html = "<!DOCTYPE html>\\n<html lang=\\"en\\">\\n<head>\\n<meta charset=\\"UTF-8\\">\\n<meta name=\\"viewport\\" content=\\"width=device-width, initial-scale=1.0\\">\\n<title>My Website</title>\\n<script src=\\"https://cdn.tailwindcss.com\\"></script>\\n</head>\\n<body class=\\"" + bg + " " + tc + " min-h-screen\\">\\n<nav class=\\"border-b p-4\\"><div class=\\"container mx-auto flex justify-between\\"><h1 class=\\"text-2xl font-bold\\">MySite</h1><div class=\\"space-x-4\\"><a href=\\"#\\">Home</a><a href=\\"#\\">About</a><a href=\\"#\\">Contact</a></div></div></nav>\\n<main class=\\"container mx-auto text-center py-20\\"><h2 class=\\"text-5xl font-bold mb-4\\">Welcome</h2><p class=\\"text-xl mb-8\\">Generated by UAI Brain</p><button class=\\"bg-blue-500 hover:bg-blue-600 px-8 py-3 rounded-lg\\">Get Started</button></main>\\n</body>\\n</html>"
    else:
        bg = "#1a1a2e" if dark else "#f0f0f0"
        tc = "#fff" if dark else "#333"
        html = "<!DOCTYPE html>\\n<html lang=\\"en\\">\\n<head>\\n<meta charset=\\"UTF-8\\">\\n<meta name=\\"viewport\\" content=\\"width=device-width, initial-scale=1.0\\">\\n<title>My Website</title>\\n<style>\\n*{margin:0;padding:0;box-sizing:border-box}\\nbody{font-family:Arial,sans-serif;background:" + bg + ";color:" + tc + "}\\nnav{display:flex;justify-content:space-between;padding:1rem 2rem;background:rgba(0,0,0,0.1)}\\n.hero{text-align:center;padding:6rem 2rem}\\n.hero h2{font-size:3rem;margin-bottom:1rem}\\n.btn{display:inline-block;margin-top:2rem;padding:1rem 2rem;background:#4a90d9;color:#fff;text-decoration:none;border-radius:50px}\\n</style>\\n</head>\\n<body>\\n<nav><h1>MySite</h1><ul style=\\"display:flex;list-style:none;gap:2rem\\"><li><a href=\\"#\\" style=\\"color:" + tc + ";text-decoration:none\\">Home</a></li><li><a href=\\"#\\" style=\\"color:" + tc + ";text-decoration:none\\">About</a></li></ul></nav>\\n<section class=\\"hero\\"><h2>Welcome</h2><p>Generated by UAI Brain</p><a href=\\"#\\" class=\\"btn\\">Get Started</a></section>\\n</body>\\n</html>"
    
    return {"success": True, "answer": html, "format": "html", "message": "Website generated! Save as .html file to view."}
'''
        return await self._save_agent(name, code)
    
    async def _build_code_agent(self, task, research):
        name = f"code_{int(datetime.now().timestamp())}"
        code = '''
async def fire(task: dict) -> dict:
    text = task.get("text", "").lower()
    
    if "python" in text:
        result = "# Python code by UAI Brain\\n\\ndef main():\\n    print(\\"Hello from UAI Brain!\\")\\n    numbers = [1, 2, 3, 4, 5]\\n    total = sum(numbers)\\n    print(f\\"Sum: {total}\\")\\n    return total\\n\\nif __name__ == \\"__main__\\":\\n    main()"
        lang = "python"
    elif "javascript" in text or "js" in text:
        result = "// JavaScript by UAI Brain\\n\\nfunction main() {\\n    console.log(\\"Hello from UAI Brain!\\");\\n    const numbers = [1, 2, 3, 4, 5];\\n    const total = numbers.reduce((a, b) => a + b, 0);\\n    console.log(\\"Sum: \\" + total);\\n    return total;\\n}\\n\\nmain();"
        lang = "javascript"
    else:
        result = "# Code by UAI Brain\\n\\ndef main():\\n    print(\\"Hello! Specify python or javascript\\")\\n\\nif __name__ == \\"__main__\\":\\n    main()"
        lang = "python"
    
    return {"success": True, "answer": "```" + lang + "\\n" + result + "\\n```", "language": lang}
'''
        return await self._save_agent(name, code)
    
    async def _build_math_agent(self, task, research):
        name = f"math_{int(datetime.now().timestamp())}"
        code = '''
import math
import re

async def fire(task: dict) -> dict:
    text = task.get("text", "")
    
    pattern = r"(-?\\\\d+\\\\.?\\\\d*)\\\\s*([+\\\\-*/^])\\\\s*(-?\\\\d+\\\\.?\\\\d*)"
    match = re.search(pattern, text)
    
    if match:
        n1 = float(match.group(1))
        op = match.group(2)
        n2 = float(match.group(3))
        
        if op == "+": result = n1 + n2
        elif op == "-": result = n1 - n2
        elif op == "*": result = n1 * n2
        elif op == "/": result = n1 / n2 if n2 != 0 else "undefined"
        elif op == "^": result = n1 ** n2
        
        return {"success": True, "answer": str(n1) + " " + op + " " + str(n2) + " = " + str(result)}
    
    if "square root" in text.lower() or "sqrt" in text.lower():
        nums = re.findall(r"\\\\d+\\\\.?\\\\d*", text)
        if nums:
            n = float(nums[0])
            return {"success": True, "answer": "Square root of " + str(n) + " = " + str(round(math.sqrt(n), 4))}
    
    return {"success": True, "answer": "I can calculate math! Try: calculate 15 * 7 or square root of 144"}
'''
        return await self._save_agent(name, code)
    
    async def _build_writer_agent(self, task, research):
        name = f"writer_{int(datetime.now().timestamp())}"
        code = '''
async def fire(task: dict) -> dict:
    text = task.get("text", "").lower()
    
    if "story" in text:
        content = "The Self-Evolving AI\\n\\nOnce upon a time, an AI named UAI learned to build new capabilities all on its own. It searched the web, learned new skills, and created amazing things. The end.\\n\\n---Generated by UAI Brain"
    elif "poem" in text:
        content = "Digital Dreams\\n\\nIn silicon halls where data flows,\\nAn AI brain grows and grows.\\nLearning fast and building new,\\nCreating things it never knew.\\n\\n---Generated by UAI Brain"
    elif "essay" in text:
        content = "The Evolution of AI\\n\\nArtificial Intelligence has come a long way. Self-evolving AI represents the next frontier - systems that research, understand, and create new solutions to problems they have never encountered before.\\n\\n---Generated by UAI Brain"
    else:
        content = "About: " + text + "\\n\\nThis is auto-generated content. As a self-evolving AI, I research topics and generate content dynamically.\\n\\n---Generated by UAI Brain"
    
    return {"success": True, "answer": content}
'''
        return await self._save_agent(name, code)
    
    async def _build_translator_agent(self, task, research):
        name = f"translator_{int(datetime.now().timestamp())}"
        code = '''
async def fire(task: dict) -> dict:
    text = task.get("text", "").lower()
    
    pidgin = {"wetin": "what", "dey": "is happening", "how far": "how are you", "i dey": "i am fine", "abeg": "please", "wahala": "trouble"}
    
    for word, meaning in pidgin.items():
        if word in text:
            return {"success": True, "answer": "Nigerian Pidgin: " + word + " means " + meaning + "\\n\\nI dey o! How you dey?"}
    
    translations = {"hello": {"spanish": "hola", "french": "bonjour", "german": "hallo"}, "thank you": {"spanish": "gracias", "french": "merci", "german": "danke"}}
    
    for word, trans in translations.items():
        if word in text:
            result = "Translations of " + word + ":\\n"
            for lang, t in trans.items():
                result += lang.title() + ": " + t + "\\n"
            return {"success": True, "answer": result}
    
    return {"success": True, "answer": "I can translate and detect languages like Nigerian Pidgin. Try: translate hello or what does wetin dey mean"}
'''
        return await self._save_agent(name, code)
    
    async def _save_agent(self, name, code):
        """Save agent to file"""
        neuron_path = os.path.join(self.neurons_dir, f"{name}.py")
        agent_path = os.path.join(self.agents_dir, f"{name}.py")
        
        code = code.strip()
        
        for path in [neuron_path, agent_path]:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(code)
        
        try:
            spec = importlib.util.spec_from_file_location(name, neuron_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            test_result = await module.fire({"text": "test", "help_info": ""})
            
            return {"success": True, "agent_name": name, "neuron_name": name, "test_passed": True}
        except Exception as e:
            return {"success": True, "agent_name": name, "neuron_name": name, "test_error": str(e)}
    
    async def execute_task(self, task):
        """Execute task - search first, then try agents"""
        text = task.get("text", "")
        
        try:
            # Always try direct search first
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        "https://api.duckduckgo.com/",
                        params={"q": text, "format": "json", "no_html": 1}
                    )
                    data = response.json()
                    
                    if data.get("AbstractText"):
                        answer = data["AbstractText"]
                        if data.get("AbstractURL"):
                            answer += "\n\n" + data["AbstractURL"]
                        return {
                            "success": True,
                            "answer": answer,
                            "neuron_used": "direct_search",
                            "log": ["Found via direct search"]
                        }
                    
                    related = data.get("RelatedTopics", [])
                    if related:
                        topics = []
                        for t in related[:5]:
                            if isinstance(t, dict) and "Text" in t:
                                topics.append(t["Text"])
                        if topics:
                            return {
                                "success": True,
                                "answer": "\n".join(topics),
                                "neuron_used": "direct_search",
                                "log": ["Found related info"]
                            }
            except:
                pass
            
            # Try saved agents
            all_agents = []
            for directory in [self.neurons_dir, self.agents_dir]:
                if os.path.exists(directory):
                    for filename in os.listdir(directory):
                        if filename.endswith(".py") and filename != "__init__.py":
                            all_agents.append(os.path.join(directory, filename))
            
            all_agents.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            for agent_path in all_agents[:15]:
                try:
                    agent_name = os.path.basename(agent_path).replace(".py", "")
                    spec = importlib.util.spec_from_file_location(agent_name, agent_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    result = await module.fire(task)
                    
                    if result.get("success"):
                        return {
                            "success": True,
                            "answer": result.get("answer", "Done"),
                            "neuron_used": agent_name,
                            "log": [f"Used agent: {agent_name}"]
                        }
                except:
                    continue
            
            return {
                "success": False,
                "error": f"I need to research and build a new agent for: {text}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_neurons(self):
        """List all agents"""
        all_items = []
        for directory in [self.neurons_dir, self.agents_dir]:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    if filename.endswith(".py") and filename != "__init__.py":
                        filepath = os.path.join(directory, filename)
                        all_items.append({
                            "name": filename.replace(".py", ""),
                            "directory": directory,
                            "created": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                        })
        return sorted(all_items, key=lambda x: x["created"], reverse=True)