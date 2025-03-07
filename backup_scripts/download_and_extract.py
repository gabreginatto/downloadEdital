#!/usr/bin/env python3
"""
Script to download and extract files from a specific URL
"""

import requests
import sys
import os
import subprocess
import shutil
import traceback
import argparse
import re

def main():
    # Prompt the user for the URL
    url = input("Please enter the URL to download from: ")
    output_dir = 'downloads_simple'  # Keep default values
    extract_dir = 'extracted_simple'
    pdf_dir = 'pdfs_simple'
    
    # Check if it's an AlertaLicitacao URL
    if 'alertalicitacao.com.br' in url:
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
            url = f"https://pncp.gov.br/pncp-api/v1/orgaos/{cnpj}/compras/{year}/{number}/arquivos/1"
            print(f"Constructed PNCP API URL: {url}")
        else:
            print("Could not extract PNCP ID from URL.")
            return 1
    
    print(f"Starting download from URL: {url}")
    
    # Create the directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(extract_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Sending GET request to {url}")
        response = requests.get(url, headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Content type: {response.headers.get('Content-Type')}")
        print(f"Content length: {len(response.content)} bytes")
        
        if response.status_code == 200:
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
            
            if is_pdf:
                # If it's a PDF, save directly to the pdf_dir
                file_path = os.path.join(pdf_dir, filename)
                print(f"Detected PDF file, saving directly to PDF directory: {file_path}")
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"Successfully saved PDF to {file_path}")
                return 0
            
            # For non-PDF files, proceed with the normal download and extraction process
            file_path = os.path.join(output_dir, filename)
            print(f"Saving file to: {file_path}")
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"Successfully downloaded file to {file_path}")
            
            # Extract only if it's not a PDF
            print(f"Extracting {file_path} to {extract_dir}")
            try:
                result = subprocess.run(['unar', '-force-overwrite', '-o', extract_dir, file_path], 
                                      capture_output=True, text=True, check=True)
                print(result.stdout)
                print("Extraction successful!")
                
                # List the extracted files
                print("\nListing extracted files:")
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        print(f"- {os.path.join(root, file)}")
                
                # Look for RAR files and extract them
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.lower().endswith('.rar'):
                            rar_file = os.path.join(root, file)
                            print(f"\nFound RAR file: {rar_file}")
                            
                            # Create a subdirectory for this RAR file
                            rar_extract_dir = os.path.join(extract_dir, os.path.splitext(file)[0])
                            os.makedirs(rar_extract_dir, exist_ok=True)
                            
                            # Extract the RAR file
                            print(f"Extracting RAR file to {rar_extract_dir}")
                            try:
                                rar_result = subprocess.run(['unar', '-force-overwrite', '-o', rar_extract_dir, rar_file], 
                                                         capture_output=True, text=True, check=True)
                                print(rar_result.stdout)
                                print("RAR extraction successful!")
                            except subprocess.CalledProcessError as e:
                                print(f"Error extracting RAR file: {e}")
                                print(f"Error output: {e.stderr}")
                
                # Look for PDF files and copy them to the PDF directory
                pdf_files = []
                for root, dirs, files in os.walk(extract_dir):
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
                        dest_path = os.path.join(pdf_dir, base_name)
                        
                        # Copy the file
                        try:
                            shutil.copy2(pdf_file, dest_path)
                            print(f"Copied {pdf_file} to {dest_path}")
                        except Exception as e:
                            print(f"Error copying {pdf_file}: {e}")
                    
                    print(f"\nSuccessfully extracted and copied {len(pdf_files)} PDF files to {pdf_dir}:")
                    for file in os.listdir(pdf_dir):
                        if file.lower().endswith('.pdf'):
                            print(f"- {os.path.join(pdf_dir, file)}")
                else:
                    print("\nNo PDF files found in the extracted archive.")
                
            except subprocess.CalledProcessError as e:
                print(f"Error extracting file: {e}")
                print(f"Error output: {e.stderr}")
            except FileNotFoundError:
                print("Error: 'unar' command not found. Please make sure it's installed.")
                print("You can install it with: brew install unar")
        else:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Unhandled exception: {e}")
        traceback.print_exc()
        sys.exit(1) 