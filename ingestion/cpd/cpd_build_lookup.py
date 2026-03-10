import argparse
import re
import time
import requests
from io import BytesIO
from pypdf import PdfReader

from dotenv import load_dotenv
load_dotenv()

from db import get_conn

CPD_PDF_URL = "https://directives.chicagopolice.org/api/publicDirective/{id}"
DIRECTIVE_NUMBER_RE = re.compile(r"\b([GESUD]\d{2}-\d{2}(?:-\d{2})?)\b", re.IGNORECASE)

def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)

def guess_title_from_text(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return " ".join(lines[:3])[:220] if lines else "CPD Directive"

def extract_directive_number(text: str, title: str = "") -> str | None:
    combined = f"{title}\n{text}"
    m = DIRECTIVE_NUMBER_RE.search(combined)
    if not m:
        return None
    return m.group(1).upper().replace(" ", "")

def fetch_pdf(did: int) -> bytes | None:
    url = CPD_PDF_URL.format(id=did)
    r = requests.get(url, timeout=60)

    if r.status_code == 404:
        print(f"[{did}] 404")
        return None

    if r.status_code != 200:
        print(f"[{did}] status={r.status_code}")
        return None

    content_type = r.headers.get("content-type", "").lower()
    if "pdf" not in content_type:
        print(f"[{did}] non-pdf content-type={content_type}")
        return None

    return r.content

def upsert_lookup(conn, public_directive_id: int, directive_number: str | None, title: str, pdf_url: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO cpd_pdf_lookup (public_directive_id, directive_number, title, pdf_url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (public_directive_id) DO UPDATE SET
              directive_number = EXCLUDED.directive_number,
              title = EXCLUDED.title,
              pdf_url = EXCLUDED.pdf_url,
              discovered_at = NOW();
            """,
            (public_directive_id, directive_number, title, pdf_url),
        )
    conn.commit()

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
    ap.add_argument("--start", type=int, default=6000)
    ap.add_argument("--end", type=int, default=6400)
    ap.add_argument("--sleep", type=float, default=0.2, help="Pause between requests")
    args = ap.parse_args()

    conn = get_conn()
    saved = 0

    try:
        for did in range(args.start, args.end + 1):
            try:
                conn = ensure_conn(conn)

                pdf_bytes = fetch_pdf(did)
                if not pdf_bytes:
                    time.sleep(args.sleep)
                    continue

                text = extract_pdf_text(pdf_bytes).strip()
                if not text:
                    print(f"[{did}] empty text")
                    time.sleep(args.sleep)
                    continue

                title = guess_title_from_text(text)
                directive_number = extract_directive_number(text, title)
                pdf_url = CPD_PDF_URL.format(id=did)

                upsert_lookup(conn, did, directive_number, title, pdf_url)
                saved += 1

                print(f"[{did}] ✅ directive_number={directive_number} title={title[:80]}")
                time.sleep(args.sleep)

            except Exception as e:
                print(f"[{did}] failed: {e}")
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

    print(f"\nDone. Saved/updated {saved} lookup rows.")

if __name__ == "__main__":
    main()