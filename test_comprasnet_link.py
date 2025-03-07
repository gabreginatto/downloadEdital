#!/usr/bin/env python3
"""
Test script specifically for ComprasNet links via AlertaLicitacao
This script tests the ability to download from ComprasNet via AlertaLicitacao
URL: https://alertalicitacao.com.br/!licitacao/CN-925777-5-901692024

Features:
- Uses Playwright for browser automation
- Gemini AI for CAPTCHA solving
- Dynamic page handling with popup support
"""

import os
import sys
import logging
import asyncio
import shutil
import requests
import re
import time
import base64
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv
import json
import random
import traceback
from PIL import Image, ImageDraw  # For visual debugging

# Load environment variables (for API keys)
load_dotenv()

# Setup logging with both file and console handlers
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"test_comprasnet_{int(time.time())}.log"),
        logging.StreamHandler()
    ]
)

# Directory setup
DOWNLOAD_DIR = "downloads_comprasnet_test"
EXTRACTED_DIR = "extracted_comprasnet_test"
PDF_DIR = "pdfs_comprasnet_test"
CAPTCHA_DIR = "captchas"
DEBUG_DIR = "debug_images"  # For visual debugging

# Target URL
TARGET_URL = "https://alertalicitacao.com.br/!licitacao/CN-925777-5-901692024"

# Gemini API setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_VISION_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-lite-001:generateContent"

# Playwright globals
playwright_instance = None
browser_instance = None

# Visual debugging function
def visualize_element_capture(image_path, box, output_path):
    """Draw a rectangle around the identified element for debugging."""
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        draw.rectangle(
            [(box['x'], box['y']), (box['x'] + box['width'], box['y'] + box['height'])],
            outline=(255, 0, 0),  # Red outline
            width=3  # Line width
        )
        img.save(output_path)
        logging.info(f"Saved debug visualization to: {output_path}")
    except Exception as e:
        logging.error(f"Error creating visualization: {e}")

def setup_directories():
    """Create necessary directories if they don't exist and clean them."""
    for directory in [DOWNLOAD_DIR, EXTRACTED_DIR, PDF_DIR, CAPTCHA_DIR, DEBUG_DIR]:
        os.makedirs(directory, exist_ok=True)
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
    """Initialize Playwright in non-headless mode."""
    global playwright_instance, browser_instance
    if playwright_instance is None:
        playwright_instance = await async_playwright().start()
        browser_instance = await playwright_instance.chromium.launch(headless=False)
    logging.info("Playwright initialized in non-headless mode.")
    return playwright_instance, browser_instance

async def teardown_playwright():
    """Clean up Playwright resources."""
    global playwright_instance, browser_instance
    if browser_instance:
        await browser_instance.close()
    if playwright_instance:
        await playwright_instance.stop()
    logging.info("Playwright resources cleaned up.")

async def solve_captcha_with_gemini(captcha_image_path):
    """Use Gemini Vision API to solve a CAPTCHA from an image file."""
    if not GEMINI_API_KEY:
        logging.error("GEMINI_API_KEY not found in environment variables")
        return None

    try:
        logging.info(f"Using Gemini to solve CAPTCHA from: {captcha_image_path}")
        with open(captcha_image_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }

        data = {
            "contents": [{
                "parts": [
                    {"text": "This image contains a CAPTCHA with distorted text. Please identify and extract ONLY the text characters (letters and/or numbers) shown in the image. The CAPTCHA text might be distorted, skewed, or have a noisy background. Look carefully for characters that might be hard to see. Only respond with the exact characters, with NO additional explanation or text. If you can't identify any characters with certainty, respond with 'uDJNs'."},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_data
                        }
                    }
                ]
            }],
            "generation_config": {
                "temperature": 0.1,
                "top_p": 0.95,
                "top_k": 40
            }
        }

        response = requests.post(GEMINI_VISION_URL, headers=headers, data=json.dumps(data))
        response_json = response.json()
        logging.debug(f"Raw Gemini response: {response_json}")

        if 'candidates' in response_json and len(response_json['candidates']) > 0:
            if 'content' in response_json['candidates'][0] and 'parts' in response_json['candidates'][0]['content']:
                predicted_text = response_json['candidates'][0]['content']['parts'][0]['text']
                predicted_text = re.sub(r'\s+', '', predicted_text)
                
                # If Gemini couldn't identify any text or returned an error-like response
                if predicted_text.lower() in ["notextvisible", "notext", "notextcharacters", "notextfound", 
                                            "icannotsee", "novisibletext", "notextispresent", "nocharacters",
                                            "theimagecontains", "sorryicannotsee"]:
                    logging.warning(f"Gemini couldn't identify text, using fallback value: uDJNs")
                    return "uDJNs"  # Return a fallback value
                
                logging.info(f"Gemini predicted CAPTCHA text: {predicted_text}")
                return predicted_text

        logging.error(f"Failed to get valid response from Gemini: {response_json}")
        return "uDJNs"  # Return a fallback value if no valid response

    except Exception as e:
        logging.error(f"Error solving CAPTCHA with Gemini: {e}")
        logging.error(traceback.format_exc())
        return "uDJNs"  # Return a fallback value on exception

