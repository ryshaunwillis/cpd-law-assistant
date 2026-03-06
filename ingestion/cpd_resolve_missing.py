import re
import requests
from pypdf import PdfReader
from io import BytesIO

from dotenv import load_dotenv
load_dotenv()

from db import get_conn

CPD_PDF_URL = "https://directives.chicagopolice.org/api/publicDirective/{id}"

def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []
    for p in reader.pages:
        t = p.extract_text() or ""
        pages.append(t)
    return "\n".join(pages)

def fetch_missing_directives(conn, limit=25):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT directive_number
            FROM cpd_expected_directives
            WHERE directive_number NOT IN (
                SELECT directive_number
                FROM documents
                WHERE source = 'CPD' AND directive_number IS NOT NULL
            )
            ORDER BY directive_number
            LIMIT %s
            """,
            (limit,)
        )
        return [row[0] for row in cur.fetchall()]

def mark_resolved(conn, directive_number, pdf_url):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE cpd_expected_directives
            SET resolved = TRUE,
                resolved_pdf_url = %s,
                found_pdf_url = %s,
                last_checked_at = NOW()
            WHERE directive_number = %s
            """,
            (pdf_url, pdf_url, directive_number)
        )
    conn.commit()

def mark_checked(conn, directive_number):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE cpd_expected_directives
            SET last_checked_at = NOW()
            WHERE directive_number = %s
            """,
            (directive_number,)
        )
    conn.commit()

def try_resolve_directive(directive_number, start_id=6000, end_id=6400):
    for did in range(start_id, end_id + 1):
        url = CPD_PDF_URL.format(id=did)
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                continue

            content_type = r.headers.get("content-type", "").lower()
            if "pdf" not in content_type:
                continue

            text = extract_pdf_text(r.content)
            if directive_number.upper() in text.upper():
                return url

        except Exception:
            continue

    return None

def main():
    conn = get_conn()

    try:
        missing = fetch_missing_directives(conn, limit=25)
        print(f"Trying to resolve {len(missing)} missing directives...")

        for directive_number in missing:
            print(f"[RESOLVE] {directive_number}")
            pdf_url = try_resolve_directive(directive_number)

            if pdf_url:
                mark_resolved(conn, directive_number, pdf_url)
                print(f"  ✅ resolved -> {pdf_url}")
            else:
                mark_checked(conn, directive_number)
                print("  - not resolved")
    finally:
        conn.close()

if __name__ == "__main__":
    main()