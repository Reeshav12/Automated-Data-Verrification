import re

from fuzzywuzzy import fuzz


FIELD_PATTERNS = {
    "Name": [
        r"(?:\bname\b|\bcandidate name\b|\bstudent name\b|\bapplicant name\b)\s*[:\-]?\s*([A-Za-z][A-Za-z\s.]{1,80})",
    ],
    "Father's Name": [
        r"(?:\bfather'?s name\b|\bfather name\b|\bfather\b)\s*[:\-]?\s*([A-Za-z][A-Za-z\s.]{1,80})",
    ],
    "Mother's Name": [
        r"(?:\bmother'?s name\b|\bmother name\b|\bmother\b)\s*[:\-]?\s*([A-Za-z][A-Za-z\s.]{1,80})",
    ],
    "DOB": [
        r"(?:\bdob\b|\bdate of birth\b|\bbirth date\b)\s*[:\-]?\s*([0-9]{1,4}[\/.\-][0-9]{1,2}[\/.\-][0-9]{1,4})",
        r"\b([0-9]{1,2}[\/.\-][0-9]{1,2}[\/.\-][0-9]{4})\b",
    ],
}


IGNORE_NAME_TERMS = {
    "GOVERNMENT",
    "INDIA",
    "UNIVERSITY",
    "SECONDARY",
    "CERTIFICATE",
    "MARKSHEET",
    "MARK SHEET",
    "BOARD",
    "ENROLMENT",
    "ENROLLMENT",
    "ROLL",
    "NUMBER",
    "DOB",
    "DATE OF BIRTH",
    "FATHER",
    "MOTHER",
}


def clean_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        normalized = clean_whitespace(value)
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            ordered.append(normalized)
    return ordered


def normalize_date(date_str: str) -> str:
    raw_value = clean_whitespace(str(date_str))
    if not raw_value:
        return ""

    match = re.search(r"([0-9]{1,4})[\/.\-]([0-9]{1,2})[\/.\-]([0-9]{1,4})", raw_value)
    if not match:
        return raw_value.lower()

    first, second, third = match.groups()
    if len(first) == 4:
        year, month, day = first, second, third
    else:
        day, month, year = first, second, third

    if len(year) == 2:
        year = f"20{year}" if int(year) <= 30 else f"19{year}"

    return f"{day.zfill(2)}-{month.zfill(2)}-{year.zfill(4)}"


def preprocess_candidate(candidate: str) -> str:
    normalized = clean_whitespace(candidate).lower()
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    return clean_whitespace(normalized)


def likely_name_lines(text: str) -> list[str]:
    candidates = []
    for line in text.splitlines():
        compact = clean_whitespace(line)
        if len(compact) < 5 or any(char.isdigit() for char in compact):
            continue

        upper_value = compact.upper()
        if any(term in upper_value for term in IGNORE_NAME_TERMS):
            continue

        words = re.findall(r"[A-Za-z]+", compact)
        if 1 < len(words) <= 5:
            candidates.append(" ".join(words))

    return dedupe(candidates[:10])


def extract_candidates_for_field(field: str, text: str) -> list[str]:
    values = []
    for pattern in FIELD_PATTERNS.get(field, []):
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            values.append(match if isinstance(match, str) else match[-1])

    if field == "Name":
        values.extend(likely_name_lines(text))

    return dedupe(values)


def extract_entities_from_text(text: str) -> dict[str, list[str]]:
    names = []
    for field in ("Name", "Father's Name", "Mother's Name"):
        names.extend(extract_candidates_for_field(field, text))

    dates = extract_candidates_for_field("DOB", text)
    return {"PERSON": dedupe(names), "DATE": dedupe(dates)}


def similarity_score(left: str, right: str) -> int:
    return max(
        fuzz.ratio(left, right),
        fuzz.partial_ratio(left, right),
        fuzz.token_set_ratio(left, right),
    )


def match_entities_across_documents(
    entity_type: str,
    target_value: str,
    extracted_texts: list[str],
    threshold: int = 85,
) -> int:
    if entity_type == "DOB":
        normalized_target = normalize_date(target_value)
    else:
        normalized_target = preprocess_candidate(target_value)

    if not normalized_target:
        return 0

    match_count = 0
    for text in extracted_texts:
        candidates = extract_candidates_for_field(entity_type, text)
        for candidate in candidates:
            normalized_candidate = (
                normalize_date(candidate)
                if entity_type == "DOB"
                else preprocess_candidate(candidate)
            )

            if not normalized_candidate:
                continue

            if similarity_score(normalized_target, normalized_candidate) >= threshold:
                match_count += 1
                break

    return match_count