async def type_like_human(element, text):
    """Type text into an element character by character with realistic timing."""
    logging.info(f"Typing like a human: '{text}'")
    await element.fill("")
    for char in text:
        await element.press(char)
        delay = random.uniform(0.1, 0.3)
        await asyncio.sleep(delay)
    await asyncio.sleep(random.uniform(0.5, 1.0))

async def handle_captcha_with_retries(main_page, popup_page, max_retries=4):
    """Handle CAPTCHA in a popup with retries."""
    captcha_attempts = 0
    captcha_solved = False

    while captcha_attempts < max_retries and not captcha_solved:
        captcha_attempts += 1
        logging.info(f"CAPTCHA attempt {captcha_attempts} of {max_retries}")

        # Take a screenshot of the popup for debugging
        attempt_screenshot = os.path.join(DOWNLOAD_DIR, f"captcha_attempt_popup_{captcha_attempts}.png")
        await popup_page.screenshot(path=attempt_screenshot)
        logging.info(f"Popup screenshot: {attempt_screenshot}")

        # Save the HTML content of the popup for debugging
        popup_html = await popup_page.content()
        popup_html_path = os.path.join(DEBUG_DIR, f"popup_html_{captcha_attempts}.html")
        with open(popup_html_path, "w", encoding="utf-8") as f:
            f.write(popup_html)
        logging.info(f"Saved popup HTML to: {popup_html_path}")

        # Find all images in the popup and log their details
        all_images = await popup_page.query_selector_all("img")
        logging.info(f"Found {len(all_images)} images in the popup")
        
        for i, img in enumerate(all_images):
            try:
                src = await img.get_attribute("src") or ""
                alt = await img.get_attribute("alt") or ""
                box = await img.bounding_box()
                logging.info(f"Image {i+1}: src='{src}', alt='{alt}', box={box}")
                
                # Save a screenshot of each image for visual inspection
                if box:
                    img_path = os.path.join(DEBUG_DIR, f"popup_img_{captcha_attempts}_{i+1}.png")
                    await img.screenshot(path=img_path)
                    logging.info(f"Saved image {i+1} to: {img_path}")
            except Exception as e:
                logging.warning(f"Error inspecting image {i+1}: {e}")

        # More specifically targeted CAPTCHA selectors based on ComprasNet's structure
        captcha_selectors = [
            # Try to find a large image near the "Digite os caracteres ao lado:" text
            "img:near(:text('Digite os caracteres ao lado:'))",
            
            # Try using a direct evaluation to find an image with specific dimensions
            # This custom evaluation targets images that are of typical CAPTCHA size (larger than icons)
            "img:eval(node => node.width > 50 && node.height > 20)",
            
            # Most specific - looking for CAPTCHA with distinctive visual clues
            "img[width>100][height>30]",
            
            # ComprasNet specific structure
            "img:near(input[name='txt_captcha'])",
            
            # Standard CAPTCHA attributes as fallback
            "img[src*='captcha']",
            "img[alt*='captcha']"
        ]

        captcha_image = None
        selector_used = None
        
        # Find CAPTCHA image
        for selector in captcha_selectors:
            try:
                elements = await popup_page.query_selector_all(selector)
                logging.info(f"Selector '{selector}' returned {len(elements)} elements")
                
                if elements:
                    for elem in elements:
                        box = await elem.bounding_box()
                        # Prioritize elements that are reasonably sized for a CAPTCHA
                        if box and box['width'] > 50 and box['height'] > 20:
                            captcha_image = elem
                            selector_used = selector
                            logging.info(f"Found likely CAPTCHA image with selector: {selector}")
                            logging.info(f"Dimensions: {box['width']}x{box['height']}px")
                            break
                    
                    if captcha_image:
                        break
            except Exception as e:
                logging.warning(f"Error with selector {selector}: {e}")

        # If still no image found, try a JavaScript-based approach to find the most likely CAPTCHA
        if not captcha_image:
            try:
                logging.info("Using JavaScript to find potential CAPTCHA images")
                potential_captchas = await popup_page.evaluate('''() => {
                    const images = Array.from(document.querySelectorAll('img'));
                    return images
                        .filter(img => img.width > 50 && img.height > 20) // Filter by size
                        .map(img => ({
                            src: img.src,
                            width: img.width,
                            height: img.height,
                            x: img.getBoundingClientRect().x,
                            y: img.getBoundingClientRect().y
                        }));
                }''')
                
                logging.info(f"Found {len(potential_captchas)} potential CAPTCHA images via JavaScript")
                
                for i, img_data in enumerate(potential_captchas):
                    logging.info(f"Potential CAPTCHA {i+1}: {img_data}")
                    
                if potential_captchas:
                    # Try to get the first potential CAPTCHA image
                    element_handle = await popup_page.evaluate_handle('''(coords) => {
                        const elements = document.elementsFromPoint(coords.x + coords.width/2, coords.y + coords.height/2);
                        return elements.find(el => el.tagName.toLowerCase() === 'img');
                    }''', potential_captchas[0])
                    
                    if element_handle:
                        captcha_image = element_handle
                        logging.info("Found CAPTCHA image via JavaScript evaluation")
            except Exception as e:
                logging.error(f"Error with JavaScript CAPTCHA detection: {e}")

        if not captcha_image:
            logging.error("No CAPTCHA image found in popup after extensive search")
            
            # Save a full screenshot with annotations pointing out all images
            all_imgs_debug = os.path.join(DEBUG_DIR, f"all_images_in_popup_{captcha_attempts}.png")
            shutil.copy(attempt_screenshot, all_imgs_debug)
            logging.info(f"Saved screenshot with all images for manual inspection: {all_imgs_debug}")
            
            # Try to use the entire popup screenshot since we can't identify the CAPTCHA element
            logging.info("Using entire popup screenshot for CAPTCHA recognition")
            
            # Find CAPTCHA input field in popup
            captcha_input_selectors = [
                "input:near(:text('Digite os caracteres ao lado:'))",
                "input[name='txt_captcha']",
                "input[name*='captcha']",
                "input[type='text']:near(:text('Digite'))"
            ]

            captcha_input = None
            for selector in captcha_input_selectors:
                try:
                    captcha_input = await popup_page.query_selector(selector)
                    if captcha_input:
                        logging.info(f"Found CAPTCHA input field with selector: {selector}")
                        break
                except Exception as e:
                    logging.warning(f"Error finding CAPTCHA input with selector {selector}: {e}")

            if not captcha_input:
                logging.error("Could not find CAPTCHA input field in popup")
                return False, None

            # Use the entire popup screenshot for CAPTCHA recognition
            captcha_text = await solve_captcha_with_gemini(attempt_screenshot)
            
            # Continue with the rest of the flow
            await type_like_human(captcha_input, captcha_text)
            
            # Find and click submit button
            submit_button = await popup_page.query_selector("input[value='Confirmar']")
            if submit_button:
                download_promise = main_page.wait_for_event("download", timeout=30000)
                await submit_button.click()
                logging.info("Clicked submit button in popup")
                
                await asyncio.sleep(3)
                
                try:
                    download = await download_promise
                    # Process download as usual
                    filename = f"comprasnet_download_{int(time.time())}.pdf"
                    try:
                        suggested_filename = await download.suggested_filename()
                        if suggested_filename:
                            filename = suggested_filename
                    except Exception as e:
                        logging.warning(f"Could not get suggested filename: {e}")
                    
                    downloaded_path = os.path.join(DOWNLOAD_DIR, filename)
                    await download.save_as(downloaded_path)
                    
                    if os.path.exists(downloaded_path) and os.path.getsize(downloaded_path) > 0:
                        pdf_path = os.path.join(PDF_DIR, filename)
                        shutil.copy2(downloaded_path, pdf_path)
                        return True, downloaded_path
                except Exception as e:
                    logging.warning(f"No download after using full screenshot: {e}")
            
            # If we got here, try the next attempt
            continue

        # Get CAPTCHA image attributes for debugging
        try:
            src = await captcha_image.get_attribute("src") or ""
            alt = await captcha_image.get_attribute("alt") or ""
            box = await captcha_image.bounding_box()
            logging.info(f"Selected CAPTCHA: src='{src}', alt='{alt}', box={box}")
        except Exception as e:
            logging.warning(f"Error getting CAPTCHA attributes: {e}")

        # Try to enhance the CAPTCHA image capture
        captcha_filename = f"captcha_attempt_{captcha_attempts}_{int(time.time())}.jpg"
        captcha_path = os.path.join(CAPTCHA_DIR, captcha_filename)
        
        try:
            # Get bounding box for better cropping
            bbox = await captcha_image.bounding_box()
            logging.info(f"CAPTCHA image bounding box: {bbox}")
            
            # Attempt to enhance the element screenshot with clip options
            await captcha_image.screenshot(path=captcha_path, 
                                          omit_background=True,  # Try to omit background 
                                          type='jpeg',          # Explicitly use JPEG format
                                          quality=100)          # Max quality
            logging.info(f"Saved enhanced CAPTCHA image to: {captcha_path}")
            
            # Also save the entire popup for comparison
            full_popup_captcha = os.path.join(CAPTCHA_DIR, f"full_popup_{captcha_attempts}_{int(time.time())}.jpg")
            await popup_page.screenshot(path=full_popup_captcha)
            logging.info(f"Saved full popup screenshot for comparison: {full_popup_captcha}")
            
            # Create a visual debug image showing what we identified as the CAPTCHA
            if bbox:
                debug_path = os.path.join(DEBUG_DIR, f"debug_captcha_{captcha_attempts}.jpg")
                visualize_element_capture(full_popup_captcha, bbox, debug_path)
            
        except Exception as e:
            logging.error(f"Error taking screenshot of CAPTCHA: {e}")
            logging.info("Falling back to using popup screenshot")
            captcha_path = attempt_screenshot

        # Find CAPTCHA input field in popup
        captcha_input_selectors = [
            "input:near(:text('Digite os caracteres ao lado:'))",
            "input:near(img[src*='captcha'])",
            "input[name='txt_captcha']",
            "input[name*='captcha']"
        ]

        captcha_input = None
        for selector in captcha_input_selectors:
            try:
                captcha_input = await popup_page.query_selector(selector)
                if captcha_input:
                    logging.info(f"Found CAPTCHA input field with selector: {selector}")
                    
                    # Debug info about the input field
                    try:
                        input_box = await captcha_input.bounding_box()
                        input_name = await captcha_input.get_attribute("name") or ""
                        input_id = await captcha_input.get_attribute("id") or ""
                        logging.info(f"CAPTCHA input: name='{input_name}', id='{input_id}', box={input_box}")
                        
                        # Visualize the input field as well
                        if input_box:
                            input_debug_path = os.path.join(DEBUG_DIR, f"debug_input_{captcha_attempts}.jpg")
                            visualize_element_capture(full_popup_captcha, input_box, input_debug_path)
                    except Exception as e:
                        logging.warning(f"Error getting input field details: {e}")
                    
                    break
            except Exception as e:
                logging.warning(f"Error finding CAPTCHA input with selector {selector}: {e}")

        if not captcha_input:
            logging.error("Could not find CAPTCHA input field in popup")
            return False, None

        # Solve CAPTCHA with Gemini
        captcha_text = await solve_captcha_with_gemini(captcha_path)
        
        # If Gemini couldn't identify anything, try using the full popup image
        if captcha_text == "uDJNs":
            logging.info("Trying with full popup image as fallback")
            captcha_text = await solve_captcha_with_gemini(full_popup_captcha)
        
        if not captcha_text or captcha_text == "uDJNs":
            logging.error("Failed to solve CAPTCHA with Gemini")
            refresh_button = await popup_page.query_selector("a:has-text('gerar outra imagem')")
            if refresh_button:
                logging.info("Clicking CAPTCHA refresh button")
                await refresh_button.click()
                await popup_page.wait_for_timeout(2000)
                continue
            
            # If we can't refresh, try a standard value as last resort
            logging.info("No refresh button found, trying with 'uDJNs' as a last resort")
            captcha_text = "uDJNs"

        # Type CAPTCHA text
        await type_like_human(captcha_input, captcha_text)

        # Find and click the submit button
        submit_selectors = [
            "input[type='button'][value='Confirmar']",
            "button:has-text('Confirmar')",
            "input[value='Confirmar']"
        ]

        submit_button = None
        for selector in submit_selectors:
            try:
                submit_button = await popup_page.query_selector(selector)
                if submit_button:
                    logging.info(f"Found submit button with selector: {selector}")
                    
                    # Debug info about the submit button
                    try:
                        button_box = await submit_button.bounding_box()
                        button_type = await submit_button.get_attribute("type") or ""
                        button_value = await submit_button.get_attribute("value") or ""
                        logging.info(f"Submit button: type='{button_type}', value='{button_value}', box={button_box}")
                    except Exception as e:
                        logging.warning(f"Error getting submit button details: {e}")
                    
                    break
            except Exception as e:
                logging.warning(f"Error finding submit button with selector {selector}: {e}")

        if not submit_button:
            logging.error("Could not find submit button in popup")
            return False, None

        logging.info("Submitting the CAPTCHA form...")

        # Take a screenshot right before submitting
        before_submit_path = os.path.join(DEBUG_DIR, f"before_submit_{captcha_attempts}.png")
        await popup_page.screenshot(path=before_submit_path)
        logging.info(f"Screenshot before submit: {before_submit_path}")

        # Set up download event listener on the main page
        download_promise = main_page.wait_for_event("download", timeout=30000)

        # Click the submit button in the popup
        await submit_button.click()
        logging.info("Clicked submit button in popup")

        # Wait for popup to close and download to start
        await asyncio.sleep(3)  # Adjust timing if needed

        # Take a screenshot right after submitting
        after_submit_path = os.path.join(DEBUG_DIR, f"after_submit_{captcha_attempts}.png")
        await main_page.screenshot(path=after_submit_path)
        logging.info(f"Screenshot after submit: {after_submit_path}")

        try:
            download = await download_promise
            logging.info("Download event triggered on main page!")

            filename = f"comprasnet_download_{int(time.time())}.pdf"
            try:
                suggested_filename = await download.suggested_filename()
                if suggested_filename:
                    filename = suggested_filename
            except Exception as e:
                logging.warning(f"Could not get suggested filename: {e}")

            downloaded_path = os.path.join(DOWNLOAD_DIR, filename)
            await download.save_as(downloaded_path)
            logging.info(f"Downloaded file: {downloaded_path}")

            if os.path.exists(downloaded_path) and os.path.getsize(downloaded_path) > 0:
                pdf_path = os.path.join(PDF_DIR, filename)
                shutil.copy2(downloaded_path, pdf_path)
                logging.info(f"Copied to PDF directory: {pdf_path}")
                captcha_solved = True
                return True, downloaded_path
            else:
                logging.error("Download failed: File is empty or doesn't exist")

        except Exception as e:
            logging.warning(f"No download event detected after CAPTCHA submission: {e}")

        # Check for CAPTCHA rejection
        try:
            popup_exists = await popup_page.evaluate('() => document.body !== null')
            
            if popup_exists:
                popup_content = await popup_page.content()
                captcha_error_indicators = [
                    "captcha inválido",
                    "captcha incorreto",
                    "caracteres informados não conferem",
                    "captcha errado",
                    "captcha não confere",
                    "invalid captcha"
                ]

                captcha_rejected = False
                for indicator in captcha_error_indicators:
                    if indicator.lower() in popup_content.lower():
                        logging.warning(f"CAPTCHA rejected: '{indicator}' found in popup content")
                        captcha_rejected = True
                        break

                if captcha_rejected:
                    logging.info("CAPTCHA was rejected. Will try again.")
                    continue
            else:
                logging.info("Popup closed without error, but no download was detected")
        except Exception as e:
            logging.warning(f"Error checking popup content after submission: {e}")

    logging.error(f"Failed to solve CAPTCHA after {max_retries} attempts")
    return False, None

