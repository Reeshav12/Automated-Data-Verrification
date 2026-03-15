from datetime import date
from pathlib import Path
import re
import time
from uuid import uuid4

import streamlit as st

from digilocker import (
    DOCUMENT_OPTIONS,
    DigiLockerConfig,
    build_authorize_url,
    build_pkce_pair,
    download_document,
    exchange_code_for_token,
    file_extension_for_item,
    filter_documents,
    list_issued_documents,
    refresh_access_token,
    validation_type_for_option,
)
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
    page_title="Smart Verification",
    page_icon="SV",
    layout="wide",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            color: #10233f;
            background:
                radial-gradient(circle at top left, rgba(251, 191, 36, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(56, 189, 248, 0.14), transparent 24%),
                linear-gradient(180deg, #fffdf8 0%, #f4f8fc 52%, #edf4fb 100%);
        }
        .stApp,
        .stApp p,
        .stApp label,
        .stApp span,
        .stApp div,
        .stMarkdown,
        .stCaption {
            color: #10233f;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #0b1f38 !important;
        }
        .hero-card,
        .section-card,
        .result-card,
        .how-card {
            background: rgba(255, 255, 255, 0.97);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 24px;
            padding: 1.4rem;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
        }
        .hero-title {
            font-size: 2.45rem;
            line-height: 1.1;
            margin-bottom: 0.45rem;
            color: #0f172a;
        }
        .hero-copy {
            font-size: 1rem;
            color: #334155;
            margin-bottom: 0;
        }
        .eyebrow {
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #0f766e;
            margin-bottom: 0.6rem;
        }
        .status-pill {
            display: inline-block;
            padding: 0.32rem 0.7rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 700;
            margin-bottom: 0.7rem;
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
        .source-grid {
            display: grid;
            grid-template-columns: 1.4fr 0.95fr 0.95fr 1.1fr;
            gap: 0.75rem;
            align-items: center;
        }
        .source-row {
            padding: 0.9rem 1rem;
            border-radius: 18px;
            background: #f8fbff;
            border: 1px solid #d7e5f4;
            margin-bottom: 0.75rem;
        }
        .source-head {
            font-weight: 700;
            color: #16314f;
            padding: 0 0.4rem 0.55rem 0.4rem;
        }
        .source-field {
            font-weight: 700;
            color: #10233f;
        }
        .doc-row {
            padding: 0.7rem 0.9rem;
            border-radius: 16px;
            background: #f8fbff;
            border: 1px solid #d7e5f4;
            margin-bottom: 0.65rem;
        }
        .chip {
            display: inline-block;
            padding: 0.28rem 0.65rem;
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
        div[data-baseweb="input"] input,
        div[data-baseweb="base-input"] input,
        .stTextInput input,
        .stDateInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {
            background: #ffffff !important;
            color: #0f172a !important;
            border-color: #bfd3e6 !important;
        }
        div[data-baseweb="input"] input::placeholder,
        .stTextArea textarea::placeholder {
            color: #64748b !important;
        }
        .stFileUploader label,
        .stTextInput label,
        .stSelectbox label,
        .stDateInput label,
        .stTextArea label,
        .stMultiSelect label,
        .stRadio label {
            color: #16314f !important;
            font-weight: 600;
        }
        button[kind="primary"],
        .stButton button {
            background: linear-gradient(135deg, #0f766e 0%, #1d4ed8 100%);
            color: #ffffff !important;
            border: none !important;
        }
        .stButton button:hover {
            filter: brightness(1.05);
        }
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 20px;
            padding: 1rem;
        }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] div {
            color: #10233f !important;
        }
        div[data-testid="stFileUploader"] {
            background: rgba(247, 250, 252, 0.98);
            border-radius: 18px;
            padding: 0.6rem;
        }
        .small-note {
            color: #475569;
            font-size: 0.92rem;
            margin-top: 0.45rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return cleaned or "document"


def save_bytes_file(file_bytes: bytes, filename: str) -> Path:
    suffix = Path(filename).suffix.lower()
    if not suffix:
        suffix = ".pdf"
    unique_name = f"{uuid4().hex}_{safe_filename(Path(filename).stem)}{suffix}"
    destination = UPLOAD_DIR / unique_name
    destination.write_bytes(file_bytes)
    return destination


def process_saved_document(
    raw_path: Path,
    label: str,
    display_name: str,
    doc_type: str | None = None,
) -> dict:
    processed_path = raw_path
    mode = "PDF extraction / OCR" if raw_path.suffix.lower() == ".pdf" else "Image OCR"

    if raw_path.suffix.lower() != ".pdf":
        processed_path = preprocess_image(raw_path, PROCESSED_DIR)

    extracted_text = extract_text_from_document(processed_path)
    text_path = TEXT_DIR / f"{raw_path.stem}.txt"
    text_path.write_text(extracted_text, encoding="utf-8")

    validation_ok = validate_data(doc_type, extracted_text) if doc_type else None

    return {
        "label": label,
        "filename": display_name,
        "mode": mode,
        "text": extracted_text,
        "text_path": text_path,
        "validation_ok": validation_ok,
    }


def process_uploaded_document(
    uploaded_file,
    label: str,
    doc_type: str | None = None,
) -> dict:
    raw_path = save_bytes_file(uploaded_file.getbuffer(), uploaded_file.name)
    return process_saved_document(raw_path, label, uploaded_file.name, doc_type)


def process_downloaded_document(
    content: bytes,
    filename: str,
    label: str,
    doc_type: str | None = None,
) -> dict:
    raw_path = save_bytes_file(content, filename)
    return process_saved_document(raw_path, label, filename, doc_type)


def init_state() -> None:
    defaults = {
        "last_run": None,
        "digilocker_token": None,
        "digilocker_items": [],
        "digilocker_connected": False,
        "digilocker_state": "",
        "digilocker_code_verifier": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_query_params() -> None:
    for key in list(st.query_params.keys()):
        del st.query_params[key]


def configure_digilocker_link(config: DigiLockerConfig | None) -> str | None:
    if not config:
        return None

    if not st.session_state.digilocker_state or not st.session_state.digilocker_code_verifier:
        code_verifier, code_challenge = build_pkce_pair()
        state = uuid4().hex
        st.session_state.digilocker_state = state
        st.session_state.digilocker_code_verifier = code_verifier
        st.session_state.digilocker_auth_url = build_authorize_url(config, state, code_challenge)

    return st.session_state.get("digilocker_auth_url")


def store_token_payload(token_payload: dict) -> None:
    token_payload = dict(token_payload)
    token_payload["expires_at"] = time.time() + int(token_payload.get("expires_in", 0))
    st.session_state.digilocker_token = token_payload
    st.session_state.digilocker_connected = True


def ensure_active_access_token(config: DigiLockerConfig | None) -> str | None:
    token_payload = st.session_state.get("digilocker_token")
    if not config or not token_payload:
        return None

    expires_at = float(token_payload.get("expires_at", 0))
    if expires_at and expires_at > time.time() + 60:
        return token_payload.get("access_token")

    refresh_token_value = token_payload.get("refresh_token")
    if not refresh_token_value:
        return token_payload.get("access_token")

    refreshed = refresh_access_token(config, refresh_token_value)
    store_token_payload(refreshed)
    return refreshed.get("access_token")


def handle_digilocker_callback(config: DigiLockerConfig | None) -> None:
    code = st.query_params.get("code")
    state = st.query_params.get("state")
    error = st.query_params.get("error")

    if error:
        st.error(f"DigiLocker authorization returned an error: {error}")
        clear_query_params()
        return

    if not code or not state:
        return

    if not config:
        st.warning("DigiLocker returned an authorization code, but app credentials are not configured.")
        clear_query_params()
        return

    if state != st.session_state.get("digilocker_state"):
        st.error("DigiLocker state validation failed. Please connect again.")
        clear_query_params()
        return

    try:
        token_payload = exchange_code_for_token(
            config,
            code,
            st.session_state.get("digilocker_code_verifier", ""),
        )
        store_token_payload(token_payload)
        clear_query_params()
        st.rerun()
    except Exception as exc:
        st.error(f"DigiLocker token exchange failed: {exc}")
        clear_query_params()


def render_document_result(document: dict) -> None:
    validation_ok = document["validation_ok"]
    if validation_ok is True:
        pill = '<div class="status-pill status-success">Document pattern detected</div>'
    elif validation_ok is False:
        pill = '<div class="status-pill status-warning">Pattern not detected automatically</div>'
    else:
        pill = '<div class="status-pill status-success">Text extracted successfully</div>'

    preview = document["text"][:800].strip() or "No text could be extracted from this file."
    st.markdown(
        f"""
        <div class="result-card">
            {pill}
            <h4 style="margin:0 0 0.35rem 0; color:#0f172a;">{document["label"]}</h4>
            <p style="margin:0; color:#334155;"><strong>File:</strong> {document["filename"]}</p>
            <p style="margin:0.2rem 0 0.8rem 0; color:#334155;"><strong>Method:</strong> {document["mode"]}</p>
            <p style="margin:0; color:#475569;"><strong>Preview:</strong> {preview}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander(f"View extracted text for {document['label']}"):
        st.text_area(
            f"Extracted text from {document['filename']}",
            document["text"],
            height=220,
            disabled=True,
            label_visibility="collapsed",
        )


def build_match_results(
    details: dict,
    digilocker_documents: list[dict],
    original_documents: list[dict],
) -> dict[str, dict[str, bool | None]]:
    digilocker_texts = [document["text"] for document in digilocker_documents]
    original_texts = [document["text"] for document in original_documents]

    fields = {
        "Name": details["name"],
        "DOB": normalize_date(details["dob"]) if details["dob"] else "",
        "Father's Name": details["father_name"],
        "Mother's Name": details["mother_name"],
    }

    results: dict[str, dict[str, bool | None]] = {}
    for field, value in fields.items():
        if not value:
            results[field] = {"digilocker": None, "original": None, "final": None}
            continue

        digilocker_match = bool(
            digilocker_texts and match_entities_across_documents(field, value, digilocker_texts)
        )
        original_match = (
            bool(original_texts and match_entities_across_documents(field, value, original_texts))
            if original_texts
            else None
        )
        final_match = digilocker_match if original_match is None else digilocker_match and original_match
        results[field] = {
            "digilocker": digilocker_match,
            "original": original_match,
            "final": final_match,
        }

    return results


def status_chip(value: bool | None, success: str, failure: str, skipped: str = "Skipped") -> str:
    if value is None:
        return f'<span class="chip chip-neutral">{skipped}</span>'
    if value:
        return f'<span class="chip chip-success">{success}</span>'
    return f'<span class="chip chip-warning">{failure}</span>'


def render_match_table(match_results: dict[str, dict[str, bool | None]]) -> None:
    st.markdown(
        """
        <div class="source-grid source-head">
            <div>Field</div>
            <div>DigiLocker</div>
            <div>Original Source</div>
            <div>Final Status</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for field, result in match_results.items():
        st.markdown(
            f"""
            <div class="source-grid source-row">
                <div class="source-field">{field}</div>
                <div>{status_chip(result["digilocker"], "Matched", "Not found")}</div>
                <div>{status_chip(result["original"], "Matched", "Not found", "Not uploaded")}</div>
                <div>{status_chip(result["final"], "Verified", "Needs review")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_available_digilocker_docs(matches: list[tuple[str, dict]]) -> None:
    if not matches:
        return

    st.markdown("**Matched DigiLocker document options**")
    for option, item in matches:
        st.markdown(
            f"""
            <div class="doc-row">
                <strong>{option}</strong><br>
                {item.get("name", "Unnamed document")}<br>
                <span class="small-note">{item.get("issuer", "Issuer not provided")}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def fetch_digilocker_documents(
    mode: str,
    requested_options: list[str],
    config: DigiLockerConfig | None,
    manual_digi_files,
) -> tuple[list[dict], list[str]]:
    documents = []
    issues = []

    if mode == "Connect DigiLocker":
        access_token = ensure_active_access_token(config)
        if not access_token or not config:
            issues.append("Connect DigiLocker first to fetch documents from the Aadhaar-linked DigiLocker account.")
            return documents, issues

        try:
            items = list_issued_documents(access_token, config)
            st.session_state.digilocker_items = items
            matches = filter_documents(items, requested_options)
            if not matches:
                issues.append("No DigiLocker documents matched the selected options.")
                return documents, issues

            render_available_digilocker_docs(matches)

            for option, item in matches:
                uri = str(item.get("uri", "")).strip()
                if not uri:
                    continue
                extension = file_extension_for_item(item)
                display_name = str(item.get("name", "")).strip() or f"{safe_filename(option)}{extension}"
                if not Path(display_name).suffix:
                    display_name = f"{display_name}{extension}"
                content, _ = download_document(access_token, uri, config)
                documents.append(
                    process_downloaded_document(
                        content,
                        display_name,
                        f"DigiLocker - {option}",
                        validation_type_for_option(option),
                    )
                )
        except Exception as exc:
            issues.append(f"DigiLocker fetch failed: {exc}")
        return documents, issues

    if not manual_digi_files:
        issues.append("Upload at least one DigiLocker document when using manual mode.")
        return documents, issues

    for uploaded_file in manual_digi_files:
        documents.append(
            process_uploaded_document(
                uploaded_file,
                f"DigiLocker Upload - {uploaded_file.name}",
            )
        )

    return documents, issues


def fetch_original_documents(original_files) -> list[dict]:
    documents = []
    for uploaded_file in original_files:
        documents.append(
            process_uploaded_document(
                uploaded_file,
                f"Original Source - {uploaded_file.name}",
            )
        )
    return documents


def reset_results() -> None:
    st.session_state.last_run = None


inject_styles()
init_state()

digilocker_config = DigiLockerConfig.from_env()
handle_digilocker_callback(digilocker_config)
authorize_url = configure_digilocker_link(digilocker_config)

st.markdown(
    """
    <div class="hero-card">
        <div class="eyebrow">Smart Verification</div>
        <div class="hero-title">Catch DigiLocker data from an Aadhaar-linked account and verify selected documents.</div>
        <p class="hero-copy">
            Choose the document options you want, connect to DigiLocker, and compare the DigiLocker
            records against the applicant details and any original source documents you upload.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

left_col, right_col = st.columns([1.2, 1], gap="large")

with left_col:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Applicant Details")
    name = st.text_input("Full Name", placeholder="Enter the applicant name")
    dob = st.date_input(
        "Date of Birth",
        value=None,
        min_value=date(1950, 1, 1),
        max_value=date.today(),
        format="DD/MM/YYYY",
    )
    father_name = st.text_input("Father's Name", placeholder="Optional")
    mother_name = st.text_input("Mother's Name", placeholder="Optional")
    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("DigiLocker Verification Source")
    source_mode = st.radio(
        "DigiLocker document source",
        ["Connect DigiLocker", "Upload DigiLocker Documents Manually"],
        horizontal=True,
    )
    requested_options = st.multiselect(
        "Select document options to verify",
        DOCUMENT_OPTIONS,
        default=["Aadhaar", "PAN Card"],
    )

    if source_mode == "Connect DigiLocker":
        if not digilocker_config:
            st.info(
                "Add `DIGILOCKER_CLIENT_ID`, `DIGILOCKER_CLIENT_SECRET`, and `DIGILOCKER_REDIRECT_URI` to enable live DigiLocker access."
            )
        else:
            if st.session_state.digilocker_connected:
                st.success("DigiLocker is connected. The app will fetch matched issued documents on verify.")
            if authorize_url:
                st.link_button(
                    "Connect Aadhaar-linked DigiLocker",
                    authorize_url,
                    use_container_width=True,
                )
            if st.button("Disconnect DigiLocker", use_container_width=True):
                st.session_state.digilocker_token = None
                st.session_state.digilocker_items = []
                st.session_state.digilocker_connected = False
                st.rerun()
        manual_digi_files = []
    else:
        manual_digi_files = st.file_uploader(
            "Upload DigiLocker documents manually",
            type=["png", "jpg", "jpeg", "pdf"],
            accept_multiple_files=True,
        )

    st.caption(
        "Official DigiLocker integrations use a user-consent login flow for an Aadhaar-linked DigiLocker account. The app does not fetch citizen records from Aadhaar alone."
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("Original Source Documents")
original_files = st.file_uploader(
    "Upload original source documents for cross-checking",
    type=["png", "jpg", "jpeg", "pdf"],
    accept_multiple_files=True,
)
st.caption("Original source uploads are optional. If you upload them, final verification requires support from both DigiLocker and the original source.")
verify_clicked = st.button("Verify Selected Documents", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if verify_clicked:
    validation_errors = []
    if not name.strip():
        validation_errors.append("Full Name is required.")
    if not dob:
        validation_errors.append("Date of Birth is required.")
    if not requested_options:
        validation_errors.append("Select at least one document option to verify.")

    if validation_errors:
        for error in validation_errors:
            st.error(error)
    else:
        formatted_dob = dob.strftime("%d/%m/%Y")
        details = {
            "name": name.strip(),
            "dob": formatted_dob,
            "father_name": father_name.strip(),
            "mother_name": mother_name.strip(),
        }

        with st.spinner("Fetching DigiLocker data and verifying the selected documents..."):
            digilocker_documents, digilocker_issues = fetch_digilocker_documents(
                source_mode,
                requested_options,
                digilocker_config,
                manual_digi_files,
            )

            original_documents = []
            original_issues = []
            try:
                original_documents = fetch_original_documents(original_files or [])
            except Exception as exc:
                original_issues.append(f"Original source processing failed: {exc}")

        for issue in digilocker_issues + original_issues:
            st.error(issue)

        if digilocker_documents:
            match_results = build_match_results(details, digilocker_documents, original_documents)
            st.session_state.last_run = {
                "details": details,
                "digilocker_documents": digilocker_documents,
                "original_documents": original_documents,
                "matches": match_results,
            }

if st.session_state.last_run:
    run = st.session_state.last_run
    match_results = run["matches"]
    verified_fields = sum(1 for value in match_results.values() if value["final"] is True)
    checked_fields = sum(1 for value in match_results.values() if value["final"] is not None)
    total_documents = len(run["digilocker_documents"]) + len(run["original_documents"])

    st.write("")
    metrics = st.columns(3)
    metrics[0].metric("Documents Processed", total_documents)
    metrics[1].metric("Fields Finally Verified", f"{verified_fields}/{checked_fields or 1}")
    metrics[2].metric("Applicant DOB", normalize_date(run["details"]["dob"]) or "Not provided")

    st.write("")
    st.subheader("Verification Results")
    render_match_table(match_results)

    for field, result in match_results.items():
        if result["final"] is None:
            st.info(f"{field}: skipped because that value was not provided.")
        elif result["final"]:
            if result["original"] is None:
                st.success(f"{field}: verified from the selected DigiLocker document set.")
            else:
                st.success(f"{field}: verified in DigiLocker and the original source upload.")
        elif result["digilocker"] and result["original"] is False:
            st.warning(f"{field}: present in DigiLocker but not in the uploaded original source.")
        elif result["digilocker"] is False:
            st.error(f"{field}: not found in the selected DigiLocker documents.")
        else:
            st.warning(f"{field}: needs manual review.")

    st.write("")
    all_documents = run["digilocker_documents"] + run["original_documents"]
    if all_documents:
        st.subheader("Processed Documents")
        result_columns = st.columns(len(all_documents))
        for column, document in zip(result_columns, all_documents):
            with column:
                render_document_result(document)

    if st.button("Start New Review", use_container_width=True):
        reset_results()
        st.rerun()

st.write("")
st.markdown(
    """
    <div class="how-card">
        <div class="eyebrow">How It Works</div>
        <h3 style="margin-top:0; color:#0f172a;">Bottom-of-page review guide</h3>
        <p class="small-note">1. Enter the applicant details you expect to see in the chosen documents.</p>
        <p class="small-note">2. Select the document options to fetch from DigiLocker, such as Aadhaar, PAN, passport, or marksheets.</p>
        <p class="small-note">3. Connect to the Aadhaar-linked DigiLocker account through the official consent flow, or upload DigiLocker documents manually if credentials are not configured.</p>
        <p class="small-note">4. The app extracts text from the matched DigiLocker files and optionally from uploaded original source documents.</p>
        <p class="small-note">5. Final verification succeeds when the selected DigiLocker documents support the applicant details, and also the original source if you uploaded one.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
