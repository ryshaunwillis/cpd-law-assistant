const { searchIlcs } = require('./ilcsRetriever');
const { analyzeChargeMatches } = require('./chargeAnalyzer');

async function analyzeNarrativeForCharges(queryText, options = {}) {
  const retrieval = await searchIlcs(queryText, {
    limit: options.limit || 12,
    threshold: options.threshold || 0.3,
    dedupeSections: true,
  });

  return analyzeChargeMatches(queryText, retrieval);
}

module.exports = {
  analyzeNarrativeForCharges,
};