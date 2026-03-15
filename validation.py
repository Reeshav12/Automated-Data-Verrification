import re


def validate_data(id_type: str, extracted_text: str) -> bool:
    text = (extracted_text or "").upper()

    patterns = {
        "Aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "PAN Card": r"\b[A-Z]{5}\d{4}[A-Z]\b",
        "Voter ID": r"\b[A-Z]{3}\d{7}\b",
        "Passport": r"\b[A-Z][0-9]{7}\b",
    }

    if id_type not in patterns:
        return False

    return bool(re.search(patterns[id_type], text))
