#!/usr/bin/env python3
"""
Test script for enhanced download_edital.py with Playwright integration
This tests the full functionality with a focus on the dynamic download capabilities
"""

import os
import sys
import json
import logging
import shutil
import subprocess
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"test_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

def clean_test_directories():
    """Clean test directories to start fresh"""
    test_dirs = ["downloads_simple", "extracted_simple", "pdfs_simple"]
    for directory in test_dirs:
        if os.path.exists(directory):
            logging.info(f"Cleaning directory: {directory}")
            try:
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        logging.warning(f"Error cleaning file {file_path}: {e}")
            except Exception as e:
                logging.error(f"Error cleaning directory {directory}: {e}")

def count_pdfs_in_directory(directory):
    """Count number of PDFs in directory"""
    if not os.path.exists(directory):
        return 0
    
    pdf_count = 0
    for file in os.listdir(directory):
        if file.lower().endswith('.pdf'):
            pdf_count += 1
    
    return pdf_count

def run_main_script(json_path):
    """Run the main download_edital.py script with specified JSON file"""
    logging.info(f"Running download_edital.py with JSON file: {json_path}")
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_edital.py")
    
    try:
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, script_path, "--json", json_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        logging.info("Script executed successfully")
        logging.debug(f"STDOUT: {result.stdout}")
        
        if result.stderr:
            logging.warning(f"STDERR: {result.stderr}")
        
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Script execution failed with error code: {e.returncode}")
        logging.error(f"STDOUT: {e.stdout}")
        logging.error(f"STDERR: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Error running script: {e}")
        return False

def verify_results():
    """Verify that PDFs were correctly downloaded and extracted"""
    pdf_count = count_pdfs_in_directory("pdfs_simple")
    logging.info(f"Found {pdf_count} PDFs in pdfs_simple directory")
    
    if pdf_count > 0:
        logging.info("✅ Test PASSED: PDFs were successfully downloaded")
        return True
    else:
        logging.error("❌ Test FAILED: No PDFs were found")
        return False

def main():
    """Main test function"""
    # 1. Clean test directories
    clean_test_directories()
    
    # 2. Path to JSON file
    json_path = "/Users/gabrielreginatto/Desktop/Code/MCP/downloadEdital/json/example.json"
    if not os.path.exists(json_path):
        logging.error(f"JSON file not found: {json_path}")
        return 1
    
    # 3. Run main script
    success = run_main_script(json_path)
    
    # 4. Verify results
    if success:
        if verify_results():
            logging.info("🎉 All tests passed successfully!")
            return 0
        else:
            logging.error("📊 Test verification failed")
            return 1
    else:
        logging.error("🚫 Script execution failed")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1) 