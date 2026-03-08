const axios = require("axios");
const searchChunks = require("./search");


async function embed(text) {
  const r = await axios.post(
    "https://api.openai.com/v1/embeddings",
    {
      model: process.env.EMBED_MODEL || "text-embedding-3-small",
      input: text,
    },
    {
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      timeout: 60000,
    }
  );

  return r.data.data[0].embedding;
}

function buildContext(sources) {
  return sources
    .map((s, i) => {
      const trimmed = (s.text || "").slice(0, 1200);
      return `[#${i + 1}] ${s.source} | ${s.title}\nURL: ${s.url}\n${trimmed}`;
    })
    .join("\n\n---\n\n");
}

function hasUsableResults(results) {
  if (!results || !results.length) return false;
  return results.some((r) => (r.text || "").trim().length > 120);
}

async function generateAnswer(question, sources) {
  const context = buildContext(sources);

  const r = await axios.post(
    "https://api.openai.com/v1/chat/completions",
    {
      model: process.env.CHAT_MODEL || "gpt-4.1-mini",
      temperature: 0,
      messages: [
        {
          role: "system",
          content:
            "Answer only from the provided excerpts. " +
            "If the answer is not in the excerpts, say you could not find it. " +
            "Give a short direct answer, then a Quotes section, then a Sources section.",
        },
        {
          role: "user",
          content: `Question:\n${question}\n\nExcerpts:\n${context}`,
        },
      ],
    },
    {
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      timeout: 60000,
    }
  );

  return r.data.choices[0].message.content;
}

async function ask(question) {
  const t0 = Date.now();

  const embedding = await embed(question);
  console.log("embed ms:", Date.now() - t0);

  const t1 = Date.now();
  const results = await searchChunks(embedding, question);
  console.log("search ms:", Date.now() - t1);

  if (!hasUsableResults(results)) {
    return {
      answer: "I could not find this information in the indexed CPD directives or ILCS.",
      sources: [],
    };
  }

  const t2 = Date.now();
  const answer = await generateAnswer(question, results);
  console.log("generate ms:", Date.now() - t2);

  return {
    answer,
    sources: results,
  };
}

module.exports = ask;