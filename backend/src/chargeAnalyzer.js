function normalizeText(value) {
  return (value || '').toString().trim();
}

function lower(value) {
  return normalizeText(value).toLowerCase();
}

function unique(arr) {
  return [...new Set((arr || []).filter(Boolean))];
}

function extractNarrativeSignals(queryText) {
  const text = lower(queryText);

  const hasAny = (phrases) => phrases.some((p) => text.includes(p));

  const signals = {
    violence: hasAny([
      'punch', 'punched', 'hit', 'struck', 'slapped', 'kicked',
      'beat', 'beaten', 'jumped', 'shoved', 'attacked', 'fight'
    ]),
    threat: hasAny([
      'threat', 'threatened', 'kill', 'shoot', 'harm', 'intimidat',
      'stalking', 'harass'
    ]),
    weapon: hasAny([
      'gun', 'firearm', 'pistol', 'revolver', 'rifle', 'shotgun',
      'knife', 'blade', 'bat', 'weapon'
    ]),
    seriousInjury: hasAny([
      'great bodily harm', 'serious injury', 'broken jaw', 'broken bone',
      'unconscious', 'hospital', 'stitches', 'severe bleeding',
      'disfigurement', 'permanent disability'
    ]),
    bodilyHarm: hasAny([
      'injury', 'injured', 'bleeding', 'pain', 'bruising', 'swelling',
      'bodily harm'
    ]),
    domestic: hasAny([
      'girlfriend', 'boyfriend', 'wife', 'husband', 'ex girlfriend',
      'ex-boyfriend', 'ex wife', 'ex husband', 'dating', 'domestic',
      'household member', 'family member', 'child mother', 'baby mother'
    ]),
    theft: hasAny([
      'stole', 'stolen', 'took', 'shoplifted', 'shoplifting',
      'retail theft', 'took property', 'took money'
    ]),
    robbery: hasAny([
      'robbery', 'mugging', 'stick up', 'took by force', 'snatched'
    ]),
    burglary: hasAny([
      'broke in', 'forced entry', 'entered house', 'entered residence',
      'entered building', 'burglary', 'residential burglary'
    ]),
    vehicle: hasAny([
      'car', 'vehicle', 'motor vehicle', 'stolen car', 'carjacking'
    ]),
    police: hasAny([
      'police', 'officer', 'peace officer', 'arrest', 'resisting',
      'obstructing', 'ran from police'
    ]),
    childVictim: hasAny([
      'child', 'kid', 'minor', 'juvenile'
    ]),
    death: hasAny([
      'killed', 'dead', 'death', 'deceased', 'fatal', 'homicide', 'murder'
    ]),
    strangulation: hasAny([
      'choked', 'choke', 'strangled', 'strangle', 'could not breathe',
      'impede breathing'
    ]),
  };

  return signals;
}

function scoreMatch(match, signals) {
  let score = Number(match.similarity || 0);

  const offenseFamily = lower(match.offenseFamily);
  const title = lower(match.sectionTitle);
  const content = lower(match.content);

  const hasFieldValue = (fieldValues, expected) =>
    (fieldValues || []).map((v) => lower(v)).includes(expected);

  if (signals.violence && ['battery', 'domestic_battery', 'assault'].includes(offenseFamily)) {
    score += 0.18;
  }

  if (signals.seriousInjury && (title.includes('aggravated battery') || hasFieldValue(match.aggravatingFactors, 'great_bodily_harm'))) {
    score += 0.22;
  }

  if (signals.bodilyHarm && offenseFamily === 'battery') {
    score += 0.12;
  }

  if (signals.domestic && offenseFamily === 'domestic_battery') {
    score += 0.26;
  }

  if (signals.strangulation && (offenseFamily === 'domestic_battery' || content.includes('strangulation'))) {
    score += 0.25;
  }

  if (signals.weapon && offenseFamily === 'weapons') {
    score += 0.22;
  }

  if (signals.weapon && title.includes('armed robbery')) {
    score += 0.18;
  }

  if (signals.robbery && offenseFamily === 'robbery') {
    score += 0.25;
  }

  if (signals.theft && offenseFamily === 'theft') {
    score += 0.18;
  }

  if (signals.burglary && offenseFamily === 'burglary') {
    score += 0.25;
  }

  if (signals.vehicle && offenseFamily === 'vehicle_offense') {
    score += 0.18;
  }

  if (signals.threat && offenseFamily === 'threat_intimidation') {
    score += 0.25;
  }

  if (signals.police && offenseFamily === 'obstructing_police') {
    score += 0.24;
  }

  if (signals.childVictim && (content.includes('child') || content.includes('minor'))) {
    score += 0.12;
  }

  if (signals.death && offenseFamily === 'homicide') {
    score += 0.35;
  }

  return score;
}

