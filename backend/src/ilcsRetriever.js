const { Pool } = require('pg');
const OpenAI = require('openai');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL?.includes('sslmode=require')
    ? { rejectUnauthorized: false }
    : false,
});

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const EMBEDDING_MODEL =
  process.env.OPENAI_EMBEDDING_MODEL || 'text-embedding-3-small';

const EMBEDDING_DIMENSIONS = process.env.OPENAI_EMBEDDING_DIMENSIONS
  ? Number(process.env.OPENAI_EMBEDDING_DIMENSIONS)
  : null;

function embeddingToPgvectorLiteral(values) {
  return `[${values.map((v) => Number(v)).join(',')}]`;
}

function dedupeBySection(rows) {
  const seen = new Set();
  const output = [];

  for (const row of rows) {
    if (seen.has(row.section_id)) continue;
    seen.add(row.section_id);
    output.push(row);
  }

  return output;
}

function buildChargeSummary(row) {
  return {
    chunkId: row.chunk_id,
    sectionId: row.section_id,
    citation: row.citation,
    sectionTitle: row.section_title,
    sectionNumber: row.section_number,
    offenseFamily: row.offense_family,
    chunkType: row.chunk_type,
    subsectionLabel: row.subsection_label,
    similarity: Number(row.similarity),
    classification: row.classification || [],
    mentalStates: row.mental_states || [],
    conductTypes: row.conduct_types || [],
    victimTypes: row.victim_types || [],
    injuryTypes: row.injury_types || [],
    weaponTypes: row.weapon_types || [],
    propertyTypes: row.property_types || [],
    locationTypes: row.location_types || [],
    relationshipContexts: row.relationship_contexts || [],
    aggravatingFactors: row.aggravating_factors || [],
    plainEnglishTerms: row.plain_english_terms || [],
    crossReferences: row.cross_references || [],
    content: row.content,
    url: row.url,
    sourceNote: row.source_note,
  };
}

async function embedQuery(queryText) {
  const request = {
    model: EMBEDDING_MODEL,
    input: queryText,
  };

  if (EMBEDDING_DIMENSIONS) {
    request.dimensions = EMBEDDING_DIMENSIONS;
  }

  const response = await openai.embeddings.create(request);
  return response.data[0].embedding;
}


function normalizeFilters(filters = {}) {
  return {
    offenseFamily: filters.offenseFamily || null,
    chunkType: filters.chunkType || null,
    citation: filters.citation || null,
    limit: Number(filters.limit || 12),
    threshold: Number(filters.threshold || 0.45),
    dedupeSections: filters.dedupeSections !== false,
  };
}

async function searchIlcs(queryText, filters = {}) {
  if (!queryText || !queryText.trim()) {
    throw new Error('queryText is required');
  }

  const opts = normalizeFilters(filters);
  const queryEmbedding = await embedQuery(queryText);
  const queryVector = embeddingToPgvectorLiteral(queryEmbedding);

  const sql = `
    SELECT
      chunk_id,
      section_id,
      chunk_type,
      subsection_label,
      citation,
      section_title,
      section_number,
      offense_family,
      classification,
      mental_states,
      conduct_types,
      victim_types,
      injury_types,
      weapon_types,
      property_types,
      location_types,
      relationship_contexts,
      aggravating_factors,
      plain_english_terms,
      cross_references,
      content,
      url,
      source_note,
      1 - (embedding <=> $1::vector) AS similarity
    FROM ilcs_chunks
    WHERE
      ($2::text IS NULL OR offense_family = $2)
      AND ($3::text IS NULL OR chunk_type = $3)
      AND ($4::text IS NULL OR citation = $4)
      AND (1 - (embedding <=> $1::vector)) >= $5
    ORDER BY embedding <=> $1::vector
    LIMIT $6
  `;

  const values = [
    queryVector,
    opts.offenseFamily,
    opts.chunkType,
    opts.citation,
    opts.threshold,
    opts.limit * 3,
  ];

  const result = await pool.query(sql, values);

  let rows = result.rows || [];

  if (opts.dedupeSections) {
    rows = dedupeBySection(rows);
  }

  rows = rows.slice(0, opts.limit);

  return {
    query: queryText,
    embeddingModel: EMBEDDING_MODEL,
    totalMatches: rows.length,
    matches: rows.map(buildChargeSummary),
  };
}

async function closeRetriever() {
  await pool.end();
}

module.exports = {
  searchIlcs,
  closeRetriever,
};