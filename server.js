const express = require("express");
const path = require("path");
const { step } = require("./brain");

const app = express();
app.use(express.json());

// serve frontend
app.use(express.static(path.join(__dirname, "public")));

// chat endpoint
app.post("/chat", (req, res) => {
  const userMessage = req.body.message;

  const result = step(userMessage);

  res.json(result);
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log("Brain server running on port", PORT);
});
