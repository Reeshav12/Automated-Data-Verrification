# Automated Data Verification

Automated Data Verification is a Streamlit-based project for checking whether user-entered personal information matches uploaded identity and academic documents.

The app extracts text from uploaded files using OCR, preprocesses images for better recognition, and compares important fields like:
- name
- date of birth
- father's name
- mother's name

## Features

- Streamlit user interface
- OCR-based text extraction using Tesseract
- document image preprocessing
- fuzzy matching across multiple uploaded documents
- support for identity documents and marksheets
- Render-ready Docker deployment

## Tech Stack

- Python
- Streamlit
- Tesseract OCR
- Pillow
- OpenCV
- spaCy
- fuzzywuzzy
- PyPDF2

## Project Structure

```text
.
├── app.py
├── validation.py
├── ocr.py
├── preprocessing.py
├── ner.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .streamlit/
│   └── config.toml
└── uploads/
```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Reeshav12/Automated-Data-Verrification.git
cd Automated-Data-Verrification
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR

On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

On macOS:

```bash
brew install tesseract
```

### 5. Run the app

```bash
streamlit run app.py
```

## Deploy on Render

This repository is configured to run as a Docker-based Render Web Service.

### Render settings

- Service Type: `Web Service`
- Runtime: `Docker`
- Branch: `main`
- Root Directory: leave blank

You do not need a separate build or start command because Render will use the included Dockerfile.

## How Deployment Works

The Docker container:
- installs Python dependencies
- installs Tesseract OCR
- starts Streamlit on Render's assigned port

Start command inside Docker:

```bash
streamlit run app.py --server.port ${PORT} --server.address 0.0.0.0 --server.headless true
```

## Current Limitations

- OCR quality depends on scan clarity
- some document types may need stronger parsing rules
- Tesseract must be available for image OCR

## Future Improvements

- better UI design
- database integration
- user authentication
- downloadable verification report
- more document templates and stronger validation rules

## License

This project includes the license in [LICENSE](LICENSE).
