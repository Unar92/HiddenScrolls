import time
import random
import re
import os
import pandas as pd
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

class SeleniumLeadScraper:
    def __init__(self, headless=True):
        """Initialize the Selenium-based scraper."""
        print("Setting up Selenium WebDriver...")
        
        # Setup Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Initialize the Chrome driver
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("WebDriver set up successfully!")
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            raise
        
        self.results = []
        
    def __del__(self):
        """Close the browser when the object is destroyed."""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                print("WebDriver closed.")
        except:
            pass
    
    def search_google(self, query, num_pages=3):
        """Search Google using Selenium."""
        leads = []
        
        try:
            print(f"Searching Google for: '{query}'")
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            self.driver.get(search_url)
            
            # Wait for search results to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
            )
            
            # Accept cookies if the dialog appears
            try:
                cookie_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept all')]"))
                )
                cookie_button.click()
                print("Accepted cookies.")
            except:
                print("No cookie dialog found or already accepted.")
            
            # Process multiple pages
            for page in range(num_pages):
                if page > 0:
                    try:
                        # Click on "Next" button to go to the next page
                        next_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.ID, "pnnext"))
                        )
                        next_button.click()
                        
                        # Wait for the new page to load
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
                        )
                    except Exception as e:
                        print(f"Could not navigate to next page: {e}")
                        break
                
                # Extract search results
                try:
                    search_results = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
                    print(f"Found {len(search_results)} results on page {page+1}")
                    
                    for result in search_results:
                        try:
                            link_element = result.find_element(By.CSS_SELECTOR, "a")
                            url = link_element.get_attribute("href")
                            
                            title_element = result.find_element(By.CSS_SELECTOR, "h3")
                            title = title_element.text if title_element else "No title"
                            
                            if url and not url.startswith("https://www.google.com"):
                                leads.append({
                                    'title': title,
                                    'url': url
                                })
                                print(f"Added lead: {title}")
                        except Exception as e:
                            print(f"Error extracting result details: {e}")
                    
                except Exception as e:
                    print(f"Error processing search results: {e}")
                
                # Be respectful with rate limiting
                time.sleep(random.uniform(2, 5))
                
        except Exception as e:
            print(f"Error in Google search: {e}")
        
        print(f"Total leads found from Google search: {len(leads)}")
        return leads
    
    def search_linkedin(self, search_term, location=None):
        """
        Search LinkedIn for companies (simplified version).
        Note: Full LinkedIn scraping would require login credentials.
        """
        leads = []
        
        try:
            query = f"{search_term} {location}" if location else search_term
            url = f"https://www.linkedin.com/search/results/companies/?keywords={query.replace(' ', '%20')}"
            print(f"Searching LinkedIn: {url}")
            
            self.driver.get(url)
            
            # Wait for search results to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "entity-result__title"))
                )
                
                # Extract company results
                company_elements = self.driver.find_elements(By.CSS_SELECTOR, ".entity-result__item")
                print(f"Found {len(company_elements)} companies on LinkedIn")
                
                for company in company_elements:
                    try:
                        title_element = company.find_element(By.CSS_SELECTOR, ".entity-result__title-text a")
                        company_name = title_element.text.strip()
                        company_url = title_element.get_attribute("href")
                        
                        leads.append({
                            'title': company_name,
                            'url': company_url
                        })
                    except:
                        continue
                        
            except TimeoutException:
                print("LinkedIn search results didn't load as expected. LinkedIn might require login.")
        
        except Exception as e:
            print(f"Error searching LinkedIn: {e}")
        
        return leads
    
    def search_yelp(self, category, location):
        """Search Yelp for local businesses."""
        leads = []
        
        try:
            query = f"{category} {location}".replace(' ', '+')
            url = f"https://www.yelp.com/search?find_desc={query}"
            print(f"Searching Yelp: {url}")
            
            self.driver.get(url)
            
            # Wait for search results to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".css-1qn0b6x"))
            )
            
            # Extract business results
            business_elements = self.driver.find_elements(By.CSS_SELECTOR, ".css-1qn0b6x")
            print(f"Found {len(business_elements)} businesses on Yelp")
            
            for business in business_elements:
                try:
                    name_element = business.find_element(By.CSS_SELECTOR, "a[name]")
                    business_name = name_element.text.strip()
                    business_url = name_element.get_attribute("href")
                    
                    leads.append({
                        'title': business_name,
                        'url': business_url
                    })
                except:
                    continue
                    
        except Exception as e:
            print(f"Error searching Yelp: {e}")
        
        return leads
    
    def scrape_website(self, url):
        """Scrape a website for contact information using Selenium."""
        contact_info = {
            'url': url,
            'email': None,
            'phone': None,
            'contact_page': None
        }
        
        try:
            print(f"Accessing: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Get the page source after JavaScript renders
            page_source = self.driver.page_source
            
            # Extract email addresses
            emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', page_source)
            if emails:
                # Filter out common false positives
                valid_emails = [email for email in emails if not (
                    'example' in email or 
                    'youremail' in email or 
                    'domain.com' in email
                )]
                if valid_emails:
                    contact_info['email'] = valid_emails[0]
                    print(f"Found email: {contact_info['email']}")
            
            # Extract phone numbers
            phone_pattern = re.compile(r'(\+\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')
            phones = phone_pattern.findall(page_source)
            if phones:
                contact_info['phone'] = ''.join(phones[0]).strip()
                print(f"Found phone: {contact_info['phone']}")
            
            # Find contact page
            try:
                contact_links = self.driver.find_elements(By.XPATH, "//a[contains(translate(text(), 'CONTACT', 'contact'), 'contact') or contains(@href, 'contact')]")
                
                if contact_links:
                    contact_href = contact_links[0].get_attribute("href")
                    if contact_href:
                        contact_info['contact_page'] = contact_href
                        print(f"Found contact page: {contact_info['contact_page']}")
                        
                        # Visit the contact page
                        if contact_info['contact_page'] != url:
                            print(f"Visiting contact page: {contact_info['contact_page']}")
                            self.driver.get(contact_info['contact_page'])
                            time.sleep(3)
                            
                            # Extract additional info from contact page
                            contact_page_source = self.driver.page_source
                            
                            # Look for emails on the contact page
                            contact_emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', contact_page_source)
                            valid_contact_emails = [email for email in contact_emails if not (
                                'example' in email or 
                                'youremail' in email or 
                                'domain.com' in email
                            )]
                            if valid_contact_emails and not contact_info['email']:
                                contact_info['email'] = valid_contact_emails[0]
                                print(f"Found email on contact page: {contact_info['email']}")
                            
                            # Look for phone numbers on the contact page
                            contact_phones = phone_pattern.findall(contact_page_source)
                            if contact_phones and not contact_info['phone']:
                                contact_info['phone'] = ''.join(contact_phones[0]).strip()
                                print(f"Found phone on contact page: {contact_info['phone']}")
            
            except Exception as e:
                print(f"Error looking for contact page: {e}")
                
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        
        return contact_info
    
    def find_leads(self, search_terms, location=None):
        """Find leads using multiple search methods."""
        all_leads = []
        
        for term in search_terms:
            # Combine search term with location if provided
            if location:
                formatted_term = f"{term} in {location}"
            else:
                formatted_term = term
                
            print(f"\n--- Searching for: {formatted_term} ---")
            
            # Get leads from Google
            google_leads = self.search_google(formatted_term)
            
            # Get leads from LinkedIn
            linkedin_leads = self.search_linkedin(term, location)
            
            # Get leads from Yelp if location is provided
            yelp_leads = self.search_yelp(term, location) if location else []
            
            # Combine all lead sources
            combined_leads = google_leads + linkedin_leads + yelp_leads
            
            # Create a set to track URLs we've seen
            processed_urls = set()
            
            # Process each lead
            for lead in combined_leads:
                if lead['url'] in processed_urls:
                    continue  # Skip duplicate URLs
                    
                processed_urls.add(lead['url'])
                
                print(f"\nProcessing lead: {lead['title']}")
                contact_info = self.scrape_website(lead['url'])
                
                lead_info = {
                    'title': lead['title'],
                    'url': lead['url'],
                    'email': contact_info['email'],
                    'phone': contact_info['phone'],
                    'contact_page': contact_info['contact_page'],
                    'search_term': term,
                    'location': location
                }
                
                all_leads.append(lead_info)
                print(f"Added lead with {'contact info' if lead_info['email'] or lead_info['phone'] else 'no contact info'}")
                
                # Be respectful with rate limiting
                time.sleep(random.uniform(1, 3))
        
        self.results = all_leads
        return all_leads
    
    def save_to_csv(self, filename='selenium_leads.csv'):
        """Save the results to a CSV file."""
        if self.results:
            df = pd.DataFrame(self.results)
            
            # Filter out leads with no contact information
            leads_with_contact = df[(df['email'].notna()) | (df['phone'].notna())]
            leads_without_contact = df[(df['email'].isna()) & (df['phone'].isna())]
            
            # Save all leads
            df.to_csv(filename, index=False)
            print(f"\nSaved {len(self.results)} total leads to {filename}")
            
            # Save leads with contact info to a separate file
            if not leads_with_contact.empty:
                contact_filename = filename.replace('.csv', '_with_contact.csv')
                leads_with_contact.to_csv(contact_filename, index=False)
                print(f"Saved {len(leads_with_contact)} leads with contact info to {contact_filename}")
            
            # Show summary
            print("\n----- LEAD GENERATION SUMMARY -----")
            print(f"Total leads found: {len(self.results)}")
            print(f"Leads with contact info: {len(leads_with_contact)}")
            print(f"Leads without contact info: {len(leads_without_contact)}")
            
            # Show the first few results with contact info
            if not leads_with_contact.empty:
                print("\nSample leads with contact info:")
                print(leads_with_contact[['title', 'email', 'phone']].head().to_string())
        else:
            print("No leads found.")
            # Create empty CSV file with headers
            columns = ['title', 'url', 'email', 'phone', 'contact_page', 'search_term', 'location']
            pd.DataFrame(columns=columns).to_csv(filename, index=False)
            print(f"Created empty leads file: {filename}")

# Example usage
if __name__ == "__main__":
    try:
        # Ask if user wants to run in headless mode
        headless = input("Run in headless mode? (y/n, default: y): ").lower() != 'n'
        
        # Initialize the scraper
        scraper = SeleniumLeadScraper(headless=headless)
        
        # Get user input
        print("\n--- FREELANCE LEAD GENERATOR ---")
        print("Enter your search terms separated by commas (related to your skills or target clients)")
        search_input = input("Search terms (default: 'web development, custom software'): ")
        search_terms = [term.strip() for term in (search_input or "web development, custom software").split(',')]
        
        location = input("Target location (e.g., New York, Los Angeles, leave blank for no location filter): ")
        
        # Limit the number of search terms for demonstration
        if len(search_terms) > 5:
            print("Limiting to first 5 search terms to avoid long processing time")
            search_terms = search_terms[:5]
        
        # Find leads
        print(f"\nStarting lead generation for {len(search_terms)} search terms...")
        leads = scraper.find_leads(search_terms, location)
        
        # Save results
        scraper.save_to_csv()
        
        print("\n===== LEAD GENERATION COMPLETE =====")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Make sure we clean up the WebDriver
        if 'scraper' in locals():
            del scraper