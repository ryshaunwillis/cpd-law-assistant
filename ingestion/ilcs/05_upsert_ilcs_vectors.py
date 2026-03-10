import json
import os
from pathlib import Path
from typing import Any

import psycopg


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_JSONL = BASE_DIR / "data" / "processed" / "ilcs" / "ilcs_720_5_chunks_embedded.jsonl"

TABLE_NAME = os.getenv("ILCS_VECTOR_TABLE", "ilcs_chunks")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def embedding_to_pgvector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(float(v)) for v in values) + "]"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return value


def get_connection() -> psycopg.Connection:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg.connect(database_url)

    db_host = require_env("PGHOST")
    db_port = os.getenv("PGPORT", "5432")
    db_name = require_env("PGDATABASE")
    db_user = require_env("PGUSER")
    db_password = require_env("PGPASSWORD")

    return psycopg.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
    )


def create_table(conn: psycopg.Connection, embedding_dimensions: int) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                chunk_id TEXT PRIMARY KEY,
                section_id TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                subsection_label TEXT NULL,

                citation TEXT,
                section_title TEXT,
                section_number TEXT,
                offense_family TEXT,

                classification JSONB NOT NULL DEFAULT '[]'::jsonb,
                mental_states JSONB NOT NULL DEFAULT '[]'::jsonb,
                conduct_types JSONB NOT NULL DEFAULT '[]'::jsonb,
                victim_types JSONB NOT NULL DEFAULT '[]'::jsonb,
                injury_types JSONB NOT NULL DEFAULT '[]'::jsonb,
                weapon_types JSONB NOT NULL DEFAULT '[]'::jsonb,
                property_types JSONB NOT NULL DEFAULT '[]'::jsonb,
                location_types JSONB NOT NULL DEFAULT '[]'::jsonb,
                relationship_contexts JSONB NOT NULL DEFAULT '[]'::jsonb,
                aggravating_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
                plain_english_terms JSONB NOT NULL DEFAULT '[]'::jsonb,
                cross_references JSONB NOT NULL DEFAULT '[]'::jsonb,

                url TEXT,
                source_note TEXT,
                content TEXT NOT NULL,

                embedding_model TEXT,
                embedding_dimensions INT,
                content_token_count INT,
                embedded_at TEXT,

                embedding VECTOR({embedding_dimensions}) NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,

                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS {TABLE_NAME}_offense_family_idx
            ON {TABLE_NAME} (offense_family);
            """
        )

        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS {TABLE_NAME}_chunk_type_idx
            ON {TABLE_NAME} (chunk_type);
            """
        )

        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS {TABLE_NAME}_citation_idx
            ON {TABLE_NAME} (citation);
            """
        )

        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS {TABLE_NAME}_metadata_gin_idx
            ON {TABLE_NAME} USING GIN (metadata);
            """
        )

    conn.commit()


