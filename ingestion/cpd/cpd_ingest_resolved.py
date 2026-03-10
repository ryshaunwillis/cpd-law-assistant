import time
import re
import datetime as dt
import requests
from io import BytesIO
from pypdf import PdfReader

from dotenv import load_dotenv
load_dotenv()

from db import get_conn, upsert_document, replace_chunks
from chunking import chunk_text
from embed import embed_texts
from util import sha256_text

DIRECTIVE_NUMBER_RE = re.compile(r"\b([GESUD]\d{2}-\d{2}(?:-\d{2})?)\b", re.IGNORECASE)

def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []
    for p in reader.pages:
        pages.append(p.extract_text() or "")
    return "\n".join(pages)

def guess_title_from_text(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return " ".join(lines[:3])[:220] if lines else "CPD Directive"

def guess_published_date_from_text(text: str):
    m = re.search(r"ISSUE DATE:\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})", text)
    if not m:
        return None
    raw = m.group(1).strip()
    try:
        return dt.datetime.strptime(raw, "%d %B %Y").date()
    except Exception:
        return None

def extract_directive_number(text: str, title: str = "") -> str | None:
    combined = f"{title}\n{text}"
    m = DIRECTIVE_NUMBER_RE.search(combined)
    if not m:
        return None
    return m.group(1).upper().replace(" ", "")

def extract_category_from_title(title: str) -> str | None:
    t = title.lower()
    if "general order" in t:
        return "General Orders"
    if "special order" in t:
        return "Special Orders"
    if "employee resource" in t:
        return "Employee Resources"
    if "department notice" in t:
        return "Department Notices"
    if "uniform and property" in t:
        return "Uniform And Property"
    return None

def fetch_resolvable_missing(conn, limit=500):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              e.directive_number,
              e.category,
              l.public_directive_id,
              l.pdf_url
            FROM cpd_expected_directives e
            JOIN cpd_pdf_lookup l
              ON l.directive_number = e.directive_number
            LEFT JOIN documents d
              ON d.source = 'CPD'
             AND d.directive_number = e.directive_number
            WHERE d.id IS NULL
            ORDER BY e.directive_number
            LIMIT %s
            """,
            (limit,)
        )
        return cur.fetchall()

def ensure_conn(conn):
    try:
        if conn is None or conn.closed != 0:
            return get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        return conn
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return get_conn()

def main():
    conn = get_conn()
    saved = 0

    try:
        rows = fetch_resolvable_missing(conn, limit=500)
        print(f"Found {len(rows)} resolvable missing directives to ingest")

        for directive_number, expected_category, public_directive_id, pdf_url in rows:
            try:
                conn = ensure_conn(conn)
                print(f"[INGEST] {directive_number} -> {pdf_url}")

                r = requests.get(pdf_url, timeout=60)
                if r.status_code != 200:
                    print(f"  - status {r.status_code}, skipping")
                    continue

                content_type = r.headers.get("content-type", "").lower()
                if "pdf" not in content_type:
                    print(f"  - non-pdf response ({content_type}), skipping")
                    continue

                text = extract_pdf_text(r.content).strip()
                if not text:
                    print("  - empty text, skipping")
                    continue

                title = guess_title_from_text(text)
                published = guess_published_date_from_text(text)
                extracted_number = extract_directive_number(text, title) or directive_number
                directive_category = expected_category or extract_category_from_title(title)
                content_hash = sha256_text(text)

                doc_id = upsert_document(
                    conn,
                    source="CPD",
                    title=title,
                    url=pdf_url,
                    published_date=published,
                    content_hash=content_hash,
                    directive_number=extracted_number,
                    directive_category=directive_category,
                )

                chunks = chunk_text(text)
                if not chunks:
                    print("  - no chunks, skipping")
                    continue

                embeddings = []
                batch_size = 10
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i + batch_size]
                    embeddings.extend(embed_texts(batch))
                    time.sleep(0.3)

                conn = ensure_conn(conn)
                replace_chunks(conn, document_id=doc_id, chunks=chunks, embeddings=embeddings)

                saved += 1
                print(f"  ✅ saved doc_id={doc_id} directive_number={extracted_number} chunks={len(chunks)}")

            except Exception as e:
                print(f"  - failed {directive_number}: {e}")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
                time.sleep(1)
                continue

    finally:
        try:
            if conn is not None and conn.closed == 0:
                conn.close()
        except Exception:
            pass

    print(f"\nDone. Saved {saved} resolved directives.")

if __name__ == "__main__":
    main()