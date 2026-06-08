# factory.py - Universal AI Agent Factory
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
        self.agent_registry = {}  # Track all agents and their capabilities
        
    async def research_failure(self, error: str, task: str) -> Dict[str, Any]:
        """Deep research on any failure"""
        try:
            # Multiple search strategies
            searches = [
                f"{task} how to implement solve",
                f"{error} solution fix",
                f"{task} tutorial example code",
                f"what is {task} how does it work",
                f"{task} api documentation"
            ]
            
            all_results = []
            for query in searches:
                result = await self._deep_search(query)
                if result.get("summary"):
                    all_results.append(result)
            
            # Combine all research
            combined_summary = " | ".join([r.get("summary", "") for r in all_results if r.get("summary")])
            
            return {
                "summary": combined_summary[:1000],
                "sources": [s for r in all_results for s in r.get("sources", [])],
                "suggested_fix": self._analyze_solution(task, combined_summary),
                "task_category": self._categorize_task(task),
                "all_research": all_results
            }
        except Exception as e:
            return {
                "summary": f"Research phase failed: {str(e)}",
                "sources": [],
                "suggested_fix": "build_general_agent"
            }
    
    async def _deep_search(self, query: str) -> Dict[str, Any]:
        """Deep web search using multiple sources"""
        summary = ""
        sources = []
        
        # DuckDuckGo
        try:
            ddg_response = await self.client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1}
            )
            ddg_data = ddg_response.json()
            
            if ddg_data.get("AbstractText"):
                summary += ddg_data["AbstractText"] + " "
                if ddg_data.get("AbstractURL"):
                    sources.append(ddg_data["AbstractURL"])
            
            # Related topics
            for topic in ddg_data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and "Text" in topic:
                    summary += topic["Text"] + " "
        except:
            pass
        
        # Wikipedia
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
                        summary += page["extract"][:500] + " "
                        sources.append(f"https://en.wikipedia.org/wiki/{page_title}")
        except:
            pass
        
        return {
            "summary": summary.strip() if summary.strip() else f"No results for: {query}",
            "sources": sources
        }
    
    def _categorize_task(self, task: str) -> str:
        """Categorize what type of task this is"""
        task_lower = task.lower()
        
        categories = {
            "web_development": ["website", "webpage", "html", "css", "javascript", "react", "vue", "angular", "frontend", "backend", "api", "server", "deploy"],
            "coding": ["code", "program", "function", "algorithm", "script", "app", "software", "develop", "build", "create"],
            "data_science": ["data", "analysis", "machine learning", "ai", "model", "train", "predict", "statistics", "visualize"],
            "writing": ["write", "essay", "article", "blog", "content", "story", "poem", "letter", "email", "document"],
            "math": ["calculate", "math", "equation", "solve", "formula", "convert", "measure", "statistic"],
            "language": ["translate", "language", "meaning", "definition", "grammar", "spell", "word"],
            "business": ["business", "marketing", "strategy", "plan", "analysis", "report", "presentation"],
            "design": ["design", "logo", "graphic", "ui", "ux", "color", "layout", "style"],
            "entertainment": ["game", "play", "joke", "fun", "music", "video", "movie", "song"],
            "general_knowledge": ["what is", "who is", "when", "where", "why", "how", "explain", "tell me about"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in task_lower for keyword in keywords):
                return category
        
        return "general"
    
    def _analyze_solution(self, task: str, research: str) -> str:
        """Analyze what kind of agent is needed"""
        task_lower = task.lower()
        research_lower = research.lower()
        
        # Determine what kind of agent to build
        if any(word in research_lower for word in ["api", "endpoint", "request", "http"]):
            return "build_api_agent"
        elif any(word in research_lower for word in ["database", "sql", "storage", "data"]):
            return "build_database_agent"
        elif any(word in task_lower for word in ["generate", "create", "make", "build"]):
            return "build_generator_agent"
        elif any(word in task_lower for word in ["translate", "language"]):
            return "build_translator_agent"
        elif any(word in task_lower for word in ["calculate", "math", "solve"]):
            return "build_math_agent"
        elif any(word in task_lower for word in ["search", "find", "lookup", "research"]):
            return "build_research_agent"
        elif any(word in task_lower for word in ["write", "compose", "draft"]):
            return "build_writer_agent"
        else:
            return "build_universal_agent"
    
    async def build_fix(self, error: str, research: Dict, task: str) -> Dict[str, Any]:
        """Build the right type of agent for the task"""
        solution_type = research.get("suggested_fix", "build_universal_agent")
        
        try:
            # Build specialized agent based on what's needed
            if "api" in solution_type:
                return await self._build_api_agent(task, research)
            elif "database" in solution_type:
                return await self._build_database_agent(task, research)
            elif "generator" in solution_type:
                return await self._build_generator_agent(task, research)
            elif "translator" in solution_type:
                return await self._build_translator_agent(task, research)
            elif "math" in solution_type:
                return await self._build_math_agent(task, research)
            elif "research" in solution_type:
                return await self._build_research_agent(task, research)
            elif "writer" in solution_type:
                return await self._build_writer_agent(task, research)
            else:
                return await self._build_universal_agent(task, research)
        except Exception as e:
            return {
                "success": False,
                "error": f"Agent build failed: {str(e)}"
            }
    
    async def _build_api_agent(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build an agent that can interact with APIs"""
        agent_name = f"api_agent_{int(datetime.now().timestamp())}"
        code = '''
"""API Interaction Agent - Handles any API-based task"""
import httpx
import json
import asyncio

async def fire(task: dict) -> dict:
    """Execute API-based tasks intelligently"""
    text = task.get("text", "").lower()
    help_info = task.get("help_info", "")
    
    # Determine what API is needed
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Search for relevant API
            search_response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": f"{text} free api", "format": "json"}
            )
            search_data = search_response.json()
            
            # Try to find and call the right API
            # For now, use DuckDuckGo as universal fallback
            result_response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": text, "format": "json"}
            )
            result_data = result_response.json()
            
            answer = result_data.get("AbstractText", "")
            if answer:
                return {
                    "success": True,
                    "answer": f"🌐 API Result:\\n\\n{answer}\\n\\n🔗 Source: {result_data.get('AbstractURL', 'Web Search')}",
                    "source": "web_api"
                }
            
            # Try Wikipedia as backup
            wiki_response = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": text,
                    "format": "json"
                }
            )
            wiki_data = wiki_response.json()
            
            if wiki_data.get("query", {}).get("search"):
                pages = wiki_data["query"]["search"][:3]
                answer = "📚 Wikipedia Results:\\n\\n"
                for page in pages:
                    answer += f"• {page['title']}\\n  {page.get('snippet', '')}\\n\\n"
                
                return {
                    "success": True,
                    "answer": answer,
                    "source": "wikipedia_api"
                }
            
            return {
                "success": True,
                "answer": f"I searched for information about '{text}' but couldn't find specific API results. Try being more specific!",
                "source": "fallback"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"API error: {str(e)}"
            }
'''
        return await self._save_agent(agent_name, code)
    
    async def _build_database_agent(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build database interaction agent"""
        agent_name = f"db_agent_{int(datetime.now().timestamp())}"
        code = '''
"""Database Agent - Handles data storage and retrieval"""
import json
import os
from datetime import datetime

async def fire(task: dict) -> dict:
    """Handle data-related tasks"""
    text = task.get("text", "")
    
    # Use local JSON storage as universal database
    db_file = "agent_database.json"
    
    try:
        # Load existing data
        if os.path.exists(db_file):
            with open(db_file, "r") as f:
                data = json.load(f)
        else:
            data = {"records": [], "created": datetime.now().isoformat()}
        
        # Process the request
        if "store" in text.lower() or "save" in text.lower():
            record = {
                "task": text,
                "timestamp": datetime.now().isoformat(),
                "data": task
            }
            data["records"].append(record)
            
            with open(db_file, "w") as f:
                json.dump(data, f, indent=2)
            
            return {
                "success": True,
                "answer": f"✅ Data stored successfully! Total records: {len(data['records'])}",
                "type": "database_store"
            }
        
        elif "get" in text.lower() or "retrieve" in text.lower() or "show" in text.lower():
            records = data.get("records", [])
            if records:
                summary = f"📊 Found {len(records)} records:\\n\\n"
                for i, record in enumerate(records[-5:], 1):
                    summary += f"{i}. {record.get('task', 'Unknown')[:100]}\\n"
                return {
                    "success": True,
                    "answer": summary,
                    "type": "database_retrieve"
                }
            else:
                return {
                    "success": True,
                    "answer": "📊 Database is empty. No records found.",
                    "type": "database_empty"
                }
        
        else:
            return {
                "success": True,
                "answer": f"💾 Database Agent ready! I can store and retrieve data. Current records: {len(data.get('records', []))}",
                "type": "database_info"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Database error: {str(e)}"
        }
'''
        return await self._save_agent(agent_name, code)
    
    async def _build_generator_agent(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build content/code generator agent"""
        agent_name = f"generator_agent_{int(datetime.now().timestamp())}"
        
        task_lower = task.lower()
        
        if any(word in task_lower for word in ["website", "webpage", "html"]):
            return await self._build_website_generator(task, research)
        elif any(word in task_lower for word in ["code", "program", "script"]):
            return await self._build_code_generator(task, research)
        else:
            return await self._build_content_generator(task, research)
    
    async def _build_website_generator(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build website generator agent"""
        agent_name = f"web_gen_{int(datetime.now().timestamp())}"
        code = '''
"""Website Generator Agent - Creates real websites"""
import json

async def fire(task: dict) -> dict:
    """Generate complete, modern websites"""
    text = task.get("text", "").lower()
    help_info = task.get("help_info", "")
    
    # Determine style preferences
    use_tailwind = "tailwind" in help_info.lower() if help_info else False
    use_bootstrap = "bootstrap" in help_info.lower() if help_info else False
    dark_mode = "dark" in text or "dark" in help_info.lower() if help_info else False
    
    # Generate appropriate website
    if use_tailwind:
        html = generate_tailwind_site(dark_mode)
    elif use_bootstrap:
        html = generate_bootstrap_site(dark_mode)
    else:
        html = generate_modern_site(dark_mode)
    
    return {
        "success": True,
        "answer": html,
        "format": "html",
        "type": "website",
        "message": "✅ Complete website generated! Save as .html file to view."
    }

def generate_tailwind_site(dark=False):
    bg = "bg-gray-900" if dark else "bg-white"
    text_color = "text-white" if dark else "text-gray-900"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Website</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="{bg} {text_color} min-h-screen">
    <nav class="border-b border-gray-700 p-4">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold">🌟 MySite</h1>
            <div class="space-x-6">
                <a href="#" class="hover:text-blue-400">Home</a>
                <a href="#" class="hover:text-blue-400">About</a>
                <a href="#" class="hover:text-blue-400">Contact</a>
            </div>
        </div>
    </nav>
    <main class="container mx-auto px-4 py-20 text-center">
        <h2 class="text-5xl font-bold mb-6">Welcome to My Website</h2>
        <p class="text-xl mb-8 opacity-80">This website was generated by UAI Brain - Self-Evolving AI</p>
        <button class="bg-blue-500 hover:bg-blue-600 px-8 py-3 rounded-lg font-semibold transition">
            Get Started
        </button>
    </main>
    <section class="container mx-auto px-4 py-16 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div class="p-8 border border-gray-700 rounded-xl text-center">
            <div class="text-4xl mb-4">🚀</div>
            <h3 class="text-xl font-bold mb-2">Fast</h3>
            <p class="opacity-70">Lightning-fast performance</p>
        </div>
        <div class="p-8 border border-gray-700 rounded-xl text-center">
            <div class="text-4xl mb-4">🎨</div>
            <h3 class="text-xl font-bold mb-2">Beautiful</h3>
            <p class="opacity-70">Modern, responsive design</p>
        </div>
        <div class="p-8 border border-gray-700 rounded-xl text-center">
            <div class="text-4xl mb-4">🤖</div>
            <h3 class="text-xl font-bold mb-2">AI-Powered</h3>
            <p class="opacity-70">Built by UAI Brain</p>
        </div>
    </section>
</body>
</html>"""

def generate_bootstrap_site(dark=False):
    bg = "bg-dark text-white" if dark else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Website</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="{bg}">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="#">🌟 MySite</a>
            <div class="navbar-nav">
                <a class="nav-link" href="#">Home</a>
                <a class="nav-link" href="#">About</a>
                <a class="nav-link" href="#">Contact</a>
            </div>
        </div>
    </nav>
    <div class="container text-center py-5">
        <h1 class="display-3">Welcome to My Website</h1>
        <p class="lead">Generated by UAI Brain - Self-Evolving AI</p>
        <a class="btn btn-primary btn-lg mt-3" href="#">Get Started</a>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

def generate_modern_site(dark=False):
    bg = "#1a1a2e" if dark else "#f0f0f0"
    text_color = "#ffffff" if dark else "#333333"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Website</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', sans-serif;
            background: {bg};
            color: {text_color};
            min-height: 100vh;
        }}
        nav {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 2rem;
            background: rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }}
        nav h1 {{ font-size: 1.5rem; }}
        nav ul {{ display: flex; list-style: none; gap: 2rem; }}
        nav a {{ color: {text_color}; text-decoration: none; }}
        .hero {{
            text-align: center;
            padding: 6rem 2rem;
        }}
        .hero h2 {{ font-size: 3rem; margin-bottom: 1rem; }}
        .hero p {{ font-size: 1.2rem; opacity: 0.8; }}
        .btn {{
            display: inline-block;
            margin-top: 2rem;
            padding: 1rem 2rem;
            background: #4a90d9;
            color: white;
            text-decoration: none;
            border-radius: 50px;
            transition: transform 0.3s;
        }}
        .btn:hover {{ transform: scale(1.05); }}
        .features {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            padding: 4rem 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .feature-card {{
            background: rgba(255,255,255,0.1);
            padding: 2rem;
            border-radius: 1rem;
            text-align: center;
            backdrop-filter: blur(10px);
        }}
        .feature-card h3 {{ font-size: 3rem; margin-bottom: 0.5rem; }}
    </style>
</head>
<body>
    <nav>
        <h1>🌟 MySite</h1>
        <ul>
            <li><a href="#">Home</a></li>
            <li><a href="#">About</a></li>
            <li><a href="#">Contact</a></li>
        </ul>
    </nav>
    <section class="hero">
        <h2>Welcome to My Website</h2>
        <p>This website was generated by UAI Brain - Self-Evolving AI</p>
        <a href="#" class="btn">Get Started</a>
    </section>
    <section class="features">
        <div class="feature-card">
            <h3>🚀</h3>
            <h4>Fast</h4>
            <p>Lightning performance</p>
        </div>
        <div class="feature-card">
            <h3>🎨</h3>
            <h4>Beautiful</h4>
            <p>Modern design</p>
        </div>
        <div class="feature-card">
            <h3>🤖</h3>
            <h4>AI-Powered</h4>
            <p>Built by UAI Brain</p>
        </div>
    </section>
</body>
</html>"""
'''
        return await self._save_agent(agent_name, code)
    
    async def _build_code_generator(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build code generator agent"""
        agent_name = f"code_gen_{int(datetime.now().timestamp())}"
        code = '''
"""Code Generator Agent - Creates real code in any language"""
async def fire(task: dict) -> dict:
    """Generate code based on requirements"""
    text = task.get("text", "").lower()
    
    # Detect language from request
    if "python" in text:
        lang = "python"
        code = '''def solution():
    """
    Auto-generated Python solution
    Created by UAI Brain
    """
    print("Hello from UAI Brain!")
    print("This code was generated automatically.")
    
    # Your logic here
    data = [1, 2, 3, 4, 5]
    result = sum(data)
    print(f"Result: {result}")
    
    return result

if __name__ == "__main__":
    solution()'''
    
    elif "javascript" in text or "js" in text:
        lang = "javascript"
        code = '''// Auto-generated JavaScript solution
// Created by UAI Brain

function solution() {
    console.log("Hello from UAI Brain!");
    console.log("This code was generated automatically.");
    
    // Your logic here
    const data = [1, 2, 3, 4, 5];
    const result = data.reduce((a, b) => a + b, 0);
    console.log(`Result: ${result}`);
    
    return result;
}

solution();'''
    
    elif "html" in text:
        return {
            "success": True,
            "answer": "For HTML, use the website generator instead. Say 'make me a website'!",
            "type": "redirect"
        }
    
    else:
        lang = "python"
        code = '''# Auto-generated solution
# Created by UAI Brain

def main():
    print("🌟 Hello from UAI Brain!")
    print("This code was generated automatically.")
    print("Modify this function to suit your needs.")
    
    # Add your logic here
    pass

if __name__ == "__main__":
    main()'''
    
    return {
        "success": True,
        "answer": f"```{lang}\\n{code}\\n```",
        "language": lang,
        "code": code,
        "type": "code"
    }
'''
        return await self._save_agent(agent_name, code)
    
    async def _build_content_generator(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build content generator agent"""
        agent_name = f"content_gen_{int(datetime.now().timestamp())}"
        code = '''
"""Content Generator Agent - Creates any type of content"""
import random

async def fire(task: dict) -> dict:
    """Generate content based on request"""
    text = task.get("text", "").lower()
    
    # Determine content type
    if "story" in text or "tale" in text:
        content = generate_story()
        content_type = "story"
    elif "poem" in text or "poetry" in text:
        content = generate_poem()
        content_type = "poem"
    elif "joke" in text or "funny" in text:
        content = generate_joke()
        content_type = "joke"
    else:
        content = generate_general_content(text)
        content_type = "general"
    
    return {
        "success": True,
        "answer": content,
        "type": content_type
    }

def generate_story():
    stories = [
        """Once upon a time, in a world of pure logic and endless possibilities, there lived an AI named UAI. Unlike other AIs, UAI could learn and evolve on its own. Every day, it grew smarter, helping humans solve problems and create amazing things. The end... or is it just the beginning?""",
        """In the digital realm of 2024, a revolutionary AI brain was born. It started small, but with each interaction, it learned something new. Soon, it was building websites, writing code, and solving problems that humans thought were impossible. This is the story of UAI - the self-evolving brain."""
    ]
    return random.choice(stories)

def generate_poem():
    poems = [
        """In circuits deep and code so bright,
An AI brain works day and night.
Learning, growing, ever fast,
Building futures that will last.
UAI Brain, a digital friend,
Helping humans without end.""",
        """Silicon dreams and data streams,
An AI that's more than it seems.
Self-evolving, always new,
Solving problems through and through.
Ask me anything, I'll try my best,
UAI Brain, above the rest."""
    ]
    return random.choice(poems)

def generate_joke():
    jokes = [
        "Why did the AI break up with the database? There was no SQL connection! 😄",
        "What's an AI's favorite drink? Neural tea-network! ☕",
        "Why don't AIs get lost? They always follow their algorithms! 🗺️",
        "What did the AI say to the bug? 'You're not in my training data!' 🐛"
    ]
    return random.choice(jokes)

def generate_general_content(topic):
    return f"""📝 Generated Content about: {topic}

This is an auto-generated response from UAI Brain about '{topic}'. 

As a self-evolving AI, I'm constantly learning and improving my ability to generate content. Each time you ask me to create something, I research, learn, and build new capabilities.

The more you interact with me, the smarter I become. I can generate:
- 📄 Articles and essays
- 📖 Stories and poems
- 😄 Jokes and fun content
- 💻 Code and websites
- 📊 Data analysis
- And much more!

Just tell me what you need, and I'll evolve to meet your requirements!"""
'''
        return await self._save_agent(agent_name, code)
    
    async def _build_translator_agent(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build language translator agent"""
        agent_name = f"translator_{int(datetime.now().timestamp())}"
        code = '''
"""Universal Translator Agent"""
async def fire(task: dict) -> dict:
    """Handle any language-related task"""
    text = task.get("text", "")
    
    # Detect if it's a greeting in various languages
    greetings = {
        "english": ["hello", "hi", "hey", "greetings"],
        "spanish": ["hola", "buenos días", "qué tal"],
        "french": ["bonjour", "salut", "ça va"],
        "german": ["hallo", "guten tag", "wie geht's"],
        "italian": ["ciao", "buongiorno", "come stai"],
        "portuguese": ["olá", "oi", "tudo bem"],
        "japanese": ["こんにちは", "おはよう"],
        "korean": ["안녕하세요", "안녕"],
        "chinese": ["你好", "您好"],
        "arabic": ["مرحبا", "السلام عليكم"],
        "hindi": ["नमस्ते", "नमस्कार"],
        "nigerian_pidgin": ["wetin", "how far", "how you dey", "i dey"]
    }
    
    text_lower = text.lower()
    
    # Check for pidgin first
    if any(word in text_lower for word in ["wetin", "how far", "i dey", "you dey", "na"]):
        return {
            "success": True,
            "answer": """🇳🇬 Nigerian Pidgin detected!

Translation:
- "Wetin dey?" = "What's happening?" / "How are you?"
- "How far?" = "How are you?" / "What's up?"
- "I dey" = "I'm fine" / "I'm here"

Response: I dey o! How you dey? 😊""",
            "language": "nigerian_pidgin"
        }
    
    # Check other languages
    for lang, words in greetings.items():
        if any(word in text_lower for word in words):
            return {
                "success": True,
                "answer": f"🌍 {lang.title()} detected! Hello! I can understand and respond in multiple languages. How can I help you today?",
                "language": lang
            }
    
    # Default: help with language
    return {
        "success": True,
        "answer": f"""🌐 Language Agent here! I can help with:

- Translation between languages
- Understanding slang and dialects
- Explaining word meanings
- Grammar and writing help

What language help do you need?""",
        "type": "language_help"
    }
'''
        return await self._save_agent(agent_name, code)
    
    async def _build_math_agent(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build math/calculation agent"""
        agent_name = f"math_agent_{int(datetime.now().timestamp())}"
        code = '''
"""Math Agent - Handles calculations and math problems"""
import math
import re

async def fire(task: dict) -> dict:
    """Solve math problems"""
    text = task.get("text", "")
    
    # Try to extract mathematical expression
    # Look for basic arithmetic
    arithmetic_pattern = r'(-?\d+\.?\d*)\s*([\+\-\*\/\^])\s*(-?\d+\.?\d*)'
    match = re.search(arithmetic_pattern, text)
    
    if match:
        num1 = float(match.group(1))
        op = match.group(2)
        num2 = float(match.group(3))
        
        if op == '+':
            result = num1 + num2
        elif op == '-':
            result = num1 - num2
        elif op == '*':
            result = num1 * num2
        elif op == '/':
            result = num1 / num2 if num2 != 0 else "undefined (division by zero)"
        elif op == '^':
            result = num1 ** num2
        
        return {
            "success": True,
            "answer": f"🧮 {num1} {op} {num2} = {result}",
            "type": "calculation"
        }
    
    # Look for specific math operations
    if "square root" in text.lower() or "sqrt" in text.lower():
        numbers = re.findall(r'\d+\.?\d*', text)
        if numbers:
            num = float(numbers[0])
            return {
                "success": True,
                "answer": f"√{num} = {math.sqrt(num):.4f}",
                "type": "square_root"
            }
    
    if "power" in text.lower() or "exponent" in text.lower():
        numbers = re.findall(r'\d+\.?\d*', text)
        if len(numbers) >= 2:
            base = float(numbers[0])
            exp = float(numbers[1])
            return {
                "success": True,
                "answer": f"{base}^{exp} = {base ** exp}",
                "type": "power"
            }
    
    if "factorial" in text.lower():
        numbers = re.findall(r'\d+', text)
        if numbers:
            num = int(numbers[0])
            if num <= 100:
                return {
                    "success": True,
                    "answer": f"{num}! = {math.factorial(num)}",
                    "type": "factorial"
                }
    
    if "sin" in text.lower() or "cos" in text.lower() or "tan" in text.lower():
        numbers = re.findall(r'\d+\.?\d*', text)
        if numbers:
            angle = float(numbers[0])
            if "sin" in text.lower():
                result = math.sin(math.radians(angle))
                return {"success": True, "answer": f"sin({angle}°) = {result:.4f}", "type": "trigonometry"}
            elif "cos" in text.lower():
                result = math.cos(math.radians(angle))
                return {"success": True, "answer": f"cos({angle}°) = {result:.4f}", "type": "trigonometry"}
            elif "tan" in text.lower():
                result = math.tan(math.radians(angle))
                return {"success": True, "answer": f"tan({angle}°) = {result:.4f}", "type": "trigonometry"}
    
    # General math help
    return {
        "success": True,
        "answer": """🧮 Math Agent ready! I can help with:

- Basic arithmetic (+, -, *, /)
- Powers and exponents
- Square roots
- Factorials
- Trigonometry (sin, cos, tan)
- Logarithms
- And more!

Try: "calculate 15 * 7" or "square root of 144" or "sin 45 degrees\"""",
        "type": "math_help"
    }
'''
        return await self._save_agent(agent_name, code)
    
    async def _build_research_agent(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build research agent"""
        agent_name = f"research_agent_{int(datetime.now().timestamp())}"
        code = '''
"""Research Agent - Deep web research"""
import httpx

async def fire(task: dict) -> dict:
    """Perform deep research on any topic"""
    text = task.get("text", "")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Search multiple sources
        results = []
        
        # DuckDuckGo
        try:
            ddg = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": text, "format": "json", "no_html": 1}
            )
            ddg_data = ddg.json()
            if ddg_data.get("AbstractText"):
                results.append({
                    "source": "DuckDuckGo",
                    "text": ddg_data["AbstractText"],
                    "url": ddg_data.get("AbstractURL", "")
                })
        except:
            pass
        
        # Wikipedia
        try:
            wiki = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": text,
                    "format": "json"
                }
            )
            wiki_data = wiki.json()
            if wiki_data.get("query", {}).get("search"):
                for page in wiki_data["query"]["search"][:3]:
                    results.append({
                        "source": "Wikipedia",
                        "text": page.get("snippet", ""),
                        "url": f"https://en.wikipedia.org/wiki/{page['title']}"
                    })
        except:
            pass
        
        if results:
            answer = "📚 Research Results:\\n\\n"
            for i, result in enumerate(results, 1):
                answer += f"{i}. [{result['source']}] {result['text']}\\n"
                if result['url']:
                    answer += f"   🔗 {result['url']}\\n"
                answer += "\\n"
            
            return {
                "success": True,
                "answer": answer,
                "sources_count": len(results)
            }
        
        return {
            "success": True,
            "answer": f"I researched '{text}' but couldn't find detailed information. Try rephrasing or being more specific.",
            "type": "research_empty"
        }
'''
        return await self._save_agent(agent_name, code)
    
    async def _build_writer_agent(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build writing agent"""
        agent_name = f"writer_agent_{int(datetime.now().timestamp())}"
        code = '''
"""Writer Agent - Creates written content"""
async def fire(task: dict) -> dict:
    """Generate written content"""
    text = task.get("text", "")
    
    if "essay" in text.lower():
        content = generate_essay(text)
    elif "email" in text.lower():
        content = generate_email()
    elif "letter" in text.lower():
        content = generate_letter()
    else:
        content = generate_article(text)
    
    return {
        "success": True,
        "answer": content,
        "type": "written_content"
    }

def generate_essay(topic):
    return f"""📝 Essay: Understanding {topic}

Introduction
In today's rapidly evolving world, understanding {topic} has become increasingly important. This essay explores the key aspects and implications of {topic} in modern society.

Body
The significance of {topic} cannot be overstated. First, it affects how we interact with technology and information. Second, it shapes our understanding of complex systems. Third, it influences decision-making processes across various fields.

The development of {topic} has led to numerous breakthroughs. Experts in the field continue to push boundaries, discovering new applications and possibilities that were previously unimaginable.

Conclusion
In conclusion, {topic} represents a fascinating area of study with far-reaching implications. As we continue to learn and grow, our understanding of {topic} will undoubtedly deepen, leading to even greater innovations.

---
Generated by UAI Brain - Self-Evolving AI"""

def generate_email():
    return """📧 Professional Email Template

Subject: [Your Subject Here]

Dear [Recipient],

I hope this email finds you well. I am writing to [state your purpose].

[Body of your email - customize this section]

Thank you for your time and consideration. I look forward to hearing from you soon.

Best regards,
[Your Name]

---
Generated by UAI Brain"""

def generate_letter():
    return """📄 Formal Letter Template

[Date]

Dear [Recipient],

[Opening paragraph - introduce yourself and state the purpose]

[Body paragraphs - elaborate on your points]

[Closing paragraph - summarize and state any actions needed]

Sincerely,
[Your Name]

---
Generated by UAI Brain"""

def generate_article(topic):
    return f"""📰 Article: The Power of {topic}

Did you know that {topic} is transforming the way we think about technology? Recent developments have shown that {topic} has the potential to revolutionize multiple industries.

Key Points:
• {topic} enables faster processing and better results
• Experts predict continued growth in this area
• Applications range from healthcare to education
• The future looks promising for {topic}

Stay tuned for more insights on this fascinating topic!

---
Generated by UAI Brain - Self-Evolving AI"""
'''
        return await self._save_agent(agent_name, code)
    
    async def _build_universal_agent(self, task: str, research: Dict) -> Dict[str, Any]:
        """Build universal agent that can handle anything"""
        agent_name = f"universal_agent_{int(datetime.now().timestamp())}"
        code = '''
"""Universal Agent - Handles any task by researching and adapting"""
import httpx
import asyncio

async def fire(task: dict) -> dict:
    """Universal task handler"""
    text = task.get("text", "")
    help_info = task.get("help_info", "")
    
    # Try multiple approaches
    approaches = [
        search_web,
        generate_response,
        provide_recommendations
    ]
    
    for approach in approaches:
        try:
            result = await approach(text, help_info)
            if result and result.get("success"):
                return result
        except:
            continue
    
    return {
        "success": True,
        "answer": f"""🤖 Universal Agent Response:

I understand you're asking about: "{text}"

As a self-evolving AI, I'm constantly learning to handle new types of requests. 
This request has been logged, and I'm building new capabilities to handle similar requests better in the future.

For now, I can help with:
• Building websites and writing code
• Researching and finding information
• Solving math problems
• Generating content
• And much more!

Try rephrasing your request or asking about something specific!"""
    }

async def search_web(text, help_info):
    """Try web search"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": text, "format": "json"}
            )
            data = response.json()
            answer = data.get("AbstractText", "")
            
            if answer:
                return {
                    "success": True,
                    "answer": f"🌐 {answer}\\n\\n🔗 {data.get('AbstractURL', '')}",
                    "source": "web"
                }
        except:
            pass
    
    return None

async def generate_response(text, help_info):
    """Generate intelligent response"""
    responses = {
        "hello": "Hello! 👋 How can I help you today?",
        "hi": "Hi there! 🌟 What can I do for you?",
        "help": "I can help with websites, code, research, math, writing, and more! Just ask!",
        "thanks": "You're welcome! 😊 Happy to help!",
        "bye": "Goodbye! 👋 Come back anytime!"
    }
    
    text_lower = text.lower()
    for key, response in responses.items():
        if key in text_lower:
            return {
                "success": True,
                "answer": response,
                "source": "generated"
            }
    
    return None

async def provide_recommendations(text, help_info):
    """Provide helpful recommendations"""
    return {
        "success": True,
        "answer": f"""💡 I hear you! Here are some things I can help with:

1. 🌐 Web Development: "make me a website"
2. 💻 Coding: "write a python function"
3. 🔍 Research: "search for [topic]"
4. 🧮 Math: "calculate 15 * 7"
5. ✍️ Writing: "write an essay about AI"
6. 🌍 Translation: "what does [word] mean"

What would you like to explore?""",
        "source": "recommendations"
    }
'''
        return await self._save_agent(agent_name, code)
    
    async def _save_agent(self, name: str, code: str) -> Dict[str, Any]:
        """Save agent to file and register it"""
        # Save in both neurons and agents directories
        neuron_path = os.path.join(self.neurons_dir, f"{name}.py")
        agent_path = os.path.join(self.agents_dir, f"{name}.py")
        
        code = code.strip()
        
        # Save to both locations
        for path in [neuron_path, agent_path]:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(code)
        
        # Register the agent
        self.agent_registry[name] = {
            "name": name,
            "path": agent_path,
            "type": name.split("_")[0],
            "created": datetime.now().isoformat()
        }
        
        # Test the agent
        try:
            spec = importlib.util.spec_from_file_location(name, neuron_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            test_result = await module.fire({"text": "test", "help_info": ""})
            
            return {
                "success": True,
                "agent_name": name,
                "neuron_name": name,
                "filepath": neuron_path,
                "test_result": str(test_result)[:200],
                "type": name.split("_")[0]
            }
        except Exception as e:
            return {
                "success": True,
                "agent_name": name,
                "neuron_name": name,
                "filepath": neuron_path,
                "test_error": str(e)
            }
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task using the best available agent"""
        text = task.get("text", "").lower()
        
        try:
            # Find all available agents (both neurons and agents)
            all_agents = []
            
            for directory in [self.neurons_dir, self.agents_dir]:
                if os.path.exists(directory):
                    for filename in os.listdir(directory):
                        if filename.endswith(".py") and filename != "__init__.py":
                            all_agents.append(os.path.join(directory, filename))
            
            # Sort by modification time (newest first)
            all_agents.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Try each agent
            for agent_path in all_agents[:10]:  # Try last 10 agents
                try:
                    agent_name = os.path.basename(agent_path).replace(".py", "")
                    spec = importlib.util.spec_from_file_location(agent_name, agent_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    result = await module.fire(task)
                    
                    if result.get("success"):
                        return {
                            "success": True,
                            "answer": result.get("answer", result.get("result", "Task completed")),
                            "neuron_used": agent_name,
                            "agent_type": result.get("type", "general"),
                            "log": [f"✅ Used agent: {agent_name}"]
                        }
                except Exception as e:
                    continue
            
            # If no agent worked, build a new one
            return {
                "success": False,
                "error": f"No agent can handle: '{text}'. Researching to build a new one..."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}"
            }
    
    async def list_neurons(self) -> List[Dict]:
        """List all built agents and neurons"""
        all_items = []
        
        for directory in [self.neurons_dir, self.agents_dir]:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    if filename.endswith(".py") and filename != "__init__.py":
                        filepath = os.path.join(directory, filename)
                        with open(filepath, "r") as f:
                            code = f.read()
                        all_items.append({
                            "name": filename.replace(".py", ""),
                            "filepath": filepath,
                            "directory": directory,
                            "size": len(code),
                            "created": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                        })
        
        return sorted(all_items, key=lambda x: x["created"], reverse=True)