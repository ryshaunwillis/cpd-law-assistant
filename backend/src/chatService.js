const ask = require('../src/ask');
const { classifyQueryIntent } = require('./queryRouter');
const { analyzeNarrativeForCharges } = require('./chargeService');

function buildChargeText(chargeResult) {
  const lines = []; 

  const addSection = (title, items) => {
    if (!items || !items.length) return;

    lines.push(title);
    for (const item of items) {
      lines.push(`- ${item.citation} — ${item.sectionTitle}`);
      if (item.whyItFits?.length) {
        lines.push(`  Why it fits: ${item.whyItFits.join(' | ')}`);
      }
      if (item.missingFacts?.length) {
        lines.push(`  Missing facts: ${item.missingFacts.join(' | ')}`);
      }
    }
    lines.push('');
  };

  addSection('Likely charges:', chargeResult.likelyCharges);
  addSection('Possible charges:', chargeResult.possibleCharges);
  addSection('Possible enhanced charges:', chargeResult.possibleEnhancedCharges);

  if (chargeResult.globalMissingFacts?.length) {
    lines.push('Important missing facts:');
    for (const fact of chargeResult.globalMissingFacts) {
      lines.push(`- ${fact}`);
    }
    lines.push('');
  }

  if (chargeResult.disclaimer) {
    lines.push(chargeResult.disclaimer);
  }

  return lines.join('\n').trim();
}

function buildContextualQuery(query, history = []) {
  if (!history.length) return query;

  const recent = history.slice(-6);

  const historyBlock = recent
    .map((msg) => {
      const role = msg.role === 'assistant' ? 'Assistant' : 'User';
      return `${role}: ${msg.text}`;
    })
    .join('\n');

  return [
    'Use the prior conversation as context when relevant.',
    '',
    historyBlock,
    '',
    `Current user message: ${query}`,
  ].join('\n');
}

async function handleChatQuery(query, history = []) {
  const routing = classifyQueryIntent(query);
  const contextualQuery = buildContextualQuery(query, history);

  if (routing.intent === 'charges') {
    const chargeResult = await analyzeNarrativeForCharges(contextualQuery, {
      limit: 12,
      threshold: 0.3,
    });

    return {
      intent: 'charges',
      answer: buildChargeText(chargeResult),
      chargeAnalysis: chargeResult,
      sources: [],
    };
  }

  if (routing.intent === 'hybrid') {
    const [qaResult, chargeResult] = await Promise.all([
      ask(contextualQuery),
      analyzeNarrativeForCharges(contextualQuery, {
        limit: 12,
        threshold: 0.3,
      }),
    ]);

    const combinedAnswer = [
      qaResult.answer || '',
      '',
      '---',
      '',
      buildChargeText(chargeResult),
    ]
      .join('\n')
      .trim();

    return {
      intent: 'hybrid',
      answer: combinedAnswer,
      chargeAnalysis: chargeResult,
      sources: qaResult.sources || [],
    };
  }

  const qaResult = await ask(contextualQuery);

  return {
    intent: 'qa',
    answer: qaResult.answer || '',
    chargeAnalysis: null,
    sources: qaResult.sources || [],
  };
}

module.exports = {
  handleChatQuery,
};