import re
import requests
import pdfplumber
from io import BytesIO
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from db import get_conn

INDEX_URL = "https://directives.chicagopolice.org/forms/CPD-11.716.pdf"

CATEGORY_HINTS = [
    ("GENERAL ORDERS", "General Orders"),
    ("SPECIAL ORDERS", "Special Orders"),
    ("EMPLOYEE RESOURCES", "Employee Resources"),
    ("DEPARTMENT NOTICES", "Department Notices"),
    ("UNIFORM AND PROPERTY", "Uniform And Property"),
]

DIRECTIVE_NUMBER_RE = re.compile(r"\b([GESUD]\d{2}-\d{2}(?:-\d{2})?)\b", re.IGNORECASE)

def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def extract_rows_from_pdf(pdf_bytes: bytes):
    rows = []
    current_category = None

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            lines = [normalize_text(x) for x in text.splitlines() if normalize_text(x)]

            for line in lines:
                upper = line.upper()

                for hint, label in CATEGORY_HINTS:
                    if hint in upper:
                        current_category = label

                matches = list(DIRECTIVE_NUMBER_RE.finditer(line))
                if not matches:
                    continue

                for i, m in enumerate(matches):
                    directive_number = m.group(1).upper().replace(" ", "")
                    start = m.end()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
                    title = normalize_text(line[start:end])

                    if not title:
                        continue

                    rows.append({
                        "directive_number": directive_number,
                        "title": title,
                        "category": current_category or "Unknown",
                        "source_index": f"{INDEX_URL}#page={page_num}",
                    })

    return rows

def upsert_expected_directives(conn, rows):
    inserted = 0

    with conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO cpd_expected_directives
                    (directive_number, title, category, source_index, last_checked_at)
                VALUES
                    (%s, %s, %s, %s, %s)
                ON CONFLICT (directive_number) DO UPDATE SET
                    title = EXCLUDED.title,
                    category = EXCLUDED.category,
                    source_index = EXCLUDED.source_index,
                    last_checked_at = EXCLUDED.last_checked_at;
                """,
                (
                    row["directive_number"],
                    row["title"],
                    row["category"],
                    row["source_index"],
                    datetime.utcnow(),
                ),
            )
            inserted += 1

    conn.commit()
    return inserted

def main():
    print(f"Downloading CPD index: {INDEX_URL}")
    r = requests.get(INDEX_URL, timeout=60)
    r.raise_for_status()

    rows = extract_rows_from_pdf(r.content)

    deduped = {}
    for row in rows:
        deduped[row["directive_number"]] = row

    final_rows = list(deduped.values())

    print(f"Extracted {len(rows)} raw entries")
    print(f"Upserting {len(final_rows)} unique directives")

    conn = get_conn()
    try:
        count = upsert_expected_directives(conn, final_rows)
        print(f"Done. Upserted {count} directives into cpd_expected_directives.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()