"""Google Drive operations for file upload and download."""

import os
import time
import glob
import shutil
import undetected_chromedriver as uc
from config import ROCKET_USER, ROCKET_PASS, DRIVE_FOLDER_ID
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from rocket_money.driver import get_chrome_options
from utils.logger import log


def verify_csv_file(file_path):
    """Verify that the CSV file exists and has content.
    
    Args:
        file_path: Path to the CSV file to verify
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is empty or has no header row
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Downloaded CSV file not found: {file_path}")
    
    if os.path.getsize(file_path) == 0:
        raise ValueError("Downloaded CSV file is empty")
    
    with open(file_path, 'r') as f:
        first_line = f.readline().strip()
        if not first_line:
            raise ValueError("CSV file has no header row")


def download_and_save_to_drive(download_link, max_retries=3):
    """Download file with retry logic and verification, then upload to Google Drive.
    
    Args:
        download_link: URL to download the file from
        max_retries: Maximum number of retry attempts (default: 3)
        
    Returns:
        str: Path to the local file
        
    Raises:
        Exception: If download fails after all retries
    """
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

