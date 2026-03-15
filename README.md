# Smart Verification

Smart Verification is a Streamlit app that compares applicant-entered details with DigiLocker documents and uploaded original-source documents. It extracts text from images, text-based PDFs, and scanned PDFs, then checks whether key fields appear consistently across the selected files.

## What It Does

- collects applicant name, date of birth, and parent names
- supports DigiLocker document options such as Aadhaar, PAN, voter ID, passport, and marksheets
- preprocesses images before OCR for better text quality
- extracts text from images with Tesseract
- extracts text from text-based PDFs with PyPDF2
- falls back to OCR for scanned PDFs
- supports DigiLocker OAuth-based fetching when partner credentials are configured
- uses fuzzy matching to verify fields across uploaded documents
- flags whether the selected ID document contains a recognizable document-number pattern

## Stack

- Python 3.12
- Streamlit
- Tesseract OCR
- Pillow
- PyPDF2
- pypdfium2
- fuzzywuzzy + python-Levenshtein

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Install Tesseract locally if it is not already available:

```bash
brew install tesseract
```

For Hindi OCR support:

```bash
brew install tesseract-lang
```

## Render Deployment

This project is ready to deploy on Render as a Docker-based web service.

### Recommended Render settings

- Service Type: `Web Service`
- Runtime: `Docker`
- Branch: `main`
- Root Directory: leave blank

Render will use the included `Dockerfile`, install Tesseract with Hindi language data, and start Streamlit on the Render-provided port.

### DigiLocker configuration

For live DigiLocker fetching, configure these environment variables in Render:

- `DIGILOCKER_CLIENT_ID`
- `DIGILOCKER_CLIENT_SECRET`
- `DIGILOCKER_REDIRECT_URI`

Optional endpoint overrides:

- `DIGILOCKER_AUTHORIZE_URL`
- `DIGILOCKER_TOKEN_URL`
- `DIGILOCKER_ISSUED_DOCS_URL`
- `DIGILOCKER_FILE_URL`

### Start command used inside the container

```bash
streamlit run app.py --server.port ${PORT} --server.address 0.0.0.0 --server.headless true
```

## Notes

- Image uploads work best when the document is cropped clearly and has good contrast.
- PDF uploads support both text-based PDFs and scanned PDFs.
- Uploaded files and extracted text are stored under `uploads/` for traceability.
