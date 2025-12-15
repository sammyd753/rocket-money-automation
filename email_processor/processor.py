"""Email processing functions for retrieving download links."""

import time
import imaplib
import email
from bs4 import BeautifulSoup
from config import GMAIL_USER, GMAIL_PASS
from utils.logger import log


def get_download_link(max_retries=1, wait_time=30):
    """Get download link from Rocket Money email with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 1)
        wait_time: Time to wait between retries in seconds (default: 30)
        
    Returns:
        str: Download link if found, None otherwise
    """
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
                    
                    # --- NEW LOGIC: Use BeautifulSoup to find the download link ---
                    soup = BeautifulSoup(body, "html.parser")
                    # Find the first anchor with text 'Download file' (strip spaces)
                    anchor = None
                    for a in soup.find_all('a'):
                        if a.text.strip().lower() == 'download file':
                            anchor = a
                            break
                    if anchor and anchor.has_attr('href'):
                        download_link = anchor['href']
                        log(f"Found download link using BeautifulSoup: text='{anchor.text.strip()}', href='{download_link}'")
                        break
                    # --- END NEW LOGIC ---
                    
                    # Fallback: Old method (in case the above fails)
                    if not download_link:
                        download_text = "Download file ➔"
                        pos = body.find(download_text)
                        if pos != -1:
                            log(f"Found '{download_text}' text in email")
                            # Search backwards for the nearest href
                            href_start = body.rfind('href=\"', 0, pos)
                            if href_start != -1:
                                href_end = body.find('"', href_start + 6)
                                if href_end != -1:
                                    download_link = body[href_start + 6:href_end]
                                    log(f"Found download link (fallback): {download_link}")
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

