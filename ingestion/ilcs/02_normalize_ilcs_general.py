import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = BASE_DIR / "data" / "raw" / "ilcs" / "ilcs_720_5_sections_raw.json"
OUT_DIR = BASE_DIR / "data" / "processed" / "ilcs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_JSON = OUT_DIR / "ilcs_720_5_sections_general.json"
OUT_JSONL = OUT_DIR / "ilcs_720_5_sections_general.jsonl"


CLASSIFICATION_PATTERNS = [
    "Class X felony",
    "Class 1 felony",
    "Class 2 felony",
    "Class 3 felony",
    "Class 4 felony",
    "Class A misdemeanor",
    "Class B misdemeanor",
    "Class C misdemeanor",
    "petty offense",
    "business offense",
]

MENTAL_STATE_PATTERNS = [
    "knowingly",
    "intentionally",
    "recklessly",
    "negligently",
    "with intent",
    "intent to",
    "knowledge that",
]

OFFENSE_RULES = [
    {
        "family": "assault",
        "title_patterns": [r"\baggravated assault\b", r"\bassault\b"],
        "conduct_types": ["threat", "menacing_conduct", "attempted_violence"],
        "victim_types": ["person"],
        "injury_types": [],
        "weapon_types": [],
        "property_types": [],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "assault", "threatened to hit", "made victim afraid",
            "raised fist", "lunged", "swung at", "attempted strike"
        ],
    },
    {
        "family": "battery",
        "title_patterns": [r"\baggravated battery\b", r"\bbattery\b"],
        "conduct_types": ["physical_contact", "bodily_harm"],
        "victim_types": ["person"],
        "injury_types": ["bodily_harm"],
        "weapon_types": [],
        "property_types": [],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "battery", "punched", "hit", "struck", "slapped",
            "kicked", "shoved", "bodily harm", "physical contact",
            "fight", "face punch"
        ],
    },
    {
        "family": "domestic_battery",
        "title_patterns": [r"\baggravated domestic battery\b", r"\bdomestic battery\b"],
        "conduct_types": ["physical_contact", "bodily_harm", "strangulation"],
        "victim_types": ["household_member", "family_member", "dating_partner"],
        "injury_types": ["bodily_harm"],
        "weapon_types": [],
        "property_types": [],
        "location_types": [],
        "relationship_contexts": ["domestic", "family", "dating"],
        "plain_terms": [
            "domestic battery", "boyfriend", "girlfriend", "wife", "husband",
            "household member", "dating relationship", "choked", "strangled"
        ],
    },
    {
        "family": "homicide",
        "title_patterns": [
            r"\bfirst degree murder\b",
            r"\bsecond degree murder\b",
            r"\bmurder\b",
            r"\bmanslaughter\b",
            r"\bhomicide\b",
        ],
        "conduct_types": ["killing", "causing_death"],
        "victim_types": ["person"],
        "injury_types": ["death"],
        "weapon_types": [],
        "property_types": [],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "killed", "caused death", "fatal", "deceased",
            "murder", "homicide", "manslaughter"
        ],
    },
    {
        "family": "kidnapping_restraint",
        "title_patterns": [
            r"\bkidnapping\b",
            r"\bunlawful restraint\b",
            r"\baggravated unlawful restraint\b",
            r"\bforcible detention\b",
        ],
        "conduct_types": ["detention", "confinement", "asportation"],
        "victim_types": ["person"],
        "injury_types": [],
        "weapon_types": [],
        "property_types": [],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "kidnapped", "held against will", "wouldn't let leave",
            "restrained", "confined", "forced into car"
        ],
    },
    {
        "family": "sexual_offense",
        "title_patterns": [
            r"\bcriminal sexual assault\b",
            r"\bcriminal sexual abuse\b",
            r"\bpredatory criminal sexual assault\b",
            r"\bsexual\b",
        ],
        "conduct_types": ["sexual_contact", "sexual_penetration", "sexual_exploitation"],
        "victim_types": ["person", "minor"],
        "injury_types": [],
        "weapon_types": [],
        "property_types": [],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "sexual assault", "sexual abuse", "molested",
            "unwanted sexual contact", "rape"
        ],
    },
    {
        "family": "robbery",
        "title_patterns": [r"\barmed robbery\b", r"\brobbery\b"],
        "conduct_types": ["taking_property", "force", "threat"],
        "victim_types": ["person"],
        "injury_types": [],
        "weapon_types": ["weapon_possible"],
        "property_types": ["property"],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "robbery", "took by force", "snatched with force",
            "mugging", "stick up", "armed robbery"
        ],
    },
    {
        "family": "burglary",
        "title_patterns": [
            r"\bresidential burglary\b",
            r"\bburglary\b",
            r"\bpossession of burglary tools\b",
        ],
        "conduct_types": ["entry", "remaining_without_authority", "intent_to_commit_felony_or_theft"],
        "victim_types": [],
        "injury_types": [],
        "weapon_types": [],
        "property_types": ["building", "dwelling", "vehicle"],
        "location_types": ["residence", "building"],
        "relationship_contexts": [],
        "plain_terms": [
            "broke in", "forced entry", "went inside to steal",
            "entered house", "entered building", "burglary tools"
        ],
    },
    {
        "family": "theft",
        "title_patterns": [r"\bretail theft\b", r"\btheft\b", r"\bstolen\b"],
        "conduct_types": ["taking_property", "deception", "control_over_property"],
        "victim_types": [],
        "injury_types": [],
        "weapon_types": [],
        "property_types": ["property", "money", "merchandise", "vehicle_possible"],
        "location_types": ["store_possible"],
        "relationship_contexts": [],
        "plain_terms": [
            "stole", "shoplifting", "took property", "took money",
            "retail theft", "stolen item"
        ],
    },
    {
        "family": "vehicle_offense",
        "title_patterns": [
            r"\bpossession of a stolen motor vehicle\b",
            r"\bstolen motor vehicle\b",
            r"\bmotor vehicle\b",
        ],
        "conduct_types": ["taking_vehicle", "possessing_stolen_vehicle"],
        "victim_types": [],
        "injury_types": [],
        "weapon_types": [],
        "property_types": ["motor_vehicle"],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "stole car", "taken vehicle", "stolen motor vehicle",
            "carjacking possible", "possessed stolen car"
        ],
    },
    {
        "family": "weapons",
        "title_patterns": [
            r"\bunlawful use of weapons\b",
            r"\baggravated unlawful use of a weapon\b",
            r"\barmed violence\b",
            r"\bweapon\b",
            r"\bfirearm\b",
        ],
        "conduct_types": ["weapon_possession", "weapon_use", "armed_conduct"],
        "victim_types": [],
        "injury_types": [],
        "weapon_types": ["firearm", "weapon"],
        "property_types": [],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "gun", "firearm", "handgun", "rifle", "weapon",
            "carried gun", "possessed gun", "armed"
        ],
    },
    {
        "family": "criminal_damage",
        "title_patterns": [
            r"\bcriminal damage\b",
            r"\bcriminal defacement\b",
            r"\bproperty damage\b",
            r"\barson\b",
        ],
        "conduct_types": ["damage_property", "defacement", "destruction", "fire_setting"],
        "victim_types": [],
        "injury_types": [],
        "weapon_types": ["fire_possible"],
        "property_types": ["property", "building", "vehicle"],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "damaged property", "vandalized", "broke window",
            "set fire", "burned building", "graffiti"
        ],
    },
    {
        "family": "disorderly_conduct",
        "title_patterns": [r"\bdisorderly conduct\b", r"\bmob action\b"],
        "conduct_types": ["public_disturbance", "false_report", "tumultuous_behavior", "group_violence"],
        "victim_types": [],
        "injury_types": [],
        "weapon_types": [],
        "property_types": [],
        "location_types": ["public"],
        "relationship_contexts": [],
        "plain_terms": [
            "disorderly", "disturbance", "mob action",
            "false alarm", "group attack", "public disruption"
        ],
    },
    {
        "family": "obstructing_police",
        "title_patterns": [
            r"\bresisting\b",
            r"\bobstructing\b",
            r"\bescape\b",
            r"\bconcealing or aiding\b",
        ],
        "conduct_types": ["resisting", "obstructing", "flight", "escape"],
        "victim_types": ["peace_officer", "corrections_staff"],
        "injury_types": [],
        "weapon_types": [],
        "property_types": [],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "resisting arrest", "ran from police", "obstructed officer",
            "fought police", "escaped custody"
        ],
    },
    {
        "family": "threat_intimidation",
        "title_patterns": [r"\bintimidation\b", r"\bthreat\b", r"\bstalking\b"],
        "conduct_types": ["threat", "harassment", "course_of_conduct"],
        "victim_types": ["person"],
        "injury_types": [],
        "weapon_types": [],
        "property_types": [],
        "location_types": [],
        "relationship_contexts": [],
        "plain_terms": [
            "threatened to kill", "threat message", "terrorized",
            "stalking", "intimidation", "harassment"
        ],
    },
]