def upsert_rows(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> None:
    sql = f"""
        INSERT INTO {TABLE_NAME} (
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
            url,
            source_note,
            content,
            embedding_model,
            embedding_dimensions,
            content_token_count,
            embedded_at,
            embedding,
            metadata,
            updated_at
        )
        VALUES (
            %(chunk_id)s,
            %(section_id)s,
            %(chunk_type)s,
            %(subsection_label)s,
            %(citation)s,
            %(section_title)s,
            %(section_number)s,
            %(offense_family)s,
            %(classification)s::jsonb,
            %(mental_states)s::jsonb,
            %(conduct_types)s::jsonb,
            %(victim_types)s::jsonb,
            %(injury_types)s::jsonb,
            %(weapon_types)s::jsonb,
            %(property_types)s::jsonb,
            %(location_types)s::jsonb,
            %(relationship_contexts)s::jsonb,
            %(aggravating_factors)s::jsonb,
            %(plain_english_terms)s::jsonb,
            %(cross_references)s::jsonb,
            %(url)s,
            %(source_note)s,
            %(content)s,
            %(embedding_model)s,
            %(embedding_dimensions)s,
            %(content_token_count)s,
            %(embedded_at)s,
            %(embedding)s::vector,
            %(metadata)s::jsonb,
            NOW()
        )
        ON CONFLICT (chunk_id)
        DO UPDATE SET
            section_id = EXCLUDED.section_id,
            chunk_type = EXCLUDED.chunk_type,
            subsection_label = EXCLUDED.subsection_label,
            citation = EXCLUDED.citation,
            section_title = EXCLUDED.section_title,
            section_number = EXCLUDED.section_number,
            offense_family = EXCLUDED.offense_family,
            classification = EXCLUDED.classification,
            mental_states = EXCLUDED.mental_states,
            conduct_types = EXCLUDED.conduct_types,
            victim_types = EXCLUDED.victim_types,
            injury_types = EXCLUDED.injury_types,
            weapon_types = EXCLUDED.weapon_types,
            property_types = EXCLUDED.property_types,
            location_types = EXCLUDED.location_types,
            relationship_contexts = EXCLUDED.relationship_contexts,
            aggravating_factors = EXCLUDED.aggravating_factors,
            plain_english_terms = EXCLUDED.plain_english_terms,
            cross_references = EXCLUDED.cross_references,
            url = EXCLUDED.url,
            source_note = EXCLUDED.source_note,
            content = EXCLUDED.content,
            embedding_model = EXCLUDED.embedding_model,
            embedding_dimensions = EXCLUDED.embedding_dimensions,
            content_token_count = EXCLUDED.content_token_count,
            embedded_at = EXCLUDED.embedded_at,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata,
            updated_at = NOW();
    """

    payload = []

    for row in rows:
        metadata = {
            "citation": row.get("citation"),
            "section_title": row.get("section_title"),
            "section_number": row.get("section_number"),
            "offense_family": row.get("offense_family"),
            "chunk_type": row.get("chunk_type"),
            "subsection_label": row.get("subsection_label"),
            "classification": row.get("classification", []),
            "mental_states": row.get("mental_states", []),
            "conduct_types": row.get("conduct_types", []),
            "victim_types": row.get("victim_types", []),
            "injury_types": row.get("injury_types", []),
            "weapon_types": row.get("weapon_types", []),
            "property_types": row.get("property_types", []),
            "location_types": row.get("location_types", []),
            "relationship_contexts": row.get("relationship_contexts", []),
            "aggravating_factors": row.get("aggravating_factors", []),
            "plain_english_terms": row.get("plain_english_terms", []),
            "cross_references": row.get("cross_references", []),
            "url": row.get("url"),
        }

        payload.append(
            {
                "chunk_id": row["chunk_id"],
                "section_id": row["section_id"],
                "chunk_type": row["chunk_type"],
                "subsection_label": row.get("subsection_label"),
                "citation": row.get("citation"),
                "section_title": row.get("section_title"),
                "section_number": row.get("section_number"),
                "offense_family": row.get("offense_family"),
                "classification": json.dumps(row.get("classification", [])),
                "mental_states": json.dumps(row.get("mental_states", [])),
                "conduct_types": json.dumps(row.get("conduct_types", [])),
                "victim_types": json.dumps(row.get("victim_types", [])),
                "injury_types": json.dumps(row.get("injury_types", [])),
                "weapon_types": json.dumps(row.get("weapon_types", [])),
                "property_types": json.dumps(row.get("property_types", [])),
                "location_types": json.dumps(row.get("location_types", [])),
                "relationship_contexts": json.dumps(row.get("relationship_contexts", [])),
                "aggravating_factors": json.dumps(row.get("aggravating_factors", [])),
                "plain_english_terms": json.dumps(row.get("plain_english_terms", [])),
                "cross_references": json.dumps(row.get("cross_references", [])),
                "url": row.get("url"),
                "source_note": row.get("source_note"),
                "content": row.get("content"),
                "embedding_model": row.get("embedding_model"),
                "embedding_dimensions": row.get("embedding_dimensions"),
                "content_token_count": row.get("content_token_count"),
                "embedded_at": row.get("embedded_at"),
                "embedding": embedding_to_pgvector_literal(row["embedding"]),
                "metadata": json.dumps(metadata),
            }
        )

    with conn.cursor() as cur:
        cur.executemany(sql, payload)

    conn.commit()


def main() -> None:
    if not INPUT_JSONL.exists():
        raise FileNotFoundError(f"Embedded chunk file not found: {INPUT_JSONL}")

    rows = load_jsonl(INPUT_JSONL)
    if not rows:
        raise RuntimeError("No embedded rows found.")

    first_embedding = rows[0].get("embedding")
    if not first_embedding:
        raise RuntimeError("First row does not contain an embedding.")

    embedding_dimensions = len(first_embedding)

    print(f"Loaded embedded rows: {len(rows)}")
    print(f"Vector dimensions:    {embedding_dimensions}")
    print(f"Target table:         {TABLE_NAME}")

    conn = get_connection()

    try:
        create_table(conn, embedding_dimensions)
        upsert_rows(conn, rows)
    finally:
        conn.close()

    print("Done.")
    print(f"Upserted rows into table: {TABLE_NAME}")


if __name__ == "__main__":
    main()