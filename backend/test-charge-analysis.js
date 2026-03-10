require('dotenv').config();

const { analyzeNarrativeForCharges } = require('./src/chargeService');
const { closeRetriever } = require('./src/ilcsRetriever');

async function run() {
  const queries = [
    'offender punched victim multiple times in the face causing injury',
    'offender choked his girlfriend during an argument and she could not breathe',
    'offender forced entry into a residence and took a television',
    'offender threatened to kill victim over text messages',
  ];

  for (const query of queries) {
    console.log('\n==================================================');
    console.log('QUERY:', query);

    const result = await analyzeNarrativeForCharges(query, {
      limit: 12,
      threshold: 0.3,
    });

    console.log('\nLIKELY CHARGES:');
    for (const item of result.likelyCharges) {
      console.log(`- ${item.citation} | ${item.sectionTitle} | score=${item.analysisScore.toFixed(3)}`);
    }

    console.log('\nPOSSIBLE CHARGES:');
    for (const item of result.possibleCharges) {
      console.log(`- ${item.citation} | ${item.sectionTitle} | score=${item.analysisScore.toFixed(3)}`);
    }

    console.log('\nPOSSIBLE ENHANCED CHARGES:');
    for (const item of result.possibleEnhancedCharges) {
      console.log(`- ${item.citation} | ${item.sectionTitle} | score=${item.analysisScore.toFixed(3)}`);
    }

    console.log('\nMISSING FACTS:');
    for (const fact of result.globalMissingFacts) {
      console.log(`- ${fact}`);
    }
  }

  await closeRetriever();
}

run().catch(async (err) => {
  console.error('TEST ERROR:', err);
  await closeRetriever();
  process.exit(1);
});