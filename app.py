# app.py
import streamlit as st
from ocr import extract_text_from_image
from preprocessing import preprocess_image
from ner import extract_entities_from_text, match_entities_across_documents
import os
import time

# Setup directories
UPLOAD_DIR = "uploads/raw"
PROCESSED_DIR = "uploads/processed"
TEXT_DIR = "uploads/extracted_texts"

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(TEXT_DIR, exist_ok=True)

# Streamlit App
st.title("Automated Data Verification System")
st.header("Upload and Verify Your Information")

if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False

if not st.session_state.form_submitted:
    # User Form
    with st.form("document_form"):
        # Personal Details
        name = st.text_input("Name")
        dob = st.date_input("Date of Birth", format="YYYY-MM-DD")
        father_name = st.text_input("Father's Name")
        mother_name = st.text_input("Mother's Name")

        # Identity Document Upload
        st.subheader("Identity Document")
        id_type = st.selectbox("Select Identity Document Type", ["Aadhaar", "PAN Card", "Voter ID", "Others"])
        id_file = st.file_uploader("Upload Identity Document", type=["png", "jpg", "jpeg", "pdf"])

        # 10th Marksheet Upload
        st.subheader("10th Marksheet")
        school_10th = st.text_input("School Name (10th)")
        roll_no_10th = st.text_input("Roll Number (10th)")
        tenth_marksheet = st.file_uploader("Upload 10th Marksheet", type=["png", "jpg", "jpeg", "pdf"])

        # 12th Marksheet Upload
        st.subheader("12th Marksheet")
        school_12th = st.text_input("School Name (12th)")
        roll_no_12th = st.text_input("Roll Number (12th)")
        twelfth_marksheet = st.file_uploader("Upload 12th Marksheet", type=["png", "jpg", "jpeg", "pdf"])

        # Submit Button
        submitted = st.form_submit_button("Submit")

    if submitted:
        st.session_state.form_submitted = True
        st.success("Processing your documents...")

        uploaded_docs = []

        # Function to process a document
        def process_document(file, file_type):
            save_path = os.path.join(UPLOAD_DIR, f"{int(time.time())}_{file.name}")
            with open(save_path, "wb") as f:
                f.write(file.getbuffer())

            preprocessed_path = preprocess_image(save_path, PROCESSED_DIR)
            extracted_text = extract_text_from_image(preprocessed_path)
            
            # Save extracted text to a file
            text_filename = os.path.join(TEXT_DIR, f"{int(time.time())}_{file_type}.txt")
            with open(text_filename, "w", encoding="utf-8") as text_file:
                text_file.write(extracted_text)
            
            uploaded_docs.append(extracted_text)
            return f"{file_type} document processed successfully!"

        # Process uploaded documents
        if id_file:
            st.success(process_document(id_file, id_type))

        if tenth_marksheet:
            st.success(process_document(tenth_marksheet, "10th Marksheet"))

        if twelfth_marksheet:
            st.success(process_document(twelfth_marksheet, "12th Marksheet"))

        # Verify fields
        if uploaded_docs:
            match_results = {
                "Name": match_entities_across_documents("Name", name, uploaded_docs),
                "DOB": match_entities_across_documents("DOB", dob.strftime("%d-%m-%Y"), uploaded_docs),  # Adjusted date format
                "Father's Name": match_entities_across_documents("Father's Name", father_name, uploaded_docs),
                "Mother's Name": match_entities_across_documents("Mother's Name", mother_name, uploaded_docs),
            }

            st.subheader("Verification Results")
            for field, matches in match_results.items():
                if matches >= 1:
                    st.success(f"{field} verified in {matches} document(s).")
                else:
                    st.error(f"{field} could not be verified. Please check the input or the documents.")
else:
    st.write("Form already submitted. Refresh the page to start again.")
