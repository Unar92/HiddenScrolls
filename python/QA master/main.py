import os
import csv
import json
import re
from datetime import datetime
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

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
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    domain = urlparse(url).netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def create_folder_name(url):
    """Create a valid folder name from a URL."""
    domain = extract_domain(url)
    folder_name = re.sub(r'[\\/*?:"<>|]', "_", domain)
    return folder_name

def extract_email_address(page_source):
    """Extract email address from page source."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, page_source)
    return emails[0] if emails else "No email found"

def extract_physical_address(page_source):
    """Extract physical address from page source."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')
    address_candidates = []
    contact_sections = soup.find_all(['div', 'section', 'footer'], class_=lambda c: c and ('contact' in c.lower() or 'address' in c.lower()))
    for section in contact_sections:
        text = section.get_text(strip=True)
        if text and len(text) > 10 and len(text) < 200:
            address_candidates.append(text)
    address_elements = soup.find_all(['address'])
    for element in address_elements:
        text = element.get_text(strip=True)
        if text:
            address_candidates.append(text)
    return address_candidates[0] if address_candidates else "No address found"

def take_full_page_screenshot_with_playwright(url, save_path):
    """Capture a full-page screenshot using Playwright."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=save_path, full_page=True)
            print(f"Full-page screenshot saved to: {save_path}")
            page_source = page.content()
            browser.close()
            return page_source
    except Exception as e:
        print(f"Error taking full-page screenshot with Playwright: {e}")
        return None

def take_full_page_screenshot_with_playwright(url, save_path, mobile=False):
    """Capture a full-page screenshot using Playwright, with optional mobile emulation."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # Configure context for mobile or desktop
            if mobile:
                context = browser.new_context(
                    viewport={"width": 375, "height": 812},  # iPhone X dimensions
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
                )
            else:
                context = browser.new_context()

            page = context.new_page()

            # Navigate to the URL
            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle")

            # Scroll through the page to trigger animations or lazy loading
            page_height = page.evaluate("document.body.scrollHeight")
            viewport_height = page.viewport_size['height']
            current_scroll = 0

            while current_scroll < page_height:
                # Scroll to the current position
                page.evaluate(f"window.scrollTo(0, {current_scroll})")
                page.wait_for_timeout(500)  # Wait for animations or lazy-loaded content
                current_scroll += viewport_height

            # Take a full-page screenshot
            page.screenshot(path=save_path, full_page=True)
            print(f"Full-page screenshot saved to: {save_path}")

            # Get the page source for further processing
            page_source = page.content()
            browser.close()
            return page_source

    except Exception as e:
        print(f"Error taking full-page screenshot with Playwright: {e}")
        return None
  
def take_screenshot_and_save_data(url, output_dir="website_data", mobile=False):
    """Take a full-page screenshot of the given URL and save data to JSON."""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        print(f"Processing: {url} (Mobile: {mobile})")

        # Create folder for the website
        folder_name = create_folder_name(url)
        folder_path = os.path.join(output_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Screenshot path
        screenshot_type = "mobile" if mobile else "desktop"
        screenshot_path = os.path.join(folder_path, f"{folder_name}_{screenshot_type}.png")

        # Take full-page screenshot and get page source
        page_source = take_full_page_screenshot_with_playwright(url, screenshot_path, mobile=mobile)
        if not page_source:
            return False

        # Extract email and address
        email = extract_email_address(page_source)
        address = extract_physical_address(page_source)

        # Save data to JSON
        data = {
            "website": url,
            "email": email,
            "address": address,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "screenshot_type": screenshot_type
        }
        json_path = os.path.join(folder_path, f"{folder_name}_{screenshot_type}.json")
        with open(json_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        print(f"JSON data saved to: {json_path}")

        return True
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return False

def find_url_column(header, rows):
    """Find which column contains URLs by analyzing multiple rows."""
    if not rows:
        return 0
    if header:
        for i, name in enumerate(header):
            if name.lower() in ['url', 'link', 'website', 'site', 'web', 'domain']:
                return i
    url_counts = [0] * len(rows[0])
    for row in rows[:min(5, len(rows))]:
        for i, cell in enumerate(row):
            if cell and is_url(cell):
                url_counts[i] += 1
    if max(url_counts) > 0:
        return url_counts.index(max(url_counts))
    return 0

def process_csv(csv_file_path, output_dir="website_data"):
    """Process websites from a CSV file, processing ALL URLs found."""
    os.makedirs(output_dir, exist_ok=True)
    results = []
    try:
        all_rows = []
        header = None
        with open(csv_file_path, 'r', encoding='utf-8', errors='ignore') as csv_file:
            sample = csv_file.read(4096)
            csv_file.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample)
                has_header = csv.Sniffer().has_header(sample)
            except:
                dialect = csv.excel
                has_header = True
            csv_reader = csv.reader(csv_file, dialect)
            if has_header:
                header = next(csv_reader, None)
            for row in csv_reader:
                if row:
                    all_rows.append(row)
        url_column = find_url_column(header, all_rows)
        print(f"Found URL column at position {url_column}")
        if header:
            print(f"Column name: {header[url_column] if url_column < len(header) else 'Unknown'}")
        urls_processed = 0
        for row in all_rows:
            if row and len(row) > url_column:
                cell_content = row[url_column].strip()
                if is_url(cell_content):
                    print(f"\nProcessing URL #{urls_processed + 1}: {cell_content}")
                    # Process desktop screenshot
                    success_desktop = take_screenshot_and_save_data(cell_content, output_dir, mobile=False)
                    # Process mobile screenshot
                    success_mobile = take_screenshot_and_save_data(cell_content, output_dir, mobile=True)
                    results.append({
                        "url": cell_content,
                        "success_desktop": success_desktop,
                        "success_mobile": success_mobile
                    })
                    urls_processed += 1
                else:
                    print(f"Skipping non-URL content: {cell_content}")
        print(f"\nProcessed {urls_processed} URLs from the CSV file")
    except Exception as e:
        print(f"Error processing CSV file: {e}")
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