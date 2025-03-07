#!/usr/bin/env python3
"""
Edital Processor - Download, extract, and summarize procurement documents

This script extends the original Edital Downloader and Extractor project to:
1. Download procurement files from URLs
2. Extract PDFs from archives
3. Summarize the PDFs using Google's Vertex AI with a Gemini model
"""

import requests
import sys
import os
import subprocess
import shutil
import traceback
import argparse
import re
import pdfplumber
from google.cloud import aiplatform

# Directory setup
DOWNLOAD_DIR = "downloads_simple"
EXTRACTED_DIR = "extracted_simple"
PDF_DIR = "pdfs_simple"
SUMMARY_DIR = "summaries"

def setup_directories():
    """Create necessary directories if they don't exist."""
    for directory in [DOWNLOAD_DIR, EXTRACTED_DIR, PDF_DIR, SUMMARY_DIR]:
        os.makedirs(directory, exist_ok=True)
    print(f"Directories setup complete.")

def download_file(url, headers=None):
    """
    Download a file from a URL and determine its filename.
    Returns (success, file_path, is_pdf)
    """
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    print(f"Sending GET request to {url}")
    try:
        response = requests.get(url, headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Content type: {response.headers.get('Content-Type')}")
        print(f"Content length: {len(response.content)} bytes")
        
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            return False, None, False
        
        # Try to get the filename from the Content-Disposition header
        content_disposition = response.headers.get('Content-Disposition', '')
        filename_match = re.search(r'filename=[\'"]?([^\'"]+)', content_disposition)
        
        if filename_match:
            filename = filename_match.group(1)
            print(f"Extracted filename from Content-Disposition: {filename}")
        else:
            # Try to guess the file extension based on the content
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' in content_type:
                ext = '.pdf'
            elif 'application/zip' in content_type:
                ext = '.zip'
            elif 'application/x-rar-compressed' in content_type:
                ext = '.rar'
            else:
                # Try to guess the extension from the first few bytes
                if response.content.startswith(b'%PDF'):
                    ext = '.pdf'
                elif response.content.startswith(b'PK\x03\x04'):
                    ext = '.zip'
                elif response.content.startswith(b'Rar!'):
                    ext = '.rar'
                else:
                    # Default to .bin if we can't determine the type
                    ext = '.bin'
            
            # Create a default filename
            filename = f"download{ext}"
            print(f"Generated filename: {filename}")
        
        # Clean the filename
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        
        # Determine if the file is a PDF
        is_pdf = ('application/pdf' in response.headers.get('Content-Type', '') or 
                 filename.lower().endswith('.pdf') or
                 response.content.startswith(b'%PDF'))
        
        # Save the file
        file_path = os.path.join(DOWNLOAD_DIR, filename)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"Successfully downloaded file to {file_path}")
        
        return True, file_path, is_pdf
    
    except Exception as e:
        print(f"Error downloading file: {e}")
        traceback.print_exc()
        return False, None, False

def extract_archive(archive_path, extract_dir):
    """Extract an archive using unar."""
    print(f"Extracting {archive_path} to {extract_dir}")
    try:
        result = subprocess.run(['unar', '-force-overwrite', '-o', extract_dir, archive_path], 
                              capture_output=True, text=True, check=True)
        print(result.stdout)
        print("Extraction successful!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting file: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: 'unar' command not found. Please make sure it's installed.")
        print("You can install it with: brew install unar")
        return False

def find_and_extract_nested_archives(extract_dir):
    """Find and extract any nested archives in the extracted directory."""
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.lower().endswith('.rar') or file.lower().endswith('.zip'):
                nested_archive = os.path.join(root, file)
                print(f"\nFound nested archive: {nested_archive}")
                
                # Create a subdirectory for this nested archive
                nested_extract_dir = os.path.join(extract_dir, os.path.splitext(file)[0])
                os.makedirs(nested_extract_dir, exist_ok=True)
                
                # Extract the nested archive
                extract_archive(nested_archive, nested_extract_dir)

