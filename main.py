import os
import time
import logging
import imaplib
import email
import gspread
import requests
import undetected_chromedriver as uc
from config import *
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from bs4 import BeautifulSoup
import glob
import csv

# Configure logging
logging.basicConfig(
    filename="automation.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log(message, level="info"):
    if level == "info":
        logging.info(message)
    elif level == "error":
        logging.error(message)
    print(message)
def wait_and_click(driver, wait, text_pattern, fallback_xpath, error_msg, retries=3):
    """Helper function to wait for and click elements with retry logic and fallback xpath"""
    for attempt in range(retries):
        try:
            try:
                # If text_pattern fails, try fallback xpath
                element = wait.until(EC.element_to_be_clickable((By.XPATH, text_pattern)))
                element.click()
                return True
            except:
                # Try fallback xpath first
                log(f"Primary text_pattern failed, trying fallback for: {error_msg}")
                element = wait.until(EC.element_to_be_clickable((By.XPATH, fallback_xpath)))
                element.click()
                return True
        except (TimeoutException, ElementClickInterceptedException) as e:
            if attempt == retries - 1:
                log(f"{error_msg}: {str(e)}", "error")
                raise
            time.sleep(2)
    return False
def handle_login_form(driver, wait):
    log("Waiting for login form...")
    try:
        # Try multiple selectors for the login form
        selectors = [
            "input[name='username']"
        ]
        
        username_field = None
        for selector in selectors:
            try:
                log(f"Trying selector: {selector}")
                username_field = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if username_field:
                    log(f"Found username field with selector: {selector}")
                    break
            except:
                continue
        
        if not username_field:
            raise Exception("Could not find username field with any selector")
        
        # Take a screenshot before entering credentials
        driver.save_screenshot("before_login.png")
        log("Screenshot saved as before_login.png")
        
        # Clear fields first
        username_field.clear()
        time.sleep(0.5)
        
        # Type credentials
        for char in ROCKET_USER:
            username_field.send_keys(char)
        time.sleep(0.5)
        
        # Try to find password field
        password_selectors = [
            "input[name='password']"
        ]
        
        password_field = None
        for selector in password_selectors:
            try:
                log(f"Trying password selector: {selector}")
                password_field = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if password_field:
                    log(f"Found password field with selector: {selector}")
                    break
            except:
                continue
        
        if not password_field:
            raise Exception("Could not find password field with any selector")
        
        password_field.clear()
        time.sleep(0.5)
        
        for char in ROCKET_PASS:
            password_field.send_keys(char)
        time.sleep(0.5)
        
        # Try to find login button
        button_selectors = [
            "button[type='submit']",
            "button:contains('Sign in')",
            "button:contains('Log in')",
            "input[type='submit']"
        ]
        
        login_button = None
        for selector in button_selectors:
            try:
                log(f"Trying button selector: {selector}")
                login_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                if login_button:
                    log(f"Found login button with selector: {selector}")
                    break
            except:
                continue
        
        if not login_button:
            raise Exception("Could not find login button with any selector")
        
        login_button.click()
        
    except Exception as e:
        log(f"Error during login form interaction: {str(e)}", "error")
        # Take screenshot on error
        driver.save_screenshot("login_error.png")
        log("Error screenshot saved as login_error.png")
        raise
def handle_2fa(driver, wait):
        """Handle 2-factor authentication flow."""
        log("Waiting for 2-factor authentication...")
        
        try:
            # Check if we are already logged in by verifying if we have reached the expected logged-in URL
            logged_in_url = "https://app.rocketmoney.com/"  # Replace with your actual logged-in page URL
            if driver.current_url.startswith(logged_in_url):
                log("Already logged in. Skipping 2FA.")
                return  # Exit gracefully
            
            # Wait for the 2FA input field
            twofa_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
            )
            log("Found 2FA input field")
            
            # Clear the field first
            twofa_field.clear()
            time.sleep(1)
            
            # Get 2FA code from user
            twofa_code = input("Please enter the 2FA code sent to your device: ")
            
            # Type the code with small delays
            for char in twofa_code:
                twofa_field.send_keys(char)
                time.sleep(0.1)
            time.sleep(0.5)
            
            # Find and click the verify button
            verify_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            verify_button.click()
            log("2FA code submitted")
            
            # Wait for 2FA verification
            time.sleep(2)
        
        except TimeoutException:
            log("2FA input field not found, assuming already logged in. Skipping 2FA.")
            return  # Gracefully exit if 2FA is not required
        
        except InvalidElementStateException:
            log("2FA field exists but is not interactable. Assuming already logged in.")
            return  # Exit gracefully
        
        except Exception as e:
            log(f"Error during 2FA: {str(e)}", "error")
            driver.save_screenshot("2fa_error.png")
            log("2FA error screenshot saved as 2fa_error.png")
            raise
