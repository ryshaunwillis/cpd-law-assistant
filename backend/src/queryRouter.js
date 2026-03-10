function normalize(text) {
  return (text || '').toLowerCase().trim();
}

function includesAny(text, phrases) {
  return phrases.some((phrase) => text.includes(phrase));
}

function classifyQueryIntent(query) {
  const text = normalize(query);

  const chargePhrases = [
    'what can i charge',
    'what could i charge',
    'what charges',
    'possible charges',
    'charge this',
    'chargeable offense',
    'what offense applies',
    'what can the offender be charged with',
    'what can the suspect be charged with',
  ];

  const incidentNarrativeSignals = [
    'offender',
    'victim',
    'suspect',
    'punched',
    'hit',
    'struck',
    'slapped',
    'kicked',
    'choked',
    'strangled',
    'threatened',
    'stole',
    'took',
    'robbed',
    'broke in',
    'forced entry',
    'gun',
    'knife',
    'weapon',
    'injury',
    'injured',
    'domestic',
    'girlfriend',
    'boyfriend',
    'wife',
    'husband',
  ];

  const qaPhrases = [
    'what does the law say',
    'what is the law',
    'what does illinois law say',
    'what does cpd say',
    'what is the rule',
    'is it allowed',
    'can officers',
    'according to cpd',
    'according to illinois law',
    'what is the policy',
    'what does the directive say',
  ];

  const asksForStatuteExplanation = [
    'under illinois law',
    'under ilcs',
    'is this battery or aggravated battery',
    'is this robbery',
    'is this burglary',
    'would this be',
  ];

  const chargeScore =
    (includesAny(text, chargePhrases) ? 3 : 0) +
    incidentNarrativeSignals.filter((p) => text.includes(p)).length;

  const qaScore =
    (includesAny(text, qaPhrases) ? 3 : 0) +
    (includesAny(text, asksForStatuteExplanation) ? 2 : 0);

  if (chargeScore >= 3 && qaScore >= 2) {
    return {
      intent: 'hybrid',
      chargeScore,
      qaScore,
    };
  }

  if (chargeScore >= 3) {
    return {
      intent: 'charges',
      chargeScore,
      qaScore,
    };
  }

  return {
    intent: 'qa',
    chargeScore,
    qaScore,
  };
}

module.exports = {
  classifyQueryIntent,
};