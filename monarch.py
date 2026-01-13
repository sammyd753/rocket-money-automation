import asyncio
import csv
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import config
from config import SHEET_ID, SHEET_NAME_MONARCH
from monarchmoney import MonarchMoney, RequireMFAException
from utils.logger import log

from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


OUTPUT_CSV = "monarch_piano_income.csv"
CATEGORY_NAME = "Piano Income"
FIELDNAMES = ["Date", "Account", "Name", "TransactionsCount", "Amount", "PlaidName", "Id"]


async def login_client() -> MonarchMoney:
    email = config.MONARCH_EMAIL
    password = config.MONARCH_PASSWORD

    if not email or not password:
        raise SystemExit(
            "Please set MONARCH_EMAIL and MONARCH_PASSWORD in config.py for Monarch login."
        )

    mm = MonarchMoney()
    log("Attempting to load saved Monarch session (non-interactive)...")
    try:
        mm.load_session()
        # Quick probe to ensure session works
        await mm.get_subscription_details()
        log("Loaded saved session successfully.")
        return mm
    except Exception as e:
        log("Saved session not available/valid; attempting password login (may require MFA)...")

    log("Logging into Monarch Money with credentials...")
    try:
        await mm.login(email=email, password=password)
        log("Login successful.")
        try:
            mm.save_session()
        except Exception as e:
            log(f"Warning: could not save session after login: {e}")
        return mm
    except RequireMFAException:
        log("Monarch requires MFA. Please enter the current MFA code from your authenticator/email.")
        mfa_code = input("Enter MFA code: ").strip()
        # multi_factor_authenticate(email, password, code)
        await mm.multi_factor_authenticate(email, password, mfa_code)
        log("MFA successful.")
        try:
            mm.save_session()
            log("Saved session for future non-MFA runs.")
        except Exception as se:
            log(f"Warning: could not save session after MFA: {se}")
        return mm

    return mm


async def get_piano_category_id(mm: MonarchMoney) -> str:
    log(f"Locating category '{CATEGORY_NAME}'...")
    data: Dict[str, Any] = await mm.get_transaction_categories()
    categories: List[Dict[str, Any]] = data.get("categories", [])

    match = next((c for c in categories if c.get("name") == CATEGORY_NAME), None)
    if not match:
        match = next(
            (c for c in categories if c.get("name", "").lower() == CATEGORY_NAME.lower()),
            None,
        )

    if not match:
        raise SystemExit(f"Category '{CATEGORY_NAME}' not found in Monarch Money.")

    category_id = match["id"]
    log(f"Found category id: {category_id}")
    return category_id


async def fetch_all_transactions(mm: MonarchMoney, category_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    limit = 500
    offset = 0
    all_results: List[Dict[str, Any]] = []

    while True:
        log(f"Fetching transactions offset {offset} limit {limit}...")
        resp: Dict[str, Any] = await mm.get_transactions(
            limit=limit,
            offset=offset,
            category_ids=[category_id],
            start_date=start_date,
            end_date=end_date,
        )

        container = resp.get("allTransactions", {})
        batch = container.get("results", []) or []
        total = container.get("totalCount", 0)

        all_results.extend(batch)
        offset += len(batch)

        if offset >= total or not batch:
            break

    log(f"Fetched {len(all_results)} transactions (totalCount reported: {total}).")
    return all_results


def extract_cleaned_row(tx: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and clean the specific fields we want from a transaction."""
    cleaned: Dict[str, Any] = {}
    
    # Date - direct from date column
    cleaned["Date"] = tx.get("date", "")
    
    # Account - get displayName from account dict
    account = tx.get("account", {})
    if isinstance(account, dict):
        cleaned["Account"] = account.get("displayName", "")
    else:
        cleaned["Account"] = ""
    
    # Name and TransactionsCount - get from merchant dict
    merchant = tx.get("merchant", {})
    if isinstance(merchant, dict):
        cleaned["Name"] = merchant.get("name", "")
        cleaned["TransactionsCount"] = merchant.get("transactionsCount", "")
    else:
        cleaned["Name"] = ""
        cleaned["TransactionsCount"] = ""
    
    # Amount - direct from amount column
    cleaned["Amount"] = tx.get("amount", "")
    
    # PlaidName - direct from plaidName column
    cleaned["PlaidName"] = tx.get("plaidName", "")

    # Id - unique transaction id
    cleaned["Id"] = tx.get("id", "")

    return cleaned


def write_csv(transactions: List[Dict[str, Any]]) -> None:
    if not transactions:
        log("No transactions to write.")
        return

    # Clean all transactions
    cleaned_transactions = [extract_cleaned_row(tx) for tx in transactions]
    
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for tx in cleaned_transactions:
            writer.writerow(tx)

    log(f"Wrote {len(cleaned_transactions)} rows to {OUTPUT_CSV}.")


def get_sheets_service():
    """Create and return Google Sheets API service."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        log("Using service account credentials from credentials.json.")
    except Exception as e:
        raise SystemExit(
            f"Could not load Google credentials from 'credentials.json'. "
            f"Please ensure the file exists and is valid. Error: {e}"
        )
    
    service = build('sheets', 'v4', credentials=creds)
    return service


def get_existing_rows(service) -> List[List[str]]:
    """Fetch all existing rows from the Google Sheet."""
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_NAME_MONARCH}!A:G"
        ).execute()
        
        values = result.get('values', [])
        log(f"Found {len(values)} existing rows in sheet (including header).")
        return values
    except HttpError as e:
        log(f"Error reading from sheet: {e}")
        return []


