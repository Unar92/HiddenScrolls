import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import random
import os
from urllib.parse import urljoin

class FreelanceLeadScraper:
    def __init__(self, user_agent=None):
        """Initialize the scraper with customizable headers."""
        self.session = requests.Session()
        self.headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.session.headers.update(self.headers)
        self.results = []
        
    def search_direct_urls(self, industry, location=None):
        """Use a list of direct URLs instead of relying on Google search."""
        print(f"Searching for {industry} businesses in {location if location else 'all locations'}")
        
        # Industry-specific websites to target
        if industry.lower() in ['tech', 'software', 'technology', 'development']:
            urls = [
                "https://www.builtinnyc.com/companies",
                "https://www.crunchbase.com/hub/new-york-startups",
                "https://www.ycombinator.com/companies",
                "https://angel.co/location/new-york"
            ]
        elif industry.lower() in ['marketing', 'digital marketing', 'advertising']:
            urls = [
                "https://clutch.co/agencies/digital-marketing",
                "https://www.digitalagencynetwork.com/agencies/new-york/",
                "https://agency.webfx.com/digital-marketing-agency-new-york-ny"
            ]
        else:
            # Default list for any industry
            urls = [
                "https://www.chamber-of-commerce.com/",
                "https://www.yelp.com/search?find_desc=" + industry.replace(' ', '+'),
                "https://www.linkedin.com/company-beta/"
            ]
            
        leads = []
        for url in urls:
            try:
                print(f"Trying to scrape directory: {url}")
                lead = {
                    'title': f"{industry} leads from {url.split('/')[2]}",
                    'url': url
                }
                leads.append(lead)
            except Exception as e:
                print(f"Error adding directory {url}: {e}")
                
        return leads
        
    def scrape_linkedin_companies(self, industry, location=None):
        """Scrape LinkedIn for company details - note this is a simplified version."""
        print("LinkedIn scraping would require selenium and login credentials.")
        print("This is a placeholder for that functionality.")
        return []
    
    def scan_business_directories(self, industry, location=None):
        """Use business directories to find leads."""
        business_directories = [
            "https://www.chamberofcommerce.com/",
            "https://www.yellowpages.com/",
            "https://www.yelp.com/",
            "https://www.manta.com/"
        ]
        
        leads = []
        for directory in business_directories:
            try:
                search_term = f"{industry} {location}" if location else industry
                search_url = f"{directory}search?q={search_term.replace(' ', '+')}"
                print(f"Would search: {search_url}")
                
                # In a full implementation, we'd scrape the directory here
                # This is simplified for demonstration
                lead = {
                    'title': f"{industry} leads from {directory.split('/')[2]}",
                    'url': search_url
                }
                leads.append(lead)
            except Exception as e:
                print(f"Error searching directory {directory}: {e}")
                
        return leads
    
    def scrape_website(self, url):
        """Scrape a website for contact information."""
        contact_info = {
            'url': url,
            'email': None,
            'phone': None,
            'contact_page': None
        }
        
        try:
            print(f"Attempting to access: {url}")
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                print(f"Successfully accessed {url}")
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract email addresses
                emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', response.text)
                if emails:
                    contact_info['email'] = emails[0]  # Take the first email found
                    print(f"Found email: {contact_info['email']}")
                
                # Extract phone numbers
                phone_pattern = re.compile(r'(\+\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')
                phones = phone_pattern.findall(response.text)
                if phones:
                    contact_info['phone'] = ''.join(phones[0]).strip()
                    print(f"Found phone: {contact_info['phone']}")
                
                # Find contact page
                contact_links = soup.find_all('a', string=re.compile(r'contact', re.I))
                if not contact_links:
                    contact_links = soup.find_all('a', href=re.compile(r'contact', re.I))
                
                if contact_links:
                    contact_href = contact_links[0].get('href')
                    if contact_href:
                        contact_info['contact_page'] = urljoin(url, contact_href)
                        print(f"Found contact page: {contact_info['contact_page']}")
                
                # If a contact page was found, scrape it as well
                if contact_info['contact_page'] and contact_info['contact_page'] != url:
                    try:
                        contact_response = self.session.get(contact_info['contact_page'], timeout=15)
                        if contact_response.status_code == 200:
                            print(f"Successfully accessed contact page: {contact_info['contact_page']}")
                            # Look for emails on the contact page
                            contact_emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', contact_response.text)
                            if contact_emails and not contact_info['email']:
                                contact_info['email'] = contact_emails[0]
                                print(f"Found email on contact page: {contact_info['email']}")
                            
                            # Look for phone numbers on the contact page
                            contact_phones = phone_pattern.findall(contact_response.text)
                            if contact_phones and not contact_info['phone']:
                                contact_info['phone'] = ''.join(contact_phones[0]).strip()
                                print(f"Found phone on contact page: {contact_info['phone']}")
                    except Exception as e:
                        print(f"Error scraping contact page: {e}")
            else:
                print(f"Failed to access {url} - Status code: {response.status_code}")
                
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        
        return contact_info
    
    def find_leads(self, industry, location=None):
        """Find leads based on industry and location."""
        all_leads = []
        
        # Get leads from multiple sources
        directory_leads = self.scan_business_directories(industry, location)
        direct_leads = self.search_direct_urls(industry, location)
        
        # Combine all lead sources
        leads = directory_leads + direct_leads
        
        for lead in leads:
            print(f"Processing lead: {lead['title']} - {lead['url']}")
            contact_info = self.scrape_website(lead['url'])
            
            lead_info = {
                'title': lead['title'],
                'url': lead['url'],
                'email': contact_info['email'],
                'phone': contact_info['phone'],
                'contact_page': contact_info['contact_page'],
                'industry': industry,
                'location': location
            }
            
            all_leads.append(lead_info)
            # Be respectful with rate limiting
            time.sleep(random.uniform(2, 5))
        
        self.results = all_leads
        return all_leads
    
    def save_to_csv(self, filename='freelance_leads.csv'):
        """Save the results to a CSV file."""
        if self.results:
            df = pd.DataFrame(self.results)
            df.to_csv(filename, index=False)
            print(f"Saved {len(self.results)} leads to {filename}")
            
            # Show the first few results
            print("\nFirst few leads:")
            print(df.head().to_string())
        else:
            print("No leads to save. Creating empty CSV file for structure.")
            # Create empty DataFrame with the right columns
            columns = ['title', 'url', 'email', 'phone', 'contact_page', 'industry', 'location']
            df = pd.DataFrame(columns=columns)
            df.to_csv(filename, index=False)
            print(f"Created empty leads file: {filename}")

# Example usage
if __name__ == "__main__":
    try:
        scraper = FreelanceLeadScraper()
        
        # Define your industry focus
        industry = input("Enter your industry focus (e.g., web development, data analysis): ") or "web development"
        
        # Add your location to target local businesses
        location = input("Enter your target location (e.g., New York, Chicago): ") or "New York"
        
        # Find leads
        print(f"Starting lead generation for {industry} in {location}...")
        leads = scraper.find_leads(industry, location)
        
        # Save results
        scraper.save_to_csv()
        
        print("\n===== LEAD GENERATION COMPLETE =====")
        print(f"Total leads found: {len(scraper.results)}")
        print("Check freelance_leads.csv for the full results.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()