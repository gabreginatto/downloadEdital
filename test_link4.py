#!/usr/bin/env python3
"""
Test script for link #4 in example.json which requires Playwright
This script tests our ability to download a file that requires clicking a button
"""

import json
import os
import sys
import logging
import asyncio
import shutil
import re
from bs4 import BeautifulSoup
import requests
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Setup logging with both file and console handlers
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_link4.log"),
        logging.StreamHandler()
    ]
)

# Directory setup
DOWNLOAD_DIR = "downloads_test_link4"
EXTRACTED_DIR = "extracted_test_link4"
PDF_DIR = "pdfs_test_link4"

def setup_directories():
    """Create necessary directories if they don't exist."""
    for directory in [DOWNLOAD_DIR, EXTRACTED_DIR, PDF_DIR]:
        os.makedirs(directory, exist_ok=True)
        # Clean directory if it exists
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logging.error(f"Error cleaning directory {directory}: {e}")

    logging.info(f"Directories setup complete.")

async def setup_playwright():
    """Initialize Playwright in headless mode."""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)  # Headless mode enabled
    logging.info("Playwright initialized in headless mode.")
    return playwright, browser

async def handle_dynamic_download(url):
    """Use Playwright to download the file by clicking the 'Baixar Arquivo' button."""
    playwright, browser = await setup_playwright()
    context = None
    try:
        logging.info(f"Starting dynamic download process for URL: {url}")
        # Set the download directory
        context = await browser.new_context(
            accept_downloads=True
        )
        
        # Set timeout for operations
        context.set_default_timeout(30000) # 30 second timeout for operations
        page = await context.new_page()
        
        # Navigate to the URL
        logging.info(f"Navigating to URL: {url}")
        response = await page.goto(url, wait_until="networkidle", timeout=60000)
        logging.info(f"Page loaded with status: {response.status}")
        
        # Take a screenshot of the page
        screenshot_path = os.path.join(DOWNLOAD_DIR, "page_before_click.png")
        await page.screenshot(path=screenshot_path)
        logging.info(f"Screenshot saved to: {screenshot_path}")
        
        # Log page title
        title = await page.title()
        logging.info(f"Page title: {title}")
        
        # Try to find the download button
        logging.info("Searching for download button...")
        
        # Try different approaches to find the download button
        download_button = None
        try:
            # Try approaches in order of preference
            selectors = [
                "button:has-text('Baixar Arquivo')",
                "a:has-text('Baixar Arquivo')",
                "div.botaoBaixar",
                "a.botaoBaixar",
                "[data-test='download-button']",
                "[aria-label='Baixar arquivo']"
            ]
            
            for selector in selectors:
                logging.info(f"Trying selector: {selector}")
                await page.wait_for_selector(selector, state="visible", timeout=3000)
                element = await page.query_selector(selector)
                if element:
                    download_button = element
                    logging.info(f"Found download button with selector: {selector}")
                    break
            
            if not download_button:
                # If no button found with selectors above, try to find any button with text containing "baixar" or "download"
                logging.info("No button found with standard selectors, trying to find by text content")
                
                all_buttons = await page.query_selector_all("button")
                all_links = await page.query_selector_all("a")
                elements = all_buttons + all_links
                
                logging.info(f"Found {len(elements)} potential clickable elements")
                
                for i, element in enumerate(elements):
                    try:
                        text_content = await element.text_content()
                        if text_content and ('baixar' in text_content.lower() or 'download' in text_content.lower() or 'arquivo' in text_content.lower()):
                            download_button = element
                            logging.info(f"Found element {i+1} with text: '{text_content}'")
                            break
                    except Exception as e:
                        logging.error(f"Error getting text content from element {i+1}: {e}")
                        continue
            
            if download_button:
                logging.info("Found download button, clicking...")
                
                # Setup download event listener before clicking
                download_promise = page.wait_for_event("download")
                await download_button.click()
                logging.info("Clicked download button")
                
                # Wait for download to start
                download = await download_promise
                logging.info(f"Download started: {await download.suggested_filename()}")
                
                # Save the file
                downloaded_filename = await download.suggested_filename()
                downloaded_path = os.path.join(DOWNLOAD_DIR, downloaded_filename)
                await download.save_as(downloaded_path)
                logging.info(f"Downloaded file: {downloaded_path}")
                
                # Check if file exists and has content
                if os.path.exists(downloaded_path) and os.path.getsize(downloaded_path) > 0:
                    logging.info(f"✅ Download successful! File size: {os.path.getsize(downloaded_path)} bytes")
                    return True, downloaded_path
                else:
                    logging.error("❌ Download failed: File is empty or doesn't exist")
                    return False, None
            else:
                logging.error("❌ Could not find any download button after trying multiple selectors")
                
                # Let's try to find any buttons that might be download buttons
                all_buttons = await page.query_selector_all("button")
                logging.info(f"Found {len(all_buttons)} buttons on the page")
                
                for i, button in enumerate(all_buttons):
                    text = await button.text_content()
                    logging.info(f"Button {i+1}: '{text}'")
                
                # Also look for links
                all_links = await page.query_selector_all("a")
                logging.info(f"Found {len(all_links)} links on the page")
                for i, link in enumerate(all_links[:10]):  # Show first 10 links
                    try:
                        href = await link.get_attribute("href")
                        text = await link.text_content()
                        logging.info(f"Link {i+1}: '{text}' -> {href}")
                    except:
                        pass
                
                return False, None
                
        except PlaywrightTimeoutError:
            logging.error("❌ Timeout waiting for download button")
            
            # Take another screenshot to see what the page looks like
            await page.screenshot(path=os.path.join(DOWNLOAD_DIR, "page_timeout.png"))
            
            # Try to look for any button with download-related text
            download_keywords = ["baixar", "download", "arquivo", "edital"]
            for keyword in download_keywords:
                buttons = await page.query_selector_all(f"button:has-text('{keyword}')")
                if buttons:
                    logging.info(f"Found {len(buttons)} buttons containing '{keyword}'")
                    for button in buttons:
                        text = await button.text_content()
                        logging.info(f"  Button text: '{text}'")
            
            # Get and log HTML content for debugging
            content = await page.content()
            with open(os.path.join(DOWNLOAD_DIR, "page_content.html"), "w", encoding="utf-8") as f:
                f.write(content)
            logging.info(f"Saved page content to page_content.html")
            
            return False, None
            
    except Exception as e:
        logging.error(f"❌ Error with Playwright: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False, None
    finally:
        if context:
            await context.close()
        await browser.close()
        await playwright.stop()
        logging.info("Playwright resources cleaned up")

def get_link4_from_json(json_path):
    """Extract link #4 from the example.json file."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Find the PCP-4215802-5-812024 entry
        link4 = None
        for licitacao in data.get('licitacoes', []):
            if licitacao.get('id') == 'PCP-4215802-5-812024':
                link4 = licitacao
                break
                
        if not link4:
            logging.error("Could not find link #4 (PCP-4215802-5-812024) in the JSON file")
            return None
            
        logging.info(f"Found link #4: {link4['titulo']} from {link4['orgao']}")
        return link4
    except Exception as e:
        logging.error(f"Error reading JSON file: {e}")
        return None

def process_alertalicitacao_url(url):
    """Process an alertalicitacao URL to find the original source URL."""
    logging.info(f"Processing AlertaLicitacao URL: {url}")
    
    # Try PCP format
    pcp_match = re.search(r'PCP-(\d+)-(\d+)-(\d+)', url)
    if pcp_match:
        logging.info("Found PCP format URL, attempting to fetch original document URL...")
        try:
            # Get the AlertaLicitacao page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Look for the original document URL
            original_url_match = re.search(r'Visitar site original para mais detalhes: (https://[^\s<>"\']+)', response.text)
            if original_url_match:
                original_url = original_url_match.group(1)
                logging.info(f"Found original document URL: {original_url}")
                return original_url
            
            # If we can't find the "Visitar site original" link, try finding any portaldecompraspublicas.com.br URL
            portal_url_match = re.search(r'(https://www\.portaldecompraspublicas\.com\.br/[^\s<>"\']+)', response.text)
            if portal_url_match:
                portal_url = portal_url_match.group(1)
                logging.info(f"Found Portal de Compras Públicas URL: {portal_url}")
                return portal_url
                
            # Look for any URL that might be relevant
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            logging.info(f"Found {len(links)} links on the page")
            
            for link in links:
                href = link.get('href')
                if 'portaldecompraspublicas.com.br' in href:
                    logging.info(f"Found link to Portal de Compras Públicas: {href}")
                    return href
            
        except Exception as e:
            logging.error(f"Error fetching original document URL: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    logging.error("Could not find original document URL from alertalicitacao")
    return None

async def main():
    """Main test function."""
    import re
    
    setup_directories()
    
    # Get link #4 from JSON
    json_path = "/Users/gabrielreginatto/Desktop/Code/MCP/downloadEdital/json/example.json"
    link4 = get_link4_from_json(json_path)
    
    if not link4:
        return 1
    
    url = link4['link']
    logging.info(f"Testing URL: {url}")
    
    # Process alertalicitacao URL if needed
    if 'alertalicitacao.com.br' in url:
        portal_url = process_alertalicitacao_url(url)
        if portal_url:
            url = portal_url
            logging.info(f"Processing URL redirected to: {url}")
        else:
            logging.error("Failed to get portal URL from alertalicitacao")
            return 1
    
    # Use Playwright to download the file
    success, file_path = await handle_dynamic_download(url)
    
    if success:
        logging.info(f"Test completed successfully! File downloaded to: {file_path}")
        # Copy to PDF directory for easy viewing
        pdf_path = os.path.join(PDF_DIR, os.path.basename(file_path))
        shutil.copy2(file_path, pdf_path)
        logging.info(f"PDF copied to: {pdf_path}")
        return 0
    else:
        logging.error("Test failed! Could not download the file.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1) 