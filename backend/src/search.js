const pool = require("./db");

function toVectorLiteral(arr) {
  if (!Array.isArray(arr)) {
    throw new Error("Embedding must be an array");
  }
  return `[${arr.join(",")}]`;
}

async function searchChunks(embedding, question = "") {
  const vector = toVectorLiteral(embedding);
  const q = question.toLowerCase();

  const cpdFirst =
    q.includes("cpd") ||
    q.includes("officer") ||
    q.includes("department") ||
    q.includes("general order") ||
    q.includes("special order") ||
    q.includes("uniform") ||
    q.includes("grooming") ||
    q.includes("appearance") ||
    q.includes("hair");

  let sql;

  if (cpdFirst) {
    sql = `
      (
        SELECT
          chunks.text,
          documents.title,
          documents.url,
          documents.source,
          chunks.embedding <=> $1::vector AS distance
        FROM chunks
        JOIN documents ON chunks.document_id = documents.id
        WHERE documents.source = 'CPD'
        ORDER BY chunks.embedding <=> $1::vector
        LIMIT 4
      )
      UNION ALL
      (
        SELECT
          chunks.text,
          documents.title,
          documents.url,
          documents.source,
          chunks.embedding <=> $1::vector AS distance
        FROM chunks
        JOIN documents ON chunks.document_id = documents.id
        WHERE documents.source = 'ILCS'
        ORDER BY chunks.embedding <=> $1::vector
        LIMIT 2
      )
      ORDER BY distance
      LIMIT 4
    `;
  } else {
    sql = `
      SELECT
        chunks.text,
        documents.title,
        documents.url,
        documents.source,
        chunks.embedding <=> $1::vector AS distance
      FROM chunks
      JOIN documents ON chunks.document_id = documents.id
      ORDER BY chunks.embedding <=> $1::vector
      LIMIT 4
    `;
  }

  const result = await pool.query(sql, [vector]);
  return result.rows;
}

module.exports = searchChunks;