async def handle_comprasnet_download(url):
    """Handle download from ComprasNet with CAPTCHA popup handling."""
    try:
        playwright, browser = await setup_playwright()

        context = await browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True
        )
        context.set_default_timeout(60000)

        page = await context.new_page()
        logging.info(f"Navigating to URL: {url}")
        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        logging.info(f"Page loaded with status: {response.status}")

        # Take screenshot for debugging
        screenshot_path = os.path.join(DOWNLOAD_DIR, f"comprasnet_page_{int(time.time())}.png")
        await page.screenshot(path=screenshot_path)
        logging.info(f"Screenshot saved to: {screenshot_path}")

        # Set up popup handler
        popup_page = None
        async def handle_popup(new_page):
            nonlocal popup_page
            popup_page = new_page
            logging.info("Popup window detected")
            await popup_page.wait_for_load_state("domcontentloaded")
            logging.info("Popup loaded")

        page.on("popup", handle_popup)

        # Look for download buttons
        download_button = None
        comprasnet_download_selectors = [
            "input[type='button'][value='Download']",
            "input[type='submit'][value='Download']",
            "a:has-text('Download')"
        ]

        for selector in comprasnet_download_selectors:
            try:
                download_button = await page.query_selector(selector)
                if download_button and await download_button.is_visible():
                    logging.info(f"Found download button with selector: {selector}")
                    break
            except Exception as e:
                logging.info(f"Error with selector {selector}: {e}")

        if not download_button:
            logging.error("Could not find download button")
            return False, None

        # Click the download button to trigger the CAPTCHA popup
        logging.info("Clicking download button to trigger CAPTCHA popup...")
        await download_button.click()
        logging.info("Clicked download button")

        # Wait for popup to appear
        popup_wait_start = time.time()
        while popup_page is None and time.time() - popup_wait_start < 10:
            await asyncio.sleep(1)
            logging.info("Waiting for popup to appear...")

        if not popup_page:
            logging.error("No popup window detected after clicking download button")
            
            # Sometimes the CAPTCHA appears in a frame instead of a popup
            logging.info("Checking if CAPTCHA appears in a frame instead...")
            frames = page.frames
            logging.info(f"Found {len(frames)} frames on the page")
            
            # Take another screenshot to see current state
            frame_screenshot_path = os.path.join(DOWNLOAD_DIR, f"frames_check_{int(time.time())}.png")
            await page.screenshot(path=frame_screenshot_path)
            logging.info(f"Screenshot after clicking download: {frame_screenshot_path}")
            
            # Check if CAPTCHA is on the main page
            captcha_on_main = await page.query_selector("img[src*='captcha']")
            if captcha_on_main:
                logging.info("CAPTCHA appears to be on the main page, not in a popup")
                
                # See if there's a form with a captcha input
                captcha_form = await page.query_selector("form:has(img[src*='captcha'])")
                if captcha_form:
                    logging.info("Found form with CAPTCHA on main page")
                    
                    # Handle CAPTCHA on main page
                    main_page_captcha_image = await page.query_selector("img[src*='captcha']")
                    if main_page_captcha_image:
                        captcha_filename = f"main_captcha_{int(time.time())}.jpg"
                        captcha_path = os.path.join(CAPTCHA_DIR, captcha_filename)
                        
                        await main_page_captcha_image.screenshot(path=captcha_path)
                        logging.info(f"Saved main page CAPTCHA image to: {captcha_path}")
                        
                        captcha_input = await page.query_selector("input:near(img[src*='captcha'])")
                        if captcha_input:
                            captcha_text = await solve_captcha_with_gemini(captcha_path)
                            if captcha_text:
                                await type_like_human(captcha_input, captcha_text)
                                
                                confirm_button = await page.query_selector("input[value='Confirmar']")
                                if confirm_button:
                                    download_promise = page.wait_for_event("download", timeout=30000)
                                    await confirm_button.click()
                                    
                                    try:
                                        download = await download_promise
                                        filename = f"comprasnet_download_{int(time.time())}.pdf"
                                        try:
                                            suggested_filename = await download.suggested_filename()
                                            if suggested_filename:
                                                filename = suggested_filename
                                        except Exception as e:
                                            logging.warning(f"Could not get suggested filename: {e}")
                                        
                                        downloaded_path = os.path.join(DOWNLOAD_DIR, filename)
                                        await download.save_as(downloaded_path)
                                        
                                        if os.path.exists(downloaded_path) and os.path.getsize(downloaded_path) > 0:
                                            pdf_path = os.path.join(PDF_DIR, filename)
                                            shutil.copy2(downloaded_path, pdf_path)
                                            return True, downloaded_path
                                    except Exception as e:
                                        logging.error(f"Error downloading after main page CAPTCHA: {e}")
            
            return False, None

        # Handle CAPTCHA in popup
        success, file_path = await handle_captcha_with_retries(page, popup_page, max_retries=4)
        if success:
            return True, file_path

        logging.error("Failed to download after CAPTCHA handling")
        return False, None

    except Exception as e:
        logging.error(f"Error with Playwright for ComprasNet: {e}")
        logging.error(traceback.format_exc())
        return False, None
    finally:
        try:
            await teardown_playwright()
        except Exception as e:
            logging.error(f"Error during Playwright teardown: {e}")

