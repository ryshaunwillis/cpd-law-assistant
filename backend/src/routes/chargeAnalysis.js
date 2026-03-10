const express = require('express');
const { analyzeNarrativeForCharges } = require('../chargeService');

const router = express.Router();

router.post('/analyze', async (req, res) => {
  try {
    const query = (req.body?.query || '').trim();

    if (!query) {
      return res.status(400).json({
        error: 'Query is required.',
      });
    }

    const result = await analyzeNarrativeForCharges(query, {
      limit: 12,
      threshold: 0.3,
    });

    return res.json({
      success: true,
      ...result,
    });
  } catch (error) {
    console.error('CHARGE ANALYSIS ERROR:', error);

    return res.status(500).json({
      success: false,
      error: 'Failed to analyze charge candidates.',
      details: error.message,
    });
  }
});

module.exports = router;