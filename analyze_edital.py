#!/usr/bin/env python3
"""
Edital Analyzer with Gemini Flash Light

This script handles:
1. Extracting text from PDFs
2. Analyzing and summarizing the content using Google's Vertex AI with Gemini model
3. Saving the summaries to a dedicated directory
"""

import sys
import os
import traceback
import argparse
import pdfplumber
from google.cloud import aiplatform

# Directory setup
PDF_DIR = "pdfs_simple"
SUMMARY_DIR = "summaries"

def setup_directories():
    """Create necessary directories if they don't exist."""
    for directory in [PDF_DIR, SUMMARY_DIR]:
        os.makedirs(directory, exist_ok=True)
    print(f"Directories setup complete.")

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF using pdfplumber."""
    print(f"Extracting text from {pdf_path}")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for i, page in enumerate(pdf.pages):
                print(f"Processing page {i+1}/{len(pdf.pages)}")
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
                else:
                    print(f"Warning: No text extracted from page {i+1}")
        
        if not text.strip():
            print("Warning: No text was extracted from the PDF. It might be a scanned document.")
        else:
            print(f"Successfully extracted {len(text)} characters of text")
        
        return text
    except Exception as e:
        print(f"Failed to extract text from {pdf_path}: {e}")
        traceback.print_exc()
        return ""

def initialize_vertex_ai(project_id, location):
    """Initialize the Vertex AI client."""
    try:
        print(f"Initializing Vertex AI with project: {project_id}, location: {location}")
        aiplatform.init(project=project_id, location=location)
        return True
    except Exception as e:
        print(f"Error initializing Vertex AI: {e}")
        traceback.print_exc()
        return False

def analyze_with_gemini(text, model_name="gemini-2.0-flash-lite-001"):
    """Analyze text using Vertex AI Gemini model."""
    if not text.strip():
        return "No text content to analyze."
    
    try:
        print(f"Sending text to Gemini model ({model_name}) for analysis...")
        
        # Initialize the model
        model = aiplatform.GenerativeModel(model_name)
        
        # Prepare the prompt
        prompt = f"""
        Please analyze the following procurement document (edital) and provide the following specific information:
        
        1. CITY: Which city is this tender for?
        
        2. COMPANY: Which company or organization is issuing this tender?
        
        3. PRODUCT: What specific product(s) do they want to buy?
        
        4. SPECIFICATIONS: What are the detailed specifications of the product(s)?
        
        5. QUANTITY: What is the amount/quantity of products they want to purchase?
        
        6. VALUE: What is the total value of the tender?
        
        7. IMPORTANT DATES: What are the key dates for this tender (submission deadline, etc.)?
        
        Please format your response clearly with these headings and provide precise information extracted from the document. If any information is not available, please indicate "Not specified in the document."
        
        Document text:
        {text[:30000]}  # Limiting to first 30000 chars as Gemini has input limits
        
        If the text appears to be truncated, please note that in your analysis.
        """
        
        # Send to the model
        response = model.generate_content(prompt)
        
        # Extract the analysis from the response
        if hasattr(response, 'text'):
            analysis = response.text
            print("Successfully generated analysis")
            return analysis
        else:
            print("Warning: Unexpected response format from Gemini API")
            return "Error: Could not generate analysis due to unexpected API response format."
    
    except Exception as e:
        print(f"Error during analysis: {e}")
        traceback.print_exc()
        return f"Error generating analysis: {str(e)}"

def process_pdfs_for_analysis(project_id, location, model_name="gemini-2.0-flash-lite-001"):
    """Process all PDFs in PDF_DIR and save analyses to SUMMARY_DIR."""
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found to analyze.")
        return
    
    print(f"Found {len(pdf_files)} PDF files to analyze.")
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        analysis_file = os.path.join(SUMMARY_DIR, f"analysis_{pdf_file.replace('.pdf', '.txt')}")
        
        # Skip if analysis already exists
        if os.path.exists(analysis_file):
            print(f"Analysis already exists for {pdf_file}, skipping.")
            continue
        
        print(f"\nProcessing {pdf_file} for analysis...")
        
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_path)
        
        if not text.strip():
            print(f"No text extracted from {pdf_file}, skipping analysis.")
            with open(analysis_file, "w", encoding="utf-8") as f:
                f.write("No text content could be extracted from this PDF. It might be a scanned document or contain only images.")
            continue
        
        # Analyze the text
        analysis = analyze_with_gemini(text, model_name)
        
        # Save the analysis
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(analysis)
        
        print(f"Saved analysis for {pdf_file} to {analysis_file}")

def main():
    """Main function to handle analyzing PDFs."""
    parser = argparse.ArgumentParser(description="Analyze procurement documents using Gemini.")
    parser.add_argument("--project-id", help="Google Cloud project ID", default=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", help="Google Cloud location", default="us-central1")
    parser.add_argument("--model", help="Gemini model name", default="gemini-2.0-flash-lite-001")
    parser.add_argument("--pdf", help="Specific PDF file to analyze (optional)")
    
    args = parser.parse_args()
    
    # Setup directories
    setup_directories()
    
    # Check for required Vertex AI parameters
    project_id = args.project_id
    
    if not project_id:
        print("Error: Google Cloud project ID not provided.")
        print("To enable analysis, provide --project-id or set GOOGLE_CLOUD_PROJECT environment variable.")
        return 1
    
    # Initialize Vertex AI
    if not initialize_vertex_ai(project_id, args.location):
        print("Failed to initialize Vertex AI.")
        return 1
    
    # Process specific PDF or all PDFs
    if args.pdf:
        pdf_path = args.pdf
        if not os.path.exists(pdf_path):
            pdf_path = os.path.join(PDF_DIR, args.pdf)
            if not os.path.exists(pdf_path):
                print(f"Error: PDF file not found: {args.pdf}")
                return 1
        
        # Extract filename
        pdf_file = os.path.basename(pdf_path)
        analysis_file = os.path.join(SUMMARY_DIR, f"analysis_{pdf_file.replace('.pdf', '.txt')}")
        
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_path)
        
        if not text.strip():
            print(f"No text extracted from {pdf_file}, skipping analysis.")
            with open(analysis_file, "w", encoding="utf-8") as f:
                f.write("No text content could be extracted from this PDF. It might be a scanned document or contain only images.")
            return 1
        
        # Analyze the text
        analysis = analyze_with_gemini(text, args.model)
        
        # Save the analysis
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(analysis)
        
        print(f"Saved analysis for {pdf_file} to {analysis_file}")
    else:
        # Process all PDFs
        process_pdfs_for_analysis(project_id, args.location, args.model)
    
    print("\nAnalysis complete!")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Unhandled exception: {e}")
        traceback.print_exc()
        sys.exit(1) 