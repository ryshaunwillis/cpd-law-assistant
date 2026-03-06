import argparse
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

from dotenv import load_dotenv
load_dotenv()

from db import get_conn, upsert_document, replace_chunks
from chunking import chunk_text
from embed import embed_texts
from util import sha256_text

CHAPTERS_URL = "https://www.ilga.gov/legislation/ILCS/Chapters"

def normalize_articles_url(u: str) -> str:
    """
    Ensure Articles URL includes Print=True so the response includes the statute text.
    """
    p = urlparse(u)
    qs = parse_qs(p.query)
    qs["Print"] = ["True"]
    new_query = urlencode(qs, doseq=True)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))

def discover_chapter_acts_pages(chapter_limit: int) -> list[str]:
    """
    From Chapters page, collect links to per-chapter Act listings:
      /Legislation/ILCS/Acts?Chapter=...&ChapterID=...&...
    """
    r = requests.get(CHAPTERS_URL, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    urls = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        abs_url = urljoin(CHAPTERS_URL, href)

        # These are the chapter act listing pages
        if "/Legislation/ILCS/Acts" in abs_url and "ChapterID=" in abs_url:
            urls.append(abs_url)

    # de-dupe preserve order
    seen = set()
    uniq = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)
        if len(uniq) >= chapter_limit:
            break

    return uniq

def discover_articles_from_chapter_acts(acts_page_url: str, act_limit: int) -> list[str]:
    """
    From a chapter Act listing page, collect Act links:
      /Legislation/ILCS/Articles?ActID=...
    """
    r = requests.get(acts_page_url, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    urls = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        abs_url = urljoin(acts_page_url, href)

        if "/Legislation/ILCS/Articles" in abs_url and "ActID=" in abs_url:
            urls.append(normalize_articles_url(abs_url))

    # de-dupe preserve order + cap
    seen = set()
    uniq = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)
        if len(uniq) >= act_limit:
            break

    return uniq

def clean_ilcs_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(" ", strip=True) if soup.title else "ILCS Act"

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return title[:240], text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", nargs="*", help="Specific ILCS Articles URLs to ingest (ActID links).")
    ap.add_argument("--chapters", type=int, default=3, help="How many chapter act-list pages to sample from Chapters.")
    ap.add_argument("--acts-per-chapter", type=int, default=5, help="How many Acts to ingest per chapter.")
    args = ap.parse_args()

    urls = args.urls or []
    if not urls:
        chapter_act_pages = discover_chapter_acts_pages(args.chapters)
        if not chapter_act_pages:
            print("No chapter Act listing pages discovered from Chapters.")
            return

        for cap_url in chapter_act_pages:
            urls.extend(discover_articles_from_chapter_acts(cap_url, args.acts_per_chapter))

    # final de-dupe
    seen = set()
    uniq_urls = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        uniq_urls.append(u)

    if not uniq_urls:
        print("No ILCS Act links discovered. (Could be temporary site blocking or HTML changed.)")
        return

    conn = get_conn()
    ingested = 0

    for url in uniq_urls:
        print(f"[ILCS] Fetching {url}")
        r = requests.get(url, timeout=60)
        if r.status_code == 404:
            print("  - 404, skipping")
            continue
        r.raise_for_status()

        title, text = clean_ilcs_text(r.text)
        if not text.strip():
            print("  - empty text, skipping")
            continue

        content_hash = sha256_text(text)

        doc_id = upsert_document(
            conn,
            source="ILCS",
            title=title,
            url=url,
            published_date=None,
            content_hash=content_hash,
        )

        chunks = chunk_text(text)
        embeddings = []
        batch_size = 10  # small to reduce 429 risk
        for i in range(0, len(chunks), batch_size):
            embeddings.extend(embed_texts(chunks[i:i+batch_size]))

        replace_chunks(conn, document_id=doc_id, chunks=chunks, embeddings=embeddings)
        ingested += 1
        print(f"  ✅ stored doc_id={doc_id} chunks={len(chunks)} title={title[:60]}")

    conn.close()
    print(f"\nDone. Ingested {ingested} ILCS Acts/pages.")

if __name__ == "__main__":
    main()