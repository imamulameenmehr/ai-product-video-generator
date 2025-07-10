import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

class GoogleDriveService:
    def __init__(self):
        self.service = None
        self.credentials = None
        self.folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        self.credentials_file = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE', 'credentials.json')
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive service with OAuth credentials"""
        try:
            credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.credentials_file)
            
            if os.path.exists(credentials_path):
                print(f"Google Drive credentials file found: {credentials_path}")
                # Check if we have stored credentials
                token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')
                if os.path.exists(token_path):
                    self.credentials = Credentials.from_authorized_user_file(token_path)
                    if self.credentials and self.credentials.valid:
                        self.service = build('drive', 'v3', credentials=self.credentials)
                        print("Google Drive service initialized with stored credentials")
                    else:
                        print("Stored credentials are invalid or expired")
                        self.service = None
                else:
                    print("No stored credentials found. OAuth flow required.")
                    self.service = None
            else:
                print("Warning: No Google Drive credentials found. Upload functionality will be disabled.")
                self.service = None
            
        except Exception as e:
            print(f"Error initializing Google Drive service: {str(e)}")
            self.service = None
    
    def get_authorization_url(self, redirect_uri=None):
        """
        Get the authorization URL for OAuth setup
        """
        try:
            credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.credentials_file)
            
            if not os.path.exists(credentials_path):
                print(f"Credentials file not found: {credentials_path}")
                return None
            
            # Use provided redirect URI or default to localhost
            if not redirect_uri:
                redirect_uri = 'http://localhost:5000/admin/google-callback'
            
            # Create flow for OAuth
            flow = Flow.from_client_secrets_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/drive.file'],
                redirect_uri=redirect_uri
            )
            
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            print(f"Generated authorization URL with redirect: {redirect_uri}")
            return authorization_url
            
        except Exception as e:
            print(f"Error getting authorization URL: {str(e)}")
            return None
    
    def handle_oauth_callback(self, authorization_code, redirect_uri=None):
        """
        Handle OAuth callback and store credentials
        """
        try:
            credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.credentials_file)
            
            if not redirect_uri:
                redirect_uri = 'http://localhost:5000/admin/google-callback'
            
            # Create flow
            flow = Flow.from_client_secrets_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/drive.file'],
                redirect_uri=redirect_uri
            )
            
            # Exchange authorization code for credentials
            flow.fetch_token(code=authorization_code)
            
            # Store credentials
            self.credentials = flow.credentials
            token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')
            
            with open(token_path, 'w') as token_file:
                token_file.write(self.credentials.to_json())
            
            # Initialize service
            self.service = build('drive', 'v3', credentials=self.credentials)
            print("Google Drive OAuth completed successfully")
            return True
            
        except Exception as e:
            print(f"Error handling OAuth callback: {str(e)}")
            return False
    
    def disconnect(self):
        """
        Disconnect Google Drive by removing stored credentials
        """
        try:
            token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')
            if os.path.exists(token_path):
                os.remove(token_path)
            
            self.credentials = None
            self.service = None
            print("Google Drive disconnected successfully")
            return True
            
        except Exception as e:
            print(f"Error disconnecting Google Drive: {str(e)}")
            return False
    
    def upload_file(self, file_path, filename, folder_id=None):
        """
        Upload a file to Google Drive and return the public URL
        
        Args:
            file_path (str): Local path to the file
            filename (str): Name for the file in Google Drive
            folder_id (str): Optional folder ID to upload to
            
        Returns:
            str: Public URL of the uploaded file or None if failed
        """
        if not self.service:
            print("Google Drive service not available")
            return None
        
        try:
            # File metadata
            file_metadata = {
                'name': filename
            }
            
            # Add to folder if specified
            if folder_id or self.folder_id:
                file_metadata['parents'] = [folder_id or self.folder_id]
            
            # Upload file
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            
            # Make file publicly accessible
            self.service.permissions().create(
                fileId=file_id,
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()
            
            # Return public URL
            public_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
            print(f"File uploaded successfully: {public_url}")
            return public_url
            
        except Exception as e:
            print(f"Error uploading file to Google Drive: {str(e)}")
            return None
    
    def is_service_available(self):
        """Check if Google Drive service is available"""
        return self.service is not None
    
    def is_authenticated(self):
        """Check if user is authenticated with Google Drive"""
        return self.credentials is not None and self.credentials.valid

# Create a global instance
google_drive_service = GoogleDriveService()