def clean_text(text: str) -> str:
    text = text or ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def strip_source_note(body_text: str) -> str:
    body_text = re.sub(
        r"\(Source:\s*.*?\)\s*$",
        "",
        body_text,
        flags=re.DOTALL | re.IGNORECASE
    )
    return clean_text(body_text)


def extract_classification(body: str) -> list[str]:
    found = []
    for item in CLASSIFICATION_PATTERNS:
        if re.search(rf"\b{re.escape(item)}\b", body, flags=re.IGNORECASE):
            found.append(item)
    return sorted(set(found))


def extract_mental_states(body: str) -> list[str]:
    lower = body.lower()
    found = [item for item in MENTAL_STATE_PATTERNS if item in lower]
    return sorted(set(found))


def extract_cross_references(body: str) -> list[str]:
    refs = set()

    for match in re.finditer(r"\b\d{3}\s+ILCS\s+\d+/[0-9A-Za-z.\-]+\b", body):
        refs.add(match.group(0).strip())

    return sorted(refs)


def extract_elements_text(body: str) -> list[str]:
    lines = []
    raw_lines = [line.strip() for line in body.split("\n") if line.strip()]

    for line in raw_lines:
        if len(line) < 20:
            continue
        if line.lower().startswith("source:"):
            continue
        lines.append(clean_text(line))

    return lines[:25]


