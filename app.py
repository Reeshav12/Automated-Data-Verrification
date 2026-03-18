from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
import re
from uuid import uuid4

import streamlit as st

from digilocker import DOCUMENT_OPTIONS, validation_type_for_option
from ner import match_entities_across_documents, normalize_date
from ocr import extract_text_from_document
from preprocessing import preprocess_image
from validation import validate_data


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads" / "raw"
PROCESSED_DIR = BASE_DIR / "uploads" / "processed"
TEXT_DIR = BASE_DIR / "uploads" / "extracted_texts"

for directory in (UPLOAD_DIR, PROCESSED_DIR, TEXT_DIR):
    directory.mkdir(parents=True, exist_ok=True)


st.set_page_config(
    page_title="Smart Verification India",
    page_icon="SV",
    layout="wide",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            color: #11233b;
            background:
                radial-gradient(circle at top left, rgba(255, 153, 51, 0.16), transparent 24%),
                radial-gradient(circle at top right, rgba(19, 136, 8, 0.13), transparent 26%),
                linear-gradient(180deg, #fff8ef 0%, #f7fbff 54%, #eef5fb 100%);
        }
        .stApp, .stApp p, .stApp div, .stApp span, .stMarkdown, .stCaption, label {
            color: #11233b;
        }
        h1, h2, h3, h4 {
            color: #0d2038 !important;
        }
        .hero-card, .panel-card, .result-card, .doc-card {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 24px;
            padding: 1.35rem;
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
        }
        .hero-title {
            font-size: 2.5rem;
            line-height: 1.05;
            margin-bottom: 0.45rem;
        }
        .hero-copy {
            font-size: 1rem;
            color: #41556f;
            margin-bottom: 0;
        }
        .eyebrow {
            display: inline-block;
            padding: 0.28rem 0.7rem;
            border-radius: 999px;
            background: rgba(255, 153, 51, 0.12);
            color: #b45309;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.8rem;
        }
        .flag-line {
            width: 120px;
            height: 5px;
            border-radius: 999px;
            background: linear-gradient(90deg, #ff9933 0%, #ffffff 50%, #138808 100%);
            margin: 0.5rem 0 1rem 0;
            border: 1px solid rgba(15, 23, 42, 0.06);
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
        }
        .summary-tile {
            background: #f8fbff;
            border: 1px solid #d8e5f3;
            border-radius: 18px;
            padding: 0.95rem;
        }
        .summary-label {
            color: #60758f;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .summary-value {
            color: #11233b;
            font-size: 1.2rem;
            font-weight: 800;
        }
        .status-pill {
            display: inline-block;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }
        .status-success {
            background: #dcfce7;
            color: #166534;
        }
        .status-warning {
            background: #fef3c7;
            color: #92400e;
        }
        .status-danger {
            background: #fee2e2;
            color: #991b1b;
        }
        .table-head, .table-row {
            display: grid;
            grid-template-columns: 1.2fr 1fr 1fr 1fr;
            gap: 0.75rem;
            align-items: center;
        }
        .table-head {
            padding: 0 0.35rem 0.5rem 0.35rem;
            font-weight: 700;
            color: #18314d;
        }
        .table-row {
            background: #f8fbff;
            border: 1px solid #d8e5f3;
            border-radius: 18px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.7rem;
        }
        .chip {
            display: inline-block;
            padding: 0.28rem 0.66rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 700;
        }
        .chip-success {
            background: #dcfce7;
            color: #166534;
        }
        .chip-warning {
            background: #fef3c7;
            color: #92400e;
        }
        .chip-neutral {
            background: #e2e8f0;
            color: #334155;
        }
        .doc-meta {
            color: #51657d;
            margin: 0.25rem 0;
        }
        div[data-baseweb="input"] input,
        div[data-baseweb="base-input"] input,
        .stTextInput input,
        .stDateInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stTextArea textarea {
            background: #ffffff !important;
            color: #0f172a !important;
            border-color: #c8d7e6 !important;
        }
        .stButton button {
            background: linear-gradient(135deg, #ea580c 0%, #2563eb 100%);
            color: white !important;
            border: none !important;
        }
        .stButton button:hover {
            filter: brightness(1.04);
        }
        div[data-testid="stFileUploader"] {
            background: rgba(247, 250, 252, 0.98);
            border-radius: 18px;
            padding: 0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return cleaned or "document"


def save_bytes_file(file_bytes: bytes, filename: str) -> Path:
    suffix = Path(filename).suffix.lower() or ".pdf"
    unique_name = f"{uuid4().hex}_{safe_filename(Path(filename).stem)}{suffix}"
    destination = UPLOAD_DIR / unique_name
    destination.write_bytes(file_bytes)
    return destination


def process_saved_document(raw_path: Path, label: str, display_name: str, doc_type: str) -> dict:
    processed_path = raw_path
    mode = "PDF extraction / OCR" if raw_path.suffix.lower() == ".pdf" else "Image OCR"

    if raw_path.suffix.lower() != ".pdf":
        processed_path = preprocess_image(raw_path, PROCESSED_DIR)

    extracted_text = extract_text_from_document(processed_path)
    text_path = TEXT_DIR / f"{raw_path.stem}.txt"
    text_path.write_text(extracted_text, encoding="utf-8")

    return {
        "label": label,
        "filename": display_name,
        "mode": mode,
        "text": extracted_text,
        "text_path": text_path,
        "validation_ok": validate_data(validation_type_for_option(doc_type), extracted_text)
        if validation_type_for_option(doc_type)
        else None,
    }


def process_uploaded_document(uploaded_file, label: str, doc_type: str) -> dict:
    raw_path = save_bytes_file(uploaded_file.getbuffer(), uploaded_file.name)
    return process_saved_document(raw_path, label, uploaded_file.name, doc_type)


def build_demo_seed(details: dict, doc_type: str) -> str:
    raw = "|".join(
        [
            details["document_number"],
            details["name"],
            details["dob"],
            details.get("father_name", ""),
            details.get("mother_name", ""),
            doc_type,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()


def build_demo_reference(seed: str) -> str:
    return f"DLK-{seed[:12]}"


def build_demo_document_number(doc_type: str, fallback_value: str, seed: str) -> str:
    if fallback_value:
        return fallback_value

    generated_values = {
        "Aadhaar": f"{seed[:4]} {seed[4:8]} {seed[8:12]}",
        "PAN Card": f"{seed[:5]}{seed[5:9]}{seed[9]}",
        "Driving Licence": f"DL-{seed[:2]}{seed[2:6]}{seed[6:13]}",
        "Voter ID": f"{seed[:3]}{seed[3:10]}",
        "Passport": f"{seed[:1]}{seed[1:8]}",
        "10th Marksheet": f"X-{seed[:10]}",
        "12th Marksheet": f"XII-{seed[:10]}",
    }
    return generated_values.get(doc_type, seed[:12])


def build_demo_document_text(details: dict, doc_type: str) -> str:
    seed = build_demo_seed(details, doc_type)
    document_number = build_demo_document_number(doc_type, details["document_number"], seed)
    reference = build_demo_reference(seed)
    issuers = {
        "Aadhaar": "UIDAI",
        "PAN Card": "Income Tax Department",
        "Driving Licence": "State Transport Department",
        "Voter ID": "Election Commission of India",
        "Passport": "Passport Seva",
        "10th Marksheet": "Central Board of Secondary Education",
        "12th Marksheet": "Central Board of Secondary Education",
    }
    labels = {
        "Aadhaar": "Aadhaar Number",
        "PAN Card": "Permanent Account Number",
        "Driving Licence": "Driving Licence No",
        "Voter ID": "EPIC No",
        "Passport": "Passport No",
        "10th Marksheet": "Certificate Number",
        "12th Marksheet": "Certificate Number",
    }

    lines = [
        "DigiLocker Verification Sandbox",
        f"Document Type: {doc_type}",
        f"Issuer: {issuers.get(doc_type, 'Government Authority')}",
        f"Reference ID: {reference}",
        f"{labels.get(doc_type, 'Document Number')}: {document_number}",
        f"Name: {details['name']}",
        f"DOB: {details['dob']}",
    ]

    if details.get("father_name"):
        lines.append(f"Father's Name: {details['father_name']}")
    if details.get("mother_name"):
        lines.append(f"Mother's Name: {details['mother_name']}")
    if doc_type in {"10th Marksheet", "12th Marksheet"}:
        lines.append("Status: Passed")

    lines.append(f"DigiLocker URI: demo://india/{safe_filename(doc_type).lower()}/{seed[:16].lower()}")
    return "\n".join(lines)


def build_demo_digilocker_document(details: dict, doc_type: str) -> dict:
    seed = build_demo_seed(details, doc_type)
    text = build_demo_document_text(details, doc_type)
    return {
        "label": f"DigiLocker Verification - {doc_type}",
        "filename": f"{safe_filename(doc_type).lower()}_sandbox_record.txt",
        "mode": "Fake DigiLocker verification",
        "text": text,
        "text_path": None,
        "validation_ok": validate_data(validation_type_for_option(doc_type), text)
        if validation_type_for_option(doc_type)
        else None,
        "reference": build_demo_reference(seed),
        "doc_number": build_demo_document_number(doc_type, details["document_number"], seed),
    }


def build_match_results(details: dict, digilocker_documents: list[dict], uploaded_documents: list[dict]) -> dict:
    digilocker_texts = [document["text"] for document in digilocker_documents]
    uploaded_texts = [document["text"] for document in uploaded_documents]
    fields = {
        "Name": details["name"],
        "DOB": normalize_date(details["dob"]),
        "Father's Name": details["father_name"],
        "Mother's Name": details["mother_name"],
    }

    results = {}
    for field, value in fields.items():
        if not value:
            results[field] = {"digilocker": None, "uploaded": None, "final": None}
            continue

        digilocker_match = bool(match_entities_across_documents(field, value, digilocker_texts))
        uploaded_match = bool(match_entities_across_documents(field, value, uploaded_texts)) if uploaded_texts else None
        final_match = digilocker_match if uploaded_match is None else digilocker_match and uploaded_match
        results[field] = {
            "digilocker": digilocker_match,
            "uploaded": uploaded_match,
            "final": final_match,
        }

    return results


def build_document_number_status(details: dict, digilocker_document: dict, uploaded_documents: list[dict]) -> dict:
    expected_number = re.sub(r"\s+", "", details["document_number"]).upper()
    sandbox_number = re.sub(r"\s+", "", digilocker_document["doc_number"]).upper()
    digilocker_match = sandbox_number == expected_number if expected_number else True

    uploaded_match = None
    if uploaded_documents and expected_number:
        uploaded_match = any(expected_number in re.sub(r"\s+", "", document["text"]).upper() for document in uploaded_documents)

    final_match = digilocker_match if uploaded_match is None else digilocker_match and uploaded_match
    return {
        "digilocker": digilocker_match,
        "uploaded": uploaded_match,
        "final": final_match,
    }


def status_chip(value: bool | None, success: str, failure: str, skipped: str = "Optional") -> str:
    if value is None:
        return f'<span class="chip chip-neutral">{skipped}</span>'
    if value:
        return f'<span class="chip chip-success">{success}</span>'
    return f'<span class="chip chip-warning">{failure}</span>'


def render_match_table(match_results: dict) -> None:
    st.markdown(
        """
        <div class="table-head">
            <div>Field</div>
            <div>DigiLocker</div>
            <div>Uploaded Document</div>
            <div>Final Result</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for field, result in match_results.items():
        st.markdown(
            f"""
            <div class="table-row">
                <div><strong>{field}</strong></div>
                <div>{status_chip(result['digilocker'], 'Matched', 'Mismatch')}</div>
                <div>{status_chip(result['uploaded'], 'Matched', 'Mismatch', 'Not uploaded')}</div>
                <div>{status_chip(result['final'], 'Verified', 'Needs review')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_document_card(document: dict) -> None:
    validation_ok = document["validation_ok"]
    if validation_ok is True:
        pill = '<div class="status-pill status-success">Pattern matched</div>'
    elif validation_ok is False:
        pill = '<div class="status-pill status-warning">Pattern not detected</div>'
    else:
        pill = '<div class="status-pill status-success">Record ready</div>'

    preview = document["text"][:700].strip() or "No text available."
    st.markdown(
        f"""
        <div class="doc-card">
            {pill}
            <h4 style="margin:0 0 0.35rem 0;">{document['label']}</h4>
            <p class="doc-meta"><strong>File:</strong> {document['filename']}</p>
            <p class="doc-meta"><strong>Mode:</strong> {document['mode']}</p>
            <p class="doc-meta"><strong>Preview:</strong> {preview}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def reset_results() -> None:
    st.session_state["last_run"] = None


inject_styles()
if "last_run" not in st.session_state:
    st.session_state["last_run"] = None

st.markdown(
    """
    <div class="hero-card">
        <div class="eyebrow">India Verification Panel</div>
        <div class="hero-title">Fake DigiLocker verification that looks real, with one clean landing page.</div>
        <div class="flag-line"></div>
        <p class="hero-copy">
            Enter the document details, upload a file if you have one, choose the provided document type
            and the DigiLocker verification type, then run a sandbox-style verification result instantly.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

left_col, right_col = st.columns([1.15, 0.85], gap="large")

with left_col:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.subheader("Verification Panel")
    document_number = st.text_input("Document Number", placeholder="Enter Aadhaar, PAN, passport, EPIC, DL, or certificate number")
    name = st.text_input("Full Name", placeholder="Enter full applicant name")
    dob = st.date_input(
        "Date of Birth",
        value=None,
        min_value=date(1950, 1, 1),
        max_value=date.today(),
        format="DD/MM/YYYY",
    )
    father_name = st.text_input("Father's Name", placeholder="Optional")
    mother_name = st.text_input("Mother's Name", placeholder="Optional")
    uploaded_file = st.file_uploader(
        "Upload Document",
        type=["png", "jpg", "jpeg", "pdf"],
        accept_multiple_files=False,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.subheader("Verification Setup")
    provided_doc_type = st.selectbox(
        "Provided Document Type",
        DOCUMENT_OPTIONS,
        index=0,
    )
    digilocker_doc_type = st.selectbox(
        "DigiLocker Verification Type",
        DOCUMENT_OPTIONS,
        index=1 if len(DOCUMENT_OPTIONS) > 1 else 0,
    )
    st.caption("No API key or login required. This page runs a DigiLocker-style sandbox verification for demo use.")
    verify_clicked = st.button("Verify With DigiLocker", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if verify_clicked:
    errors = []
    if not document_number.strip():
        errors.append("Document Number is required.")
    if not name.strip():
        errors.append("Full Name is required.")
    if not dob:
        errors.append("Date of Birth is required.")

    if errors:
        for error in errors:
            st.error(error)
    else:
        details = {
            "document_number": document_number.strip(),
            "name": name.strip(),
            "dob": dob.strftime("%d/%m/%Y"),
            "father_name": father_name.strip(),
            "mother_name": mother_name.strip(),
        }

        digilocker_document = build_demo_digilocker_document(details, digilocker_doc_type)
        uploaded_documents = []
        issues = []

        if uploaded_file is not None:
            try:
                uploaded_documents.append(
                    process_uploaded_document(
                        uploaded_file,
                        f"Uploaded Document - {uploaded_file.name}",
                        provided_doc_type,
                    )
                )
            except Exception as exc:
                issues.append(f"Uploaded document processing failed: {exc}")

        match_results = build_match_results(details, [digilocker_document], uploaded_documents)
        match_results["Document Number"] = build_document_number_status(details, digilocker_document, uploaded_documents)

        st.session_state["last_run"] = {
            "details": details,
            "provided_doc_type": provided_doc_type,
            "digilocker_doc_type": digilocker_doc_type,
            "digilocker_document": digilocker_document,
            "uploaded_documents": uploaded_documents,
            "issues": issues,
            "match_results": match_results,
        }

if st.session_state["last_run"]:
    run = st.session_state["last_run"]
    match_results = run["match_results"]
    verified_count = sum(1 for value in match_results.values() if value["final"] is True)
    checked_count = sum(1 for value in match_results.values() if value["final"] is not None)
    upload_status = "Uploaded" if run["uploaded_documents"] else "Not uploaded"

    st.write("")
    st.markdown(
        f"""
        <div class="result-card">
            <div class="eyebrow">Verification Result</div>
            <h3 style="margin-top:0;">DigiLocker sandbox verification summary</h3>
            <div class="summary-grid">
                <div class="summary-tile">
                    <div class="summary-label">Provided Type</div>
                    <div class="summary-value">{run['provided_doc_type']}</div>
                </div>
                <div class="summary-tile">
                    <div class="summary-label">DigiLocker Type</div>
                    <div class="summary-value">{run['digilocker_doc_type']}</div>
                </div>
                <div class="summary-tile">
                    <div class="summary-label">Fields Verified</div>
                    <div class="summary-value">{verified_count}/{checked_count or 1}</div>
                </div>
                <div class="summary-tile">
                    <div class="summary-label">Upload Status</div>
                    <div class="summary-value">{upload_status}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for issue in run["issues"]:
        st.warning(issue)

    st.write("")
    st.subheader("Field Verification Matrix")
    render_match_table(match_results)

    st.write("")
    for field, result in match_results.items():
        if result["final"] is None:
            st.info(f"{field}: skipped because that value was optional or not uploaded.")
        elif result["final"]:
            st.success(f"{field}: verified against the DigiLocker sandbox record.")
        else:
            st.warning(f"{field}: needs manual review.")

    st.write("")
    st.subheader("Documents")
    doc_columns = st.columns(2 if run["uploaded_documents"] else 1)
    with doc_columns[0]:
        render_document_card(run["digilocker_document"])
        with st.expander("View DigiLocker sandbox record"):
            st.text_area(
                "DigiLocker sandbox record text",
                run["digilocker_document"]["text"],
                height=220,
                disabled=True,
                label_visibility="collapsed",
            )

    if run["uploaded_documents"]:
        with doc_columns[1]:
            render_document_card(run["uploaded_documents"][0])
            with st.expander("View uploaded document extracted text"):
                st.text_area(
                    "Uploaded document extracted text",
                    run["uploaded_documents"][0]["text"],
                    height=220,
                    disabled=True,
                    label_visibility="collapsed",
                )

    st.write("")
    if st.button("Start New Verification", use_container_width=True):
        reset_results()
        st.rerun()

st.write("")
st.markdown(
    """
    <div class="panel-card">
        <div class="eyebrow">How It Works</div>
        <h3 style="margin-top:0;">Single-page India verification flow</h3>
        <p style="margin:0.3rem 0; color:#4c6178;">1. Enter document number, name, DOB, and optional parent names.</p>
        <p style="margin:0.3rem 0; color:#4c6178;">2. Select the provided document type and the DigiLocker verification type.</p>
        <p style="margin:0.3rem 0; color:#4c6178;">3. Upload a document if you want OCR-based cross-checking.</p>
        <p style="margin:0.3rem 0; color:#4c6178;">4. Click Verify With DigiLocker to generate a realistic fake verification result.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
