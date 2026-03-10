
const express = require("express");
const cors = require("cors");
require("dotenv").config();
const ask = require("./ask");
const app = express();
const chargeAnalysisRoutes = require('./routes/chargeAnalysis');
const chatRoutes = require('./routes/chat');


const allowedOrigins = [
  'http://localhost:4200',
  'https://cpd-law-assistant-frontend.onrender.com',
];

app.use(cors({
  origin(origin, callback) {
    if (!origin) return callback(null, true);

    if (allowedOrigins.includes(origin)) {
      return callback(null, true);
    }

    return callback(new Error(`CORS blocked for origin: ${origin}`));
  },
  credentials: false,
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