def infer_title_rule_matches(section_title: str, clean_body: str) -> list[dict]:
    haystack = f"{section_title}\n{clean_body}".lower()
    matches = []

    for rule in OFFENSE_RULES:
        for pattern in rule["title_patterns"]:
            if re.search(pattern, haystack, flags=re.IGNORECASE):
                matches.append(rule)
                break

    return matches


def choose_primary_family(matches: list[dict]) -> str | None:
    if not matches:
        return None

    priority = [
        "domestic_battery",
        "homicide",
        "sexual_offense",
        "robbery",
        "burglary",
        "vehicle_offense",
        "weapons",
        "obstructing_police",
        "kidnapping_restraint",
        "threat_intimidation",
        "criminal_damage",
        "disorderly_conduct",
        "theft",
        "battery",
        "assault",
    ]

    found = [m["family"] for m in matches]

    for item in priority:
        if item in found:
            return item

    return found[0]


def merge_rule_fields(matches: list[dict], field_name: str) -> list[str]:
    values = set()
    for match in matches:
        for value in match.get(field_name, []):
            values.add(value)
    return sorted(values)


def infer_weapon_types(section_title: str, clean_body: str) -> list[str]:
    text = f"{section_title}\n{clean_body}".lower()
    values = set()

    keywords = {
        "firearm": ["firearm", "gun", "handgun", "rifle", "shotgun"],
        "knife": ["knife", "dagger", "blade"],
        "blunt_object": ["bat", "club", "blunt object"],
        "deadly_weapon": ["deadly weapon"],
        "dangerous_instrument": ["dangerous instrument"],
    }

    for weapon_type, terms in keywords.items():
        if any(term in text for term in terms):
            values.add(weapon_type)

    return sorted(values)


def infer_victim_types(section_title: str, clean_body: str) -> list[str]:
    text = f"{section_title}\n{clean_body}".lower()
    values = set()

    mapping = {
        "person": ["individual", "person", "victim"],
        "peace_officer": ["peace officer", "police officer", "law enforcement officer"],
        "child": ["child", "minor"],
        "elderly_person": ["60 years of age or older", "elderly", "senior citizen"],
        "teacher": ["teacher", "school employee"],
        "household_member": ["family or household member", "household member"],
    }

    for victim_type, terms in mapping.items():
        if any(term in text for term in terms):
            values.add(victim_type)

    return sorted(values)


def infer_injury_types(section_title: str, clean_body: str) -> list[str]:
    text = f"{section_title}\n{clean_body}".lower()
    values = set()

    mapping = {
        "bodily_harm": ["bodily harm"],
        "great_bodily_harm": ["great bodily harm"],
        "permanent_disability": ["permanent disability"],
        "disfigurement": ["disfigurement"],
        "death": ["death", "killed", "causes death"],
        "strangulation": ["strangulation", "strangle", "impede the normal breathing"],
    }

    for injury_type, terms in mapping.items():
        if any(term in text for term in terms):
            values.add(injury_type)

    return sorted(values)