def read_csv_rows() -> List[List[str]]:
    """Read rows from the CSV file."""
    rows = []
    try:
        with open(OUTPUT_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        log(f"Read {len(rows)} rows from {OUTPUT_CSV} (including header).")
    except FileNotFoundError:
        log(f"CSV file {OUTPUT_CSV} not found.")
    return rows


def create_row_key(row: List[str]) -> str:
    """Create a unique key for a row to identify duplicates.
    Uses Id for all rows."""
    if len(row) >= 7:
        return row[6]
    else:
        return ""


def append_to_sheet(service, new_rows: List[List[str]]) -> None:
    """Append new rows to the Google Sheet."""
    if not new_rows:
        log("No new rows to append.")
        return
    
    try:
        sheet = service.spreadsheets()
        body = {'values': new_rows}
        
        result = sheet.values().append(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_NAME_MONARCH}!A:G",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        log(f"Appended {len(new_rows)} new rows to Google Sheet.")
        log(f"Updated range: {result.get('updates', {}).get('updatedRange', 'N/A')}")
    except HttpError as e:
        log(f"Error appending to sheet: {e}")
        raise


def sync_to_google_sheets() -> None:
    """Read CSV, compare with existing sheet data, and append non-duplicates."""
    log("Starting Google Sheets sync...")
    
    service = get_sheets_service()
    
    # Get existing data from sheet
    existing_rows = get_existing_rows(service)
    
    # Read CSV data
    csv_rows = read_csv_rows()
    
    if not csv_rows:
        log("No CSV data to process.")
        return
    
    # If sheet is empty, write header + all data
    if not existing_rows:
        log("Sheet is empty. Writing header and all rows.")
        append_to_sheet(service, csv_rows)
        return
    
    # Build set of existing row keys (skip header)
    existing_keys = set()
    for row in existing_rows[1:]:  # Skip header
        key = create_row_key(row)
        if key:
            existing_keys.add(key)

    log(f"Found {len(existing_keys)} unique existing transactions.")
    
    # Find new rows (skip header from CSV)
    new_rows = []
    for row in csv_rows[1:]:  # Skip header
        key = create_row_key(row)
        if key and key not in existing_keys:
            new_rows.append(row)

    log(f"Identified {len(new_rows)} new transactions to append.")
    if new_rows: ##
        log("New transaction keys:")
        for row in new_rows:
            key = create_row_key(row)
            log(f"New key: {key} -> {row}") ##

    # Append new rows
    append_to_sheet(service, new_rows)


async def main() -> None:
    mm = await login_client()
    category_id = await get_piano_category_id(mm)

    # Check if sheet has existing data
    service = get_sheets_service()
    existing_rows = get_existing_rows(service)

    if existing_rows:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        transactions = await fetch_all_transactions(mm, category_id, start_date=start_date, end_date=end_date)
    else:
        transactions = await fetch_all_transactions(mm, category_id)

    write_csv(transactions)

    # Sync to Google Sheets
    sync_to_google_sheets()


if __name__ == "__main__":
    asyncio.run(main())
