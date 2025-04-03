import requests
import argparse
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WebVulnScanner")

class WebVulnerabilityScanner:
    def __init__(self, target_url, threads=5, timeout=10):
        self.target_url = target_url
        self.threads = threads
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'VulnScanner/1.0 (Educational Purposes Only)'
        })
        self.visited_urls = set()
        self.forms = []
        self.vulnerabilities = []
    
    def run_scan(self):
        """Main method to run the vulnerability scan"""
        logger.info(f"Starting scan on {self.target_url}")
        
        # Verify target is accessible
        try:
            response = self.session.get(self.target_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Cannot access target: {e}")
            return False
        
        # Crawl the website to find all links and forms
        self.crawl(self.target_url)
        
        # Run vulnerability checks
        self.check_for_vulnerabilities()
        
        # Display results
        self.display_results()
        return True
    
    def crawl(self, url, depth=2):
        """Crawl the website to a certain depth"""
        if depth <= 0 or url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        logger.info(f"Crawling: {url}")
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            if 'text/html' not in response.headers.get('Content-Type', ''):
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links
            links = [urljoin(url, link.get('href')) for link in soup.find_all('a', href=True)]
            links = [link for link in links if self.is_same_domain(link)]
            
            # Find all forms
            for form in soup.find_all('form'):
                form_info = {
                    'action': urljoin(url, form.get('action', '')),
                    'method': form.get('method', 'get').lower(),
                    'inputs': []
                }
                
                for input_tag in form.find_all(['input', 'textarea']):
                    input_info = {
                        'name': input_tag.get('name', ''),
                        'type': input_tag.get('type', 'text'),
                        'value': input_tag.get('value', '')
                    }
                    form_info['inputs'].append(input_info)
                
                self.forms.append(form_info)
            
            # Crawl next level with thread pool
            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                executor.map(lambda link: self.crawl(link, depth - 1), links)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error crawling {url}: {e}")
    
    def is_same_domain(self, url):
        """Check if a URL belongs to the same domain as the target"""
        target_domain = urlparse(self.target_url).netloc
        url_domain = urlparse(url).netloc
        return url_domain == target_domain
    
    def check_for_vulnerabilities(self):
        """Run all vulnerability checks"""
        logger.info("Starting vulnerability checks")
        
        # Check for XSS in forms
        self.check_xss_vulnerability()
        
        # Check for SQL injection
        self.check_sql_injection()
        
        # Check for sensitive files
        self.check_sensitive_files()
        
        # Check for security headers
        self.check_security_headers()
    
    def check_xss_vulnerability(self):
        """Check for potential XSS vulnerabilities in forms"""
        logger.info("Checking for XSS vulnerabilities")
        
        # XSS test payloads (safe to use - these won't actually cause harm)
        xss_payloads = [
            '<script>alert("XSS_TEST")</script>',
            '"><script>alert("XSS_TEST")</script>',
            '<img src="x" onerror="alert(\'XSS_TEST\')">',
        ]
        
        for form in self.forms:
            for payload in xss_payloads:
                data = {}
                
                # Fill in the form with test data
                for input_field in form['inputs']:
                    if input_field['type'] not in ['submit', 'button', 'image', 'reset', 'file']:
                        data[input_field['name']] = payload
                
                try:
                    if form['method'] == 'post':
                        response = self.session.post(form['action'], data=data, timeout=self.timeout)
                    else:
                        response = self.session.get(form['action'], params=data, timeout=self.timeout)
                    
                    # Check if the payload is reflected in the response
                    if payload in response.text:
                        self.vulnerabilities.append({
                            'type': 'XSS',
                            'url': form['action'],
                            'method': form['method'],
                            'details': f"Potential XSS vulnerability found in form: {payload} was reflected"
                        })
                        break  # Move to next form once vulnerability is found
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error testing XSS on {form['action']}: {e}")
    
    def check_sql_injection(self):
        """Check for potential SQL injection vulnerabilities"""
        logger.info("Checking for SQL Injection vulnerabilities")
        
        # SQL injection test payloads (safe to use)
        sql_payloads = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "admin' --",
            "1' OR '1'='1"
        ]
        
        for form in self.forms:
            for payload in sql_payloads:
                data = {}
                
                # Fill in the form with test data
                for input_field in form['inputs']:
                    if input_field['type'] not in ['submit', 'button', 'image', 'reset', 'file']:
                        data[input_field['name']] = payload
                
                try:
                    if form['method'] == 'post':
                        response = self.session.post(form['action'], data=data, timeout=self.timeout)
                    else:
                        response = self.session.get(form['action'], params=data, timeout=self.timeout)
                    
                    # Look for SQL error messages
                    sql_errors = [
                        "SQL syntax",
                        "mysql_fetch",
                        "ORA-",
                        "MySQL server",
                        "You have an error in your SQL syntax"
                    ]
                    
                    for error in sql_errors:
                        if error in response.text:
                            self.vulnerabilities.append({
                                'type': 'SQL Injection',
                                'url': form['action'],
                                'method': form['method'],
                                'details': f"Potential SQL injection vulnerability found: '{error}' error message detected"
                            })
                            break  # Move to next form once vulnerability is found
                            
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error testing SQL injection on {form['action']}: {e}")
    
    def check_sensitive_files(self):
        """Check for sensitive files that might be accessible"""
        logger.info("Checking for sensitive files")
        
        sensitive_paths = [
            "/.git/config",
            "/.env",
            "/config.php",
            "/wp-config.php",
            "/phpinfo.php",
            "/robot.txt",
            "/.htaccess",
            "/server-status",
            "/backup/",
            "/admin/",
            "/logs/",
        ]
        
        base_url = f"{urlparse(self.target_url).scheme}://{urlparse(self.target_url).netloc}"
        
        for path in sensitive_paths:
            url = urljoin(base_url, path)
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    self.vulnerabilities.append({
                        'type': 'Sensitive File',
                        'url': url,
                        'method': 'GET',
                        'details': f"Potentially sensitive file accessible: {path} (Status Code: {response.status_code})"
                    })
            except requests.exceptions.RequestException:
                # If we can't access it, it's not vulnerable
                pass
    
    def check_security_headers(self):
        """Check for missing security headers"""
        logger.info("Checking security headers")
        
        important_headers = {
            'Strict-Transport-Security': 'Missing HSTS header',
            'Content-Security-Policy': 'Missing Content-Security-Policy header',
            'X-Frame-Options': 'Missing X-Frame-Options header (clickjacking protection)',
            'X-Content-Type-Options': 'Missing X-Content-Type-Options header',
            'X-XSS-Protection': 'Missing X-XSS-Protection header',
            'Referrer-Policy': 'Missing Referrer-Policy header'
        }
        
        try:
            response = self.session.get(self.target_url, timeout=self.timeout)
            
            for header, message in important_headers.items():
                if header not in response.headers:
                    self.vulnerabilities.append({
                        'type': 'Missing Security Header',
                        'url': self.target_url,
                        'method': 'GET',
                        'details': message
                    })
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking security headers: {e}")
    
    def display_results(self):
        """Display the vulnerability scan results"""
        print("\n" + "="*80)
        print(f"VULNERABILITY SCAN RESULTS FOR: {self.target_url}")
        print("="*80)
        
        if not self.vulnerabilities:
            print("\nNo vulnerabilities were detected. This doesn't guarantee the site is secure.")
        else:
            print(f"\nDetected {len(self.vulnerabilities)} potential vulnerabilities:\n")
            
            for i, vuln in enumerate(self.vulnerabilities, 1):
                print(f"{i}. {vuln['type']}")
                print(f"   URL: {vuln['url']}")
                print(f"   Method: {vuln['method']}")
                print(f"   Details: {vuln['details']}")
                print()
        
        print(f"Crawled {len(self.visited_urls)} URLs")
        print(f"Analyzed {len(self.forms)} forms")
        print("="*80)
        print("Note: This is a basic scan and may include false positives.")
        print("Always verify findings manually and only test websites you have permission to scan.")
        print("="*80)


def main():
    parser = argparse.ArgumentParser(description="Basic Web Vulnerability Scanner")
    parser.add_argument("url", help="Target URL to scan (e.g., http://example.com)")
    parser.add_argument("-t", "--threads", type=int, default=5, help="Number of threads for crawling (default: 5)")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)")
    
    args = parser.parse_args()
    
    scanner = WebVulnerabilityScanner(args.url, args.threads, args.timeout)
    scanner.run_scan()


if __name__ == "__main__":
    main()