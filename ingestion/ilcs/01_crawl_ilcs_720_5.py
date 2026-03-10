import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "ilcs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_URL = (
    "https://www.ilga.gov/legislation/ILCS/details"
    "?ActID=1876"
    "&ActName=Criminal+Code+of+2012."
    "&ChapAct=720+ILCS+5%2F"
    "&Chapter="
    "&ChapterID=53"
    "&MajorTopic="
    "&SeqEnd=99999999"
    "&SeqStart=0"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_candidate_text_blocks(soup: BeautifulSoup) -> list[str]:
    """
    ILGA pages are inconsistent, so we collect text from likely content containers
    and pick the biggest useful block.
    """
    candidates = []

    selectors = [
        "body",
        "td",
        "div",
        "font",
        "p",
    ]

    for selector in selectors:
        for node in soup.select(selector):
            text = node.get_text("\n", strip=True)
            text = clean_text(text)
            if len(text) > 500:
                candidates.append(text)

    # remove near-duplicates while preserving order
    unique = []
    seen = set()
    for block in candidates:
        key = block[:1000]
        if key not in seen:
            seen.add(key)
            unique.append(block)

    return unique


def choose_best_block(blocks: list[str]) -> str:
    """
    Prefer blocks that clearly contain ILCS citations and section markers.
    """
    scored = []

    for block in blocks:
        score = 0

        if "720 ILCS 5/" in block:
            score += 10
        if "Sec." in block:
            score += 10
        if "Source:" in block:
            score += 5
        if "Criminal Code of 2012" in block:
            score += 5

        # more sections = more useful
        score += len(re.findall(r"720 ILCS 5/\d", block)) * 2
        score += len(re.findall(r"\bSec\.\s+\d", block)) * 2

        scored.append((score, len(block), block))

    scored.sort(reverse=True, key=lambda x: (x[0], x[1]))
    return scored[0][2] if scored else ""


def split_into_sections(text: str) -> list[dict]:
    """
    Split the full act text into individual section records.
    Each record keeps:
      - citation
      - section number
      - section title
      - section body
      - source note
    """
    pattern = re.compile(
        r"(\(720 ILCS 5/([^)]+)\).*?Sec\.\s*([0-9A-Za-z.\-]+)\.\s*(.*?))"
        r"(?=(\(720 ILCS 5/[^)]+\).*?Sec\.\s*[0-9A-Za-z.\-]+\.)|$)",
        re.DOTALL
    )

    matches = list(pattern.finditer(text))
    sections = []

    for match in matches:
        full_block = clean_text(match.group(1))
        citation_section = clean_text(match.group(2))
        sec_number = clean_text(match.group(3))

        block_without_prefix = full_block

        title_match = re.search(
            r"Sec\.\s*[0-9A-Za-z.\-]+\.\s*([^\n.]{1,200})\.",
            block_without_prefix
        )
        section_title = title_match.group(1).strip() if title_match else ""

        source_match = re.search(r"\(Source:\s*(.*?)\)\s*$", full_block, re.DOTALL)
        source_note = clean_text(source_match.group(1)) if source_match else ""

        body = full_block
        body = re.sub(r"^\(720 ILCS 5/[^)]+\)\s*", "", body)
        body = clean_text(body)

        sections.append({
            "id": f"720-5-{sec_number}",
            "citation": f"720 ILCS 5/{citation_section}",
            "section_number": sec_number,
            "section_title": section_title,
            "body_text": body,
            "source_note": source_note,
            "chapter_number": "720",
            "chapter_name": "Criminal Offenses",
            "act_id": "1876",
            "act_name": "Criminal Code of 2012",
            "url": SOURCE_URL,
        })

    return sections


def main() -> None:
    print("Fetching ILCS page...")
    html = fetch_html(SOURCE_URL)

    print("Parsing HTML...")
    soup = BeautifulSoup(html, "html.parser")

    print("Finding main text block...")
    blocks = extract_candidate_text_blocks(soup)
    best_block = choose_best_block(blocks)

    if not best_block:
        raise RuntimeError("Could not find a usable ILCS content block.")

    print("Splitting into sections...")
    sections = split_into_sections(best_block)

    if not sections:
        debug_path = OUTPUT_DIR / "debug_ilcs_720_5_full_text.txt"
        debug_path.write_text(best_block, encoding="utf-8")
        raise RuntimeError(
            f"No sections parsed. Saved debug text to: {debug_path}"
        )

    output = {
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source_url": SOURCE_URL,
        "total_sections": len(sections),
        "sections": sections,
    }

    output_path = OUTPUT_DIR / "ilcs_720_5_sections_raw.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Done. Saved {len(sections)} sections to:")
    print(output_path)


if __name__ == "__main__":
    main()