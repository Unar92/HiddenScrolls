import os
import csv
import json
import re
import time
import urllib.parse
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import io


import re

def is_url(text):
    """Check if the given text is a valid URL."""
    url_pattern = re.compile(
        r'^(https?:\/\/)?'  # http:// or https:// (optional)
        r'(([a-zA-Z\d]([a-zA-Z\d-]*[a-zA-Z\d])*)\.)+[a-zA-Z]{2,}'  # domain
        r'|((\d{1,3}\.){3}\d{1,3})'  # OR IP address
        r'(\:\d+)?(\/[-a-zA-Z\d%_.~+]*)*'  # port and path
        r'(\?[;&a-zA-Z\d%_.~+=-]*)?'  # query string
        r'(\#[-a-zA-Z\d_]*)?$',  # fragment
        re.IGNORECASE
    )
    return bool(url_pattern.match(text))


def extract_domain(url):
    """Extract domain name from URL."""
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    # Parse the URL and extract the domain
    domain = urlparse(url).netloc
    
    # Remove www. if present
    if domain.startswith('www.'):
        domain = domain[4:]
        
    return domain


def create_folder_name(url):
    """Create a valid folder name from a URL."""
    domain = extract_domain(url)
    # Replace invalid characters with underscores
    folder_name = re.sub(r'[\\/*?:"<>|]', "_", domain)
    return folder_name


def extract_email_address(page_source):
    """Extract email address from page source."""
    # Simple regex pattern to find email addresses
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, page_source)
    return emails[0] if emails else "No email found"


def extract_physical_address(page_source):
    """Extract physical address from page source."""
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # Look for common address containers
    address_candidates = []
    
    # Check for address in contact page sections
    contact_sections = soup.find_all(['div', 'section', 'footer'], class_=lambda c: c and ('contact' in c.lower() or 'address' in c.lower()))
    for section in contact_sections:
        text = section.get_text(strip=True)
        if text and len(text) > 10 and len(text) < 200:  # Reasonable address length
            address_candidates.append(text)
    
    # Look for address in structured data
    address_elements = soup.find_all(['address'])
    for element in address_elements:
        text = element.get_text(strip=True)
        if text:
            address_candidates.append(text)
    
    return address_candidates[0] if address_candidates else "No address found"


from PIL import Image

def take_full_page_screenshot(driver, save_path):
    """
    Capture a full-page screenshot by scrolling through the page and stitching viewports together.
    """
    try:
        # Get the total height of the page
        total_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        driver_width = driver.execute_script("return window.innerWidth")

        # Set the browser window size to match the viewport width and height
        driver.set_window_size(driver_width, viewport_height)

        # Create a blank image to stitch screenshots
        stitched_image = Image.new('RGB', (driver_width, total_height))

        # Scroll through the page and capture screenshots
        current_scroll = 0
        while current_scroll < total_height:
            # Scroll to the current position
            driver.execute_script(f"window.scrollTo(0, {current_scroll})")
            time.sleep(0.5)  # Allow time for animations or dynamic content to load

            # Capture the current viewport screenshot
            screenshot = driver.get_screenshot_as_png()
            screenshot_image = Image.open(io.BytesIO(screenshot))

            # Paste the screenshot into the stitched image
            stitched_image.paste(screenshot_image, (0, current_scroll))

            # Move to the next scroll position
            current_scroll += viewport_height

        # Save the stitched image
        stitched_image.save(save_path)
        print(f"Full-page screenshot saved to: {save_path}")

    except Exception as e:
        print(f"Error taking full-page screenshot: {e}")

def handle_captcha(driver):
    """
    Detect and handle CAPTCHA by pausing for manual intervention.
    """
    try:
        # Check for common CAPTCHA indicators (e.g., iframe or specific elements)
        captcha_present = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'captcha')]") or \
                          driver.find_elements(By.XPATH, "//*[contains(text(), 'CAPTCHA')]")
        if captcha_present:
            print("CAPTCHA detected. Please solve it manually in the browser.")
            input("Press Enter after solving the CAPTCHA to continue...")
    except Exception as e:
        print(f"Error detecting CAPTCHA: {e}")
        
        
def set_correct_width(driver):
    """
    Adjust the browser width to match the page's content width.
    """
    try:
        required_width = driver.execute_script("return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth)")
        driver.set_window_size(required_width, driver.execute_script("return window.innerHeight"))
        print(f"Browser width adjusted to: {required_width}")
    except Exception as e:
        print(f"Error adjusting browser width: {e}")

