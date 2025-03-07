#!/usr/bin/env python3
"""
Test script for Playwright download functionality
This script tests the Playwright implementation for downloading files that require button clicks
"""

import os
import logging
import asyncio
import sys
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Directory setup
DOWNLOAD_DIR = "downloads_test"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def test_dynamic_download(url):
    """Test dynamic download with Playwright."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            logging.info(f"Testing download from URL: {url}")
            
            context = await browser.new_context(
                accept_downloads=True,
                downloads_path=DOWNLOAD_DIR
            )
            page = await context.new_page()
            
            # Navigate to the URL
            await page.goto(url, wait_until="networkidle")
            logging.info(f"Page loaded: {url}")
            
            # Check if there's a download button
            download_button = await page.query_selector("button:has-text('Baixar Arquivo')")
            if download_button:
                logging.info("Found 'Baixar Arquivo' button, clicking...")
                
                # Setup download event listener before clicking
                download_promise = page.wait_for_event("download")
                await download_button.click()
                
                # Wait for download to start
                download = await download_promise
                logging.info(f"Download started: {await download.suggested_filename()}")
                
                # Save the file
                downloaded_path = os.path.join(DOWNLOAD_DIR, await download.suggested_filename())
                await download.save_as(downloaded_path)
                logging.info(f"File downloaded to: {downloaded_path}")
                
                # Print success message
                logging.info("✅ Test successful: File downloaded successfully")
                return True
            else:
                logging.error("❌ Test failed: Could not find 'Baixar Arquivo' button")
                
                # Take a screenshot to see what the page looks like
                await page.screenshot(path=os.path.join(DOWNLOAD_DIR, "page_screenshot.png"))
                logging.info(f"Screenshot saved to: {os.path.join(DOWNLOAD_DIR, 'page_screenshot.png')}")
                
                # Print the page content to help debugging
                content = await page.content()
                logging.info(f"Page content snippet: {content[:500]}...")
                
                return False
                
        except PlaywrightTimeoutError:
            logging.error("❌ Test failed: Timeout waiting for page or button")
            return False
        except Exception as e:
            logging.error(f"❌ Test failed with error: {e}")
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_playwright.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    success = asyncio.run(test_dynamic_download(url))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1) 