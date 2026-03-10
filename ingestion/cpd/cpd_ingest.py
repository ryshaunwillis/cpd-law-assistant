import argparse
import datetime as dt
import re
import time
import requests
from pypdf import PdfReader
from io import BytesIO

from dotenv import load_dotenv
load_dotenv()

from db import get_conn, upsert_document, replace_chunks
from chunking import chunk_text
from embed import embed_texts
from util import sha256_text

CPD_PDF_URL = "https://directives.chicagopolice.org/api/publicDirective/{id}"

DIRECTIVE_NUMBER_RE = re.compile(r"\b([GESUD]\d{2}-\d{2}(?:-\d{2})?)\b", re.IGNORECASE)

CATEGORY_RULES = [
    ("general order", "General Orders"),
    ("special order", "Special Orders"),
    ("employee resource", "Employee Resources"),
    ("department notice", "Department Notices"),
    ("uniform and property", "Uniform And Property"),
]

def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []
    for p in reader.pages:
        t = p.extract_text() or ""
        pages.append(t)
    return "\n".join(pages)

def guess_title_from_text(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    head = " ".join(lines[:3])[:180] if lines else "CPD Directive"
    return head

def guess_published_date_from_text(text: str):
    m = re.search(r"ISSUE DATE:\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})", text)
    if not m:
        return None
    raw = m.group(1).strip()
    try:
        return dt.datetime.strptime(raw, "%d %B %Y").date()
    except Exception:
        return None

def extract_directive_number(text: str) -> str | None:
    m = DIRECTIVE_NUMBER_RE.search(text)
    if not m:
        return None
    return m.group(1).upper()

def lookup_directive_category(conn, directive_number: str | None) -> str | None:
    if not directive_number:
        return None

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT category
            FROM cpd_expected_directives
            WHERE directive_number = %s
            LIMIT 1
            """,
            (directive_number,),
        )
        row = cur.fetchone()
        return row[0] if row else None

def download_pdf(directive_id: int) -> bytes | None:
    url = CPD_PDF_URL.format(id=directive_id)
    r = requests.get(url, timeout=60)

    if r.status_code == 404:
        print(f"  - 404, skipping id={directive_id}")
        return None

    if r.status_code != 200:
        print(f"  - status {r.status_code}, skipping id={directive_id}")
        return None

    content_type = r.headers.get("content-type", "").lower()
    if "pdf" not in content_type:
        print(f"  - non-pdf response ({content_type}), skipping id={directive_id}")
        return None

    return r.content

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
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", type=int, help="Directive IDs to ingest")
    ap.add_argument("--range", nargs=2, type=int, metavar=("START", "END"), help="Ingest a range of IDs (inclusive)")
    ap.add_argument("--max", type=int, default=50, help="Max directives to ingest (when using --range)")
    args = ap.parse_args()

    ids = []
    if args.ids:
        ids.extend(args.ids)
    if args.range:
        start, end = args.range
        ids.extend(list(range(start, end + 1)))

    if not ids:
        ids = [6197, 6120, 6230]

    conn = get_conn()
    ingested = 0

    for did in ids:
        if args.range and ingested >= args.max:
            break

        try:
            conn = ensure_conn(conn)

            url = CPD_PDF_URL.format(id=did)
            print(f"[CPD] Fetching {url}")

            pdf_bytes = download_pdf(did)
            if pdf_bytes is None:
                continue

            text = extract_pdf_text(pdf_bytes).strip()
            if not text:
                print(f"  - empty text, skipping id={did}")
                continue

            title = guess_title_from_text(text)
            published = guess_published_date_from_text(text)
            directive_number = extract_directive_number(text)
            directive_category = lookup_directive_category(conn, directive_number)
            content_hash = sha256_text(text)

            doc_id = upsert_document(
                conn,
                source="CPD",
                title=title,
                url=url,
                published_date=published,
                content_hash=content_hash,
                directive_number=directive_number,
                directive_category=directive_category,
            )

            chunks = chunk_text(text)
            if not chunks:
                print(f"  - no chunks, skipping id={did}")
                continue

            embeddings = []
            batch_size = 10
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i+batch_size]
                embeddings.extend(embed_texts(batch))
                time.sleep(0.3)

            conn = ensure_conn(conn)
            replace_chunks(conn, document_id=doc_id, chunks=chunks, embeddings=embeddings)

            ingested += 1
            print(
                f"  ✅ stored doc_id={doc_id} directive_number={directive_number} "
                f"category={directive_category} chunks={len(chunks)}"
            )

        except Exception as e:
            print(f"  - failed id={did}: {e}")
            try:
                conn.close()
            except Exception:
                pass
            conn = None
            time.sleep(1)
            continue

    try:
        if conn is not None and conn.closed == 0:
            conn.close()
    except Exception:
        pass

    print(f"\nDone. Ingested {ingested} CPD directives.")

if __name__ == "__main__":
    main()