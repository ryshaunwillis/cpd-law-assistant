const express = require('express');
const { handleChatQuery } = require('../chatService');

const router = express.Router();

router.post('/', async (req, res) => {
  try {
    const query = (req.body?.query || '').trim();
    const history = Array.isArray(req.body?.history) ? req.body.history : [];

    if (!query) {
      return res.status(400).json({
        success: false,
        error: 'Query is required.',
      });
    }

    const result = await handleChatQuery(query, history);

    return res.json({
      success: true,
      ...result,
    });
  } catch (error) {
    console.error('CHAT ROUTE ERROR:', error);

    return res.status(500).json({
      success: false,
      error: 'Failed to process chat request.',
      details: error.message,
    });
  }
});

module.exports = router;