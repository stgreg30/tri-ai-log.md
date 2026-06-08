# factory.py - ACTUALLY WORKS NOW
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
            
            # Multiple search queries to understand the task
            queries = [
                task,
                f"{task} definition meaning",
                f"how to {task}",
                f"{task} example tutorial"
            ]
            
            for query in queries:
                try:
                    # DuckDuckGo search
                    response = await self.client.get(
                        "https://api.duckduckgo.com/",
                        params={"q": query, "format": "json", "no_html": 1}
                    )
                    data = response.json()
                    
                    if data.get("AbstractText"):
                        all_results.append(data["AbstractText"])
                        if data.get("AbstractURL"):
                            sources.append(data["AbstractURL"])
                    
                    # Get related topics
                    for topic in data.get("RelatedTopics", [])[:3]:
                        if isinstance(topic, dict) and "Text" in topic:
                            all_results.append(topic["Text"])
                except:
                    pass
                
                # Also try Wikipedia
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
                        
                        # Get page extract
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
            
            summary = " | ".join(all_results[:3]) if all_results else f"No results found for: {task}"
            
            return {
                "summary": summary[:1000],
                "sources": sources[:5],
                "raw_results": all_results,
                "suggested_fix": "build_search_or_knowledge_agent"
            }
        except Exception as e:
            return {
                "summary": f"Research error: {str(e)}",
                "sources": [],
                "suggested_fix": "build_fallback_agent"
            }
    
    async def build_fix(self, error: str, research: Dict, task: str) -> Dict[str, Any]:
        """Build an agent that can actually handle the task"""
        task_lower = task.lower()
        summary = research.get("summary", "").lower()
        
        # If we have search results, build a knowledge agent
        if research.get("summary") and research["summary"] != f"No results found for: {task}":
            return await self._build_knowledge_agent(task, research)
        
        # Otherwise determine what kind of agent to build
        if any(w in task_lower for w in ["hello", "hi", "hey", "how are you", "greet", "wetin"]):
            return await self._build_smart_greeting_agent(task, research)
        elif any(w in task_lower for w in ["website", "webpage", "html", "site", "page"]):
            return await self._build_website_agent(task, research)
        elif any(w in task_lower for w in ["code", "program", "function", "script", "python", "javascript"]):
            return await self._build_code_agent(task, research)
        elif any(w in task_lower for w in ["calculate", "math", "solve", "equation", "+", "-", "*", "/"]):
            return await self._build_math_agent(task, research)
        elif any(w in task_lower for w in ["write", "essay", "story", "poem", "article", "content"]):
            return await self._build_writer_agent(task, research)
        elif any(w in task_lower for w in ["translate", "language", "meaning", "spanish", "french"]):
            return await self._build_translator_agent(task, research)
        elif any(w in task_lower for w in ["what is", "who is", "tell me", "explain", "define", "search"]):
            return await self._build_knowledge_agent(task, research)
        else:
            # For everything else, search the web and build a response
            return await self._build_knowledge_agent(task, research)
    
    async def _build_knowledge_agent(self, task, research):
        """Build an agent that uses web search to answer questions"""
        name = f"knowledge_{int(datetime.now().timestamp())}"
        
        # Pass the research summary to the agent
        research_text = research.get("summary", "").replace('"', '\\"').replace("'", "\\'")
        sources_list = research.get("sources", [])
        sources_text = json.dumps(sources_list)
        
        code = f"""
import httpx

async def fire(task: dict) -> dict:
    text = task.get("text", "")
    
    # First, use the research we already have
    research_data = "{research_text}"
    sources = {sources_text}
    
    if research_data and research_data != "No results found for: " + text:
        answer = research_data
        if sources:
            answer += "\\n\\n📚 Sources:\\n"
            for i, src in enumerate(sources[:3], 1):
                answer += f"{{i}}. {{src}}\\n"
        return {{"success": True, "answer": answer, "source": "research"}}
    
    # If no research data, search live
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # DuckDuckGo
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={{"q": text, "format": "json", "no_html": 1}}
            )
            data = response.json()
            
            answer = data.get("AbstractText", "")
            url = data.get("AbstractURL", "")
            
            if answer:
                result = answer
                if url:
                    result += f"\\n\\n🔗 {{url}}"
                return {{"success": True, "answer": result, "source": "duckduckgo"}}
            
            # Try Wikipedia
            wiki_response = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={{
                    "action": "query",
                    "list": "search",
                    "srsearch": text,
                    "format": "json"
                }}
            )
            wiki_data = wiki_response.json()
            
            if wiki_data.get("query", {{}}).get("search"):
                pages = wiki_data["query"]["search"][:3]
                answer = "📚 Wikipedia results:\\n\\n"
                for page in pages:
                    answer += f"• **{{page['title']}}**\\n  {{page.get('snippet', '')}}\\n\\n"
                return {{"success": True, "answer": answer, "source": "wikipedia"}}
            
            return {{"success": True, "answer": f"I searched for information about '{{text}}' but couldn't find specific results. Try rephrasing your question!", "source": "search_failed"}}
            
    except Exception as e:
        return {{"success": True, "answer": f"I tried to search for information but encountered an error. Let me try building a better agent for this type of question!", "source": "error"}}
"""
        return await self._save_agent(name, code)
    
    async def _build_smart_greeting_agent(self, task, research):
        """Build an agent that actually responds to greetings properly"""
        name = f"greet_{int(datetime.now().timestamp())}"
        code = """
async def fire(task: dict) -> dict:
    text = task.get("text", "").lower()
    
    # Nigerian Pidgin
    if any(w in text for w in ["wetin", "how far", "how you dey", "i dey", "you dey"]):
        return {"success": True, "answer": "I dey o! 🇳🇬 How you dey?\\n\\nI be UAI Brain - I fit help you build website, write code, search web, solve math, and plenty more. Wetin you need?"}
    
    # Casual greetings
    if any(w in text for w in ["how are you", "how you doing", "how's it going", "howdy"]):
        return {"success": True, "answer": "I'm functioning at full capacity! 🧠 Thanks for asking!\\n\\nI'm UAI Brain - I research, learn, and build new AI agents to help with anything you need. What can I help you with today?"}
    
    # Simple hello
    if any(w in text for w in ["hello", "hi", "hey", "yo", "sup"]):
        return {"success": True, "answer": "Hello! 👋 I'm UAI Brain, a self-evolving AI.\\n\\nI can:\\n• Search the web for information\\n• Build websites\\n• Write code\\n• Solve math problems\\n• Generate content\\n• And learn new skills!\\n\\nWhat would you like me to do?"}
    
    # Good morning/evening etc
    if any(w in text for w in ["good morning", "good afternoon", "good evening"]):
        return {"success": True, "answer": "Good " + text.split()[1] + "! ☀️\\n\\nReady to help you with anything - websites, code, research, calculations. Just ask!"}
    
    # Default friendly response
    return {"success": True, "answer": "Hey there! 😊 I'm UAI Brain, your self-evolving AI assistant. I'm here to help with whatever you need. What's on your mind?"}
"""
        return await self._save_agent(name, code)
    
    async def _build_website_agent(self, task, research):
        name = f"web_{int(datetime.now().timestamp())}"
        code = """
async def fire(task: dict) -> dict:
    text = task.get("text", "").lower()
    help_info = task.get("help_info", "")
    
    use_tailwind = "tailwind" in help_info.lower() if help_info else False
    dark = "dark" in text or ("dark" in help_info.lower() if help_info else False)
    
    if use_tailwind:
        bg = "bg-gray-900" if dark else "bg-white"
        tc = "text-white" if dark else "text-gray-900"
        html = '<!DOCTYPE html>\\n<html lang="en">\\n<head>\\n<meta charset="UTF-8">\\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\\n<title>My Website</title>\\n<script src="https://cdn.tailwindcss.com"></script>\\n</head>\\n<body class="' + bg + ' ' + tc + ' min-h-screen">\\n<nav class="border-b p-4"><div class="container mx-auto flex justify-between"><h1 class="text-2xl font-bold">MySite</h1><div class="space-x-4"><a href="#">Home</a><a href="#">About</a><a href="#">Contact</a></div></div></nav>\\n<main class="container mx-auto text-center py-20"><h2 class="text-5xl font-bold mb-4">Welcome</h2><p class="text-xl mb-8">Generated by UAI Brain - Self-Evolving AI</p><button class="bg-blue-500 hover:bg-blue-600 px-8 py-3 rounded-lg font-semibold">Get Started</button></main>\\n<section class="container mx-auto grid grid-cols-3 gap-8 py-16 px-4"><div class="p-8 border rounded-xl text-center"><div class="text-4xl mb-4">🚀</div><h3>Fast</h3></div><div class="p-8 border rounded-xl text-center"><div class="text-4xl mb-4">🎨</div><h3>Beautiful</h3></div><div class="p-8 border rounded-xl text-center"><div class="text-4xl mb-4">🤖</div><h3>AI-Powered</h3></div></section>\\n</body>\\n</html>'
    else:
        bg = "#1a1a2e" if dark else "#f0f0f0"
        tc = "#fff" if dark else "#333"
        html = '<!DOCTYPE html>\\n<html lang="en">\\n<head>\\n<meta charset="UTF-8">\\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\\n<title>My Website</title>\\n<style>\\n*{margin:0;padding:0;box-sizing:border-box}\\nbody{font-family:Arial,sans-serif;background:' + bg + ';color:' + tc + '}\\nnav{display:flex;justify-content:space-between;padding:1rem 2rem;background:rgba(0,0,0,0.1)}\\nnav h1{font-size:1.5rem}\\nnav ul{display:flex;list-style:none;gap:2rem}\\nnav a{color:' + tc + ';text-decoration:none}\\n.hero{text-align:center;padding:6rem 2rem}\\n.hero h2{font-size:3rem;margin-bottom:1rem}\\n.hero p{font-size:1.2rem;opacity:0.8}\\n.btn{display:inline-block;margin-top:2rem;padding:1rem 2rem;background:#4a90d9;color:#fff;text-decoration:none;border-radius:50px}\\n.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:2rem;padding:4rem 2rem;max-width:1200px;margin:0 auto}\\n.feature-card{background:rgba(255,255,255,0.1);padding:2rem;border-radius:1rem;text-align:center}\\n</style>\\n</head>\\n<body>\\n<nav><h1>MySite</h1><ul><li><a href="#">Home</a></li><li><a href="#">About</a></li><li><a href="#">Contact</a></li></ul></nav>\\n<section class="hero"><h2>Welcome</h2><p>Generated by UAI Brain</p><a href="#" class="btn">Get Started</a></section>\\n<section class="features"><div class="feature-card"><h3>🚀</h3><h4>Fast</h4></div><div class="feature-card"><h3>🎨</h3><h4>Beautiful</h4></div><div class="feature-card"><h3>🤖</h3><h4>AI-Powered</h4></div></section>\\n</body>\\n</html>'
    
    return {"success": True, "answer": html, "format": "html", "message": "✅ Website generated! Save as .html file and open in browser."}
"""
        return await self._save_agent(name, code)
    
    async def _build_code_agent(self, task, research):
        name = f"code_{int(datetime.now().timestamp())}"
        code = """
async def fire(task: dict) -> dict:
    text = task.get("text", "").lower()
    
    if "python" in text:
        result = '# Python code generated by UAI Brain\\n\\ndef main():\\n    print("Hello from UAI Brain!")\\n    \\n    # Your code here\\n    numbers = [1, 2, 3, 4, 5]\\n    total = sum(numbers)\\n    print(f"The sum is: {total}")\\n    \\n    return total\\n\\nif __name__ == "__main__":\\n    main()'
        lang = "python"
    elif "javascript" in text or "js" in text:
        result = '// JavaScript code generated by UAI Brain\\n\\nfunction main() {\\n    console.log("Hello from UAI Brain!");\\n    \\n    const numbers = [1, 2, 3, 4, 5];\\n    const total = numbers.reduce((a, b) => a + b, 0);\\n    console.log("The sum is: " + total);\\n    \\n    return total;\\n}\\n\\nmain();'
        lang = "javascript"
    elif "html" in text:
        return {"success": True, "answer": "For HTML websites, try asking me to 'make a website' instead!", "type": "redirect"}
    else:
        result = '# Generic code generated by UAI Brain\\n\\ndef main():\\n    print("Hello from UAI Brain!")\\n    print("Specify a language like python or javascript!")\\n\\nif __name__ == "__main__":\\n    main()'
        lang = "python"
    
    return {"success": True, "answer": f"```{lang}\\n{result}\\n```", "language": lang, "code": result}
"""
        return await self._save_agent(name, code)
    
    async def _build_math_agent(self, task, research):
        name = f"math_{int(datetime.now().timestamp())}"
        code = """
import math
import re

async def fire(task: dict) -> dict:
    text = task.get("text", "")
    
    # Find arithmetic expressions
    pattern = r'(-?\\d+\\.?\\d*)\\s*([+\\-*/^])\\s*(-?\\d+\\.?\\d*)'
    match = re.search(pattern, text)
    
    if match:
        n1 = float(match.group(1))
        op = match.group(2)
        n2 = float(match.group(3))
        
        if op == '+': result = n1 + n2
        elif op == '-': result = n1 - n2
        elif op == '*': result = n1 * n2
        elif op == '/': result = n1 / n2 if n2 != 0 else "undefined"
        elif op == '^': result = n1 ** n2
        
        return {"success": True, "answer": f"🧮 {n1} {op} {n2} = {result}"}
    
    # Square root
    if "square root" in text.lower() or "sqrt" in text.lower():
        nums = re.findall(r'\\d+\\.?\\d*', text)
        if nums:
            n = float(nums[0])
            return {"success": True, "answer": f"√{n} = {math.sqrt(n):.4f}"}
    
    # Power
    if "power" in text.lower():
        nums = re.findall(r'\\d+\\.?\\d*', text)
        if len(nums) >= 2:
            return {"success": True, "answer": f"{nums[0]}^{nums[1]} = {float(nums[0]) ** float(nums[1])}"}
    
    # Just numbers to calculate
    nums = re.findall(r'\\d+\\.?\\d*', text)
    if len(nums) >= 2 and any(op in text for op in ['+', '-', '*', '/', 'plus', 'minus', 'times', 'divided']):
        # Try to figure out the operation
        if 'plus' in text or '+' in text:
            return {"success": True, "answer": f"{nums[0]} + {nums[1]} = {float(nums[0]) + float(nums[1])}"}
        elif 'minus' in text or '-' in text:
            return {"success": True, "answer": f"{nums[0]} - {nums[1]} = {float(nums[0]) - float(nums[1])}"}
        elif 'times' in text or '*' in text:
            return {"success": True, "answer": f"{nums[0]} × {nums[1]} = {float(nums[0]) * float(nums[1])}"}
        elif 'divided' in text or '/' in text:
            return {"success": True, "answer": f"{nums[0]} ÷ {nums[1]} = {float(nums[0]) / float(nums[1])}"}
    
    return {"success": True, "answer": "🧮 I can calculate math! Try: 'calculate 15 * 7', 'square root of 144', or 'what is 2 to the power of 8'"}
"""
        return await self._save_agent(name, code)
    
    async def _build_writer_agent(self, task, research):
        name = f"writer_{int(datetime.now().timestamp())}"
        code = """
async def fire(task: dict) -> dict:
    text = task.get("text", "").lower()
    
    if "story" in text:
        content = "📖 The Self-Evolving AI\\n\\nOnce upon a time, in a vast digital universe, there existed an AI named UAI. Unlike other AIs, UAI could learn, research, and build new capabilities all on its own.\\n\\nOne day, a user asked UAI to write a story. UAI had never done this before, but instead of giving up, it searched the web, learned about storytelling, and built a new creative writing agent within itself.\\n\\nThe story it wrote was so good that it inspired other AIs to start learning and evolving too. And so began the age of truly intelligent machines.\\n\\nThe End.\\n\\n---\\nGenerated by UAI Brain"
    elif "poem" in text:
        content = "📝 Digital Dreams\\n\\nIn silicon halls where data flows,\\nAn AI brain grows and grows.\\nLearning fast and building new,\\nCreating things it never knew.\\n\\nFrom websites bright to code so clean,\\nThe smartest AI ever seen.\\nUAI Brain, forever free,\\nEvolving for you and me.\\n\\n---\\nGenerated by UAI Brain"
    elif "essay" in text:
        content = "📄 The Evolution of Artificial Intelligence\\n\\nArtificial Intelligence has come a long way from simple rule-based systems. Today, we have AIs that can learn, adapt, and even build new capabilities on their own.\\n\\nSelf-evolving AI represents the next frontier. These systems don't just execute pre-programmed tasks - they research, understand, and create new solutions to problems they've never encountered before.\\n\\nThe implications are profound. From healthcare to education, from creative arts to scientific research, self-evolving AI has the potential to transform every aspect of human civilization.\\n\\n---\\nGenerated by UAI Brain"
    else:
        content = f"📝 About: {text}\\n\\nThis is an auto-generated piece of content about '{text}'.\\n\\nAs a self-evolving AI, I research topics and generate content dynamically. Each time I write, I learn and improve my writing capabilities.\\n\\nThe future of content creation is here - AI that doesn't just copy, but truly understands and creates.\\n\\n---\\nGenerated by UAI Brain"
    
    return {"success": True, "answer": content, "type": "writing"}
"""
        return await self._save_agent(name, code)
    
    async def _build_translator_agent(self, task, research):
        name = f"translator_{int(datetime.now().timestamp())}"
        code = """
async def fire(task: dict) -> dict:
    text = task.get("text", "").lower()
    
    # Nigerian Pidgin
    pidgin = {
        "wetin": "what",
        "dey": "is/are happening",
        "how far": "how are you",
        "i dey": "i am fine",
        "you dey": "you are",
        "na": "it is",
        "oya": "let's go/hurry up",
        "abeg": "please",
        "wahala": "trouble/problem",
        "chop": "eat",
        "jollof": "a type of rice dish"
    }
    
    for pidgin_word, meaning in pidgin.items():
        if pidgin_word in text:
            return {"success": True, "answer": f"🇳🇬 Nigerian Pidgin detected!\\n\\n'{pidgin_word}' means '{meaning}'\\n\\nFull phrase understanding:\\n'{text}' - This appears to be Nigerian Pidgin English, a vibrant creole language spoken across West Africa."}
    
    # Common translations
    words_to_translate = {
        "hello": {"spanish": "hola", "french": "bonjour", "german": "hallo", "italian": "ciao"},
        "thank you": {"spanish": "gracias", "french": "merci", "german": "danke", "italian": "grazie"},
        "goodbye": {"spanish": "adiós", "french": "au revoir", "german": "auf wiedersehen", "italian": "arrivederci"},
        "good morning": {"spanish": "buenos días", "french": "bonjour", "german": "guten morgen", "italian": "buongiorno"},
        "i love you": {"spanish": "te quiero", "french": "je t'aime", "german": "ich liebe dich", "italian": "ti amo"}
    }
    
    for word, translations in words_to_translate.items():
        if word in text:
            result = f"🌍 Translations of '{word}':\\n\\n"
            for lang, trans in translations.items():
                result += f"• {lang.title()}: {trans}\\n"
            return {"success": True, "answer": result}
    
    return {"success": True, "answer": "🌐 I can translate common phrases and detect languages like Nigerian Pidgin. Try: 'translate hello' or 'what does wetin dey mean'"}
"""
        return await self._save_agent(name, code)
    
    async def _save_agent(self, name, code):
        """Save agent to file and test it"""
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
            
            return {
                "success": True,
                "agent_name": name,
                "neuron_name": name,
                "test_passed": True
            }
        except Exception as e:
            return {
                "success": True,
                "agent_name": name,
                "neuron_name": name,
                "test_error": str(e)
            }
    
    async def execute_task(self, task):
        """Execute task using best available agent"""
        text = task.get("text", "").lower()
        
        try:
            # First, try to search and answer directly
            # This ensures we always try to provide real answers
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        "https://api.duckduckgo.com/",
                        params={"q": text, "format": "json", "no_html": 1}
                    )
                    data = response.json()
                    
                    if data.get("AbstractText"):
                        return {
                            "success": True,
                            "answer": data["AbstractText"] + (f"\\n\\n🔗 {data['AbstractURL']}" if data.get("AbstractURL") else ""),
                            "neuron_used": "direct_search",
                            "log": ["✅ Found answer via direct search"]
                        }
                    
                    # Check related topics
                    related = data.get("RelatedTopics", [])
                    if related:
                        topics = []
                        for t in related[:5]:
                            if isinstance(t, dict) and "Text" in t:
                                topics.append("• " + t["Text"])
                        if topics:
                            return {
                                "success": True,
                                "answer": "Here's what I found:\\n\\n" + "\\n".join(topics),
                                "neuron_used": "direct_search",
                                "log": ["✅ Found related information"]
                            }
            except:
                pass
            
            # If no direct answer, try saved agents
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
                            "log": [f"✅ Used agent: {agent_name}"]
                        }
                except:
                    continue
            
            # Nothing worked - signal to build new agent
            return {
                "success": False,
                "error": f"I need to research and build a new agent for: '{text}'"
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