# Google Credentials Setup Guide

This document walks you through the complete process of obtaining the `credentials.json` file needed for Google Sheets and Google Drive integration in the Rocket Money automation script.

## Overview

The `credentials.json` file is a service account key that allows your script to authenticate with Google APIs (Google Sheets and Google Drive) without requiring user interaction. This is essential for automated operations.

## Prerequisites

- A Google account
- Access to Google Cloud Console
- Basic understanding of Google APIs

## Step-by-Step Process

### Step 1: Create a Google Cloud Project

1. **Go to Google Cloud Console**
   - Visit [https://console.cloud.google.com/](https://console.cloud.google.com/)
   - Sign in with your Google account

2. **Create a New Project**
   - Click on the project dropdown at the top of the page
   - Click "New Project"
   - Enter a project name (e.g., "Rocket Money Automation")
   - Click "Create"
   - Wait for the project to be created and select it

### Step 2: Enable Required APIs

1. **Enable Google Sheets API**
   - In the Google Cloud Console, go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click on it and press "Enable"

2. **Enable Google Drive API**
   - In the same library, search for "Google Drive API"
   - Click on it and press "Enable"

3. **Enable Google Docs API** (if needed)
   - Search for "Google Docs API"
   - Click on it and press "Enable"

### Step 3: Create a Service Account

1. **Navigate to Service Accounts**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"

2. **Configure Service Account**
   - **Service account name**: Enter a descriptive name (e.g., "rocket-money-automation")
   - **Service account ID**: This will be auto-generated
   - **Description**: Optional description
   - Click "Create and Continue"

3. **Grant Access (Optional)**
   - You can skip the "Grant users access" step for now
   - Click "Done"

### Step 4: Generate Service Account Key

1. **Find Your Service Account**
   - In the "Credentials" page, you should see your service account listed
   - Click on the service account email address

2. **Create Key**
   - Go to the "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Click "Create"

3. **Download the Key**
   - The JSON file will automatically download to your computer
   - **Important**: This file contains sensitive credentials - keep it secure!

### Step 5: Rename and Place the File

1. **Rename the File**
   - Rename the downloaded file to `credentials.json`
   - Place it in your project directory (same folder as `main.py`)

2. **File Structure Should Look Like:**
   ```
   rocket-money-automation/
   ├── main.py
   ├── config.py
   ├── credentials.json  ← Your service account key
   └── .gitignore
   ```

### Step 6: Share Google Sheets with Service Account

1. **Get Service Account Email**
   - Open your `credentials.json` file
   - Find the `client_email` field
   - Copy this email address (it looks like: `your-service-account@project-id.iam.gserviceaccount.com`)

2. **Share Your Google Sheet**
   - Open your Google Sheet in a web browser
   - Click the "Share" button (top right)
   - Add the service account email as a collaborator
   - Give it "Editor" permissions
   - Click "Send"

3. **Share Your Google Drive Folder** (if using Drive)
   - Open your Google Drive folder
   - Right-click on the folder
   - Select "Share"
   - Add the service account email
   - Give it "Editor" permissions
   - Click "Send"

### Step 7: Update Your Configuration

1. **Update `config.py`**
   - Open your `config.py` file
   - Set the `SHEET_ID` to your Google Sheet ID (found in the URL)
   - Set the `SHEET_NAME` to your worksheet name
   - Set the `DRIVE_FOLDER_ID` to your Google Drive folder ID (if using Drive)

2. **Example `config.py` content:**
   ```python
   # Google Sheets Configuration
   SHEET_ID = "{Sheet_ID}"  # Your sheet ID
   SHEET_NAME = "Sheet1"  # Your worksheet name
   DRIVE_FOLDER_ID = "{Drive_folder_ID}"  # Your folder ID
   ```

## Security Best Practices

### 1. Keep Credentials Secure
- **Never commit `credentials.json` to version control**
- Add `credentials.json` to your `.gitignore` file
- Store it in a secure location

### 2. Limit Permissions
- Only share the specific Google Sheet and Drive folder needed
- Don't give the service account broader access than necessary

### 3. Rotate Keys Regularly
- Consider rotating your service account keys periodically
- Delete old keys when creating new ones

## Troubleshooting

### Common Issues

1. **"Access Denied" Error**
   - Ensure the service account email has been shared with your Google Sheet
   - Check that the sheet ID is correct in your config

2. **"File Not Found" Error**
   - Verify the `credentials.json` file is in the correct location
   - Check that the file name is exactly `credentials.json`

3. **"Invalid Credentials" Error**
   - Ensure the JSON file is valid and not corrupted
   - Check that the service account is properly configured

### Verification Steps

1. **Test the Setup**
   ```python
   import gspread
   from oauth2client.service_account import ServiceAccountCredentials
   
   scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
   creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
   client = gspread.authorize(creds)
   
   # Test access to your sheet
   spreadsheet = client.open_by_key("YOUR_SHEET_ID")
   worksheet = spreadsheet.worksheet("YOUR_SHEET_NAME")
   print("Connection successful!")
   ```

## File Structure After Setup

Your project should look like this:

```
rocket-money-automation/
├── main.py
├── config.py
├── credentials.json          # Service account key (DO NOT COMMIT)
├── .gitignore              # Should include credentials.json
├── chrome_user_data/       # Browser session data (DO NOT COMMIT)
├── automation.log          # Log file
└── README.md
```

## Next Steps

Once you have the `credentials.json` file set up:

1. Test the connection using the verification code above
2. Run your automation script
3. Monitor the logs to ensure everything works correctly

## Important Notes

- The `credentials.json` file contains sensitive information
- Never share this file publicly
- Always add it to `.gitignore` to prevent accidental commits
- If you suspect the credentials are compromised, delete the service account and create a new one

## Gmail App Password Setup

The `GMAIL_PASS` in your `config.py` file is a Gmail App Password, not your regular Gmail password. This is a special password generated by Google for applications that need to access your Gmail account via IMAP.

### Why Use App Passwords?

- **Security**: App passwords are more secure than using your regular Gmail password
- **Two-Factor Authentication**: Required when 2FA is enabled on your Google account
- **Application Access**: Specifically designed for third-party applications
- **Revocable**: Can be easily revoked without changing your main password

### Step-by-Step: Creating Gmail App Password

#### Prerequisites
- A Gmail account
- Two-Factor Authentication (2FA) enabled on your Google account
- Access to your Google Account settings

#### Step 1: Enable Two-Factor Authentication (if not already enabled)

1. **Go to Google Account Settings**
   - Visit [https://myaccount.google.com/](https://myaccount.google.com/)
   - Sign in with your Google account

2. **Navigate to Security**
   - Click on "Security" in the left sidebar
   - Look for "2-Step Verification"

3. **Enable 2-Step Verification**
   - Click "2-Step Verification"
   - Follow the setup process
   - You'll need to verify your phone number
   - **Important**: App passwords are only available when 2FA is enabled

#### Step 2: Generate App Password

1. **Go to App Passwords**
   - In your Google Account settings, go to "Security"
   - Look for "App passwords" (you may need to scroll down)
   - Click on "App passwords"

2. **Create New App Password**
   - Select "Mail" as the app type
   - Select "Other (custom name)" as the device
   - Enter a descriptive name (e.g., "Rocket Money Automation")
   - Click "Generate"

3. **Copy the Generated Password**
   - Google will generate a 16-character password
   - **Example format**: `xxxx yyyy zzzz aaaa`
   - Copy this password immediately
   - **Important**: You won't be able to see this password again

#### Step 3: Update Your Configuration

1. **Open your `config.py` file**
2. **Update the GMAIL_PASS value**
   ```python
   GMAIL_USER = "your-email@gmail.com"
   GMAIL_PASS = "your-16-character-app-password"  # No spaces needed
   ```

3. **Example configuration:**
   ```python
   ROCKET_USER = "your-email@gmail.com"
   ROCKET_PASS = "your-rocket-money-password"
   GMAIL_USER = "your-email@gmail.com"
   GMAIL_PASS = "xxxxyyyyzzzzaaaa"  # App password without spaces
   ```

### Important Notes About App Passwords

#### Security Considerations
- **Never share your app password** with anyone
- **Store it securely** - treat it like your regular password
- **Revoke it immediately** if you suspect it's compromised
- **Use different app passwords** for different applications

#### Format and Usage
- App passwords are **16 characters long**
- They may contain **spaces** (you can remove them for config files)
- They are **case-sensitive**
- They **expire** when you change your Google account password

#### Troubleshooting App Passwords

1. **"Invalid Credentials" Error**
   - Verify the app password is correct (no typos)
   - Ensure 2FA is enabled on your Google account
   - Check that the app password hasn't been revoked

2. **"App Passwords Not Available"**
   - Ensure 2FA is enabled on your Google account
   - Wait a few minutes after enabling 2FA before creating app passwords
   - Try signing out and back into your Google account

3. **"Access Denied" Error**
   - Verify the Gmail account has IMAP enabled
   - Check that "Less secure app access" is not blocking the connection
   - Ensure the app password is for the correct Google account

### Enabling IMAP Access

Your Gmail account must have IMAP enabled for the script to work:

1. **Go to Gmail Settings**
   - Open Gmail in your browser
   - Click the gear icon (Settings)
   - Click "See all settings"

2. **Enable IMAP**
   - Go to the "Forwarding and POP/IMAP" tab
   - Under "IMAP access", select "Enable IMAP"
   - Click "Save Changes"

### Testing Your Gmail Configuration

You can test your Gmail setup with this simple script:

```python
import imaplib

def test_gmail_connection():
    try:
        # Connect to Gmail IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        
        # Login with your credentials
        mail.login("your-email@gmail.com", "your-app-password")
        print("✅ Gmail connection successful!")
        
        # Select inbox
        mail.select("inbox")
        print("✅ Inbox access successful!")
        
        # Logout
        mail.logout()
        print("✅ Gmail test completed successfully!")
        
    except Exception as e:
        print(f"❌ Gmail connection failed: {str(e)}")

# Run the test
test_gmail_connection()
```

### Revoking App Passwords

If you need to revoke an app password:

1. **Go to Google Account Settings**
   - Visit [https://myaccount.google.com/](https://myaccount.google.com/)
   - Go to "Security" > "App passwords"

2. **Find and Revoke**
   - Find the app password you want to revoke
   - Click the trash/delete icon
   - Confirm the deletion

3. **Generate New Password**
   - Create a new app password if needed
   - Update your `config.py` with the new password

## Support

If you encounter issues:
1. Check the Google Cloud Console for any error messages
2. Verify all APIs are enabled
3. Ensure the service account has proper permissions
4. Check that your Google Sheet and Drive folder are shared correctly
5. For Gmail issues: Verify 2FA is enabled and IMAP is accessible
6. Test your Gmail connection using the provided test script