def copy_pdfs_to_pdf_dir(source_dir):
    """Copy all PDFs from source_dir to PDF_DIR."""
    pdf_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    if pdf_files:
        print(f"\nFound {len(pdf_files)} PDF files:")
        for pdf_file in pdf_files:
            print(f"- {pdf_file}")
        
        # Copy PDFs to the PDF directory
        for pdf_file in pdf_files:
            # Get the base filename
            base_name = os.path.basename(pdf_file)
            
            # Create a destination path
            dest_path = os.path.join(PDF_DIR, base_name)
            
            # Copy the file
            try:
                shutil.copy2(pdf_file, dest_path)
                print(f"Copied {pdf_file} to {dest_path}")
            except Exception as e:
                print(f"Error copying {pdf_file}: {e}")
        
        print(f"\nSuccessfully copied {len(pdf_files)} PDF files to {PDF_DIR}")
    else:
        print("\nNo PDF files found in the extracted archive.")

def process_file(file_path, is_pdf):
    """Process a downloaded file (PDF or archive)."""
    if is_pdf:
        # If it's a PDF, copy directly to the PDF directory
        filename = os.path.basename(file_path)
        dest_path = os.path.join(PDF_DIR, filename)
        shutil.copy2(file_path, dest_path)
        print(f"Copied PDF directly to {dest_path}")
        return True
    else:
        # For non-PDF files, try to extract them
        extract_dir = EXTRACTED_DIR
        if extract_archive(file_path, extract_dir):
            # Look for nested archives and extract them
            find_and_extract_nested_archives(extract_dir)
            
            # Copy any PDFs found to the PDF directory
            copy_pdfs_to_pdf_dir(extract_dir)
            return True
        return False

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

def summarize_with_gemini(text, endpoint_id, project_id, location):
    """Summarize text using Vertex AI Gemini model."""
    if not text.strip():
        return "No text content to summarize."
    
    try:
        print("Sending text to Gemini model for summarization...")
        
        # Construct the endpoint path
        endpoint_path = f"projects/{project_id}/locations/{location}/endpoints/{endpoint_id}"
        print(f"Using endpoint: {endpoint_path}")
        
        # Get the endpoint
        endpoint = aiplatform.Endpoint(endpoint_name=endpoint_path)
        
        # Prepare the prompt
        prompt = f"""
        Please provide a concise summary of the following procurement document. 
        Focus on key information such as:
        - The type of procurement
        - The goods or services being procured
        - Important dates and deadlines
        - Eligibility requirements
        - Estimated value (if mentioned)
        
        Document text:
        {text[:10000]}  # Limiting to first 10000 chars as Gemini has input limits
        
        If the text appears to be truncated, please note that in your summary.
        """
        
        # Send to the model
        response = endpoint.predict(
            instances=[{"text": prompt}],
            parameters={
                "temperature": 0.2,  # Lower temperature for more factual output
                "maxOutputTokens": 1024,  # Reasonable summary length
                "topK": 40,
                "topP": 0.95,
            }
        )
        
        # Extract the summary from the response
        # Note: The exact structure depends on the Gemini model's API
        # This might need adjustment based on the actual response format
        if hasattr(response, 'predictions') and response.predictions:
            summary = response.predictions[0]
            print("Successfully generated summary")
            return summary
        else:
            print("Warning: Unexpected response format from Gemini API")
            return "Error: Could not generate summary due to unexpected API response format."
    
    except Exception as e:
        print(f"Error during summarization: {e}")
        traceback.print_exc()
        return f"Error generating summary: {str(e)}"