def take_screenshot_and_save_data(url, output_dir="website_data"):
    """
    Take a full page screenshot of the given URL and save data to JSON.
    """
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")  # Start with large window
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    
    # Initialize the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        print(f"Processing: {url}")
        
        # Set page load timeout to 30 seconds
        driver.set_page_load_timeout(30)
        
        # Load the page
        driver.get(url)
        
        # Wait for the page to load completely
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)  # Additional wait for dynamic content
        
        # Handle CAPTCHA if present
        handle_captcha(driver)
        
        # Adjust browser width to match page content
        set_correct_width(driver)
        
        # Create folder name based on the domain
        folder_name = create_folder_name(url)
        folder_path = os.path.join(output_dir, folder_name)
        
        # Create folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        # Take full page screenshot and save
        screenshot_path = os.path.join(folder_path, f"{folder_name}.png")
        take_full_page_screenshot(driver, screenshot_path)
        print(f"Full page screenshot saved to: {screenshot_path}")
        
        # Get page source for data extraction
        page_source = driver.page_source
        
        # Extract data
        email = extract_email_address(page_source)
        address = extract_physical_address(page_source)
        
        # Create JSON data
        data = {
            "website": url,
            "email": email,
            "address": address,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save JSON file
        json_path = os.path.join(folder_path, f"{folder_name}.json")
        with open(json_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        print(f"JSON data saved to: {json_path}")
        
        return True
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return False
    finally:
        driver.quit()
def find_url_column(header, rows):
    """Find which column contains URLs by analyzing multiple rows."""
    if not rows:
        return 0
        
    # First check header for common URL column names
    if header:
        for i, name in enumerate(header):
            if name.lower() in ['url', 'link', 'website', 'site', 'web', 'domain']:
                return i
    
    # Count URL-like entries in each column
    url_counts = [0] * len(rows[0])
    
    # Check first 5 rows (or fewer if not available)
    for row in rows[:min(5, len(rows))]:
        for i, cell in enumerate(row):
            if cell and is_url(cell):
                url_counts[i] += 1
    
    # Find column with most URLs
    if max(url_counts) > 0:
        return url_counts.index(max(url_counts))
    
    # Default to first column if no URLs found
    return 0


def process_csv(csv_file_path, output_dir="website_data"):
    """
    Process websites from a CSV file, processing ALL URLs found.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # List to store results
    results = []
    
    try:
        # Read the entire CSV file into memory first to analyze
        all_rows = []
        header = None
        
        with open(csv_file_path, 'r', encoding='utf-8', errors='ignore') as csv_file:
            # Try to detect the CSV format
            sample = csv_file.read(4096)
            csv_file.seek(0)
            
            try:
                dialect = csv.Sniffer().sniff(sample)
                has_header = csv.Sniffer().has_header(sample)
            except:
                # If detection fails, use default CSV format
                dialect = csv.excel
                has_header = True
            
            csv_reader = csv.reader(csv_file, dialect)
            
            # Get header if present
            if has_header:
                header = next(csv_reader, None)
            
            # Read all rows
            for row in csv_reader:
                if row:  # Skip empty rows
                    all_rows.append(row)
        
        # Find URL column by analyzing multiple rows
        url_column = find_url_column(header, all_rows)
        
        print(f"Found URL column at position {url_column}")
        if header:
            print(f"Column name: {header[url_column] if url_column < len(header) else 'Unknown'}")
        
        # Process each URL
        urls_processed = 0
        for row in all_rows:
            if row and len(row) > url_column:
                cell_content = row[url_column].strip()
                
                # Process if it's a URL
                if is_url(cell_content):
                    print(f"\nProcessing URL #{urls_processed + 1}: {cell_content}")
                    success = take_screenshot_and_save_data(cell_content, output_dir)
                    results.append({
                        "url": cell_content,
                        "success": success
                    })
                    urls_processed += 1
                else:
                    print(f"Skipping non-URL content: {cell_content}")
        
        print(f"\nProcessed {urls_processed} URLs from the CSV file")
    
    except Exception as e:
        print(f"Error processing CSV file: {e}")
    
    # Save summary of results
    summary_path = os.path.join(output_dir, "processing_summary.json")
    with open(summary_path, 'w') as summary_file:
        json.dump(results, summary_file, indent=4)
    
    print(f"Processing complete. Summary saved to: {summary_path}")

if __name__ == "__main__":
    csv_file_path = input("Enter the path to your CSV file: ")
    output_directory = input("Enter the output directory (press Enter for default 'website_data'): ")
    
    if not output_directory:
        output_directory = "website_data"
    
    process_csv(csv_file_path, output_directory)