def infer_property_types(section_title: str, clean_body: str) -> list[str]:
    text = f"{section_title}\n{clean_body}".lower()
    values = set()

    mapping = {
        "property": ["property"],
        "money": ["money", "currency", "cash"],
        "merchandise": ["merchandise", "retail"],
        "dwelling": ["dwelling", "residence"],
        "building": ["building"],
        "motor_vehicle": ["motor vehicle", "vehicle", "car"],
        "firearm": ["firearm"],
    }

    for property_type, terms in mapping.items():
        if any(term in text for term in terms):
            values.add(property_type)

    return sorted(values)


def infer_location_types(section_title: str, clean_body: str) -> list[str]:
    text = f"{section_title}\n{clean_body}".lower()
    values = set()

    mapping = {
        "public_way": ["public way"],
        "school": ["school", "school grounds"],
        "place_of_worship": ["place of worship", "church", "synagogue", "mosque"],
        "residence": ["dwelling", "residence", "home"],
        "park": ["public park", "park district"],
        "public": ["public place", "public property"],
        "correctional_facility": ["correctional institution", "penal institution", "jail", "prison"],
    }

    for location_type, terms in mapping.items():
        if any(term in text for term in terms):
            values.add(location_type)

    return sorted(values)


def infer_relationship_contexts(section_title: str, clean_body: str) -> list[str]:
    text = f"{section_title}\n{clean_body}".lower()
    values = set()

    mapping = {
        "domestic": ["family or household member", "domestic", "dating relationship"],
        "dating": ["dating relationship"],
        "family": ["family member", "household member"],
    }

    for rel_type, terms in mapping.items():
        if any(term in text for term in terms):
            values.add(rel_type)

    return sorted(values)


def infer_aggravating_factors(section_title: str, clean_body: str) -> list[str]:
    text = f"{section_title}\n{clean_body}".lower()
    factors = set()

    checks = {
        "great_bodily_harm": ["great bodily harm"],
        "disfigurement": ["disfigurement"],
        "permanent_disability": ["permanent disability"],
        "weapon_involved": ["deadly weapon", "firearm", "weapon"],
        "protected_victim": ["peace officer", "child", "teacher"],
        "public_location": ["public way", "public property", "school", "park district"],
        "residential_context": ["dwelling", "residence"],
        "domestic_context": ["family or household member", "domestic battery"],
        "strangulation": ["strangulation", "impede the normal breathing"],
    }

    for factor, terms in checks.items():
        if any(term in text for term in terms):
            factors.add(factor)

    return sorted(factors)


def build_plain_english_terms(
    section_title: str,
    primary_family: str | None,
    rule_terms: list[str],
    conduct_types: list[str],
    weapon_types: list[str],
    property_types: list[str],
    relationship_contexts: list[str],
) -> list[str]:
    terms = set(rule_terms)
    title_lower = (section_title or "").lower()

    if "battery" in title_lower:
        terms.update(["hit", "punch", "slap", "kick", "shove", "fight"])

    if "assault" in title_lower:
        terms.update(["threatened", "swung at", "attempted attack"])

    if "robbery" in title_lower:
        terms.update(["mugging", "stick up", "took by force"])

    if "burglary" in title_lower:
        terms.update(["broke in", "forced entry", "entered to steal"])

    if "theft" in title_lower:
        terms.update(["stole", "shoplifted", "took item"])

    if "weapon" in title_lower or "firearm" in title_lower:
        terms.update(["gun", "armed", "carried weapon"])

    if "domestic" in title_lower:
        terms.update(["boyfriend", "girlfriend", "spouse", "household member"])

    if primary_family == "obstructing_police":
        terms.update(["ran from police", "resisted arrest", "obstructed officer"])

    if "weapon_possession" in conduct_types:
        terms.update(["possessed gun", "had firearm"])

    if "motor_vehicle" in property_types:
        terms.update(["car", "vehicle", "stolen car"])

    if "domestic" in relationship_contexts:
        terms.update(["domestic violence"])

    for conduct in conduct_types:
        terms.add(conduct.replace("_", " "))

    for weapon in weapon_types:
        terms.add(weapon.replace("_", " "))

    return sorted(terms)


