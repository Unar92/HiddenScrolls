import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

class GoogleMapsBusinessScraper:
    def __init__(self, headless=True):
        """Initialize the scraper with browser options."""
        self.options = Options()
        if headless:
            self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option("useAutomationExtension", False)
        
        # Initialize the driver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=self.options
        )
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 10)

    def search_businesses(self, query, location, max_results=20):
        """Search for businesses on Google Maps based on query and location."""
        try:
            # Format the search URL
            # Try this format instead
            search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}+near+{location.replace(' ', '+')}"
            self.driver.get(search_url)
            time.sleep(5)  # Let the page load
            
            self.wait = WebDriverWait(self.driver, 15)  # Increase from 10 to 15
            
            # Wait for results to load
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
            
            # Add this right after loading the page to see what's happening
            print(f"Page title: {self.driver.title}")
            print(f"Current URL: {self.driver.current_url}")
            
            # Add this after loading the page
            if "captcha" in self.driver.page_source.lower() or "unusual traffic" in self.driver.page_source.lower():
                print("Google is requesting verification. Please run in non-headless mode and manually solve the CAPTCHA.")
                return []
            
            businesses = []
            current_count = 0
            last_height = self.driver.execute_script("return document.body.scrollHeight")

            # Scroll to load more results
            while current_count < max_results:
                # Get all currently visible business listings
                business_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[role='article']")
                
                # Process only new results
                for element in business_elements[current_count:]:
                    if current_count >= max_results:
                        break
                    
                    try:
                        # Click to open the business details
                        element.click()
                        time.sleep(2)
                        
                        # Extract business info
                        business_data = self._extract_business_info()
                        if business_data:
                            businesses.append(business_data)
                            current_count += 1
                            print(f"Extracted data for: {business_data['name']} ({current_count}/{max_results})")
                        
                        # Go back to the list
                        self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Back']").click()
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"Error processing business: {e}")
                        continue
                
                # Scroll down to load more
                self.driver.execute_script("document.querySelector('div[role=\"feed\"]').scrollTop += 500")
                time.sleep(2)
                
                # Check if we've reached the end of the feed
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # Try clicking the "More results" button if available
                    try:
                        more_button = self.driver.find_element(By.CSS_SELECTOR, "button[jsaction='pane.paginationSection.nextPage']")
                        more_button.click()
                        time.sleep(2)
                    except NoSuchElementException:
                        print("No more results to load.")
                        break
                last_height = new_height
            
            return businesses
            
        except Exception as e:
            print(f"An error occurred during search: {e}")
            return []
    
    def _extract_business_info(self):
        """Extract business details from the details pane."""
        try:
            # Wait for the details pane to load
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.fontHeadlineSmall")))
            
            # Extract business name
            name_element = self.driver.find_element(By.CSS_SELECTOR, "div.fontHeadlineSmall")
            name = name_element.text if name_element else "N/A"
            
            # Initialize business data
            business_data = {
                "name": name,
                "address": "N/A",
                "phone": "N/A",
                "website": "N/A",
                "email": "N/A",
                "rating": "N/A",
                "reviews": "N/A",
                "category": "N/A"
            }
            
            # Extract other info
            info_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[role='button'][aria-label]")
            
            for element in info_elements:
                aria_label = element.get_attribute("aria-label") or ""
                
                if "Address" in aria_label:
                    business_data["address"] = element.text
                elif "Phone" in aria_label:
                    business_data["phone"] = element.text
                elif "Website" in aria_label:
                    # Click to go to website
                    element.click()
                    time.sleep(1)
                    
                    # Get the opened tab with the website
                    tabs = self.driver.window_handles
                    if len(tabs) > 1:
                        self.driver.switch_to.window(tabs[1])
                        business_data["website"] = self.driver.current_url
                        
                        # Try to extract email from the website
                        email = self._extract_email_from_website()
                        if email:
                            business_data["email"] = email
                        
                        # Close the website tab and switch back
                        self.driver.close()
                        self.driver.switch_to.window(tabs[0])
            
            # Extract rating and reviews if available
            try:
                rating_element = self.driver.find_element(By.CSS_SELECTOR, "div.fontBodyMedium span:first-child")
                rating_text = rating_element.text
                if rating_text:
                    parts = rating_text.split()
                    if len(parts) >= 1:
                        business_data["rating"] = parts[0]
                    if len(parts) >= 2 and parts[1].startswith('(') and parts[1].endswith(')'):
                        business_data["reviews"] = parts[1].strip('()')
            except NoSuchElementException:
                pass
            
            # Extract category
            try:
                category_element = self.driver.find_element(By.CSS_SELECTOR, "button[jsaction='pane.rating.category']")
                business_data["category"] = category_element.text
            except NoSuchElementException:
                pass
                
            return business_data
            
        except Exception as e:
            print(f"Error extracting business info: {e}")
            return None
    
    def _extract_email_from_website(self):
        """Extract email addresses from the current website."""
        try:
            # Get page source
            page_source = self.driver.page_source
            
            # Use regex to find email addresses
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, page_source)
            
            # Check for common contact page patterns and visit if found
            contact_links = self.driver.find_elements(By.XPATH, 
                "//a[contains(translate(text(), 'CONTACT', 'contact'), 'contact') or @href[contains(., 'contact')]]")
            
            if contact_links and len(contact_links) > 0:
                try:
                    contact_links[0].click()
                    time.sleep(2)
                    # Try to find emails on the contact page
                    contact_page_source = self.driver.page_source
                    contact_emails = re.findall(email_pattern, contact_page_source)
                    emails.extend(contact_emails)
                except:
                    pass
            
            # Return the first valid email or None
            valid_emails = [email for email in set(emails) 
                          if not email.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')) 
                          and 'example' not in email
                          and not email.startswith(('jquery', 'example', 'name@', 'info@example'))]
            
            return valid_emails[0] if valid_emails else None
            
        except Exception as e:
            print(f"Error extracting email: {e}")
            return None
    
    def save_to_csv(self, businesses, filename="business_leads.csv"):
        """Save the extracted business data to a CSV file."""
        if not businesses:
            print("No businesses to save.")
            return
        
        df = pd.DataFrame(businesses)
        df.to_csv(filename, index=False)
        print(f"Saved {len(businesses)} businesses to {filename}")
    
    def close(self):
        """Close the browser and end the session."""
        if self.driver:
            self.driver.quit()

