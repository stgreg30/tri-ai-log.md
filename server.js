const express = require("express");
const cors = require("cors");
const fs = require("fs");

const app = express();
app.use(cors());
app.use(express.json());

// =========================
// EMERGENT BRAIN CORE
// =========================

const NODE_COUNT = 20;
const CONNECTIONS_PER_NODE = 4;
const LEARNING_RATE = 0.005;
const DECAY = 0.997;

const MEMORY_FILE = "memory_log.json";
const MAX_MEMORY = 500;

function loadMemory() {
  try {
    if (!fs.existsSync(MEMORY_FILE)) return [];
    return JSON.parse(fs.readFileSync(MEMORY_FILE, "utf-8") || "[]");
  } catch {
    return [];
  }
}

function saveMemory(entry) {
  const mem = loadMemory();
  mem.push(entry);

  if (mem.length > MAX_MEMORY) {
    mem.splice(0, mem.length - MAX_MEMORY);
  }

  fs.writeFileSync(MEMORY_FILE, JSON.stringify(mem, null, 2));
}

// =========================
// NODE SYSTEM
// =========================

class Node {
  constructor(id) {
    this.id = id;
    this.state = Math.random() * 2 - 1;
    this.output = 0;
    this.inputs = [];
    this.activity = 0;
  }

  compute(nodes) {
    let sum = 0;
    for (const c of this.inputs) {
      sum += nodes[c.from].output * c.weight;
    }
    return sum;
  }

  update(nodes) {
    const input = this.compute(nodes);

    this.state = this.state * 0.88 + input * 0.12;
    this.output = Math.tanh(this.state);
    this.activity = Math.abs(this.output);

    for (const c of this.inputs) {
      const pre = nodes[c.from].output;
      const post = this.output;

      c.weight += LEARNING_RATE * pre * post;
      c.weight = Math.max(-1.5, Math.min(1.5, c.weight));
      c.weight *= DECAY;
    }
  }
}

// =========================
// NETWORK
// =========================

function createNetwork() {
  const nodes = [];

  for (let i = 0; i < NODE_COUNT; i++) {
    nodes.push(new Node(i));
  }

  for (const n of nodes) {
    for (let i = 0; i < CONNECTIONS_PER_NODE; i++) {
      n.inputs.push({
        from: Math.floor(Math.random() * NODE_COUNT),
        weight: Math.random() * 2 - 1
      });
    }
  }

  return nodes;
}

const nodes = createNetwork();
let tick = 0;

// =========================
// BRAIN LOOP
// =========================

function step() {
  // small random stimulation
  if (tick % 25 === 0) {
    const t = Math.floor(Math.random() * NODE_COUNT);
    nodes[t].state += (Math.random() - 0.5) * 0.8;
  }

  for (const n of nodes) n.update(nodes);

  let avgState = 0;
  let avgActivity = 0;

  for (const n of nodes) {
    avgState += n.state;
    avgActivity += n.activity;
  }

  avgState /= NODE_COUNT;
  avgActivity /= NODE_COUNT;

  if (tick % 10 === 0) {
    saveMemory({
      tick,
      avgState,
      avgActivity,
      timestamp: Date.now()
    });
  }

  tick++;

  return { tick, avgState, avgActivity };
}

// run brain loop continuously
setInterval(step, 200);

// =========================
// WEB API (THIS IS YOUR WEBSITE)
// =========================

// health check
app.get("/", (req, res) => {
  res.json({
    status: "brain online 🧠",
    tick,
  });
});

// live brain state
app.get("/state", (req, res) => {
  const mem = step(); // returns current snapshot
  res.json(mem);
});

// memory logs (THIS FIXES YOUR GITHUB QUESTION)
app.get("/memory", (req, res) => {
  res.json(loadMemory());
});

// chat endpoint (simple interface)
app.post("/chat", (req, res) => {
  const message = req.body.message || "";

  const mem = loadMemory().slice(-10);

  const response =
    `I received: "${message}". ` +
    `My current state is ${step().avgState.toFixed(3)} ` +
    `based on recent memory patterns.`;

  res.json({
    reply: response,
    memoryUsed: mem.length
  });
});

// =========================
// START SERVER
// =========================

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log("Brain server running on port", PORT);
});