def build_search_text(record: dict) -> str:
    parts = [
        record.get("citation", ""),
        record.get("section_title", ""),
        record.get("act_name", ""),
        record.get("clean_text", ""),
        " ".join(record.get("conduct_types", [])),
        " ".join(record.get("victim_types", [])),
        " ".join(record.get("injury_types", [])),
        " ".join(record.get("weapon_types", [])),
        " ".join(record.get("property_types", [])),
        " ".join(record.get("location_types", [])),
        " ".join(record.get("relationship_contexts", [])),
        " ".join(record.get("aggravating_factors", [])),
        " ".join(record.get("mental_states", [])),
        " ".join(record.get("classification", [])),
        " ".join(record.get("plain_english_terms", [])),
        record.get("offense_family", "") or "",
    ]
    return clean_text("\n".join([p for p in parts if p]))


def normalize_section(section: dict) -> dict:
    citation = clean_text(section.get("citation", ""))
    section_number = clean_text(section.get("section_number", ""))
    section_title = clean_text(section.get("section_title", ""))
    chapter_number = clean_text(section.get("chapter_number", ""))
    chapter_name = clean_text(section.get("chapter_name", ""))
    act_id = clean_text(section.get("act_id", ""))
    act_name = clean_text(section.get("act_name", ""))
    url = clean_text(section.get("url", ""))
    source_note = clean_text(section.get("source_note", ""))
    raw_text = clean_text(section.get("body_text", ""))
    clean_body = strip_source_note(raw_text)

    matches = infer_title_rule_matches(section_title, clean_body)
    primary_family = choose_primary_family(matches)

    conduct_types = merge_rule_fields(matches, "conduct_types")
    victim_types = sorted(set(
        merge_rule_fields(matches, "victim_types") + infer_victim_types(section_title, clean_body)
    ))
    injury_types = sorted(set(
        merge_rule_fields(matches, "injury_types") + infer_injury_types(section_title, clean_body)
    ))
    weapon_types = sorted(set(
        merge_rule_fields(matches, "weapon_types") + infer_weapon_types(section_title, clean_body)
    ))
    property_types = sorted(set(
        merge_rule_fields(matches, "property_types") + infer_property_types(section_title, clean_body)
    ))
    location_types = sorted(set(
        merge_rule_fields(matches, "location_types") + infer_location_types(section_title, clean_body)
    ))
    relationship_contexts = sorted(set(
        merge_rule_fields(matches, "relationship_contexts") + infer_relationship_contexts(section_title, clean_body)
    ))

    rule_terms = merge_rule_fields(matches, "plain_terms")
    classification = extract_classification(clean_body)
    mental_states = extract_mental_states(clean_body)
    cross_references = extract_cross_references(clean_body)
    elements_text = extract_elements_text(clean_body)
    aggravating_factors = infer_aggravating_factors(section_title, clean_body)

    plain_english_terms = build_plain_english_terms(
        section_title=section_title,
        primary_family=primary_family,
        rule_terms=rule_terms,
        conduct_types=conduct_types,
        weapon_types=weapon_types,
        property_types=property_types,
        relationship_contexts=relationship_contexts,
    )

    record = {
        "id": clean_text(section.get("id", "")),
        "citation": citation,
        "section_number": section_number,
        "section_title": section_title,
        "chapter_number": chapter_number,
        "chapter_name": chapter_name,
        "act_id": act_id,
        "act_name": act_name,
        "url": url,
        "source_note": source_note,
        "raw_text": raw_text,
        "clean_text": clean_body,
        "offense_family": primary_family,
        "conduct_types": conduct_types,
        "victim_types": victim_types,
        "injury_types": injury_types,
        "weapon_types": weapon_types,
        "property_types": property_types,
        "location_types": location_types,
        "relationship_contexts": relationship_contexts,
        "aggravating_factors": aggravating_factors,
        "mental_states": mental_states,
        "classification": classification,
        "cross_references": cross_references,
        "elements_text": elements_text,
        "plain_english_terms": plain_english_terms,
        "is_repealed": "repealed" in clean_body.lower() or "repealed" in section_title.lower(),
    }

    record["search_text"] = build_search_text(record)
    return record


def main() -> None:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw ILCS file not found: {RAW_PATH}")

    payload = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    raw_sections = payload.get("sections", [])

    normalized_sections = [normalize_section(section) for section in raw_sections]

    output_payload = {
        "source_url": payload.get("source_url"),
        "scraped_at": payload.get("scraped_at"),
        "total_sections": len(normalized_sections),
        "sections": normalized_sections,
    }

    OUT_JSON.write_text(
        json.dumps(output_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for item in normalized_sections:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Normalized {len(normalized_sections)} sections")
    print(f"Saved JSON:  {OUT_JSON}")
    print(f"Saved JSONL: {OUT_JSONL}")


if __name__ == "__main__":
    main()