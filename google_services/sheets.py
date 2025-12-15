"""Google Sheets operations for appending transaction data."""

import time
import csv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SHEET_ID, SHEET_NAME
from utils.logger import log


def append_to_google_sheets(file_path, max_retries=3):
    """Append data to Google Sheets with duplicate prevention using composite key.
    
    Args:
        file_path: Path to the CSV file to append
        max_retries: Maximum number of retry attempts (default: 3)
    """
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