async def process_alertalicitacao_comprasnet_url(url):
    """Process an AlertaLicitacao URL for ComprasNet to find the original URL."""
    logging.info(f"Processing AlertaLicitacao ComprasNet URL: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        cn_id_match = re.search(r'CN-(\d+)-(\d+)-(\d+)', url)
        if cn_id_match:
            uasg = cn_id_match.group(1)
            modality = cn_id_match.group(2)
            number = cn_id_match.group(3)
            logging.info(f"Extracted ComprasNet parameters from URL:")
            logging.info(f"UASG: {uasg}")
            logging.info(f"Modality: {modality}")
            logging.info(f"Number: {number}")
            
            comprasnet_url = f"http://comprasnet.gov.br/ConsultaLicitacoes/download/download_editais_detalhe.asp?coduasg={uasg}&modprp={modality}&numprp={number}"
            logging.info(f"Constructed ComprasNet URL: {comprasnet_url}")
            return comprasnet_url
        
        # Try to parse with BeautifulSoup if regex doesn't work
        soup = BeautifulSoup(response.text, 'html.parser')
        
        original_url_match = re.search(r'Visitar site original[^:]*: (https?://[^\s<>"\']+)', response.text)
        if original_url_match:
            original_url = original_url_match.group(1)
            logging.info(f"Found original document URL: {original_url}")
            return original_url
        
        site_original_links = soup.find_all('a', href=True, text=lambda text: text and 'site original' in text.lower())
        if site_original_links:
            original_url = site_original_links[0]['href']
            logging.info(f"Found original document URL from anchor: {original_url}")
            return original_url
        
        comprasnet_url_match = re.search(r'(https?://comprasnet\.gov\.br[^\s<>"\']+)', response.text)
        if comprasnet_url_match:
            comprasnet_url = comprasnet_url_match.group(1)
            logging.info(f"Found ComprasNet URL in page: {comprasnet_url}")
            return comprasnet_url

    except Exception as e:
        logging.error(f"Error processing AlertaLicitacao URL: {e}")
        logging.error(traceback.format_exc())
    
    logging.error("Could not find ComprasNet URL.")
    return None

async def main():
    """Main test function for ComprasNet URL."""
    setup_directories()

    comprasnet_url = await process_alertalicitacao_comprasnet_url(TARGET_URL)
    if not comprasnet_url:
        logging.error("Failed to extract ComprasNet URL. Test failed.")
        return 1

    if not GEMINI_API_KEY:
        logging.warning("GEMINI_API_KEY not set in environment. CAPTCHA solving will not work.")
        logging.warning("Please set GEMINI_API_KEY in the .env file to enable CAPTCHA solving.")

    success, file_path = await handle_comprasnet_download(comprasnet_url)
    if success:
        logging.info("✅ TEST PASSED: Successfully downloaded file from ComprasNet!")
        logging.info(f"File path: {file_path}")
        return 0
    else:
        logging.error("❌ TEST FAILED: Could not download file from ComprasNet")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        logging.error(traceback.format_exc())
        sys.exit(1) 