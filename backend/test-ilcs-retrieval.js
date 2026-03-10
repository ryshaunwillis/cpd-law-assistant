require('dotenv').config();

const { searchIlcs, closeRetriever } = require('./src/ilcsRetriever');

async function main() {
  console.log("Testing ILCS retrieval...\n");

  const query = "offender punched victim multiple times in the face causing injury";

  const result = await searchIlcs(query, {
    limit: 5,
    threshold: 0.30,
  });

  console.log("Query:");
  console.log(query);
  console.log("\nResults:\n");

  for (const match of result.matches) {
    console.log("Citation:", match.citation);
    console.log("Title:", match.sectionTitle);
    console.log("Offense Family:", match.offenseFamily);
    console.log("Similarity:", match.similarity.toFixed(3));
    console.log("---------------------------------\n");
  }

  await closeRetriever();
}

main().catch(async (err) => {
  console.error("TEST ERROR:", err);
  await closeRetriever();
  process.exit(1);
});