def main():
    # Example usage
    scraper = GoogleMapsBusinessScraper(headless=False)  # Set to True for headless mode
    try:
        # Get user input
        search_query = input("Enter business type to search (e.g., plumber, dentist): ")
        location = input("Enter location (e.g., Portland, OR): ")
        max_results = int(input("Maximum number of businesses to scrape (default 20): ") or "20")
        
        print(f"Searching for {search_query} in {location}...")
        businesses = scraper.search_businesses(search_query, location, max_results)
        
        if businesses:
            filename = f"{search_query.replace(' ', '_')}_{location.replace(' ', '_')}.csv"
            scraper.save_to_csv(businesses, filename)
            
            # Display stats
            emails_found = sum(1 for b in businesses if b["email"] != "N/A")
            websites_found = sum(1 for b in businesses if b["website"] != "N/A")
            
            print(f"\nSummary:")
            print(f"Total businesses scraped: {len(businesses)}")
            print(f"Businesses with websites: {websites_found} ({(websites_found/len(businesses))*100:.1f}%)")
            print(f"Businesses with emails: {emails_found} ({(emails_found/len(businesses))*100:.1f}%)")
            print(f"Data saved to {filename}")
        else:
            print("No businesses found.")
    
    finally:
        scraper.close()

if __name__ == "__main__":
    main()