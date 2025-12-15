"""Main entry point for Rocket Money automation.

This script orchestrates the complete workflow:
1. Export transactions from Rocket Money
2. Retrieve download link from email
3. Download and upload file to Google Drive
4. Append data to Google Sheets
"""

import time
from utils.logger import log
from rocket_money.export import export_rocket_money_data
from email_processor.processor import get_download_link
from google_services.drive import download_and_save_to_drive
from google_services.sheets import append_to_google_sheets


def main():
    """Main function that orchestrates the automation workflow."""
    local_file = None
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
