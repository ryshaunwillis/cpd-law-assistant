import os
import psycopg2
from psycopg2.extras import execute_values

def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is missing. Put it in your .env")
    return psycopg2.connect(db_url, sslmode="require")

def upsert_document(
    conn,
    *,
    source: str,
    title: str,
    url: str,
    published_date,
    content_hash: str,
    directive_number: str | None = None,
    directive_category: str | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (
              source, title, url, published_date, content_hash, directive_number, directive_category
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO UPDATE SET
              source = EXCLUDED.source,
              title = EXCLUDED.title,
              published_date = EXCLUDED.published_date,
              content_hash = EXCLUDED.content_hash,
              directive_number = EXCLUDED.directive_number,
              directive_category = EXCLUDED.directive_category
            RETURNING id;
            """,
            (
                source,
                title,
                url,
                published_date,
                content_hash,
                directive_number,
                directive_category,
            ),
        )
        doc_id = cur.fetchone()[0]
    conn.commit()
    return doc_id

def replace_chunks(conn, *, document_id: int, chunks: list[str], embeddings: list[list[float]]):
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")

    with conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE document_id = %s;", (document_id,))
        rows = [(document_id, i, chunks[i], embeddings[i]) for i in range(len(chunks))]
        execute_values(
            cur,
            """
            INSERT INTO chunks (document_id, chunk_index, text, embedding)
            VALUES %s
            """,
            rows,
            template="(%s, %s, %s, %s)",
        )
    conn.commit()