function buildWhyItFits(match, signals) {
  const reasons = [];

  if (signals.violence && ['battery', 'domestic_battery', 'assault'].includes(lower(match.offenseFamily))) {
    reasons.push('The narrative describes violent physical conduct.');
  }

  if (signals.bodilyHarm && (match.injuryTypes || []).length) {
    reasons.push('The facts suggest bodily harm or injury.');
  }

  if (signals.seriousInjury && lower(match.sectionTitle).includes('aggravated')) {
    reasons.push('The facts may support an aggravated form based on injury severity.');
  }

  if (signals.domestic && lower(match.offenseFamily) === 'domestic_battery') {
    reasons.push('The relationship described may place this in a domestic context.');
  }

  if (signals.strangulation && lower(match.content).includes('strangulation')) {
    reasons.push('The narrative suggests choking or impeded breathing.');
  }

  if (signals.weapon && ((match.weaponTypes || []).length || lower(match.content).includes('firearm') || lower(match.content).includes('weapon'))) {
    reasons.push('A weapon may be involved based on the narrative.');
  }

  if (signals.robbery && lower(match.offenseFamily) === 'robbery') {
    reasons.push('The facts suggest taking property by force or threat.');
  }

  if (signals.theft && lower(match.offenseFamily) === 'theft') {
    reasons.push('The facts suggest unauthorized taking or control of property.');
  }

  if (signals.burglary && lower(match.offenseFamily) === 'burglary') {
    reasons.push('The narrative suggests unlawful entry tied to theft or another felony.');
  }

  if (signals.police && lower(match.offenseFamily) === 'obstructing_police') {
    reasons.push('The facts suggest resisting, obstructing, or fleeing from officers.');
  }

  if (signals.threat && lower(match.offenseFamily) === 'threat_intimidation') {
    reasons.push('The narrative includes threats, intimidation, or harassment language.');
  }

  if (signals.death && lower(match.offenseFamily) === 'homicide') {
    reasons.push('The narrative involves a death or fatal injury.');
  }

  if (!reasons.length) {
    reasons.push('This statute is semantically similar to the incident narrative.');
  }

  return unique(reasons);
}

function buildMissingFacts(match, signals) {
  const missing = [];

  const title = lower(match.sectionTitle);
  const offenseFamily = lower(match.offenseFamily);

  if (offenseFamily === 'battery' || title.includes('battery')) {
    missing.push('Whether the victim suffered bodily harm or only insulting/provoking contact.');
  }

  if (title.includes('aggravated') || (match.aggravatingFactors || []).length) {
    missing.push('Whether there was great bodily harm, disfigurement, a weapon, or another aggravating factor.');
  }

  if (offenseFamily === 'domestic_battery') {
    missing.push('The exact relationship between offender and victim.');
  }

  if (offenseFamily === 'robbery') {
    missing.push('Whether property was taken by force or threat, and whether a weapon was used.');
  }

  if (offenseFamily === 'burglary') {
    missing.push('Whether entry was without authority and whether there was intent to commit theft or another felony.');
  }

  if (offenseFamily === 'theft') {
    missing.push('The property type and value involved.');
  }

  if (offenseFamily === 'vehicle_offense') {
    missing.push('Whether the vehicle was stolen, possessed knowing it was stolen, or taken by force.');
  }

  if (offenseFamily === 'weapons') {
    missing.push('The exact weapon type, possession status, and where the conduct occurred.');
  }

  if (offenseFamily === 'obstructing_police') {
    missing.push('Whether the suspect resisted, obstructed, fled, or used force against officers.');
  }

  if (offenseFamily === 'threat_intimidation') {
    missing.push('The exact threatening words, method of communication, and intended effect on the victim.');
  }

  if (offenseFamily === 'homicide') {
    missing.push('The mental state, causation facts, and surrounding circumstances of the death.');
  }

  if (signals.weapon && !title.includes('armed') && offenseFamily !== 'weapons') {
    missing.push('Whether weapon involvement supports an enhanced or additional charge.');
  }

  return unique(missing).slice(0, 4);
}

function classifyRecommendation(scoredMatch) {
  const score = scoredMatch.analysisScore;
  const title = lower(scoredMatch.sectionTitle);

  if (score >= 0.78) return 'likely';
  if (score >= 0.62) return title.includes('aggravated') ? 'possible_enhanced' : 'possible';
  return 'context';
}

function analyzeChargeMatches(queryText, retrievalResult) {
  const matches = retrievalResult?.matches || [];
  const signals = extractNarrativeSignals(queryText);

  const scored = matches
    .map((match) => {
      const analysisScore = scoreMatch(match, signals);
      return {
        ...match,
        analysisScore,
        recommendationType: classifyRecommendation({ ...match, analysisScore }),
        whyItFits: buildWhyItFits(match, signals),
        missingFacts: buildMissingFacts(match, signals),
      };
    })
    .sort((a, b) => b.analysisScore - a.analysisScore);

  const likelyCharges = scored.filter((m) => m.recommendationType === 'likely').slice(0, 4);
  const possibleCharges = scored.filter((m) => m.recommendationType === 'possible').slice(0, 4);
  const possibleEnhancedCharges = scored.filter((m) => m.recommendationType === 'possible_enhanced').slice(0, 4);
  const contextualMatches = scored.filter((m) => m.recommendationType === 'context').slice(0, 4);

  const globalMissingFacts = unique(
    scored.flatMap((m) => m.missingFacts || [])
  ).slice(0, 8);

  return {
    query: queryText,
    extractedSignals: signals,
    likelyCharges,
    possibleCharges,
    possibleEnhancedCharges,
    contextualMatches,
    globalMissingFacts,
    disclaimer:
      'These are candidate Illinois charges based on the facts provided and retrieved statutes. Final charging decisions depend on complete facts, statutory elements, current law, and agency/legal review.',
  };
}

module.exports = {
  analyzeChargeMatches,
  extractNarrativeSignals,
};