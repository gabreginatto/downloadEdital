#!/usr/bin/env python3

import requests
import re
import sys

def main():
    url = "https://alertalicitacao.com.br/!licitacao/PNCP-86050978000183-1-000148-2024"
    print(f"Downloading from {url}")
    
    # Try to extract PNCP ID
    pncp_id_match = re.search(r'PNCP-(\d+)-(\d+)-(\d+)-(\d+)', url)
    if pncp_id_match:
        cnpj = pncp_id_match.group(1)
        sequence = pncp_id_match.group(2)
        number = pncp_id_match.group(3)
        year = pncp_id_match.group(4)
        print(f"PNCP ID: CNPJ={cnpj}, sequence={sequence}, number={number}, year={year}")
        
        # Construct PNCP API URL
        pncp_url = f"https://pncp.gov.br/pncp-api/v1/orgaos/{cnpj}/compras/{year}/{number}/arquivos/1"
        print(f"PNCP API URL: {pncp_url}")
        
        # Download from PNCP API
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            response = requests.get(pncp_url, headers=headers)
            print(f"Status code: {response.status_code}")
            print(f"Content type: {response.headers.get('Content-Type')}")
            print(f"Content length: {len(response.content)} bytes")
            
            if response.status_code == 200:
                # Save the file
                with open("download_test.bin", "wb") as f:
                    f.write(response.content)
                print("File downloaded successfully to download_test.bin")
            else:
                print(f"Error: {response.status_code}")
                print(f"Response: {response.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Could not extract PNCP ID from URL")

if __name__ == "__main__":
    main() 