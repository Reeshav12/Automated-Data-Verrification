from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


DOCUMENT_OPTIONS = [
    "Aadhaar",
    "PAN Card",
    "Driving Licence",
    "Voter ID",
    "Passport",
    "10th Marksheet",
    "12th Marksheet",
]


DOCUMENT_RULES = {
    "Aadhaar": {
        "keywords": ["aadhaar", "aadhaar card", "uidai", "eaadhaar", "e-aadhaar"],
        "validation_type": "Aadhaar",
    },
    "PAN Card": {
        "keywords": ["pan", "permanent account number", "income tax"],
        "validation_type": "PAN Card",
    },
    "Driving Licence": {
        "keywords": ["driving", "licence", "license", "dl"],
        "validation_type": None,
    },
    "Voter ID": {
        "keywords": ["voter", "elector", "epic"],
        "validation_type": "Voter ID",
    },
    "Passport": {
        "keywords": ["passport"],
        "validation_type": "Passport",
    },
    "10th Marksheet": {
        "keywords": ["10th", "class x", "secondary", "matric", "marksheet", "mark sheet"],
        "validation_type": None,
    },
    "12th Marksheet": {
        "keywords": ["12th", "class xii", "senior secondary", "intermediate", "marksheet", "mark sheet"],
        "validation_type": None,
    },
}


@dataclass
class DigiLockerConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    authorize_url: str
    token_url: str
    issued_docs_url: str
    file_url: str
    purpose: str = "verification"

    @classmethod
    def from_env(cls) -> "DigiLockerConfig | None":
        client_id = os.getenv("DIGILOCKER_CLIENT_ID", "").strip()
        client_secret = os.getenv("DIGILOCKER_CLIENT_SECRET", "").strip()
        redirect_uri = os.getenv("DIGILOCKER_REDIRECT_URI", "").strip()

        if not client_id or not client_secret or not redirect_uri:
            return None

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            authorize_url=os.getenv(
                "DIGILOCKER_AUTHORIZE_URL",
                "https://entity.digilocker.gov.in/public/oauth2/1/authorize",
            ).strip(),
            token_url=os.getenv(
                "DIGILOCKER_TOKEN_URL",
                "https://entity.digilocker.gov.in/public/oauth2/1/token",
            ).strip(),
            issued_docs_url=os.getenv(
                "DIGILOCKER_ISSUED_DOCS_URL",
                "https://entity.digilocker.gov.in/public/oauth2/2/entity/files/issued",
            ).strip(),
            file_url=os.getenv(
                "DIGILOCKER_FILE_URL",
                "https://entity.digilocker.gov.in/public/oauth2/1/entity/file/uri",
            ).strip(),
            purpose=os.getenv("DIGILOCKER_CONSENT_PURPOSE", "verification").strip(),
        )


def build_pkce_pair() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(64)
    challenge_digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_digest).decode("utf-8").rstrip("=")
    return code_verifier, code_challenge


def build_authorize_url(config: DigiLockerConfig, state: str, code_challenge: str) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "purpose": config.purpose,
        }
    )
    return f"{config.authorize_url}?{query}"


def exchange_code_for_token(
    config: DigiLockerConfig,
    code: str,
    code_verifier: str,
) -> dict[str, Any]:
    response = requests.post(
        config.token_url,
        data={
            "code": code,
            "grant_type": "authorization_code",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "redirect_uri": config.redirect_uri,
            "code_verifier": code_verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(config: DigiLockerConfig, refresh_token: str) -> dict[str, Any]:
    response = requests.post(
        config.token_url,
        auth=(config.client_id, config.client_secret),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def list_issued_documents(access_token: str, config: DigiLockerConfig) -> list[dict[str, Any]]:
    response = requests.get(
        config.issued_docs_url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("items", [])


def file_extension_for_item(item: dict[str, Any]) -> str:
    mime = str(item.get("mime", "")).lower()
    name = Path(str(item.get("name", "")))
    if name.suffix:
        return name.suffix.lower()
    if "pdf" in mime:
        return ".pdf"
    if "png" in mime:
        return ".png"
    if "jpg" in mime or "jpeg" in mime:
        return ".jpg"
    return ".pdf"


def verify_response_hmac(content: bytes, expected_hmac: str, client_secret: str) -> bool:
    if not expected_hmac:
        return True
    digest = hmac.new(
        client_secret.encode("utf-8"),
        content,
        hashlib.sha256,
    ).digest()
    calculated_hmac = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(calculated_hmac, expected_hmac)


def download_document(
    access_token: str,
    uri: str,
    config: DigiLockerConfig,
) -> tuple[bytes, str]:
    response = requests.get(
        config.file_url,
        params={"uri": uri},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=60,
    )
    response.raise_for_status()

    response_hmac = response.headers.get("hmac", "")
    if not verify_response_hmac(response.content, response_hmac, config.client_secret):
        raise ValueError("DigiLocker file integrity check failed.")

    return response.content, response.headers.get("Content-Type", "")


def item_matches_option(item: dict[str, Any], selected_option: str) -> bool:
    rule = DOCUMENT_RULES.get(selected_option)
    if not rule:
        return False

    searchable_text = " ".join(
        [
            str(item.get("name", "")),
            str(item.get("description", "")),
            str(item.get("issuer", "")),
            str(item.get("doctype", "")),
            str(item.get("uri", "")),
        ]
    ).lower()

    return any(keyword in searchable_text for keyword in rule["keywords"])


def filter_documents(
    items: list[dict[str, Any]],
    selected_options: list[str],
) -> list[tuple[str, dict[str, Any]]]:
    matches: list[tuple[str, dict[str, Any]]] = []
    seen_uris = set()

    for option in selected_options:
        for item in items:
            uri = str(item.get("uri", "")).strip()
            if not uri or uri in seen_uris:
                continue
            if item_matches_option(item, option):
                matches.append((option, item))
                seen_uris.add(uri)

    return matches


def validation_type_for_option(option: str) -> str | None:
    rule = DOCUMENT_RULES.get(option, {})
    return rule.get("validation_type")
