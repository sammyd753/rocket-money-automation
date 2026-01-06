# Rocket Money Automation

This Python script automates the process of:
1. Exporting transaction data from Rocket Money with a piano income filter
2. Retrieving the download link from Gmail
3. Downloading the exported file
4. Uploading the file to Google Drive
5. Appending the data to a Google Sheet

## Setup

1. Clone this repository
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `config.py` file with your credentials:
   ```python
   ROCKET_USER = "your_rocket_money_username"
   ROCKET_PASS = "your_rocket_money_password"
   GMAIL_USER = "your_gmail_address"
   GMAIL_PASS = "your_gmail_app_password"
   SHEET_ID = "your_google_sheet_id"
   SHEET_NAME = "your_sheet_name"
   DRIVE_FOLDER_ID = "your_google_drive_folder_id"
   ```
4. Set up Google Cloud credentials:
   - Create a service account in Google Cloud Console
   - Download the credentials and save as `credentials.json`
   - Share your Google Sheet and Drive folder with the service account email

## Usage

Run the script:
```bash
python main.py
```

The script will:
1. Log into Rocket Money and export transactions with the piano income filter
2. Wait for and retrieve the download link from your Gmail
3. Download the file from the link
4. Upload it to the specified Google Drive folder
5. Append the data to your Google Sheet

## Features

- Automatic handling of 2FA authentication
- Retry logic for failed operations
- Detailed logging
- Error screenshots for debugging
- Proper data type handling for Google Sheets
- Batch processing to avoid API quotas
- Automatic email monitoring for download links
- Smart file handling with timestamp-based naming

## Monarch Piano Income Export (API-based)

Use `monarch.py` to pull Piano Income transactions directly from the Monarch Money API and write them to `monarch_piano_income.csv` with the raw fields returned by Monarch.

### Setup

1. Install dependencies (includes `monarchmoney`):
   ```bash
   pip install -r requirements.txt
   ```
2. Set credentials in `config.py`:
   ```python
   MONARCH_EMAIL = "your_monarch_email"
   MONARCH_PASSWORD = "your_monarch_password"
   ```
   (No MFA secret is required if you don't use two-factor codes.)

### Run

```bash
python monarch.py
```

The script:
- Logs into Monarch using the provided credentials
- Finds the `Piano Income` category
- Retrieves all available transactions for that category
- Writes them to `monarch_piano_income.csv`

## Requirements

- Python 3.x
- Chrome browser
- Google Cloud account with Drive and Sheets APIs enabled
- Rocket Money account
- Gmail account with IMAP enabled

## Security Note

Never commit your `config.py` or `credentials.json` files to version control. These files contain sensitive information and should be kept private. 