def navigate_and_export_transactions(driver, wait):
            """Navigate to transactions page and export filtered data"""
            # Wait for login and navigate to transactions
            log("Waiting for login to complete...")
            time.sleep(2.5)  # Increased wait time for login
            
            log("Navigating to transactions page...")
            driver.get("https://app.rocketmoney.com/transactions")
            time.sleep(2.5)  # Increased wait time for page load
            
            # DEBUG: Print all button texts on the page
            log('--- DEBUG: Listing all button texts on the page ---')
            buttons = driver.find_elements(By.TAG_NAME, 'button')
            for idx, b in enumerate(buttons):
                log(f'Button {idx}: {repr(b.text)}')
            log('--- END DEBUG BUTTON LIST ---')
            
            # 1. Click All dates button
            log("Clicking All dates button...")
            wait_and_click(
                driver, 
                wait, 
                # "/html/body/div[3]/main/div/div/div[1]/div/div[1]/header/div/div/div[2]/div/div[1]/div/button",
                "//button[contains(normalize-space(.), 'All dates')]",
                "/html/body/div[1]/main/div/div/div[1]/div/div[1]/header/div/div/div[2]/div/div[1]/div/button",
                "Failed to click All dates button"
            )
            
            time.sleep(0.5)  # Wait for dropdown
            
            # 2. Select date range based on config
            date_range_index, date_range_text = ROCKET_DATE_RANGE_MAP[ROCKET_DATE_SELECT]
            log(f"Selecting {date_range_text}...")
            wait_and_click(
                driver,
                wait,
                # f"/html/body/div[3]/main/div/div/div[3]/div/div/div/div/li[{date_range_index}]",
                f"//li[contains(normalize-space(.), '{date_range_text}')]",
                f"/html/body/div[1]/main/div/div/div[3]/div/div/div/div/li[3]",
                f"Failed to select {date_range_text}"
            )
            
            time.sleep(0.5)  # Wait for filter to apply
            
            # 3. Click All Categories button
            log("Clicking All Categories button...")
            wait_and_click(
                driver,
                wait,
                # "/html/body/div[3]/main/div/div/div[1]/div/div[1]/header/div/div/div[2]/div/div[2]/div/button",
                "//button[contains(normalize-space(.), 'All categories')]",
                "/html/body/div[1]/main/div/div/div[1]/div/div[1]/header/div/div/div[2]/div/div[2]/div/button",
                "Failed to click All Categories button"
            )
            
            time.sleep(0.5)  # Wait for dropdown
            
            # 4. Select Piano Income category
            log("Selecting Piano Income category...")
            wait_and_click(
                driver,
                wait,
                # "/html/body/div[3]/main/div/div/div[4]/div/div/div/ul/li[3]",
                "//li[contains(normalize-space(.), 'Piano Income')]",
                "/html/body/div[1]/main/div/div/div[4]/div/div/div/ul/li[4]",
                "Failed to select Piano Income category"
            )
            
            time.sleep(0.5)  # Wait for filter to apply
            
            # 5. Click Export button
            log("Clicking Export button...")
            wait_and_click(
                driver,
                wait,
                # "/html/body/div[3]/main/div/div/div[1]/div/div[1]/header/div/div/div[1]/div[2]/div[1]/div/button",
                "//button[contains(normalize-space(.), 'Export')]",
                "/html/body/div[1]/main/div/div/div[1]/div/div[1]/header/div/div/div[1]/div[2]/div[1]/div/button",
                "Failed to click Export button"
            )
            
            # Wait for and click the export confirmation button
            log("Waiting for export confirmation button...")
            try:
                # Try exact text pattern first, then fallback to xpath
                try:
                    confirm_button = wait.until(
                        # EC.element_to_be_clickable((By.XPATH, "/html/body/div[7]/div/div/div/div[2]/button"))
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(normalize-space(.), 'Export') and contains(normalize-space(.), 'transactions')]"))
                    )
                except:
                    confirm_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, "/html/body/div[5]/div/div/div/div[2]/button"))
                    )
                
                time.sleep(1)  # Short wait to ensure modal is fully loaded
                log("Clicking export confirmation button...")
                confirm_button.click()
                log("Export confirmation clicked")
            except Exception as e:
                log(f"Error clicking export confirmation: {str(e)}", "error")
                driver.save_screenshot("export_confirm_error.png")
                raise
            
            log(f"Export request submitted for Piano Income transactions from {date_range_text}.")
            time.sleep(0.1)  # Wait for export to initiate
