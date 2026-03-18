from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps
from PyPDF2 import PdfReader
import pypdfium2 as pdfium
import pytesseract


def extract_text_from_pil_image(image: Image.Image, languages: str = "eng+hin") -> str:
    prepared = ImageOps.exif_transpose(image)
    prepared = ImageOps.autocontrast(prepared.convert("L"))
    return pytesseract.image_to_string(prepared, lang=languages).strip()


def extract_text_from_image(image_path: str | Path, languages: str = "eng+hin") -> str:
    image_file = Path(image_path)
    with Image.open(image_file) as image:
        return extract_text_from_pil_image(image, languages=languages)


def extract_text_from_scanned_pdf(pdf_path: str | Path, languages: str = "eng+hin") -> str:
    pdf = pdfium.PdfDocument(str(pdf_path))
    extracted_pages = []

    for index in range(len(pdf)):
        page = pdf[index]
        bitmap = page.render(scale=2.5)
        pil_image = bitmap.to_pil()
        page_text = extract_text_from_pil_image(pil_image, languages=languages)
        if page_text:
            extracted_pages.append(page_text)

    combined_text = "\n\n".join(extracted_pages).strip()
    if combined_text:
        return combined_text

    raise ValueError(
        "Unable to extract readable text from this PDF. Please upload a clearer scan or image."
    )


def extract_text_from_pdf(pdf_path: str | Path, languages: str = "eng+hin") -> str:
    reader = PdfReader(str(pdf_path))
    extracted_pages = []
    for page in reader.pages:
        page_text = (page.extract_text() or "").strip()
        if page_text:
            extracted_pages.append(page_text)

    combined_text = "\n".join(extracted_pages).strip()
    if combined_text:
        return combined_text

    return extract_text_from_scanned_pdf(pdf_path, languages=languages)


def extract_text_from_document(document_path: str | Path, languages: str = "eng+hin") -> str:
    path = Path(document_path)
    if path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(path, languages=languages)
    return extract_text_from_image(path, languages=languages)
