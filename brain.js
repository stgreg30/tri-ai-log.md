const fs = require("fs");

// =========================
// EMERGENT BRAIN v0.2 (STABLE)
// =========================

const NODE_COUNT = 20;
const CONNECTIONS_PER_NODE = 4;
const LEARNING_RATE = 0.005;
const DECAY = 0.997;

const TICK_INTERVAL = 200;
const STIMULUS_INTERVAL = 25;

const MEMORY_FILE = "memory_log.json";
const MAX_MEMORY_ENTRIES = 500;

// =========================
// MEMORY CACHE (IMPORTANT FIX)
// =========================
let memoryCache = [];

// load once at startup
function loadMemory() {
  try {
    if (!fs.existsSync(MEMORY_FILE)) return [];
    const data = fs.readFileSync(MEMORY_FILE, "utf-8");
    return JSON.parse(data || "[]");
  } catch (err) {
    return [];
  }
}

// initialize memory in RAM
memoryCache = loadMemory();

// optimized save (NO re-reading file every tick)
function saveMemory(entry) {
  memoryCache.push(entry);

  if (memoryCache.length > MAX_MEMORY_ENTRIES) {
    memoryCache.splice(0, memoryCache.length - MAX_MEMORY_ENTRIES);
  }

  try {
    fs.writeFileSync(MEMORY_FILE, JSON.stringify(memoryCache, null, 2));
  } catch (err) {
    console.error("Memory save failed:", err.message);
  }
}

// =========================
// NODE CLASS
// =========================
class Node {
  constructor(id) {
    this.id = id;
    this.state = Math.random() * 2 - 1;
    this.output = 0;
    this.inputs = [];
    this.activity = 0;
  }

  computeInput(nodes) {
    let sum = 0;

    for (const conn of this.inputs) {
      sum += nodes[conn.from].output * conn.weight;
    }

    return sum;
  }

  update(nodes) {
    const inputSum = this.computeInput(nodes);

    // smoother memory blending (more stable brain)
    this.state = this.state * 0.9 + inputSum * 0.1;

    this.output = Math.tanh(this.state);
    this.activity = Math.abs(this.output);

    for (const conn of this.inputs) {
      const pre = nodes[conn.from].output;
      const post = this.output;

      conn.weight += LEARNING_RATE * pre * post;

      // stable clamp
      conn.weight = Math.max(-1.2, Math.min(1.2, conn.weight));

      conn.weight *= DECAY;
    }
  }
}

// =========================
// NETWORK CREATION
// =========================
function createNetwork() {
  const nodes = [];

  for (let i = 0; i < NODE_COUNT; i++) {
    nodes.push(new Node(i));
  }

  for (const node of nodes) {
    for (let i = 0; i < CONNECTIONS_PER_NODE; i++) {
      node.inputs.push({
        from: Math.floor(Math.random() * NODE_COUNT),
        weight: Math.random() * 2 - 1
      });
    }
  }

  return nodes;
}

// =========================
// STIMULUS
// =========================
function stimulate(nodes, tick) {
  if (tick % STIMULUS_INTERVAL === 0) {
    const target = Math.floor(Math.random() * NODE_COUNT);
    nodes[target].state += (Math.random() - 0.5) * 0.6;
  }
}

// =========================
// RUN ENGINE
// =========================
const nodes = createNetwork();
let tick = 0;

function runStep() {
  stimulate(nodes, tick);

  for (const node of nodes) {
    node.update(nodes);
  }

  let avgState = 0;
  let avgActivity = 0;

  for (const node of nodes) {
    avgState += node.state;
    avgActivity += node.activity;
  }

  avgState /= NODE_COUNT;
  avgActivity /= NODE_COUNT;

  // memory write (throttled)
  if (tick % 10 === 0) {
    saveMemory({
      tick,
      avgState,
      avgActivity,
      activityLevel:
        avgActivity > 0.2
          ? "high"
          : avgActivity > 0.05
          ? "medium"
          : "low",
      timestamp: Date.now()
    });
  }

  console.log(
    `Tick ${tick} | State: ${avgState.toFixed(3)} | Activity: ${avgActivity.toFixed(3)}`
  );

  tick++;
}

setInterval(runStep, TICK_INTERVAL);