def verify_csv_file(file_path):
    """Verify that the CSV file exists and has content"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Downloaded CSV file not found: {file_path}")
    
    if os.path.getsize(file_path) == 0:
        raise ValueError("Downloaded CSV file is empty")
    
    with open(file_path, 'r') as f:
        first_line = f.readline().strip()
        if not first_line:
            raise ValueError("CSV file has no header row")

def get_chrome_options():
    """Configure Chrome options with user data persistence"""
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    
    # Set up user data directory for session persistence
    user_data_dir = os.path.join(os.getcwd(), 'chrome_user_data')
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    options.add_argument(f'--user-data-dir={user_data_dir}')
    options.add_argument('--profile-directory=Default')
    
    return options

def export_rocket_money_data():
    log("Starting Rocket Money export...")
    
    driver = None
    try:
        log("Initializing Chrome driver...")
        options = get_chrome_options()
        driver = uc.Chrome(options=options)
        wait = WebDriverWait(driver, 20)
        
        # Login to Rocket Money
        log("Navigating to Rocket Money app...")
        driver.get("https://app.rocketmoney.com")
        time.sleep(2)  # Wait for initial page load and redirect
        
        # Log the current URL to verify we're on the right page
        current_url = driver.current_url
        log(f"Current URL: {current_url}")

        # Check if we need to log in
        try:
            # Quick check for login form
            username_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']"))
            )
            log("Login required, proceeding with authentication...")
            handle_login_form(driver, wait)
            handle_2fa(driver, wait)
        except TimeoutException:
            log("Already logged in, skipping authentication...")

        # Navigate to transactions page and export data
        navigate_and_export_transactions(driver, wait)
        
    except Exception as e:
        log(f"Error during Rocket Money export: {str(e)}", "error")
        if driver:
            try:
                screenshot_path = "error_screenshot.png"
                driver.save_screenshot(screenshot_path)
                log(f"Error screenshot saved to {screenshot_path}")
            except:
                pass
        raise
    finally:
        log(f"Quitting driver...")
        if driver:
            driver.quit()

def get_download_link(max_retries=1, wait_time=30):
    """Get download link with retry logic"""
    for attempt in range(max_retries):
        try:
            log(f"Checking email for Rocket Money download link (attempt {attempt + 1}/{max_retries})...")
            log(f"Connecting to Gmail IMAP server...")
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            
            log(f"Attempting login with user: {GMAIL_USER}")
            mail.login(GMAIL_USER, GMAIL_PASS)
            log("Successfully logged into Gmail!")
            
            mail.select("inbox")
            log("Selected inbox")
            
            # Search for specific email
            search_criteria = '(FROM "hello@insights.rocketmoney.com" SUBJECT "Transaction export complete")'
            log(f"Searching with criteria: {search_criteria}")
            result, data = mail.search(None, search_criteria)
            
            if not data[0]:
                if attempt == max_retries - 1:
                    log("No matching email found after all retries", "error")
                    return None
                log(f"No email found yet, waiting {wait_time} seconds...")
                mail.logout()
                time.sleep(wait_time)
                continue
            
            email_ids = data[0].split()
            latest_email_id = email_ids[-1]
            log(f"Found {len(email_ids)} matching emails, using most recent")
            
            result, msg_data = mail.fetch(latest_email_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Log email details
            log(f"Email Subject: {msg['subject']}")
            log(f"Email From: {msg['from']}")
            log(f"Email Date: {msg['date']}")
            
            download_link = None
            for part in msg.walk():
                content_type = part.get_content_type()
                log(f"Processing email part with content type: {content_type}")
                
                if content_type == "text/html":
                    body = part.get_payload(decode=True).decode()
                    log("Found HTML content in email")
                    
                    # Save email content for debugging
                    with open("email_content.html", "w", encoding="utf-8") as f:
                        f.write(body)
                    log("Saved email content to email_content.html for inspection")
                    
                    # Look for the specific download link text
                    download_text = "Download file ➔"
                    pos = body.find(download_text)
                    if pos != -1:
                        log(f"Found '{download_text}' text in email")
                        # Search backwards for the nearest href
                        href_start = body.rfind('href="', 0, pos)
                        if href_start != -1:
                            href_end = body.find('"', href_start + 6)
                            if href_end != -1:
                                download_link = body[href_start + 6:href_end]
                                log(f"Found download link: {download_link}")
                                break
                    else:
                        log(f"Could not find '{download_text}' text in email")
            
            mail.logout()
            
            if download_link:
                log(f"Download link found")
                return download_link
            else:
                log("No download link found in email", "error")
                
        except Exception as e:
            log(f"Error checking email (attempt {attempt + 1}): {str(e)}", "error")
            if attempt == max_retries - 1:
                raise
            time.sleep(wait_time)
    
    return None
def download_and_save_to_drive(download_link, max_retries=3):
    """Download file with retry logic and verification"""
    log("Downloading file...")
    local_file = "rocket_money_data.csv"
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    
    for attempt in range(max_retries):
        driver = None
        try:
            log(f"Download attempt {attempt + 1}/{max_retries}")
            
            # Get list of existing transaction files before download
            before_files = set(glob.glob(os.path.join(downloads_dir, "*-transactions.csv")))
            log(f"Found {len(before_files)} existing transaction files")
            for f in before_files:
                log(f"  - {f}")
            
            # Configure Chrome with session persistence
            options = get_chrome_options()
            
            log("Initializing Chrome driver for download...")
            driver = uc.Chrome(options=options)
            wait = WebDriverWait(driver, 20)
            
            # First get the download page
            log("Fetching download page...")
            driver.get(download_link)
            time.sleep(5)  # Wait for redirect
            
            # Log the current URL
            download_url = driver.current_url
            log(f"Current URL: {download_url}")
            
            # Check if we need to log in
            if 'login' in download_url.lower():
                log("Login required, authenticating...")
                
                # Find and fill username field
                username_field = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']"))
                )
                username_field.clear()
                username_field.send_keys(ROCKET_USER)
                
                # Find and fill password field
                password_field = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
                )
                password_field.clear()
                password_field.send_keys(ROCKET_PASS)
                
                # Click login button
                login_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
                login_button.click()
                
                # Handle 2FA if needed
                try:
                    twofa_field = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
                    )
                    log("2FA required")
                    
                    # Take a screenshot to help with debugging
                    driver.save_screenshot("2fa_page.png")
                    log("2FA page screenshot saved as 2fa_page.png")
                    
                    # Get 2FA code from user with extended timeout
                    log("Waiting for 2FA code input (you have 60 seconds)...")
                    log("Please check your device for the 2FA code and enter it below.")
                    
                    try:
                        twofa_code = None
                        while not twofa_code:
                            try:
                                twofa_code = input("Enter 2FA code (or press Ctrl+C to retry): ").strip()
                                if not twofa_code:
                                    log("Empty code entered, please try again...")
                            except KeyboardInterrupt:
                                log("2FA input interrupted, retrying...")
                                if driver:
                                    driver.quit()
                                raise KeyboardInterrupt
                        
                        log("2FA code received, submitting...")
                        twofa_field.clear()
                        time.sleep(1)
                        
                        # Type code with delays
                        for char in twofa_code:
                            twofa_field.send_keys(char)
                            time.sleep(0.1)
                        time.sleep(1)
                        
                        verify_button = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                        )
                        verify_button.click()
                        log("2FA code submitted")
                        
                        # Wait longer for 2FA verification
                        time.sleep(1)
                        
                        # Verify we're logged in by checking URL or content
                        if 'login' in driver.current_url.lower():
                            driver.save_screenshot("after_2fa_error.png")
                            raise Exception("Still on login page after 2FA")
                        
                        log("2FA verification successful")
                        
                    except KeyboardInterrupt:
                        raise KeyboardInterrupt
                    except Exception as e:
                        log(f"Error during 2FA code entry: {str(e)}", "error")
                        driver.save_screenshot("2fa_error.png")
                        raise
                    
                except TimeoutException:
                    log("No 2FA required, continuing...")
                except Exception as e:
                    log(f"Error during 2FA process: {str(e)}", "error")
                    if driver:
                        driver.quit()
                    continue
                
                # Wait for redirect to download page
                time.sleep(3)
            
            # Now we should be on the download page
            log("Waiting for new file to appear in Downloads...")
            
            # Wait for a new file to appear
            start_time = time.time()
            new_file = None
            while time.time() - start_time < 60:  # Wait up to 60 seconds
                current_files = set(glob.glob(os.path.join(downloads_dir, "*-transactions.csv")))
                new_files = current_files - before_files
                if new_files:
                    # Get the most recent file from the new files
                    new_file = max(new_files, key=os.path.getctime)
                    log(f"Found new CSV file: {new_file}")
                    time.sleep(2)  # Wait a bit to ensure file is completely written
                    break
                time.sleep(1)
                if (time.time() - start_time) % 10 == 0:  # Log every 10 seconds
                    log(f"Still waiting for new file... ({int(time.time() - start_time)} seconds elapsed)")
            
            if not new_file:
                raise TimeoutException("Timeout waiting for file to download")
            
            # Copy file to working directory
            import shutil
            shutil.copy2(new_file, local_file)
            log(f"Copied file from Downloads to working directory: {local_file}")
            
            # Verify the downloaded file
            log("Verifying downloaded CSV file...")
            verify_csv_file(local_file)
            
            # Read and log the first few lines of the CSV
            with open(local_file, 'r') as f:
                header = f.readline().strip()
                log(f"CSV Header: {header}")
                # Read next 2 lines as sample data
                sample_lines = [f.readline().strip() for _ in range(2)]
                log("Sample data rows:")
                for line in sample_lines:
                    if line:  # Only log if line is not empty
                        log(line)
            
            # Upload to Google Drive
            try:
                SCOPES = ['https://www.googleapis.com/auth/drive.file']
                creds = service_account.Credentials.from_service_account_file(
                    'credentials.json', scopes=SCOPES)
                
                drive_service = build('drive', 'v3', credentials=creds)
                
                file_metadata = {
                    'name': os.path.basename(new_file),  # Use original filename
                    'parents': [DRIVE_FOLDER_ID]
                }
                
                media = MediaFileUpload(local_file, mimetype='text/csv', resumable=True)
                file = drive_service.files().create(body=file_metadata,
                                                  media_body=media,
                                                  fields='id').execute()
                
                log(f"File uploaded to Google Drive with ID: {file.get('id')}")
                
                # Verify the file was uploaded to the correct folder
                file_info = drive_service.files().get(
                    fileId=file.get('id'),
                    fields='parents'
                ).execute()
                
                if DRIVE_FOLDER_ID in file_info.get('parents', []):
                    log("File confirmed to be in the correct Drive folder")
                else:
                    log("Warning: File may not be in the expected Drive folder", "error")
                
                return local_file
                
            except Exception as e:
                log(f"Error uploading to Google Drive: {str(e)}", "error")
                raise
                
        except KeyboardInterrupt:
            log("Process interrupted by user, retrying...")
            continue
        except Exception as e:
            log(f"Error during download attempt {attempt + 1}: {str(e)}", "error")
            if driver:
                # Take screenshot on error
                try:
                    screenshot_path = f"download_error_{attempt + 1}.png"
                    driver.save_screenshot(screenshot_path)
                    log(f"Error screenshot saved to {screenshot_path}")
                except:
                    pass
            
            if attempt == max_retries - 1:
                raise
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    raise Exception("Failed to download file after all retries")
def append_to_google_sheets(file_path, max_retries=3):
    """Append data to Google Sheets with duplicate prevention using composite key"""
    log("Appending data to Google Sheets...")
    
    for attempt in range(max_retries):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            client = gspread.authorize(creds)
            
            # Open specific spreadsheet and worksheet
            spreadsheet = client.open_by_key(SHEET_ID)
            worksheet = spreadsheet.worksheet(SHEET_NAME)
            
            # Get all existing values from the worksheet
            log("Fetching existing data from Google Sheets...")
            existing_data = worksheet.get_all_values()
            if not existing_data:
                log("Sheet is empty, initializing with header row")
                # Read CSV header to initialize sheet
                with open(file_path, "r", newline='') as f:
                    csv_reader = csv.reader(f)
                    header = next(csv_reader)  # Get header row
                worksheet.append_row(header)
                existing_data = [header]  # Update existing_data to include header
                existing_keys = set()
            else:
                header = existing_data[0]
                # Find indices for our composite key columns
                try:
                    date_idx = header.index("Date")
                    amount_idx = header.index("Amount")
                    desc_idx = header.index("Description")
                except ValueError as e:
                    log(f"Error finding required columns: {str(e)}", "error")
                    raise
                
                # Create set of existing composite keys
                existing_keys = {
                    (row[date_idx], row[amount_idx], row[desc_idx])
                    for row in existing_data[1:]  # Skip header row
                    if len(row) > max(date_idx, amount_idx, desc_idx) and row[date_idx] and row[amount_idx] and row[desc_idx]  # Only include rows with valid data
                }
                log(f"Found {len(existing_keys)} existing transactions")
            
            # Read and process new CSV data
            new_rows = []
            duplicate_count = 0
            with open(file_path, "r", newline='') as f:
                csv_reader = csv.reader(f)
                csv_header = next(csv_reader)  # Skip header row from CSV
                
                # Find indices in CSV data
                csv_date_idx = csv_header.index("Date")
                csv_amount_idx = csv_header.index("Amount")
                csv_desc_idx = csv_header.index("Description")
                
                # Process each row
                for row in csv_reader:
                    # Skip empty rows
                    if not row or all(cell.strip() == '' for cell in row):
                        log("Skipping empty row")
                        continue
                        
                    # Ensure row has enough elements for our key fields
                    if len(row) <= max(csv_date_idx, csv_amount_idx, csv_desc_idx):
                        log(f"Skipping incomplete row: {row}", "error")
                        continue
                        
                    # Skip rows where key fields are empty
                    if not row[csv_date_idx] or not row[csv_amount_idx] or not row[csv_desc_idx]:
                        log(f"Skipping row with empty key fields: {row}", "error")
                        continue
                    
                    # Create composite key for new row using original values
                    new_key = (row[csv_date_idx], row[csv_amount_idx], row[csv_desc_idx])
                    
                    if new_key not in existing_keys:
                        # Format row based on column types, preserving original strings
                        formatted_row = []
                        for i, (value, col_name) in enumerate(zip(row, csv_header)):
                            if col_name == "Amount":
                                try:
                                    # Convert amount to float for proper numeric handling
                                    formatted_row.append(float(value))
                                except ValueError:
                                    log(f"Warning: Invalid amount value: {value}", "error")
                                    formatted_row.append(value)
                            else:
                                # Keep original string values for all other fields
                                formatted_row.append(value)
                        
                        # Make sure the formatted row isn't empty
                        if formatted_row and any(cell for cell in formatted_row):
                            new_rows.append(formatted_row)
                            existing_keys.add(new_key)  # Add to existing keys to prevent duplicates within new data
                            log(f"New transaction found: Date={new_key[0]}, Amount={new_key[1]}, Description={new_key[2]}")
                    else:
                        duplicate_count += 1
                        log(f"Skipping duplicate transaction: Date={new_key[0]}, Amount={new_key[1]}, Description={new_key[2]}")
            
            if not new_rows:
                log(f"No new transactions to append. Found {duplicate_count} duplicate entries.")
                return
            
            # Ensure all rows in batch have the same length (match the header length)
            expected_length = len(csv_header)
            for i in range(len(new_rows)):
                if len(new_rows[i]) < expected_length:
                    # Pad shorter rows with empty strings
                    new_rows[i].extend([''] * (expected_length - len(new_rows[i])))
                elif len(new_rows[i]) > expected_length:
                    # Truncate longer rows
                    new_rows[i] = new_rows[i][:expected_length]
            
            # Log the rows we're about to append
            log(f"Preparing to append {len(new_rows)} non-empty rows")
            
            # Append in batches of 100 to avoid quota limits
            batch_size = 100
            for i in range(0, len(new_rows), batch_size):
                batch = new_rows[i:i + batch_size]
                worksheet.append_rows(batch, value_input_option='USER_ENTERED')
                log(f"Appended batch of {len(batch)} rows")
            
            log(f"Successfully appended {len(new_rows)} new rows to the worksheet.")
            if duplicate_count > 0:
                log(f"Skipped {duplicate_count} duplicate entries.")
            return
            
        except Exception as e:
            log(f"Append attempt {attempt + 1} failed: {str(e)}", "error")
            if attempt == max_retries - 1:
                raise
            time.sleep(5)



def main():
    local_file = None
    latest_file = None
    try:
        # 1. Export Rocket Money Data with piano income filter
        export_rocket_money_data()
        log("Waiting 30 seconds for email...")
        time.sleep(30)  # Initial wait for email
        
        # 2. Get Download Link from Email (with retries)
        download_link = get_download_link()
        if not download_link:
            raise Exception("Failed to get download link after all retries")
        
        # 3. Download file using the link
        log("Starting download using link...")
        local_file = download_and_save_to_drive(download_link)
        if not local_file:
            raise Exception("Failed to download and save file")
        
        # 4. Append Data to Google Sheets
        append_to_google_sheets(local_file)
        
    except Exception as e:
        log(f"Automation failed: {str(e)}", "error")
        raise
    finally:
        log("Script completed. Local files have been preserved for debugging.")

if __name__ == "__main__":
    main()