# Google Drive Integration Setup Guide

This guide explains how to set up automated data synchronization with Google Drive for the Ukulele Tuesday Stats application.

## Overview

The application can automatically fetch song sheet metadata from Google Drive folders instead of requiring manual dataset builds. This is done using:

- Google Drive API with proper authentication
- Streamlit caching for performance (1-hour cache TTL)
- Fallback to local JSON file if Google Drive is unavailable

## Prerequisites

1. Google Cloud Project with Google Drive API enabled
2. Service account with appropriate permissions
3. Access to the Google Drive folders containing song sheets

## Setup Steps

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the Google Drive API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

### 2. Create a Service Account

1. Navigate to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Provide a name and description (e.g., "Ukulele Tuesday Stats")
4. Grant the service account appropriate roles (you may not need any specific project roles)
5. Create and download a JSON key file for the service account

### 3. Grant Google Drive Access

The service account needs access to the Google Drive folders containing song sheets:

1. Share each Google Drive folder with the service account email address
2. Grant "Viewer" permissions (read-only access is sufficient)
3. Note down the folder IDs from the Google Drive URLs

**Finding Folder IDs:**
- Open the folder in Google Drive
- The folder ID is in the URL: `https://drive.google.com/drive/folders/{FOLDER_ID}`

### 4. Configure Application Secrets

#### For Local Development

1. Copy the secrets template:
   ```bash
   cp secrets.toml.template .streamlit/secrets.toml
   ```

2. Edit `.streamlit/secrets.toml`:
   ```toml
   [gdrive]
   folder_ids = "folder_id_1,folder_id_2,folder_id_3"
   # Optional: for service account impersonation
   # target_principal = "service-account@project-id.iam.gserviceaccount.com"
   ```

3. Set up authentication:
   
   **Option A: Application Default Credentials (Recommended for development)**
   ```bash
   gcloud auth application-default login
   ```
   
   **Option B: Service Account Key File**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   ```

#### For Streamlit Cloud Deployment

1. In your Streamlit Cloud dashboard, go to app settings
2. Add secrets in the "Secrets" section:
   ```toml
   [gdrive]
   folder_ids = "folder_id_1,folder_id_2,folder_id_3"
   target_principal = "service-account@project-id.iam.gserviceaccount.com"
   
   # Add service account credentials directly
   GOOGLE_APPLICATION_CREDENTIALS_JSON = '''
   {
     "type": "service_account",
     "project_id": "your-project-id",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "client_email": "service-account@project-id.iam.gserviceaccount.com",
     "client_id": "...",
     "auth_uri": "https://accounts.google.com/o/oauth2/auth",
     "token_uri": "https://oauth2.googleapis.com/token",
     "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
     "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/service-account%40project-id.iam.gserviceaccount.com"
   }
   '''
   ```

### 5. Optional: Service Account Impersonation

For enhanced security, you can set up impersonation:

1. Create a dedicated service account for the application
2. Grant your primary account `roles/iam.serviceAccountTokenCreator` on the target service account
3. Use the target service account email in the `target_principal` setting

## Testing the Setup

1. Run the Streamlit app:
   ```bash
   streamlit run main.py
   ```

2. Click the "🔧 Test Config" button to verify your configuration

3. The app should automatically load data from Google Drive

4. Use the "🔄 Refresh Data" button to clear cache and reload fresh data

## Troubleshooting

### Common Issues

1. **"Missing required secret" error**
   - Ensure `.streamlit/secrets.toml` exists and contains the `[gdrive]` section
   - Verify `folder_ids` is properly set

2. **"Access denied" errors**
   - Check that the service account has access to the Google Drive folders
   - Verify the folder IDs are correct

3. **"Authentication failed" errors**
   - Ensure Google Cloud credentials are properly set up
   - Check that the Google Drive API is enabled in your project

4. **App falls back to local JSON file**
   - This is expected behavior when Google Drive is unavailable
   - Check the error messages for specific authentication issues

### Logs and Debugging

- The app will display detailed error messages in the Streamlit interface
- Use the "Test Config" button to diagnose configuration issues
- Check that folder IDs are accessible and contain the expected files

## Security Best Practices

1. Use service accounts with minimal required permissions
2. Regularly rotate service account keys
3. Consider using service account impersonation for production deployments
4. Never commit service account keys or secrets to version control
5. Monitor Google Cloud audit logs for service account usage

## Performance Notes

- Data is cached for 1 hour by default to minimize API calls
- Initial load may take a few seconds depending on the number of files
- Subsequent loads will be instant (served from cache)
- Use the refresh button only when you need to fetch the latest data