"""Flask Web Server - The interface between you and the AI agents"""
import os
from flask import Flask, render_template, request, jsonify, session
import uuid, time
from memory import Memory
from factory_agent import FactoryAgent
from translator_agent import TranslatorAgent

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "factory-secret-change-me-2024")

# Shared memory (Supabase)
memory = Memory()

# Per-session agents
factories = {}
translators = {}

def get_sid():
    if 'sid' not in session:
        session['sid'] = str(uuid.uuid4())
    return session['sid']

def get_agents(sid: str):
    """Get or create agents for a session"""
    if sid not in factories:
        factories[sid] = FactoryAgent(memory)
    if sid not in translators:
        translators[sid] = TranslatorAgent(memory)
    return factories[sid], translators[sid]

@app.route('/')
def index():
    get_sid()
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    sid = get_sid()
    factory, translator = get_agents(sid)
    
    data = request.json
    english = data.get('message', '').strip()
    
    if not english:
        return jsonify({"error": "empty"}), 400
    
    # FLOW:
    # 1. Translator AI Agent: English → Machine Packet
    pkt = translator.translate_to_machine(english)
    
    # 2. Factory AI Agent: Machine Packet → Machine Response
    response_pkt = factory.receive(pkt)
    
    # 3. Translator AI Agent: Machine Response → English
    english_response = translator.translate_to_english(response_pkt)
    
    # Translator learns from this interaction
    success = response_pkt.op not in ["ERR"]
    translator.learn(english, pkt, success)
    
    # Save message to memory
    memory.save_message({
        "english_in": english,
        "machine_sent": pkt.to_dict(),
        "machine_received": response_pkt.to_dict(),
        "english_out": english_response,
        "ts": time.time()
    })
    
    return jsonify({
        "response": english_response,
        "factory_thoughts": factory.get_thoughts(10),
        "agent_count": len(factory.agents),
        "debug": {
            "op_sent": pkt.op,
            "op_received": response_pkt.op,
            "payload_sent": pkt.payload,
            "payload_received": response_pkt.payload
        }
    })

@app.route('/api/thoughts', methods=['GET'])
def thoughts():
    sid = get_sid()
    if sid in factories:
        return jsonify({"thoughts": factories[sid].get_thoughts(30)})
    return jsonify({"thoughts": []})

@app.route('/api/agents', methods=['GET'])
def agents():
    sid = get_sid()
    if sid in factories:
        factory = factories[sid]
        agents_data = []
        for aid, agent in factory.agents.items():
            agents_data.append({
                "id": aid,
                "type": agent.type,
                "status": agent.status,
                "runs": agent.runs,
                "caps": agent.caps()
            })
        return jsonify({"agents": agents_data})
    return jsonify({"agents": []})

@app.route('/api/reset', methods=['POST'])
def reset():
    sid = get_sid()
    if sid in factories:
        del factories[sid]
    if sid in translators:
        del translators[sid]
    return jsonify({"ok": True})

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)