def process_pdfs_for_summaries(project_id, location, endpoint_id):
    """Process all PDFs in PDF_DIR and save summaries to SUMMARY_DIR."""
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found to summarize.")
        return
    
    print(f"Found {len(pdf_files)} PDF files to summarize.")
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        summary_file = os.path.join(SUMMARY_DIR, f"summary_{pdf_file.replace('.pdf', '.txt')}")
        
        # Skip if summary already exists
        if os.path.exists(summary_file):
            print(f"Summary already exists for {pdf_file}, skipping.")
            continue
        
        print(f"\nProcessing {pdf_file} for summarization...")
        
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_path)
        
        if not text.strip():
            print(f"No text extracted from {pdf_file}, skipping summarization.")
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write("No text content could be extracted from this PDF. It might be a scanned document or contain only images.")
            continue
        
        # Summarize the text
        summary = summarize_with_gemini(text, endpoint_id, project_id, location)
        
        # Save the summary
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)
        
        print(f"Saved summary for {pdf_file} to {summary_file}")

def process_alertalicitacao_url(url):
    """Process an alertalicitacao URL to extract PNCP parameters and construct API URL."""
    print(f"Processing AlertaLicitacao URL: {url}")
    pncp_id_match = re.search(r'PNCP-(\d+)-(\d+)-(\d+)-(\d+)', url)
    if pncp_id_match:
        cnpj = pncp_id_match.group(1)
        sequence = pncp_id_match.group(2)
        year = pncp_id_match.group(4)
        number = pncp_id_match.group(3)
        print(f"PNCP ID information:")
        print(f"CNPJ: {cnpj}")
        print(f"Sequence: {sequence}")
        print(f"Year: {year}")
        print(f"Number: {number}")
        
        # Construct the PNCP API URL
        pncp_url = f"https://pncp.gov.br/pncp-api/v1/orgaos/{cnpj}/compras/{year}/{number}/arquivos/1"
        print(f"Constructed PNCP API URL: {pncp_url}")
        return pncp_url
    else:
        print("Could not extract PNCP ID from URL.")
        return None

def main():
    """Main function to handle downloading, extracting, and summarizing."""
    parser = argparse.ArgumentParser(description="Download, extract, and summarize procurement documents.")
    parser.add_argument("--url", help="URL to download from")
    parser.add_argument("--project-id", help="Google Cloud project ID", default=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", help="Google Cloud location", default="us-central1")
    parser.add_argument("--endpoint-id", help="Vertex AI endpoint ID")
    parser.add_argument("--skip-summarization", action="store_true", help="Skip the summarization step")
    
    args = parser.parse_args()
    
    # Setup directories
    setup_directories()
    
    # Get URL from argument or prompt
    url = args.url
    if not url:
        url = input("Please enter the URL to download from: ")
    
    # Process alertalicitacao URLs
    if 'alertalicitacao.com.br' in url:
        pncp_url = process_alertalicitacao_url(url)
        if pncp_url:
            url = pncp_url
        else:
            print("Failed to process alertalicitacao URL.")
            return 1
    
    # Download the file
    print(f"Starting download from URL: {url}")
    success, file_path, is_pdf = download_file(url)
    
    if not success:
        print("Download failed.")
        return 1
    
    # Process the downloaded file
    if not process_file(file_path, is_pdf):
        print("File processing failed.")
        return 1
    
    # Skip summarization if requested or if required parameters are missing
    if args.skip_summarization:
        print("Summarization step skipped as requested.")
        return 0
    
    # Check for required Vertex AI parameters
    project_id = args.project_id
    endpoint_id = args.endpoint_id
    
    if not project_id:
        print("Warning: Google Cloud project ID not provided. Skipping summarization.")
        print("To enable summarization, provide --project-id or set GOOGLE_CLOUD_PROJECT environment variable.")
        return 0
    
    if not endpoint_id:
        print("Warning: Vertex AI endpoint ID not provided. Skipping summarization.")
        print("To enable summarization, provide --endpoint-id parameter.")
        return 0
    
    # Initialize Vertex AI
    if not initialize_vertex_ai(project_id, args.location):
        print("Failed to initialize Vertex AI. Skipping summarization.")
        return 1
    
    # Process PDFs for summaries
    process_pdfs_for_summaries(project_id, args.location, endpoint_id)
    
    print("\nProcessing complete!")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Unhandled exception: {e}")
        traceback.print_exc()
        sys.exit(1) 