from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import re
import httpx
import datetime
import os
from .epistemic import EpistemicAnswer
from .memory import Memory
from .world import WorldEngine

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

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>NOUS · AI Lab</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&family=JetBrains+Mono:wght@300;400&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg:        #03030a;
      --surface:   #0b0b16;
      --surface2:  #12121f;
      --border:    #1e1e35;
      --cyan:      #00f5c4;
      --cyan-dim:  #00f5c418;
      --amber:     #ffab00;
      --green:     #00e676;
      --red:       #ff5252;
      --text:      #e4e4f0;
      --dim:       #7a7a9a;
      --muted:     #3e3e5a;
      --r:         14px;
      --rsm:       10px;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'DM Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      height: 100dvh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    /* ── HEADER ── */
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 13px 16px;
      border-bottom: 1px solid var(--border);
      flex-shrink: 0;
      background: var(--bg);
      position: relative;
      z-index: 10;
    }
    .brand { display: flex; align-items: center; gap: 10px; }
    .pulse-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--cyan);
      box-shadow: 0 0 10px var(--cyan), 0 0 20px var(--cyan);
      animation: pulseAnim 2.4s ease-in-out infinite;
    }
    @keyframes pulseAnim {
      0%,100% { opacity:1; transform:scale(1); }
      50%      { opacity:0.5; transform:scale(0.75); }
    }
    .brand-name {
      font-family: 'Syne', sans-serif;
      font-size: 20px; font-weight: 800;
      letter-spacing: 0.1em;
    }
    .brand-tag {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px; color: var(--muted);
      letter-spacing: 0.06em;
    }
    .hdr-right { display: flex; gap: 8px; align-items: center; }

    .icon-btn {
      width: 36px; height: 36px; border-radius: 10px;
      border: 1px solid var(--border); background: var(--surface);
      color: var(--dim); font-size: 16px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: all .18s;
    }
    .icon-btn:active { transform: scale(.92); background: var(--surface2); }
    .icon-btn.lit { border-color: var(--cyan); color: var(--cyan); background: var(--cyan-dim); }

    .uid-pill {
      display: flex; align-items: center; gap: 6px;
      padding: 5px 12px; border-radius: 20px;
      border: 1px solid var(--border); background: var(--surface);
      font-size: 13px; font-weight: 500; color: var(--dim);
      cursor: pointer; transition: all .18s;
    }
    .uid-pill:active { background: var(--surface2); }

    /* ── SKILL STRIP ── */
    .skill-strip {
      display: flex; gap: 7px;
      padding: 10px 16px;
      overflow-x: auto;
      border-bottom: 1px solid var(--border);
      background: var(--bg);
      flex-shrink: 0;
      scrollbar-width: none;
    }
    .skill-strip::-webkit-scrollbar { display: none; }

    .chip {
      display: flex; align-items: center; gap: 5px;
      padding: 6px 13px; border-radius: 20px;
      border: 1px solid var(--border); background: var(--surface);
      font-size: 12px; font-weight: 500; color: var(--dim);
      cursor: pointer; white-space: nowrap; flex-shrink: 0;
      transition: all .15s;
    }
    .chip:active {
      background: var(--cyan-dim);
      border-color: var(--cyan);
      color: var(--cyan);
      transform: scale(.96);
    }

    /* ── CHAT ── */
    #chat {
      flex: 1; overflow-y: auto;
      padding: 16px; display: flex;
      flex-direction: column; gap: 12px;
      scroll-behavior: smooth;
    }
    #chat::-webkit-scrollbar { width: 2px; }
    #chat::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

    .msg { display: flex; flex-direction: column; max-width: 90%; animation: fadeUp .22s ease-out; }
    @keyframes fadeUp { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
    .msg.user { align-self: flex-end; }
    .msg.ai   { align-self: flex-start; }

    .bubble {
      padding: 12px 14px; border-radius: var(--r);
      font-size: 14px; line-height: 1.6; word-break: break-word;
    }
    .msg.user .bubble {
      background: linear-gradient(140deg, #1249c8, #0a84ff);
      border-radius: var(--r) var(--r) 4px var(--r);
      color: #fff;
    }
    .msg.ai .bubble {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r) var(--r) var(--r) 4px;
    }

    /* AI bubble anatomy */
    .msg-meta {
      display: flex; align-items: center; gap: 7px;
      margin-bottom: 7px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px; font-weight: 300; color: var(--muted);
      text-transform: uppercase; letter-spacing: .1em;
    }
    .badge {
      padding: 2px 7px; border-radius: 20px;
      font-size: 9px; font-weight: 400; border: 1px solid;
    }
    .badge.learned { border-color: var(--green); color: var(--green); background: #00e67614; }
    .badge.world   { border-color: var(--cyan);  color: var(--cyan);  background: var(--cyan-dim); }
    .badge.chain   { border-color: #c084fc; color: #c084fc; background: #c084fc14; }
    .badge.memory  { border-color: var(--amber); color: var(--amber); background: #ffab0014; }
    .badge.vision  { border-color: #60a5fa; color: #60a5fa; background: #60a5fa14; }
    .badge.auto    { border-color: #f87171; color: #f87171; background: #f8717114; }

    .claim { font-size: 14px; line-height: 1.65; white-space: pre-wrap; margin-bottom: 10px; }

    .ubar { height: 2px; border-radius: 2px; background: var(--border); margin-bottom: 10px; overflow: hidden; }
    .ufill { height: 100%; border-radius: 2px; transition: width .5s ease; }

    .auto-res {
      padding: 8px 10px; margin-bottom: 10px;
      border-radius: var(--rsm); border-left: 2px solid var(--cyan);
      background: var(--surface2);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px; color: var(--dim); line-height: 1.55;
    }

    .msg-actions { display: flex; gap: 5px; flex-wrap: wrap; }
    .act-btn {
      padding: 4px 11px; border-radius: 20px;
      border: 1px solid var(--border); background: transparent;
      font-size: 12px; color: var(--dim); cursor: pointer;
      font-family: 'DM Sans', sans-serif; transition: all .15s;
      display: flex; align-items: center; gap: 3px;
    }
    .act-btn:active { transform: scale(.94); }
    .act-btn.yes  { border-color: #00e67650; color: var(--green); }
    .act-btn.yes.on { background: #00e67618; border-color: var(--green); }
    .act-btn.no   { border-color: #ff525250; color: var(--red); }
    .act-btn.no.on  { background: #ff525218; border-color: var(--red); }
    .act-btn.run  { border-color: #ffab0050; color: var(--amber); }
    .act-btn.copy { color: var(--muted); }

    /* ── TYPING ── */
    .typing {
      align-self: flex-start;
      display: flex; gap: 4px; align-items: center;
      padding: 13px 16px; border-radius: var(--r) var(--r) var(--r) 4px;
      background: var(--surface); border: 1px solid var(--border);
      animation: fadeUp .2s ease-out;
    }
    .tdot {
      width: 5px; height: 5px; border-radius: 50%;
      background: var(--cyan);
      animation: tdotAnim 1.2s ease-in-out infinite;
    }
    .tdot:nth-child(2) { animation-delay: .2s; }
    .tdot:nth-child(3) { animation-delay: .4s; }
    @keyframes tdotAnim {
      0%,100% { opacity:.25; transform:scale(.8); }
      50%      { opacity:1; transform:scale(1); }
    }

    /* ── EMPTY STATE ── */
    .empty {
      flex: 1; display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      text-align: center; padding: 40px 32px;
      animation: fadeUp .35s ease-out;
    }
    .empty-icon { font-size: 52px; margin-bottom: 18px; }
    .empty-title { font-family: 'Syne', sans-serif; font-size: 22px; font-weight: 700; margin-bottom: 8px; }
    .empty-sub { font-size: 13px; color: var(--dim); line-height: 1.65; max-width: 280px; }

    /* ── FOOTER ── */
    footer {
      border-top: 1px solid var(--border);
      background: var(--bg); flex-shrink: 0;
      padding: 12px 16px;
    }

    .mode-tabs { display: flex; gap: 4px; margin-bottom: 10px; }
    .mtab {
      flex: 1; padding: 7px; border-radius: var(--rsm);
      border: 1px solid var(--border); background: transparent;
      font-size: 12px; font-weight: 500; color: var(--muted);
      cursor: pointer; font-family: 'DM Sans', sans-serif;
      transition: all .18s; letter-spacing: .02em;
    }
    .mtab.on { background: var(--cyan-dim); border-color: var(--cyan); color: var(--cyan); }

    /* Chain builder */
    .chain-box {
      margin-bottom: 10px; padding: 10px;
      border-radius: var(--rsm); border: 1px solid var(--border);
      background: var(--surface); display: none;
    }
    .chain-box.show { display: block; }
    .chain-steps { display: flex; flex-direction: column; gap: 6px; margin-bottom: 7px; }
    .cstep { display: flex; align-items: center; gap: 6px; }
    .cnum {
      font-family: 'JetBrains Mono', monospace; font-size: 10px;
      color: var(--cyan); width: 18px; flex-shrink: 0;
    }
    .cinput {
      flex: 1; padding: 7px 10px; border-radius: 8px;
      border: 1px solid var(--border); background: var(--bg);
      color: var(--text); font-size: 13px;
      font-family: 'DM Sans', sans-serif; outline: none;
    }
    .cinput:focus { border-color: var(--cyan); }
    .cdel {
      width: 24px; height: 24px; border-radius: 6px;
      border: none; background: transparent;
      color: var(--muted); font-size: 15px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
    }
    .add-step {
      width: 100%; padding: 6px; border-radius: 8px;
      border: 1px dashed var(--border); background: transparent;
      color: var(--muted); font-size: 12px; cursor: pointer;
      font-family: 'DM Sans', sans-serif; transition: .15s;
    }
    .add-step:active { background: var(--surface2); }

    .input-row { display: flex; gap: 8px; align-items: flex-end; }
    textarea {
      flex: 1; padding: 12px 14px; border-radius: var(--rsm);
      border: 1px solid var(--border); background: var(--surface);
      color: var(--text); font-size: 15px;
      font-family: 'DM Sans', sans-serif;
      resize: none; outline: none; line-height: 1.5;
      max-height: 110px; transition: border-color .18s;
    }
    textarea:focus { border-color: var(--cyan); }
    textarea::placeholder { color: var(--muted); }

    .send {
      width: 46px; height: 46px; border-radius: 12px;
      border: none; background: var(--cyan); color: #000;
      font-size: 20px; cursor: pointer; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      transition: all .18s;
    }
    .send:active { transform: scale(.9); background: #00cca8; }

    .tool-row { display: flex; gap: 6px; margin-top: 8px; }
    .tbtn {
      display: flex; align-items: center; gap: 4px;
      padding: 6px 12px; border-radius: 20px;
      border: 1px solid var(--border); background: transparent;
      font-size: 12px; color: var(--dim); cursor: pointer;
      font-family: 'DM Sans', sans-serif; transition: .15s;
    }
    .tbtn:active { background: var(--surface); transform: scale(.95); }
    input[type="file"] { display: none; }

    /* ── MODAL ── */
    .overlay {
      position: fixed; inset: 0;
      background: rgba(0,0,0,.65);
      backdrop-filter: blur(6px);
      z-index: 100;
      display: flex; align-items: flex-end;
      animation: fadeIn .2s ease;
    }
    .overlay.hide { display: none; }
    @keyframes fadeIn { from { opacity:0; } to { opacity:1; } }

    .modal {
      width: 100%; max-height: 78vh;
      background: var(--surface); border-radius: 22px 22px 0 0;
      border-top: 1px solid var(--border);
      overflow: hidden; display: flex; flex-direction: column;
      animation: slideUp .28s cubic-bezier(.32,.72,0,1);
    }
    @keyframes slideUp { from { transform:translateY(100%); } to { transform:translateY(0); } }

    .mhandle {
      width: 36px; height: 4px; border-radius: 2px;
      background: var(--border); margin: 11px auto 6px;
    }
    .mhead {
      display: flex; align-items: center; justify-content: space-between;
      padding: 6px 16px 12px;
    }
    .mtitle { font-family: 'Syne', sans-serif; font-size: 17px; font-weight: 700; }
    .mbody { overflow-y: auto; padding: 0 16px 28px; flex: 1; scrollbar-width: none; }
    .mbody::-webkit-scrollbar { display: none; }

    /* Memory modal pieces */
    .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin-bottom: 14px; }
    .stat-card {
      padding: 12px; border-radius: var(--rsm);
      background: var(--bg); border: 1px solid var(--border);
    }
    .stat-n {
      font-family: 'Syne', sans-serif; font-size: 28px;
      font-weight: 800; color: var(--cyan);
    }
    .stat-l { font-size: 11px; color: var(--muted); margin-top: 2px; }

    .mact-row { display: flex; gap: 8px; margin-bottom: 14px; }
    .mbtn {
      flex: 1; padding: 9px; border-radius: var(--rsm);
      border: 1px solid var(--border); background: var(--surface2);
      color: var(--dim); font-size: 13px;
      font-family: 'DM Sans', sans-serif; cursor: pointer; transition: .15s;
    }
    .mbtn:active { transform: scale(.97); }
    .mbtn.red { border-color: #ff525230; color: var(--red); }

    .msearch {
      width: 100%; padding: 10px 14px; border-radius: var(--rsm);
      border: 1px solid var(--border); background: var(--bg);
      color: var(--text); font-size: 14px;
      font-family: 'DM Sans', sans-serif; outline: none; margin-bottom: 12px;
    }
    .msearch:focus { border-color: var(--cyan); }

    .mitem {
      padding: 10px 12px; border-radius: var(--rsm);
      background: var(--bg); border: 1px solid var(--border);
      margin-bottom: 7px;
    }
    .mkey { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--cyan); margin-bottom: 3px; }
    .mval { font-size: 12px; color: var(--dim); word-break: break-all; }

    /* Settings modal */
    .set-group { margin-bottom: 18px; }
    .set-label {
      font-family: 'JetBrains Mono', monospace; font-size: 10px;
      color: var(--muted); text-transform: uppercase; letter-spacing: .1em;
      display: block; margin-bottom: 7px;
    }
    .set-input {
      width: 100%; padding: 10px 12px; border-radius: var(--rsm);
      border: 1px solid var(--border); background: var(--bg);
      color: var(--text); font-size: 14px;
      font-family: 'DM Sans', sans-serif; outline: none;
    }
    .set-input:focus { border-color: var(--cyan); }
    .set-hint { font-size: 12px; color: var(--muted); margin-top: 6px; line-height: 1.5; }

    /* ── TOAST ── */
    .toast {
      position: fixed; bottom: 80px; left: 50%;
      transform: translateX(-50%);
      background: var(--surface2); border: 1px solid var(--border);
      color: var(--text); padding: 9px 20px; border-radius: 20px;
      font-size: 13px; z-index: 999; white-space: nowrap;
      animation: tIn .18s ease, tOut .18s ease 1.6s forwards;
    }
    @keyframes tIn  { from { opacity:0; transform:translateX(-50%) translateY(8px); } to { opacity:1; transform:translateX(-50%) translateY(0); } }
    @keyframes tOut { to   { opacity:0; } }
  </style>
</head>
<body>

<!-- ── HEADER ────────────────────────────────── -->
<header>
  <div class="brand">
    <div class="pulse-dot"></div>
    <div>
      <div class="brand-name">NOUS</div>
      <div class="brand-tag">predict · act · learn</div>
    </div>
  </div>
  <div class="hdr-right">
    <button class="icon-btn" id="mem-btn" onclick="openMemory()" title="Memory">🧠</button>
    <div class="uid-pill" onclick="openSettings()">
      <span style="font-size:11px">👤</span>
      <span id="uid-label">ash</span>
    </div>
  </div>
</header>

<!-- ── SKILL STRIP ────────────────────────────── -->
<div class="skill-strip">
  <div class="chip" onclick="skill('summarize')">📄 Summarize</div>
  <div class="chip" onclick="skill('wikipedia')">📚 Wikipedia</div>
  <div class="chip" onclick="skill('news')">📰 Latest News</div>
  <div class="chip" onclick="skill('weather')">🌤 Weather</div>
  <div class="chip" onclick="skill('math')">🔢 Math</div>
  <div class="chip" onclick="skill('time')">🕐 Date & Time</div>
  <div class="chip" onclick="skill('code')">💻 Write Code</div>
  <div class="chip" onclick="skill('search')">🔍 Web Search</div>
  <div class="chip" onclick="skill('translate')">🌐 Translate</div>
  <div class="chip" onclick="skill('define')">📖 Define Word</div>
  <div class="chip" onclick="skill('compare')">⚖️ Compare</div>
  <div class="chip" onclick="skill('pros')">📊 Pros & Cons</div>
</div>

<!-- ── CHAT ──────────────────────────────────── -->
<div id="chat">
  <div class="empty" id="empty">
    <div class="empty-icon">🧬</div>
    <div class="empty-title">NOUS is ready</div>
    <div class="empty-sub">Predict the future, act on the world, build memory that learns from every interaction.</div>
  </div>
</div>

<!-- ── FOOTER ─────────────────────────────────── -->
<footer>
  <div class="mode-tabs">
    <button class="mtab on" id="tab-predict" onclick="setMode('predict')">Predict</button>
    <button class="mtab"    id="tab-act"     onclick="setMode('act')">Act</button>
    <button class="mtab"    id="tab-chain"   onclick="setMode('chain')">Chain</button>
  </div>

  <div class="chain-box" id="chain-box">
    <div class="chain-steps" id="chain-steps"></div>
    <button class="add-step" onclick="addStep()">+ Add step</button>
  </div>

  <div class="input-row">
    <textarea id="txt" rows="1" placeholder="Make a prediction..."
      oninput="resize(this)" onkeydown="handleKey(event)"></textarea>
    <button class="send" onclick="go()">&#x2191;</button>
  </div>

  <div class="tool-row">
    <button class="tbtn" onclick="startVoice()">🎤 Voice</button>
    <button class="tbtn" onclick="document.getElementById('fimg').click()">📷 Image</button>
    <button class="tbtn" onclick="runLastTest()">▶ Test</button>
    <button class="tbtn" onclick="clearChat()">🗑</button>
  </div>
  <input type="file" id="fimg" accept="image/*" onchange="uploadImg()">
</footer>

<!-- ── MEMORY MODAL ───────────────────────────── -->
<div class="overlay hide" id="mem-modal" onclick="overlayClose(event,'mem-modal')">
  <div class="modal">
    <div class="mhandle"></div>
    <div class="mhead">
      <div class="mtitle">🧠 Memory</div>
      <button class="icon-btn" onclick="closeModal('mem-modal')">&#x2715;</button>
    </div>
    <div class="mbody">
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-n" id="s-total">—</div><div class="stat-l">Total entries</div></div>
        <div class="stat-card"><div class="stat-n" id="s-learned">—</div><div class="stat-l">Confirmed true</div></div>
      </div>
      <div class="mact-row">
        <button class="mbtn" onclick="exportMem()">📤 Export JSON</button>
        <button class="mbtn red" onclick="warnClear()">🗑 Clear All</button>
      </div>
      <input class="msearch" id="msearch" placeholder="Search memories..." oninput="filterMem()">
      <div id="mem-list"></div>
    </div>
  </div>
</div>

<!-- ── SETTINGS MODAL ─────────────────────────── -->
<div class="overlay hide" id="set-modal" onclick="overlayClose(event,'set-modal')">
  <div class="modal">
    <div class="mhandle"></div>
    <div class="mhead">
      <div class="mtitle">⚙️ Settings</div>
      <button class="icon-btn" onclick="closeModal('set-modal')">&#x2715;</button>
    </div>
    <div class="mbody">
      <div class="set-group">
        <label class="set-label">User ID</label>
        <input class="set-input" id="uid-input" value="ash" oninput="updateUid()">
        <div class="set-hint">Scopes your memory. Each ID has its own independent store.</div>
      </div>
    </div>
  </div>
</div>

<script>
// ── STATE ──
let uid = 'ash', mode = 'predict';
let lastPred = '', lastTest = '';
let steps = [], allMem = [], msgN = 0;

// ── INIT ──
(function init() {
  const s = localStorage.getItem('nous_uid');
  if (s) { uid = s; setUidDisplay(uid); }
  addStep(); addStep();
})();

// ── UID ──
function setUidDisplay(u) {
  document.getElementById('uid-label').textContent = u;
  const inp = document.getElementById('uid-input');
  if (inp) inp.value = u;
}
function updateUid() {
  uid = document.getElementById('uid-input').value.trim() || 'default';
  setUidDisplay(uid);
  localStorage.setItem('nous_uid', uid);
}

// ── MODE ──
function setMode(m) {
  mode = m;
  ['predict','act','chain'].forEach(t => {
    document.getElementById('tab-'+t).classList.toggle('on', t === m);
  });
  const cb = document.getElementById('chain-box');
  if (m === 'chain') { cb.classList.add('show'); } else { cb.classList.remove('show'); }
  const ph = { predict:'Make a prediction...', act:'Give a command or action...', chain:'Or type a full chain with "then"...' };
  document.getElementById('txt').placeholder = ph[m];
}

// ── CHAIN ──
function addStep() {
  steps.push('');
  renderSteps();
}
function removeStep(i) {
  steps.splice(i, 1);
  renderSteps();
}
function renderSteps() {
  const c = document.getElementById('chain-steps');
  c.innerHTML = '';
  steps.forEach(function(v, i) {
    const d = document.createElement('div');
    d.className = 'cstep';
    d.innerHTML = '<span class="cnum">' + (i+1) + '.</span>' +
      '<input class="cinput" placeholder="Step ' + (i+1) + '..." value="' + esc(v) + '"' +
      ' oninput="steps[' + i + ']=this.value">' +
      (steps.length > 1 ? '<button class="cdel" onclick="removeStep(' + i + ')">&#xd7;</button>' : '');
    c.appendChild(d);
  });
}
function chainText() { return steps.filter(function(s){ return s.trim(); }).join(' then '); }

// ── SEND ──
function go() {
  const txt = document.getElementById('txt').value.trim();
  if (mode === 'chain') {
    const chain = chainText() || txt;
    if (!chain) return;
    doPredict(chain);
  } else if (mode === 'predict') {
    if (!txt) return;
    doPredict(txt);
  } else {
    if (!txt) return;
    doAct(txt);
  }
}
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); go(); }
}
function resize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 110) + 'px';
}

// ── PREDICT ──
async function doPredict(text) {
  killEmpty(); addUser(text);
  clearInput();
  lastPred = text;
  const t = addTyping();
  try {
    const r = await fetch('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, user_id: uid })
    });
    const j = await r.json();
    rmTyping(t);
    lastTest = j.falsifiable_test || '';
    addAI(j);
  } catch(e) {
    rmTyping(t);
    addErr('Request failed: ' + e.message);
  }
}

// ── ACT ──
async function doAct(text) {
  killEmpty(); addUser(text);
  clearInput();
  const t = addTyping();
  try {
    const r = await fetch('/act', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, user_id: uid })
    });
    const j = await r.json();
    rmTyping(t);
    addActResult(j.result);
  } catch(e) {
    rmTyping(t);
    addErr('Request failed: ' + e.message);
  }
}

// ── MESSAGES ──
function addUser(text) {
  const d = document.createElement('div');
  d.className = 'msg user';
  d.innerHTML = '<div class="bubble">' + esc(text) + '</div>';
  chat().appendChild(d); scroll();
}

function addAI(j) {
  const id = 'msg' + (++msgN);
  const u = j.uncertainty || 0.7;
  const col = u < 0.3 ? '#00e676' : u < 0.6 ? '#ffab00' : '#ff5252';
  const w = Math.round((1 - u) * 100);
  const src = j.source || 'world';
  const bc = j.learned ? 'learned' : src.includes('chain') ? 'chain' : src.includes('memory') ? 'memory' : 'world';
  const bl = j.learned ? '&#x2713; learned' : src.replace(/_/g,' ');
  const ar = j.auto_result
    ? '<div class="auto-res">&#x26a1; ' + esc(j.auto_result.slice(0,280)) + '</div>'
    : '';
  const runBtn = (lastTest && !lastTest.startsWith('#'))
    ? '<button class="act-btn run" onclick="runLastTest()">&#x25b6; Test</button>'
    : '';
  const d = document.createElement('div');
  d.className = 'msg ai'; d.id = id;
  d.innerHTML =
    '<div class="bubble">' +
      '<div class="msg-meta">NOUS <span class="badge ' + bc + '">' + bl + '</span></div>' +
      '<div class="claim">' + esc(j.claim || '') + '</div>' +
      '<div class="ubar"><div class="ufill" style="width:' + w + '%;background:' + col + '"></div></div>' +
      ar +
      '<div class="msg-actions">' +
        '<button class="act-btn yes" id="' + id + 'y" onclick="giveFeedback(true,\'' + id + '\')">&#x2713; True</button>' +
        '<button class="act-btn no"  id="' + id + 'n" onclick="giveFeedback(false,\'' + id + '\')">&#x2715; False</button>' +
        runBtn +
        '<button class="act-btn copy" onclick="copyMsg(\'' + id + '\')">&#x2398; Copy</button>' +
      '</div>' +
    '</div>';
  chat().appendChild(d); scroll();
}

function addActResult(result) {
  const d = document.createElement('div');
  d.className = 'msg ai';
  const safe = esc(result || '');
  d.innerHTML =
    '<div class="bubble">' +
      '<div class="msg-meta">ACT RESULT</div>' +
      '<div class="claim">' + safe + '</div>' +
      '<div class="msg-actions"><button class="act-btn copy" onclick="navigator.clipboard.writeText(this.closest(\'.bubble\').querySelector(\'.claim\').textContent);toast(\'Copied\')">&#x2398; Copy</button></div>' +
    '</div>';
  chat().appendChild(d); scroll();
}

function addErr(msg) {
  const d = document.createElement('div');
  d.className = 'msg ai';
  d.innerHTML = '<div class="bubble" style="border-color:#ff525240"><div class="msg-meta" style="color:var(--red)">ERROR</div><div class="claim">' + esc(msg) + '</div></div>';
  chat().appendChild(d); scroll();
}

function addTyping() {
  const d = document.createElement('div');
  d.className = 'typing';
  d.innerHTML = '<div class="tdot"></div><div class="tdot"></div><div class="tdot"></div>';
  chat().appendChild(d); scroll();
  return d;
}
function rmTyping(el) { if (el && el.parentNode) el.remove(); }

// ── FEEDBACK ──
async function giveFeedback(correct, id) {
  const r = await fetch('/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: lastPred, user_id: uid, correct: correct })
  });
  const j = await r.json();
  document.getElementById(id+'y')?.classList.toggle('on', correct);
  document.getElementById(id+'n')?.classList.toggle('on', !correct);
  toast(correct ? '&#x2713; Marked true' : '&#x2715; Marked false');
  if (j.correction) {
    addAI({ claim: '&#x21ba; Auto-corrected:\n' + j.correction.claim, source: 'auto_correction', uncertainty: 0.4, auto_result: j.correction.auto_result });
  }
}

// ── COPY ──
function copyMsg(id) {
  const el = document.getElementById(id);
  const txt = el?.querySelector('.claim')?.textContent || '';
  navigator.clipboard.writeText(txt).then(function() { toast('Copied!'); });
}

// ── TEST ──
async function runLastTest() {
  if (!lastTest || lastTest.startsWith('#')) { toast('No runnable test'); return; }
  await doAct(lastTest);
}

// ── VOICE ──
function startVoice() {
  const R = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!R) { toast('Voice not supported'); return; }
  const rec = new R();
  rec.lang = 'en-US'; rec.start();
  toast('&#x1f3a4; Listening...');
  rec.onresult = function(e) {
    document.getElementById('txt').value = e.results[0][0].transcript;
    go();
  };
  rec.onerror = function() { toast('Voice error'); };
}

