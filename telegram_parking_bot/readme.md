# Vehicle Tracking Data Processor

This script processes vehicle tracking data from CSV files, calculates time intervals between checkpoints, and uploads the results to Google Sheets.

## Features

- Downloads CSV attachments from Gmail accounts
- Processes vehicle tracking data from multiple channels (CH01, CH02)
- Calculates time intervals between checkpoint passages
- Organizes data by month
- Uploads processed data to Google Sheets
- Tracks processed emails to avoid duplicates

## Prerequisites

1. Python 3.6+
2. Google Cloud Project with Sheets API enabled
3. Service Account credentials
4. Gmail accounts with IMAP enabled

## Required Python Packages

```bash
pip install pandas google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-dotenv numpy
```

## Setup

1. Create a .env file with the following variables:

```bash
EMAIL1=your_first_email@gmail.com
EMAIL1_PASSWORD=your_first_email_app_password
EMAIL2=your_second_email@gmail.com
EMAIL2_PASSWORD=your_second_email_app_password
SPREADSHEET_ID=your_google_sheets_id
```

2. Place your Google Service Account key file as service-account-key.json in the project root

3. Create required directories:

```bash
    ./csvdata - for temporary CSV storage
    ./csvbymonth - for processed monthly data
```

## How It Works

1. Email Processing
    - Downloads CSV attachments from specified Gmail accounts
    - Stores message IDs in SQLite database to prevent duplicate processing

2. Data Processing
    - Reads CSV files and identifies channels based on IP addresses
    - Groups data by month
    - Calculates time intervals between CH01 and CH02 passages

3. Output Generation
    - Creates monthly summary files in csvbymonth directory
    - Generates two types of files:
        - data_YYYY-MM.csv: Raw processed data
        - intervals_YYYY-MM.csv: Calculated time intervals

4. Google Sheets Integration
    - Creates monthly sheets automatically
    - Uploads interval calculations to corresponding sheets
    - Names sheets in MM.YYYY format

## Output Format

The interval calculations include:

- License plate number
- Number of passages
- Total time in days
- Detailed passage information with timestamps

## Error Handling

- Creates necessary directories automatically
- Skips previously processed emails
- Handles missing or invalid data gracefully
- Logs processing errors for troubleshooting

## Usage

Run the script using:

```bash
python script_name.py
```
## Maintenance

- Regularly check the processed_emails.db size
- Monitor Gmail storage usage
- Verify Google Sheets API quota limits
- Update service account credentials before expiration

## Security Notes

- Store credentials securely
- Use app-specific passwords for Gmail
- Restrict service account permissions appropriately
- Never commit sensitive credentials to version control



## Creating and Setting Up Google Service Account

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click on "New Project" in the top-right corner
3. Enter a project name and click "Create"

### 2. Enable the Google Sheets API

1. In the Cloud Console, select your project
2. Go to "APIs & Services" > "Library"
3. Search for "Google Sheets API"
4. Click "Enable"

### 3. Create a Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the service account details:
   - Name: `vehicle-tracking-processor` (or your preferred name)
   - Description: "Service account for vehicle tracking data processing"
   - Click "Create"

### 4. Generate the Service Account Key

1. In the Service Accounts list, find your newly created service account
2. Click the three dots menu (⋮) > "Manage keys"
3. Click "Add Key" > "Create new key"
4. Choose "JSON" format
5. Click "Create"
   - The key file will automatically download to your computer

### 5. Set Up the Key File

1. Rename the downloaded JSON file to `service-account-key.json`
2. Place it in your project's root directory
3. Your key file should look similar to this:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n.....\n-----END PRIVATE KEY-----\n",
  "client_email": "service-account-name@project-id.iam.gserviceaccount.com",
  "client_id": "client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/service-account..."
}
```
### 6. Share Your Google Sheet

1. Create a new Google Sheet or open an existing one
2. Copy the Spreadsheet ID from the URL:
        URL format: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
3. Share the spreadsheet with the service account:
4. Click "Share" button
5. Add the service account email (found in client_email field of your JSON key)
6. Give "Editor" access
7. Click "Share"

### 7. Update Environment Variables

Add the Spreadsheet ID to your .env file:
```bash
SPREADSHEET_ID=your_copied_spreadsheet_id
```

### Security Best Practices
- Never commit the service-account-key.json to version control
- Add service-account-key.json to your .gitignore file
- Restrict the service account's permissions to only necessary APIs
- Regularly rotate the service account key
- Store the key file securely and limit access to authorized personnel only

### Troubleshooting

If you encounter authentication issues:

- Verify the key file is correctly named and placed in the root directory
- Ensure the Sheets API is enabled in your Google Cloud Project
- Confirm the service account has editor access to the spreadsheet
- Check that the SPREADSHEET_ID in your .env file matches your Google Sheet
- Verify your Google Cloud Project is not disabled