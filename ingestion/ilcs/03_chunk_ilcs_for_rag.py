import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_JSON = BASE_DIR / "data" / "processed" / "ilcs" / "ilcs_720_5_sections_general.json"
OUT_DIR = BASE_DIR / "data" / "processed" / "ilcs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_JSON = OUT_DIR / "ilcs_720_5_chunks.json"
OUT_JSONL = OUT_DIR / "ilcs_720_5_chunks.jsonl"


MAX_CHARS_FALLBACK = 1800
OVERLAP_CHARS = 250


def clean_text(text: str) -> str:
    text = text or ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_whitespace_for_embedding(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def split_by_subsections(text: str) -> list[dict[str, str]]:
    """
    Try to split statute text on subsection markers like:
      (a)
      (a-5)
      (1)
      (A)
    Returns ordered blocks with labels.
    """
    text = clean_text(text)

    pattern = re.compile(
        r"(?=(\(([A-Za-z0-9\-]+)\)))"
    )

    matches = list(pattern.finditer(text))

    if len(matches) < 2:
        return []

    parts: list[dict[str, str]] = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        label = match.group(2).strip()
        block = clean_text(text[start:end])

        if len(block) < 40:
            continue

        parts.append({
            "label": label,
            "text": block,
        })

    # Require real content to count as subsection splits
    if len(parts) < 2:
        return []

    return parts


def fallback_window_chunks(text: str, max_chars: int = MAX_CHARS_FALLBACK, overlap: int = OVERLAP_CHARS) -> list[str]:
    text = normalize_whitespace_for_embedding(text)

    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(0, end - overlap)

    return chunks


def build_parent_chunk(section: dict[str, Any]) -> dict[str, Any]:
    citation = section.get("citation", "")
    title = section.get("section_title", "")
    clean_text_body = clean_text(section.get("clean_text", ""))

    content_parts = [
        f"Citation: {citation}",
        f"Title: {title}",
        f"Act: {section.get('act_name', '')}",
        f"Offense family: {section.get('offense_family', '') or 'unknown'}",
    ]

    if section.get("classification"):
        content_parts.append(f"Classification: {', '.join(section['classification'])}")

    if section.get("mental_states"):
        content_parts.append(f"Mental states: {', '.join(section['mental_states'])}")

    if section.get("conduct_types"):
        content_parts.append(f"Conduct types: {', '.join(section['conduct_types'])}")

    if section.get("victim_types"):
        content_parts.append(f"Victim types: {', '.join(section['victim_types'])}")

    if section.get("injury_types"):
        content_parts.append(f"Injury types: {', '.join(section['injury_types'])}")

    if section.get("weapon_types"):
        content_parts.append(f"Weapon types: {', '.join(section['weapon_types'])}")

    if section.get("property_types"):
        content_parts.append(f"Property types: {', '.join(section['property_types'])}")

    if section.get("location_types"):
        content_parts.append(f"Location types: {', '.join(section['location_types'])}")

    if section.get("relationship_contexts"):
        content_parts.append(f"Relationship contexts: {', '.join(section['relationship_contexts'])}")

    if section.get("aggravating_factors"):
        content_parts.append(f"Aggravating factors: {', '.join(section['aggravating_factors'])}")

    if section.get("plain_english_terms"):
        content_parts.append(f"Plain English terms: {', '.join(section['plain_english_terms'])}")

    content_parts.append(f"Statute text: {clean_text_body}")

    return {
        "chunk_id": f"{section['id']}::parent",
        "section_id": section["id"],
        "chunk_type": "section_parent",
        "citation": citation,
        "section_title": title,
        "section_number": section.get("section_number"),
        "offense_family": section.get("offense_family"),
        "classification": section.get("classification", []),
        "mental_states": section.get("mental_states", []),
        "conduct_types": section.get("conduct_types", []),
        "victim_types": section.get("victim_types", []),
        "injury_types": section.get("injury_types", []),
        "weapon_types": section.get("weapon_types", []),
        "property_types": section.get("property_types", []),
        "location_types": section.get("location_types", []),
        "relationship_contexts": section.get("relationship_contexts", []),
        "aggravating_factors": section.get("aggravating_factors", []),
        "plain_english_terms": section.get("plain_english_terms", []),
        "cross_references": section.get("cross_references", []),
        "url": section.get("url"),
        "source_note": section.get("source_note"),
        "content": "\n".join([part for part in content_parts if part]).strip(),
    }


def build_subsection_chunks(section: dict[str, Any]) -> list[dict[str, Any]]:
    body = clean_text(section.get("clean_text", ""))
    subsection_parts = split_by_subsections(body)

    if not subsection_parts:
        return []

    chunks: list[dict[str, Any]] = []

    for idx, part in enumerate(subsection_parts, start=1):
        label = part["label"]
        text = part["text"]

        content_parts = [
            f"Citation: {section.get('citation', '')}",
            f"Title: {section.get('section_title', '')}",
            f"Subsection: ({label})",
            f"Offense family: {section.get('offense_family', '') or 'unknown'}",
        ]

        if section.get("classification"):
            content_parts.append(f"Classification: {', '.join(section['classification'])}")

        if section.get("plain_english_terms"):
            content_parts.append(f"Plain English terms: {', '.join(section['plain_english_terms'])}")

        content_parts.append(f"Subsection text: {text}")

        chunks.append({
            "chunk_id": f"{section['id']}::sub::{idx}",
            "section_id": section["id"],
            "chunk_type": "subsection",
            "subsection_label": label,
            "citation": section.get("citation"),
            "section_title": section.get("section_title"),
            "section_number": section.get("section_number"),
            "offense_family": section.get("offense_family"),
            "classification": section.get("classification", []),
            "mental_states": section.get("mental_states", []),
            "conduct_types": section.get("conduct_types", []),
            "victim_types": section.get("victim_types", []),
            "injury_types": section.get("injury_types", []),
            "weapon_types": section.get("weapon_types", []),
            "property_types": section.get("property_types", []),
            "location_types": section.get("location_types", []),
            "relationship_contexts": section.get("relationship_contexts", []),
            "aggravating_factors": section.get("aggravating_factors", []),
            "plain_english_terms": section.get("plain_english_terms", []),
            "cross_references": section.get("cross_references", []),
            "url": section.get("url"),
            "source_note": section.get("source_note"),
            "content": "\n".join([part for part in content_parts if part]).strip(),
        })

    return chunks


def build_fallback_text_chunks(section: dict[str, Any]) -> list[dict[str, Any]]:
    body = clean_text(section.get("clean_text", ""))
    text_chunks = fallback_window_chunks(body)

    if len(text_chunks) <= 1:
        return []

    chunks: list[dict[str, Any]] = []

    for idx, text in enumerate(text_chunks, start=1):
        content_parts = [
            f"Citation: {section.get('citation', '')}",
            f"Title: {section.get('section_title', '')}",
            f"Text chunk: {idx}",
            f"Offense family: {section.get('offense_family', '') or 'unknown'}",
        ]

        if section.get("classification"):
            content_parts.append(f"Classification: {', '.join(section['classification'])}")

        if section.get("plain_english_terms"):
            content_parts.append(f"Plain English terms: {', '.join(section['plain_english_terms'])}")

        content_parts.append(f"Chunk text: {text}")

        chunks.append({
            "chunk_id": f"{section['id']}::text::{idx}",
            "section_id": section["id"],
            "chunk_type": "text_window",
            "citation": section.get("citation"),
            "section_title": section.get("section_title"),
            "section_number": section.get("section_number"),
            "offense_family": section.get("offense_family"),
            "classification": section.get("classification", []),
            "mental_states": section.get("mental_states", []),
            "conduct_types": section.get("conduct_types", []),
            "victim_types": section.get("victim_types", []),
            "injury_types": section.get("injury_types", []),
            "weapon_types": section.get("weapon_types", []),
            "property_types": section.get("property_types", []),
            "location_types": section.get("location_types", []),
            "relationship_contexts": section.get("relationship_contexts", []),
            "aggravating_factors": section.get("aggravating_factors", []),
            "plain_english_terms": section.get("plain_english_terms", []),
            "cross_references": section.get("cross_references", []),
            "url": section.get("url"),
            "source_note": section.get("source_note"),
            "content": "\n".join([part for part in content_parts if part]).strip(),
        })

    return chunks


def chunk_section(section: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    parent_chunk = build_parent_chunk(section)
    chunks.append(parent_chunk)

    subsection_chunks = build_subsection_chunks(section)
    if subsection_chunks:
        chunks.extend(subsection_chunks)
        return chunks

    fallback_chunks = build_fallback_text_chunks(section)
    chunks.extend(fallback_chunks)

    return chunks


def main() -> None:
    if not INPUT_JSON.exists():
        raise FileNotFoundError(f"Normalized ILCS file not found: {INPUT_JSON}")

    payload = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    sections = payload.get("sections", [])

    all_chunks: list[dict[str, Any]] = []

    for section in sections:
        section_chunks = chunk_section(section)
        all_chunks.extend(section_chunks)

    output_payload = {
        "source_url": payload.get("source_url"),
        "scraped_at": payload.get("scraped_at"),
        "total_sections": len(sections),
        "total_chunks": len(all_chunks),
        "chunks": all_chunks,
    }

    OUT_JSON.write_text(
        json.dumps(output_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Loaded sections: {len(sections)}")
    print(f"Built chunks:    {len(all_chunks)}")
    print(f"Saved JSON:      {OUT_JSON}")
    print(f"Saved JSONL:     {OUT_JSONL}")


if __name__ == "__main__":
    main()