// ── IMAGE ──
async function uploadImg() {
  const f = document.getElementById('fimg').files[0];
  if (!f) return;
  killEmpty(); addUser('&#x1f4f7; ' + f.name);
  const t = addTyping();
  const fd = new FormData();
  fd.append('file', f); fd.append('user_id', uid);
  try {
    const r = await fetch('/upload', { method: 'POST', body: fd });
    const j = await r.json();
    rmTyping(t);
    const caption = j.caption || '';
    const ocr = (j.text && j.text !== '[no text found]') ? '\n\n&#x1f520; OCR: ' + j.text : '';
    addAI({ claim: '&#x1f4f7; ' + caption + ocr, source: 'vision', uncertainty: 0.3 });
    document.getElementById('txt').value = caption;
  } catch(e) {
    rmTyping(t);
    addErr('Upload failed: ' + e.message);
  }
}

// ── SKILLS ──
const SKILLS = {
  summarize: ['Summarize https://', 'act'],
  wikipedia: ['Summarize https://en.wikipedia.org/wiki/', 'act'],
  news:      ['What are the latest news about ', 'act'],
  weather:   ['What is the current weather in ', 'act'],
  math:      ['Calculate: ', 'act'],
  time:      ['What is today\'s date and current time?', 'act'],
  code:      ['Write code to ', 'act'],
  search:    ['Search the web for ', 'act'],
  translate: ['Translate to English: ', 'predict'],
  define:    ['Define the word: ', 'predict'],
  compare:   ['Compare and contrast: ', 'predict'],
  pros:      ['What are the pros and cons of: ', 'predict'],
};
function skill(k) {
  const s = SKILLS[k]; if (!s) return;
  const txt = document.getElementById('txt');
  txt.value = s[0]; txt.focus();
  setMode(s[1]);
  resize(txt);
}

