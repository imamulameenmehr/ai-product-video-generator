import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class GoogleDriveService:
    def __init__(self):
        self.service = None
        self.credentials = None
        self.folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        self._initialize_service()
    
    def _initialize_service(self):
        try:
            token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')

            if os.path.exists(token_path):
                self.credentials = Credentials.from_authorized_user_file(token_path)
                if self.credentials and self.credentials.valid:
                    self.service = build('drive', 'v3', credentials=self.credentials)
                    print("✅ Google Drive service initialized with stored credentials")
                else:
                    print("⚠️ Stored credentials are invalid or expired")
            else:
                print("🔁 No stored credentials found. OAuth flow required.")
        except Exception as e:
            print(f"❌ Error initializing Google Drive service: {str(e)}")

    def get_authorization_url(self, redirect_uri=None):
        try:
            credentials_json = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE")
            if not credentials_json:
                print("❌ GOOGLE_DRIVE_CREDENTIALS_FILE not set")
                return None

            credentials_data = json.loads(credentials_json)
            if not redirect_uri:
                redirect_uri = 'https://ai-product-video-generator-production.up.railway.app/admin/google-callback'

            flow = Flow.from_client_config(
                credentials_data,
                scopes=['https://www.googleapis.com/auth/drive.file'],
                redirect_uri=redirect_uri
            )

            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )

            print(f"✅ Generated Google OAuth URL: {auth_url}")
            return auth_url

        except Exception as e:
            print(f"❌ Error generating OAuth URL: {str(e)}")
            return None

    def handle_oauth_callback(self, authorization_code, redirect_uri=None):
        try:
            credentials_json = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE")
            if not credentials_json:
                print("❌ GOOGLE_DRIVE_CREDENTIALS_FILE not set")
                return False

            credentials_data = json.loads(credentials_json)
            if not redirect_uri:
                redirect_uri = 'https://ai-product-video-generator-production.up.railway.app/admin/google-callback'

            flow = Flow.from_client_config(
                credentials_data,
                scopes=['https://www.googleapis.com/auth/drive.file'],
                redirect_uri=redirect_uri
            )

            flow.fetch_token(code=authorization_code)
            self.credentials = flow.credentials

            token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')
            with open(token_path, 'w') as f:
                f.write(self.credentials.to_json())

            self.service = build('drive', 'v3', credentials=self.credentials)
            print("✅ OAuth token exchange completed successfully")
            return True

        except Exception as e:
            print(f"❌ OAuth callback error: {str(e)}")
            return False

    def disconnect(self):
        try:
            token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')
            if os.path.exists(token_path):
                os.remove(token_path)
            self.credentials = None
            self.service = None
            print("✅ Google Drive disconnected successfully")
            return True

        except Exception as e:
            print(f"❌ Error disconnecting Google Drive: {str(e)}")
            return False

    def upload_file(self, file_path, filename, folder_id=None):
        if not self.service:
            print("❌ Google Drive service not available")
            return None
        try:
            file_metadata = {'name': filename}
            if folder_id or self.folder_id:
                file_metadata['parents'] = [folder_id or self.folder_id]

            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            file_id = file.get('id')

            self.service.permissions().create(
                fileId=file_id,
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()

            public_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
            print(f"✅ File uploaded: {public_url}")
            return public_url

        except Exception as e:
            print(f"❌ Error uploading file: {str(e)}")
            return None

    def is_service_available(self):
        return self.service is not None

    def is_authenticated(self):
        return self.credentials is not None and self.credentials.valid

# Global instance
google_drive_service = GoogleDriveService()
