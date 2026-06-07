
// =========================
// EMERGENT BRAIN v0.1.1
// =========================

const NODE_COUNT = 20;
const CONNECTIONS_PER_NODE = 4;

const LEARNING_RATE = 0.005;   // reduced for stability
const DECAY = 0.995;           // stronger stability
const TICK_INTERVAL = 200;

const STIMULUS_INTERVAL = 25;

// -------------------------
// NODE CLASS
// -------------------------
class Node {
  constructor(id) {
    this.id = id;
    this.state = Math.random() * 2 - 1;
    this.output = 0;
    this.inputs = []; // { from, weight }
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

    // -------------------------
    // RULE 1: MEMORY UPDATE
    // smoother integration (more brain-like)
    // -------------------------
    this.state =
      (0.85 * this.state) +
      (0.15 * input_sum);

    // -------------------------
    // RULE 2: OUTPUT
    // -------------------------
    this.output = Math.tanh(this.state);

    // -------------------------
    // track activity (for observation)
    // -------------------------
    this.activity = Math.abs(this.output);

    // -------------------------
    // RULE 3: LEARNING (stabilized Hebbian-style)
    // -------------------------
    for (const conn of this.inputs) {
      const pre = nodes[conn.from].output;
      const post = this.output;

      // correlation learning (more stable than raw multiplication)
      const delta = LEARNING_RATE * pre * post;

      conn.weight += delta;

      // clamp weights
      conn.weight = Math.max(-1, Math.min(1, conn.weight));

      // decay
      conn.weight *= DECAY;
    }
  }
}

// -------------------------
// CREATE NETWORK
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
// EXTERNAL STIMULUS
// -------------------------
function stimulate(nodes, tick) {
  if (tick % STIMULUS_INTERVAL === 0) {
    const target = Math.floor(Math.random() * NODE_COUNT);

    // softer stimulus (prevents chaos spikes)
    nodes[target].state += (Math.random() * 2 - 1) * 0.5;
  }
}

// -------------------------
// METRICS
// -------------------------
function getMetrics(nodes) {
  const avgState =
    nodes.reduce((s, n) => s + n.state, 0) / NODE_COUNT;

  const avgActivity =
    nodes.reduce((s, n) => s + n.activity, 0) / NODE_COUNT;

  return { avgState, avgActivity };
}

// -------------------------
// BRAIN LOOP
// -------------------------
const nodes = createNetwork();
let tick = 0;

function runStep() {
  stimulate(nodes, tick);

  for (const node of nodes) {
    node.update(nodes);
  }

  if (tick % 10 === 0) {
    const { avgState, avgActivity } = getMetrics(nodes);

    console.log(
      `Tick ${tick} | Avg State: ${avgState.toFixed(3)} | Activity: ${avgActivity.toFixed(3)}`
    );
  }

  tick++;
}

// -------------------------
// START
// -------------------------
setInterval(runStep, TICK_INTERVAL);
