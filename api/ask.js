import { ask } from '../backend/src/ask.js';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const mod = await import('../backend/src/ask.js');
    const ask = mod.ask;

    if (typeof ask !== 'function') {
      throw new Error('ask export not found from ../backend/src/ask.js');
    }

    const { question } = req.body || {};

    if (!question) {
      return res.status(400).json({ error: 'Question required' });
    }

    const result = await ask(question);
    return res.status(200).json(result);
  } catch (err) {
    console.error('Vercel /api/ask crash:', err);
    return res.status(500).json({
      error: 'Server error',
      details: err?.message || String(err),
    });
  }
}