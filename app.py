"""Flask web server for Render deployment"""
from flask import Flask, render_template, request, jsonify, session
import uuid
import time
from factory import Factory
from translator import Translator

app = Flask(__name__)
app.secret_key = "factory-machine-language-secret-key-change-in-production"

# Store factories per session (in production, use Redis)
factories = {}
translators = {}

def get_or_create_factory(session_id: str):
    if session_id not in factories:
        factories[session_id] = Factory()
        translators[session_id] = Translator()
        # Auto-init
        init_instr = translators[session_id].english_to_machine("init")
        factories[session_id].receive_instruction(init_instr)
    return factories[session_id], translators[session_id]

@app.route('/')
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session['chat_history'] = []
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    
    data = request.json
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    
    factory, translator = get_or_create_factory(session_id)
    
    # Full translation cycle
    response = translator.translate_roundtrip(user_message, factory)
    
    # Store in history
    history = session.get('chat_history', [])
    history.append({
        "user": user_message,
        "system": response,
        "timestamp": time.time()
    })
    session['chat_history'] = history[-50:]  # Keep last 50 messages
    
    # Get agent list for display
    list_instr = translator.english_to_machine("list agents")
    list_response = factory.receive_instruction(list_instr)
    agents_data = list_response.params.get("agents", [])
    
    return jsonify({
        "response": response,
        "agents": agents_data,
        "agent_count": len(agents_data)
    })

@app.route('/api/agents', methods=['GET'])
def get_agents():
    session_id = session.get('session_id', '')
    if session_id in factories:
        factory = factories[session_id]
        translator = translators[session_id]
        list_instr = translator.english_to_machine("list agents")
        list_response = factory.receive_instruction(list_instr)
        return jsonify(list_response.params)
    return jsonify({"agents": [], "total_count": 0})

@app.route('/api/reset', methods=['POST'])
def reset():
    session_id = session.get('session_id', '')
    if session_id in factories:
        del factories[session_id]
        del translators[session_id]
    session['chat_history'] = []
    return jsonify({"status": "reset_complete"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
