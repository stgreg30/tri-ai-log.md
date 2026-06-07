Worlds Best AI — Starter Skeleton

This is not the full brain. It's the workshop you asked for: a GitHub-ready repo you can deploy on Render today.

What it implements from our blueprint:
- World engine stub (predicts next state, currently a placeholder)
- Epistemic layer (every answer has source, uncertainty, falsifiability)
- Persistent memory graph (SQLite, user-owned)
- Action loop (tool runner that can call web or code)

## First principles in code
Intelligence = prediction + action + update. This repo wires those three together, so you can swap in better models later without rewriting the architecture.

## Run locally
pip install -r requirements.txt
uvicorn app.main:app --reload

## Push to GitHub
1. git init
2. git add .
3. git commit -m "init worlds best ai"
4. gh repo create worlds-best-ai --public --source=. --push

## Deploy on Render
- Connect your GitHub repo
- Render detects render.yaml and creates a web service
- Free tier works for the skeleton. No GPU, so plug in external model APIs for now.

Next upgrades: replace world.py with a real simulator, connect memory to Neo4j, add the society-of-agents voting.
