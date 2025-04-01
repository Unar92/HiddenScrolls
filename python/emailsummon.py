import time
import random
import csv
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
os.system('chcp 65001')  # Set console to UTF-8
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='linkedin_email_retrieval.log',
    encoding='utf-8'  # Add this parameter
)

class LinkedInEmailRetriever:
    def __init__(self, username, password, max_daily_contacts=50):
        self.username = username
        self.password = password
        self.max_daily_contacts = max_daily_contacts
        self.driver = None
        self.retrieved_today = 0
        self.start_date = datetime.now().date()
        
        # Track processed contacts to avoid duplicates
        self.processed_contacts = set()
        self.load_processed_contacts()
        
    def load_processed_contacts(self):
        """Load previously processed contacts from CSV file"""
        encodings = ['utf-8', 'latin-1', 'cp1252']  # Try these encodings in order
        
        for encoding in encodings:
            try:
                self.processed_contacts = set()  # Reset the set
                with open('processed_contacts.csv', 'r', encoding=encoding) as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row:  # Skip empty rows
                            self.processed_contacts.add(row[0])  # LinkedIn profile ID
                logging.info(f"Loaded {len(self.processed_contacts)} previously processed contacts using {encoding} encoding")
                return  # Successfully loaded, exit the method
            except FileNotFoundError:
                logging.info("No previous contacts file found, starting fresh")
                return  # No file exists, exit the method
            except UnicodeDecodeError:
                continue  # Try the next encoding
    
        # If we get here, none of the encodings worked
        logging.warning("Could not decode the existing contacts file with any encoding. Creating a backup and starting fresh.")
        import shutil
        try:
            shutil.copy('processed_contacts.csv', 'processed_contacts_backup.csv')
        except:
            pass
        # Create a new empty file
        with open('processed_contacts.csv', 'w', encoding='utf-8') as f:
            pass
    
    def save_processed_contact(self, profile_id, name, email):
        """Save processed contact to CSV file"""
        with open('processed_contacts.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([profile_id, name, email, datetime.now().isoformat()])
        
        # Also append to results file
        with open('contact_emails.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([name, email, datetime.now().isoformat()])
            
        self.processed_contacts.add(profile_id)
    
    def login(self):
        """Log in to LinkedIn"""
        # Add these lines at the beginning of the login method
        options = webdriver.ChromeOptions()
        options.add_argument('--log-level=3')  # Set to ERROR level only
        options.add_argument('--disable-gpu')  # Disable GPU acceleration
        options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Disable logging
        
        # Replace this line
        # self.driver = webdriver.Chrome()  # Or webdriver.Firefox()
        
        # With this line
        self.driver = webdriver.Chrome(options=options)
        
        self.driver.get("https://www.linkedin.com/login")
        
        try:
            # Enter username
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_field.send_keys(self.username)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(self.password)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for login to complete
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "global-nav"))
            )
            logging.info("Successfully logged in to LinkedIn")
            return True
            
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Login failed: {str(e)}")
            return False
    
    def get_contact_list(self, page=1, limit=50):
        """Get a list of LinkedIn contacts"""
        self.driver.get(f"https://www.linkedin.com/mynetwork/invite-connect/connections/?page={page}")
        
        try:
            # Wait for contacts to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "mn-connection-card"))
            )
            
            # Get all contact cards
            contact_cards = self.driver.find_elements(By.CLASS_NAME, "mn-connection-card")
            logging.info(f"Found {len(contact_cards)} contacts on page {page}")
            
            contacts = []
            for card in contact_cards[:limit]:
                try:
                    name = card.find_element(By.CLASS_NAME, "mn-connection-card__name").text
                    profile_link = card.find_element(By.CLASS_NAME, "mn-connection-card__link").get_attribute("href")
                    profile_id = profile_link.split("/in/")[1].split("/")[0]
                    
                    if profile_id not in self.processed_contacts:
                        contacts.append({
                            "name": name,
                            "profile_link": profile_link,
                            "profile_id": profile_id
                        })
                except Exception as e:
                    logging.warning(f"Could not process a contact card: {str(e)}")
            
            return contacts
            
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Failed to get contact list: {str(e)}")
            return []
    
   
    def extract_email_from_profile(self, profile_link):
        """Visit profile and extract email if available"""
        try:
            self.driver.get(profile_link)
            time.sleep(random.uniform(2, 4))  # Random wait to appear more human-like
            
            # Look for the Contact Info section - different selectors to try
            contact_info_selectors = [
                "//a[contains(@href, 'detail/contact-info')]",
                "//a[contains(@id, 'contact-info')]",
                "//button[contains(text(), 'Contact info')]",
                "//span[text()='Contact info']/parent::*",
                "//div[contains(@class, 'pv-contact-info')]",
                "//button[@id='top-card-text-details-contact-info']"  # Added selector for the button with the specific ID
            ]
            
            # Try each selector until one works
            contact_button = None
            for selector in contact_info_selectors:
                try:
                    contact_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    logging.info(f"Found contact info button using selector: {selector}")
                    break
                except Exception as e:
                    logging.debug(f"Selector failed: {selector} - {str(e)}")
                    continue
                    
            if not contact_button:
                logging.warning(f"Could not find contact info button on profile: {profile_link}")
                return None
                
            # Click the contact info button
            contact_button.click()
            
            # Wait for the contact info modal to appear
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".artdeco-modal__content, .pv-contact-info"))
            )
            logging.info("Contact info modal appeared")
            
            # Add a delay to prevent the modal from closing immediately
            time.sleep(random.uniform(2, 4))  # Mimic human behavior
           
           # Extract the modal's HTML for debugging
            modal_html = self.driver.find_element(By.CSS_SELECTOR, ".artdeco-modal__content").get_attribute("outerHTML")
            logging.debug(f"Modal HTML: {modal_html}")
            
            # Look for email in the modal
            email_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'mailto:')]")
            if email_elements:
                email = email_elements[0].get_attribute("href").replace("mailto:", "").strip()
                logging.info(f"Email found: {email}")
            else:
                logging.warning("No email found in the modal.")
           
           
           
            # Save a screenshot for debugging
            self.driver.save_screenshot(f"contact_info_{int(time.time())}.png")
            
            # Look for email - try multiple approaches
            email = None
            
            

            # Approach 1: Look for email by link containing 'mailto:'
            try:
                email_elements = self.driver.find_elements(By.XPATH, "//section[contains(@class, 'pv-contact-info__contact-type')]//a[contains(@href, 'mailto:')]")
                if email_elements:
                    email = email_elements[0].get_attribute("href").replace("mailto:", "").strip()
                    logging.info(f"Email found using 'mailto:' approach: {email}")
            except Exception as e:
                logging.debug(f"Email extraction using 'mailto:' failed: {str(e)}")

            # Approach 2: Look for email by specific CSS classes
            if not email:
                try:
                    email_elements = self.driver.find_elements(By.CSS_SELECTOR, ".pv-contact-info__contact-type a[href^='mailto:']")
                    if email_elements:
                        email = email_elements[0].get_attribute("href").replace("mailto:", "").strip()
                        logging.info(f"Email found using CSS class approach: {email}")
                except Exception as e:
                    logging.debug(f"Email extraction using CSS classes failed: {str(e)}")

            if not email:
                logging.warning("No email found in the modal.")
            
            # Approach 3: Look for email by specific CSS classes LinkedIn might use
            if not email:
                try:
                    email_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                        ".ci-email .pv-contact-info__contact-link, .ci-email .pv-contact-info__ci-container")
                    if email_elements:
                        email = email_elements[0].text
                        logging.info(f"Email found using Approach 3: {email}")
                except Exception as e:
                    logging.debug(f"Email approach 3 failed: {str(e)}")
            
            # Close the modal - try different approaches as this can vary
            try:
                close_buttons = self.driver.find_elements(By.XPATH, 
                    "//button[contains(@aria-label, 'Dismiss') or contains(@aria-label, 'Close')]")
                if close_buttons:
                    close_buttons[0].click()
                else:
                    # Try clicking outside the modal
                    actions = webdriver.ActionChains(self.driver)
                    actions.move_by_offset(10, 10).click().perform()
            except Exception as e:
                logging.warning(f"Error closing modal: {str(e)}")
                # Sometimes we can just continue without closing it as navigation will close it
            
            if email:
                logging.info(f"Retrieved email: {email}")
            
            return email
            
        except Exception as e:
            logging.error(f"Error extracting email: {str(e)}")
            return None
   
   
    def process_daily_contacts(self):
        """Process up to max_daily_contacts per day"""
        # Reset counter if it's a new day
        current_date = datetime.now().date()
        if current_date > self.start_date:
            self.retrieved_today = 0
            self.start_date = current_date
            
        if self.retrieved_today >= self.max_daily_contacts:
            logging.info(f"Daily limit of {self.max_daily_contacts} contacts reached")
            return False
            
        # Log in to LinkedIn
        if not self.login():
            return False
            
        try:
            contacts_needed = self.max_daily_contacts - self.retrieved_today
            page = 1
            processed_count = 0
            
            while processed_count < contacts_needed:
                # Get contacts from current page
                contacts = self.get_contact_list(page=page, limit=contacts_needed - processed_count)
                
                if not contacts:
                    break  # No more contacts to process
                
                for contact in contacts:
                    # Random delay between processing contacts (3-7 seconds)
                    time.sleep(random.uniform(3, 7))
                    
                    email = self.extract_email_from_profile(contact["profile_link"])
                    
                    if email:
                        logging.info(f"Retrieved email for {contact['name']}: {email}")
                    else:
                        email = "Not available"
                        logging.info(f"No email found for {contact['name']}")
                    
                    # Save the contact details
                    self.save_processed_contact(contact["profile_id"], contact["name"], email)
                    
                    processed_count += 1
                    self.retrieved_today += 1
                    
                    # Check if we've reached the daily limit
                    if self.retrieved_today >= self.max_daily_contacts:
                        break
                        
                # Go to next page if needed
                if processed_count < contacts_needed:
                    page += 1
                else:
                    break
                    
            logging.info(f"Processed {processed_count} contacts today. Total for today: {self.retrieved_today}")
            return True
            
        except Exception as e:
            logging.error(f"Error during contact processing: {str(e)}")
            return False
        finally:
            # Always close the browser when done
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    # Load environment variables from .env file
    retriever = LinkedInEmailRetriever(
        username=os.getenv("LINKEDIN_USERNAME"),
        password=os.getenv("LINKEDIN_PASSWORD"),
        max_daily_contacts=5
    )
    
    retriever.process_daily_contacts()