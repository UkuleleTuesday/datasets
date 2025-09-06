"""
Google Drive data fetching module for Streamlit app.

This module provides functions to fetch song sheets data from Google Drive
using Streamlit's caching and secrets management.
"""
import json
import os
import streamlit as st
from typing import List, Optional, Dict, Any
from google.auth import credentials, default, impersonated_credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_credentials(
    scopes: List[str], target_principal: Optional[str] = None
) -> credentials.Credentials:
    """
    Get Google API credentials for given scopes, with optional impersonation.

    Args:
        scopes: List of OAuth2 scopes to request.
        target_principal: The service account to impersonate.

    Returns:
        A Google credentials object.
    """
    # Try to get credentials from Streamlit secrets first
    try:
        if "GOOGLE_APPLICATION_CREDENTIALS_JSON" in st.secrets:
            # Parse service account JSON from secrets
            service_account_info = json.loads(st.secrets["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=scopes
            )
        else:
            # Fall back to default credentials (ADC or environment)
            creds, _ = default(scopes=scopes)
    except Exception:
        # Fall back to default credentials
        creds, _ = default(scopes=scopes)

    if target_principal:
        creds = impersonated_credentials.Credentials(
            source_credentials=creds,
            target_principal=target_principal,
            target_scopes=scopes,
        )

    return creds


@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_song_sheets_data(
    folder_ids: List[str], target_principal: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch song sheets data from Google Drive folders.
    
    This function is cached by Streamlit to avoid repeated API calls.
    
    Args:
        folder_ids: List of Google Drive folder IDs to query
        target_principal: Optional service account to impersonate
        
    Returns:
        List of file data dictionaries with properties
        
    Raises:
        Exception: If there's an error fetching data from Google Drive
    """
    try:
        creds = get_credentials(
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
            target_principal=target_principal,
        )
        service = build("drive", "v3", credentials=creds)

        all_files = []
        for folder_id in folder_ids:
            page_token = None
            while True:
                response = (
                    service.files()
                    .list(
                        q=f"'{folder_id}' in parents and trashed=false",
                        fields="nextPageToken, files(id, name, properties)",
                        pageToken=page_token,
                    )
                    .execute()
                )
                all_files.extend(response.get("files", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        # Sort properties and files for consistency
        for file_data in all_files:
            if "properties" in file_data and file_data["properties"]:
                file_data["properties"] = dict(sorted(file_data["properties"].items()))

        all_files.sort(key=lambda item: item["name"])
        
        return all_files

    except HttpError as error:
        st.error(f"Google Drive API error: {error}")
        raise Exception(f"Failed to fetch data from Google Drive: {error}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        raise Exception(f"Unexpected error fetching data: {e}")


def load_song_sheets_data_from_secrets() -> List[Dict[str, Any]]:
    """
    Load song sheets data using configuration from Streamlit secrets.
    
    Expected secrets structure:
    [gdrive]
    folder_ids = "folder1,folder2,folder3"
    target_principal = "service-account@project.iam.gserviceaccount.com"  # optional
    
    Returns:
        List of file data dictionaries with properties
        
    Raises:
        Exception: If secrets are not configured properly or API calls fail
    """
    try:
        # Check if secrets are available
        if "gdrive" not in st.secrets:
            raise KeyError("gdrive section not found in secrets")
            
        # Get configuration from Streamlit secrets
        folder_ids_str = st.secrets["gdrive"]["folder_ids"]
        if not folder_ids_str or folder_ids_str.strip() == "":
            raise ValueError("folder_ids cannot be empty")
            
        folder_ids = [folder_id.strip() for folder_id in folder_ids_str.split(",") if folder_id.strip()]
        
        if not folder_ids:
            raise ValueError("No valid folder IDs found")
        
        # Optional target principal for impersonation
        target_principal = st.secrets["gdrive"].get("target_principal", None)
        if target_principal and target_principal.strip() == "":
            target_principal = None
        
        return fetch_song_sheets_data(folder_ids, target_principal)
        
    except KeyError as e:
        error_msg = f"Missing required secret: {e}. Please configure 'gdrive.folder_ids' in secrets."
        st.error(error_msg)
        raise Exception(error_msg)
    except ValueError as e:
        error_msg = f"Invalid configuration: {e}"
        st.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        st.error(f"Failed to load data from Google Drive: {e}")
        raise


def clear_data_cache():
    """Clear the cached song sheets data."""
    fetch_song_sheets_data.clear()


def test_configuration() -> bool:
    """
    Test the Google Drive configuration without making API calls.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        # Check if secrets are available
        if "gdrive" not in st.secrets:
            st.error("❌ Missing 'gdrive' section in secrets configuration")
            st.info("📝 Copy `secrets.toml.template` to `.streamlit/secrets.toml` and configure your values.")
            return False
            
        # Check folder_ids
        folder_ids_str = st.secrets["gdrive"].get("folder_ids", "")
        if not folder_ids_str or folder_ids_str.strip() == "":
            st.error("❌ Missing or empty 'folder_ids' in gdrive configuration")
            st.info("📝 Add your Google Drive folder IDs to the configuration.")
            return False
            
        folder_ids = [folder_id.strip() for folder_id in folder_ids_str.split(",") if folder_id.strip()]
        if not folder_ids:
            st.error("❌ No valid folder IDs found in configuration")
            st.info("📝 Ensure folder IDs are comma-separated and not empty.")
            return False
            
        st.success(f"✅ Found {len(folder_ids)} folder ID(s)")
        
        # Check optional target principal
        target_principal = st.secrets["gdrive"].get("target_principal", None)
        if target_principal and target_principal.strip():
            st.info(f"ℹ️ Using impersonation with: {target_principal}")
        else:
            st.info("ℹ️ Using default credentials (no impersonation)")
        
        # Check for credentials
        if "GOOGLE_APPLICATION_CREDENTIALS_JSON" in st.secrets:
            st.success("✅ Service account JSON found in secrets")
        else:
            st.info("ℹ️ No service account JSON in secrets - using default credentials")
            
        st.info("🔧 Configuration appears valid. Try the 'Refresh Data' button to test the actual connection.")
        return True
        
    except Exception as e:
        st.error(f"❌ Configuration error: {e}")
        return False