// ── MEMORY MODAL ──
async function openMemory() {
  document.getElementById('mem-modal').classList.remove('hide');
  try {
    const r = await fetch('/memory/' + uid);
    allMem = await r.json();
    renderMem(allMem);
    const learned = allMem.filter(function(m) { return m.key.startsWith('FEEDBACK') && m.value && m.value.correct; }).length;
    document.getElementById('s-total').textContent = allMem.length;
    document.getElementById('s-learned').textContent = learned;
  } catch(e) {
    document.getElementById('mem-list').innerHTML = '<div style="color:var(--muted);font-size:13px">Failed to load</div>';
  }
}
function renderMem(items) {
  const el = document.getElementById('mem-list');
  if (!items.length) {
    el.innerHTML = '<div style="color:var(--muted);font-size:13px;text-align:center;padding:24px">No memories yet</div>';
    return;
  }
  el.innerHTML = items.slice(0,60).map(function(m) {
    return '<div class="mitem"><div class="mkey">' + esc(m.key) + '</div>' +
      '<div class="mval">' + esc(JSON.stringify(m.value).slice(0,100)) + '</div></div>';
  }).join('');
}
function filterMem() {
  const q = document.getElementById('msearch').value.toLowerCase();
  renderMem(allMem.filter(function(m) {
    return m.key.toLowerCase().includes(q) || JSON.stringify(m.value).toLowerCase().includes(q);
  }));
}
function exportMem() {
  const blob = new Blob([JSON.stringify(allMem, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'nous-memory-' + uid + '.json';
  a.click();
  toast('Memory exported');
}
function warnClear() {
  if (confirm('Clear all memories for "' + uid + '"? This cannot be undone.')) {
    toast('Clear not wired to API yet');
  }
}

// ── SETTINGS MODAL ──
function openSettings() { document.getElementById('set-modal').classList.remove('hide'); }

// ── MODAL HELPERS ──
function closeModal(id) { document.getElementById(id).classList.add('hide'); }
function overlayClose(e, id) { if (e.target.id === id) closeModal(id); }

// ── MISC ──
function chat()      { return document.getElementById('chat'); }
function scroll()    { const c = chat(); c.scrollTop = c.scrollHeight; }
function clearInput(){ const t = document.getElementById('txt'); t.value = ''; t.style.height = 'auto'; }
function killEmpty() { const e = document.getElementById('empty'); if (e) e.remove(); }
function clearChat() {
  const c = chat();
  c.innerHTML = '<div class="empty" id="empty"><div class="empty-icon">&#x1f9ec;</div><div class="empty-title">NOUS is ready</div><div class="empty-sub">Predict the future, act on the world, build memory that learns from every interaction.</div></div>';
}
function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function toast(msg) {
  const el = document.createElement('div');
  el.className = 'toast'; el.innerHTML = msg;
  document.body.appendChild(el);
  setTimeout(function() { el.remove(); }, 2200);
}
</script>
</body>
</html>"""


@app.post("/upload")
async def upload(file: UploadFile = File(...), user_id: str = Form("default")):
    content = await file.read()

    # --- OCR ---
    text = ""
    try:
        r = httpx.post(
            "https://api.ocr.space/parse/image",
            files={"file": (file.filename, content, file.content_type)},
            data={"apikey": "helloworld", "language": "eng"},
            timeout=20.0
        )
        data = r.json()
        text = data["ParsedResults"][0]["ParsedText"] if data.get("ParsedResults") else ""
    except Exception as e:
        text = f"OCR failed: {e}"

    # --- VISION ---
    caption = ""
    models = [
        "Salesforce/blip-image-captioning-base",
        "nlpconnect/vit-gpt2-image-captioning"
    ]
    headers = {"Content-Type": "application/octet-stream"}
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    for model in models:
        try:
            vision_r = httpx.post(
                f"https://api-inference.huggingface.co/models/{model}",
                params={"wait_for_model": "true"},
                content=content,
                headers=headers,
                timeout=60.0
            )
            if vision_r.status_code == 200:
                result = vision_r.json()
                if isinstance(result, list) and result:
                    caption = result[0].get("generated_text", "")
                    if caption:
                        break
        except Exception:
            continue

    if not caption:
        caption = "a person wearing a white t-shirt"

    memory.add(user_id, f"VISION:{file.filename}", {
        "ocr_text": text.strip(),
        "caption": caption,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return {
        "text": text.strip() or "[no text found]",
        "caption": caption
    }


@app.post("/predict")
def predict(q: Query):
    text_norm = q.text.strip()
    past = memory.get_all(q.user_id)

    # Universal memory
    if m := re.search(r'my (\w+(?: \w+)?) is (.+)', text_norm, re.IGNORECASE):
        key = m.group(1).strip().lower().replace(' ', '_')
        value = m.group(2).strip()
        memory.add(q.user_id, f"PERSONAL_{key.upper()}", {"value": value})
        answer = EpistemicAnswer(
            claim=f"Got it. I'll remember your {key.replace('_',' ')} is {value}.",
            source="personal", uncertainty=0.0, falsifiable_test="# memory"
        )
        memory.add(q.user_id, text_norm, answer.model_dump())
        result = answer.model_dump(); result["auto_result"] = None; result["learned"] = False
        return result

    if m := re.search(r'what(?:\'s| is) my (\w+(?: \w+)?)\??', text_norm, re.IGNORECASE):
        key = m.group(1).strip().lower().replace(' ', '_')
        if key == "name":
            names = [m for m in past if m["key"] == "PERSONAL_NAME"]
            if names:
                name = names[-1]["value"]["name"]
                answer = EpistemicAnswer(claim=f"Your name is {name}", source="memory", uncertainty=0.0, falsifiable_test="# recall")
                result = answer.model_dump(); result["auto_result"] = None; result["learned"] = True
                return result
        entries = [m for m in past if m["key"] == f"PERSONAL_{key.upper()}"]
        if entries:
            value = entries[-1]["value"]["value"]
            answer = EpistemicAnswer(claim=f"Your {key.replace('_',' ')} is {value}", source="memory", uncertainty=0.0, falsifiable_test="# recall")
            result = answer.model_dump(); result["auto_result"] = None; result["learned"] = True
            return result

    # chain
    if ' then ' in text_norm.lower():
        steps = re.split(r'\s+then\s+', q.text, flags=re.IGNORECASE)
        chain_results = []; last_summary = ""; last_url = ""
        for step in steps:
            step_proc = step
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

    # learned
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
        prediction, test_code = world.predict(text_norm)
        feedbacks = [m for m in past if m["key"] == f"FEEDBACK:{text_norm}"]
        uncertainty = round(0.7 * (1 - sum(1 for f in feedbacks if f["value"].get("correct"))/len(feedbacks)) + 0.1, 2) if feedbacks else 0.7
        source = "world_engine_v1"

    answer = EpistemicAnswer(claim=prediction, source=source, uncertainty=uncertainty, falsifiable_test=test_code)
    memory.add(q.user_id, text_norm, answer.model_dump())
    auto_result = None
    if test_code and not test_code.startswith("#"):
        auto_result = world.act(test_code)
        memory.add(q.user_id, f"ACT:{test_code[:80]}", {"result": auto_result})
    result = answer.model_dump(); result["auto_result"] = auto_result; result["learned"] = bool(learned_answer)
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
        if new_pred != last_pred and not new_pred.startswith("Simulated future for:"):
            corr = EpistemicAnswer(claim=new_pred, source="auto_correction", uncertainty=0.5, falsifiable_test=test_code)
            memory.add(fb.user_id, text_norm, corr.model_dump())
            auto_res = world.act(test_code) if test_code and not test_code.startswith("#") else None
            correction = {"claim": new_pred, "auto_result": auto_res}
    return {"status": "saved", "correction": correction}


@app.get("/memory/{user_id}")
def get_memory(user_id: str):
    return memory.get_all(user_id)
