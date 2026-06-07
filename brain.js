const fs = require("fs");

// =========================
// EMERGENT BRAIN v0.1 + MEMORY
// =========================

const NODE_COUNT = 20;
const CONNECTIONS_PER_NODE = 4;
const LEARNING_RATE = 0.005;
const DECAY = 0.995;
const TICK_INTERVAL = 200;
const STIMULUS_INTERVAL = 25;

// -------------------------
// MEMORY FUNCTION
// -------------------------
function saveMemory(data) {
  const file = "memory_log.json";

  let log = [];

  if (fs.existsSync(file)) {
    try {
      log = JSON.parse(fs.readFileSync(file));
    } catch (e) {
      log = [];
    }
  }

  log.push(data);

  fs.writeFileSync(file, JSON.stringify(log, null, 2));
}

// -------------------------
// NODE CLASS
// -------------------------
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
    const input_sum = this.computeInput(nodes);

    // memory update
    this.state = (0.85 * this.state) + (0.15 * input_sum);

    // output
    this.output = Math.tanh(this.state);

    this.activity = Math.abs(this.output);

    // learning
    for (const conn of this.inputs) {
      const pre = nodes[conn.from].output;
      const post = this.output;

      conn.weight += LEARNING_RATE * pre * post;

      conn.weight = Math.max(-1, Math.min(1, conn.weight));

      conn.weight *= DECAY;
    }
  }
}

// -------------------------
// NETWORK
// -------------------------
function createNetwork() {
  const nodes = [];

  for (let i = 0; i < NODE_COUNT; i++) {
    nodes.push(new Node(i));
  }

  for (const node of nodes) {
    for (let i = 0; i < CONNECTIONS_PER_NODE; i++) {
      const target = Math.floor(Math.random() * NODE_COUNT);

      node.inputs.push({
        from: target,
        weight: Math.random() * 2 - 1
      });
    }
  }

  return nodes;
}

// -------------------------
// STIMULUS
// -------------------------
function stimulate(nodes, tick) {
  if (tick % STIMULUS_INTERVAL === 0) {
    const target = Math.floor(Math.random() * NODE_COUNT);
    nodes[target].state += (Math.random() * 2 - 1) * 0.5;
  }
}

// -------------------------
// RUN
// -------------------------
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

  // -------------------------
  // MEMORY SAVE (IMPORTANT PART)
  // -------------------------
  if (tick % 10 === 0) {
    saveMemory({
      tick,
      avgState,
      avgActivity,
      timestamp: Date.now()
    });
  }

  console.log(
    `Tick ${tick} | Avg State: ${avgState.toFixed(3)} | Activity: ${avgActivity.toFixed(3)}`
  );

  tick++;
}

// -------------------------
setInterval(runStep, TICK_INTERVAL);