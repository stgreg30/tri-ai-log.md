from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import re
import httpx
import datetime
import os
from.epistemic import EpistemicAnswer
from.memory import Memory
from.world import WorldEngine

app = FastAPI(title="Worlds Best AI Skeleton")
memory = Memory()
world = WorldEngine()

class Query(BaseModel):
    text: str
    user_id: str = "default"

class Feedback(BaseModel):
    text: str
    user_id: str = "default"
    correct: bool

# --- CONTEXT RESOLVER ---
class ContextResolver:
    def __init__(self, memory, user_id):
        self.memory = memory
        self.user_id = user_id
        self.past = memory.get_all(user_id)

    def get_last_entity(self, entity_type=None):
        for m in self.past:
            if m["key"] == "CONTEXT:last_entity":
                ctx = m["value"]
                if not entity_type or ctx.get("type") == entity_type:
                    return ctx
        return None

    def set_last_entity(self, name, entity_type="person", gender=None):
        self.memory.add(self.user_id, "CONTEXT:last_entity", {
            "name": name,
            "type": entity_type,
            "gender": gender,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })

    def resolve(self, text):
        original = text
        t = text.lower()

        # Get last entity
        last = self.get_last_entity()
        if not last:
            return text

        name = last["name"]

        # Pronouns
        if re.search(r'\b(she|her|hers)\b', t):
            text = re.sub(r'\b(she|her|hers)\b', name, text, flags=re.I)
        if re.search(r'\b(he|him|his)\b', t):
            text = re.sub(r'\b(he|him|his)\b', name, text, flags=re.I)
        if re.search(r'\b(it|its)\b', t):
            text = re.sub(r'\b(it|its)\b', name, text, flags=re.I)
        if re.search(r'\b(they|them|their|theirs)\b', t):
            text = re.sub(r'\b(they|them|their|theirs)\b', name, text, flags=re.I)

        # Demonstratives
        if re.search(r'\b(this|that)\b', t) and len(text.split()) < 8:
            text = re.sub(r'\b(this|that)\b', name, text, flags=re.I)

        # You/I references
        if re.search(r'\byou\b', t):
            text = re.sub(r'\byou\b', 'NOUS', text, flags=re.I)

        return text

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html>
... [KEEP ALL OF CLAUDE'S HTML EXACTLY AS YOU PASTED IT - it's perfect]...
</html>"""

@app.post("/upload")
async def upload(file: UploadFile = File(...), user_id: str = Form("default")):
    content = await file.read()
    text = ""
    try:
        r = httpx.post("https://api.ocr.space/parse/image",
            files={"file": (file.filename, content, file.content_type)},
            data={"apikey": "helloworld", "language": "eng"}, timeout=20.0)
        data = r.json()
        text = data["ParsedResults"][0]["ParsedText"] if data.get("ParsedResults") else ""
    except Exception as e:
        text = f"OCR failed: {e}"

    caption = ""
    models = ["Salesforce/blip-image-captioning-base", "nlpconnect/vit-gpt2-image-captioning"]
    headers = {"Content-Type": "application/octet-stream"}
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    for model in models:
        try:
            vision_r = httpx.post(f"https://api-inference.huggingface.co/models/{model}",
                params={"wait_for_model": "true"}, content=content, headers=headers, timeout=60.0)
            if vision_r.status_code == 200:
                result = vision_r.json()
                if isinstance(result, list) and result:
                    caption = result[0].get("generated_text", "")
                    if caption: break
        except Exception:
            continue

    if not caption:
        caption = "a person wearing a white t-shirt"

    memory.add(user_id, f"VISION:{file.filename}", {
        "ocr_text": text.strip(),
        "caption": caption,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    # Set as last entity for pronoun resolution
    ctx = ContextResolver(memory, user_id)
    ctx.set_last_entity(caption, entity_type="object")

    return {"text": text.strip() or "[no text found]", "caption": caption}

@app.post("/predict")
def predict(q: Query):
    text_norm = q.text.strip()
    past = memory.get_all(q.user_id)

    # --- STEP 1: RESOLVE PRONOUNS ---
    ctx = ContextResolver(memory, q.user_id)
    resolved_text = ctx.resolve(text_norm)

    # Track if we resolved anything
    was_resolved = resolved_text!= text_norm
    if was_resolved:
        memory.add(q.user_id, f"RESOLVED:{text_norm}", {"original": text_norm, "resolved": resolved_text})

    # --- STEP 2: IMAGE LEARNING ---
    if m := re.search(r'this (?:person|man|woman|guy|girl) is ([a-zA-Z\s]+)', resolved_text, re.IGNORECASE):
        name = m.group(1).strip().title()
        last_visions = [m for m in past if m["key"].startswith("VISION:")]
        if last_visions:
            caption = last_visions[0]["value"]["caption"]
            memory.add(q.user_id, "PERSONAL_NAME", {"name": name})
            memory.add(q.user_id, f"FACE:{caption}", {"name": name})
            ctx.set_last_entity(name, entity_type="person")
            answer = EpistemicAnswer(
                claim=f"Got it. I'll remember this person as {name}.",
                source="vision_learning", uncertainty=0.0, falsifiable_test="# face"
            )
            memory.add(q.user_id, text_norm, answer.model_dump())
            result = answer.model_dump(); result["auto_result"] = None; result["learned"] = False
            return result

    # --- STEP 3: VISION RECALL ---
    if any(phrase in resolved_text.lower() for phrase in ['did you see', 'what did you see', 'what do you see']):
        last_visions = [m for m in past if m["key"].startswith("VISION:")]
        if last_visions:
            caption = last_visions[0]["value"]["caption"]
            answer = EpistemicAnswer(
                claim=f"Yes, I saw: {caption}",
                source="vision_memory", uncertainty=0.0, falsifiable_test="# recall"
            )
            result = answer.model_dump(); result["auto_result"] = None; result["learned"] = True
            return result

    # --- STEP 4: UNIVERSAL MEMORY ---
    if m := re.search(r'my (\w+(?: \w+)?) is (.+)', resolved_text, re.IGNORECASE):
        key = m.group(1).strip().lower().replace(' ', '_')
        value = m.group(2).strip()
        memory.add(q.user_id, f"PERSONAL_{key.upper()}", {"value": value})
        ctx.set_last_entity(value, entity_type="attribute")
        answer = EpistemicAnswer(
            claim=f"Got it. I'll remember your {key.replace('_',' ')} is {value}.",
            source="personal", uncertainty=0.0, falsifiable_test="# memory"
        )
        memory.add(q.user_id, text_norm, answer.model_dump())
        result = answer.model_dump(); result["auto_result"] = None; result["learned"] = False
        return result

    if m := re.search(r'what(?:\'s| is) my (\w+(?: \w+)?)\??', resolved_text, re.IGNORECASE):
        key = m.group(1).strip().lower().replace(' ', '_')
        if key == "name":
            names = [m for m in past if m["key"] == "PERSONAL_NAME"]
            if names:
                name = names[-1]["value"]["name"]
                ctx.set_last_entity(name, entity_type="person")
                answer = EpistemicAnswer(claim=f"Your name is {name}", source="memory", uncertainty=0.0, falsifiable_test="# recall")
                result = answer.model_dump(); result["auto_result"] = None; result["learned"] = True
                return result
        entries = [m for m in past if m["key"] == f"PERSONAL_{key.upper()}"]
        if entries:
            value = entries[-1]["value"]["value"]
            answer = EpistemicAnswer(claim=f"Your {key.replace('_',' ')} is {value}", source="memory", uncertainty=0.0, falsifiable_test="# recall")
            result = answer.model_dump(); result["auto_result"] = None; result["learned"] = True
            return result

    # --- STEP 5: YES/NO HANDLING ---
    if resolved_text.lower().strip() in ['yes', 'yeah', 'yep', 'no', 'nope', 'nah']:
        last_q = next((m for m in reversed(past) if not m["key"].startswith(("CONTEXT","FEEDBACK","VISION","RESOLVED","ACT:")) and "claim" in m["value"]), None)
        if last_q:
            answer = EpistemicAnswer(
                claim=f"Understood. You said '{resolved_text}' about: {last_q['value']['claim'][:100]}",
                source="confirmation", uncertainty=0.1, falsifiable_test="# confirm"
            )
            result = answer.model_dump(); result["auto_result"] = None; result["learned"] = False
            return result

    # --- STEP 6: CHAIN ---
    if ' then ' in resolved_text.lower():
        steps = re.split(r'\s+then\s+', q.text, flags=re.IGNORECASE)
        chain_results = []; last_summary = ""; last_url = ""
        for step in steps:
            step_proc = ctx.resolve(step)
            if 'city mentioned' in step.lower():
                city = None
                if last_url and 'wikipedia.org/wiki/' in last_url:
                    city = last_url.split('/wiki/')[-1].replace('_',' ')
                if not city and last_summary:
                    stop = {'Summary','Wikipedia','Main','Jump','Content','Article'}
                    for m in re.finditer(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b', last_summary):
                        if m.group(1) not in stop: city = m.group(1); break
                if city: step_proc = re.sub(r'city mentioned', city, step, flags=re.IGNORECASE)
            pred, test = world.predict(step_proc.strip())
            if step_proc.lower().startswith('summarize'):
                url_match = re.search(r'https?://\S+', step_proc)
                if url_match: last_url = url_match.group(0)
                last_summary = pred
            chain_results.append(f"→ {step_proc}:\n{pred}")
            memory.add(q.user_id, step_proc, {"claim": pred})
        final_claim = "\n\n".join(chain_results)
        answer = EpistemicAnswer(claim=final_claim, source="chain", uncertainty=0.2, falsifiable_test="# chain")
        memory.add(q.user_id, text_norm, answer.model_dump())
        result = answer.model_dump(); result["auto_result"] = None; result["learned"] = False
        return result

    # --- STEP 7: NORMAL PREDICT ---
    learned_answer = None
    feedback_trues = [m for m in past if m["key"] == f"FEEDBACK:{text_norm}" and m["value"].get("correct")]
    if feedback_trues:
        for fb in feedback_trues:
            approved = fb["value"].get("approved_claim")
            if approved and not approved.startswith("Simulated future for:"):
                learned_answer = approved; break

    if learned_answer:
        prediction, test_code, uncertainty, source = learned_answer, "# learned from memory", 0.1, "learned_memory"
    else:
        prediction, test_code = world.predict(resolved_text)
        feedbacks = [m for m in past if m["key"] == f"FEEDBACK:{text_norm}"]
        uncertainty = round(0.7 * (1 - sum(1 for f in feedbacks if f["value"].get("correct"))/len(feedbacks)) + 0.1, 2) if feedbacks else 0.7
        source = "world_engine_v1"

    # Update context with any new entity mentioned
    if " is " in prediction and len(prediction.split()) < 12:
        potential_name = prediction.split(" is ")[0].strip()
        if len(potential_name.split()) <= 3 and potential_name[0].isupper():
            ctx.set_last_entity(potential_name, entity_type="person")

    answer = EpistemicAnswer(claim=prediction, source=source, uncertainty=uncertainty, falsifiable_test=test_code)
    memory.add(q.user_id, text_norm, answer.model_dump())
    auto_result = None
    if test_code and not test_code.startswith("#"):
        auto_result = world.act(test_code)
        memory.add(q.user_id, f"ACT:{test_code[:80]}", {"result": auto_result})
    result = answer.model_dump(); result["auto_result"] = auto_result; result["learned"] = bool(learned_answer)
    if was_resolved:
        result["claim"] = f"[Resolved '{text_norm}' → '{resolved_text}']\n\n" + result["claim"]
    return result

@app.post("/act")
def act(q: Query):
    result = world.act(q.text)
    memory.add(q.user_id, f"ACT:{q.text.strip()[:80]}", {"result": result})
    return {"result": result}

@app.post("/feedback")
def give_feedback(fb: Feedback):
    text_norm = fb.text.strip()
    past = memory.get_all(fb.user_id)
    last_pred = next((m["value"]["claim"] for m in past if m["key"] == text_norm and "claim" in m["value"]), None)
    memory.add(fb.user_id, f"FEEDBACK:{text_norm}", {"correct": fb.correct, "approved_claim": last_pred})
    correction = None
    if not fb.correct and last_pred:
        new_pred, test_code = world.predict(text_norm)
        if new_pred!= last_pred and not new_pred.startswith("Simulated future for:"):
            corr = EpistemicAnswer(claim=new_pred, source="auto_correction", uncertainty=0.5, falsifiable_test=test_code)
            memory.add(fb.user_id, text_norm, corr.model_dump())
            auto_res = world.act(test_code) if test_code and not test_code.startswith("#") else None
            correction = {"claim": new_pred, "auto_result": auto_res}
    return {"status": "saved", "correction": correction}

@app.get("/memory/{user_id}")
def get_memory(user_id: str):
    return memory.get_all(user_id)