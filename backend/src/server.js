const express = require("express");
const cors = require("cors");
require("dotenv").config();

const ask = require("./ask");

const app = express();

app.use(cors());
app.use(express.json());

app.get("/health", (req,res)=>{
  res.send("API running");
});

app.post("/api/ask", async (req, res) => {
  const started = Date.now();

  try {
    const { question } = req.body;

    if (!question) {
      return res.status(400).json({ error: "Question required" });
    }

    const result = await ask(question);

    console.log("TOTAL /api/ask ms:", Date.now() - started);
    res.json(result);
  } catch (err) {
    console.error("API ERROR:", err?.response?.data || err);
    console.log("FAILED /api/ask ms:", Date.now() - started);

    res.status(500).json({
      error: "Server error",
      details: err?.response?.data || err?.message || String(err),
    });
  }
});

const PORT = 4242;

app.listen(PORT, ()=>{
  console.log(`API running on port ${PORT}`);
});