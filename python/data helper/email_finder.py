import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import csv
from urllib.parse import urljoin, urlparse

def clean_url(url):
    """Clean and validate URL"""
    # Remove leading/trailing whitespace
    url = url.strip()
    
    # Remove any trailing slashes or spaces
    url = url.rstrip('/')
    
    # Ensure URL has protocol
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Validate URL format
    try:
        result = urlparse(url)
        if all([result.scheme, result.netloc]):
            return url
        return None
    except:
        return None

def find_emails(url):
    """Function to find emails on a webpage"""
    try:
        # Clean URL first
        clean_url_str = clean_url(url)
        if not clean_url_str:
            return None
            
        # Send GET request to the URL
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(clean_url_str, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all text in the page
        text = soup.get_text()
        
        # Regular expression for email pattern
        email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
        emails = set(re.findall(email_pattern, text))
        
        # Also check mailto links
        for mailto in soup.find_all('a', href=True):
            if 'mailto:' in mailto['href']:
                email = mailto['href'].replace('mailto:', '')
                emails.add(email)
                
        return emails if emails else None
    
    except (requests.RequestException, Exception) as e:
        print(f"Error processing {url}: {str(e)}")
        return None

def process_csv(input_file, output_file):
    """Process CSV file and find emails"""
    try:
        df = pd.read_csv(input_file)
        
        if 'url' not in df.columns:
            raise ValueError("CSV file must contain a 'url' column")
            
        results = []
        
        for index, row in df.iterrows():
            url = str(row['url'])  # Convert to string in case of numeric values
            print(f"Processing: {url}")
            
            emails = find_emails(url)
            
            result = {
                'url': url,
                'emails': '; '.join(emails) if emails else 'No emails found'
            }
            results.append(result)
            
            print(f"Found emails: {result['emails']}")
        
        # Write results to new CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['url', 'emails'])
            writer.writeheader()
            writer.writerows(results)
            
        print(f"\nResults saved to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    input_csv = 'links.csv'
    output_csv = 'email_results.csv'
    
    print("Starting email finder...")
    process_csv(input_csv, output_csv)

if __name__ == "__main__":
    main()