
const express = require("express");
const cors = require("cors");
require("dotenv").config();
const ask = require("./ask");
const app = express();
const chargeAnalysisRoutes = require('./routes/chargeAnalysis');
const chatRoutes = require('./routes/chat');


app.use(cors({
  origin: [
    'http://localhost:4200',
    // 'https://YOUR-FRONTEND.onrender.com'
  ]
}));

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

app.get('/api/health', (req, res) => {
  res.json({ ok: true });
});
app.use('/api/charges', chargeAnalysisRoutes);


app.use('/api/chat', chatRoutes);

const port = process.env.PORT || 4242;
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});