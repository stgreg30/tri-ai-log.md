"""Run this once to create initial neurons"""
import asyncio
from factory import ResearchFactory
import sys

async def init():
    factory = ResearchFactory()
    
    # Create initial translator
    result = await factory._build_translator("initial setup", {})
    print(f"✅ Created translator: {result['neuron_name']}")
    
    # Create initial capability
    result = await factory._build_capability("search", {})
    print(f"✅ Created capability: {result['neuron_name']}")
    
    print("🧠 Initial neurons created successfully!")

if __name__ == "__main__":
    asyncio.run(init())
    # Don't exit - if running as main, just finish normally
    # The render.yaml will call this during build, then start uvicorn separately