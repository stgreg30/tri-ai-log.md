from fastapi import FastAPI
from pydantic import BaseModel
from .epistemic import EpistemicAnswer
from .memory import Memory
from .world import WorldEngine

app = FastAPI(title="Worlds Best AI Skeleton")
memory = Memory()
world = WorldEngine()

class Query(BaseModel):
    text: str
    user_id: str = "default"

@app.post("/predict")
def predict(q: Query):
    # 1. predict next state
    prediction = world.predict(q.text)
    # 2. wrap in epistemic layer
    answer = EpistemicAnswer(
        claim=prediction,
        source="world_engine_stub",
        uncertainty=0.7,
        falsifiable_test=f"Check if '{prediction}' holds in real world"
    )
    # 3. store in memory
    memory.add(q.user_id, q.text, answer.model_dump())
    return answer

@app.post("/act")
def act(q: Query):
    result = world.act(q.text)
    memory.add(q.user_id, f"ACT:{q.text}", {"result": result})
    return {"result": result}

@app.get("/memory/{user_id}")
def get_memory(user_id: str):
    return memory.get_all(user_id)
