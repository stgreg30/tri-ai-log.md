const express = require("express");
const cors = require("cors");
const fs = require("fs");

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static("public"));

// simple brain memory endpoint
app.get("/memory", (req, res) => {
  if (!fs.existsSync("memory_log.json")) {
    return res.json([]);
  }

  const data = JSON.parse(fs.readFileSync("memory_log.json"));
  res.json(data.slice(-50)); // last 50 logs
});

// simple chat endpoint (for later upgrade)
app.post("/talk", (req, res) => {
  const message = req.body.message;

  res.json({
    reply: "Brain received: " + message,
    status: "alive"
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log("Brain web running on port " + PORT);
});