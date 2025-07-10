import os
import json
import time
import requests
import re
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from src.services.google_drive import google_drive_service

video_generator_bp = Blueprint('video_generator', __name__)

# Configuration
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Environment variables
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL')
GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

# Avatar URLs mapping
AVATAR_URLS = {
    'Anna': 'https://drive.google.com/file/d/1LXdfsyTJgprNJ2r9SQLG8YFiSFzJHPSm/view?usp=drive_link',
    'David': 'https://drive.google.com/file/d/1JEDjfw8jdd0wNDBZYHiutRnirltvTYIe/view?usp=drive_link',
    'Emma': 'https://drive.google.com/file/d/1e13SnuKVFYGWSGg7RRNj4W7nuhaKdciU/view?usp=drive_link',
    'James': 'https://drive.google.com/file/d/1ICrWMOidMzob2I5CKKDZsqSUYVJFTrAa/view?usp=sharing',
    'Marcus': 'https://drive.google.com/file/d/1FE4weyK7cvqnj4hQ23_Dc9ANNKYgSRLA/view?usp=drive_link',
    'Sophia': 'https://drive.google.com/file/d/1pCoVW1YPwCXe74-9fjnbK3LQ5d17Ygxr/view?usp=sharing'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_to_n8n_webhook(payload):
    """
    Send payload to n8n webhook
    """
    if not N8N_WEBHOOK_URL:
        print("Warning: N8N_WEBHOOK_URL not configured")
        return False
    
    try:
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=30)
        print(f"n8n webhook response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending to n8n webhook: {str(e)}")
        return False

@video_generator_bp.route('/generate-video', methods=['POST'])
def generate_video():
    try:
        # Validate request
        if 'productImage' not in request.files:
            return jsonify({'error': 'No product image uploaded'}), 400
        
        file = request.files['productImage']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WEBP'}), 400
        
        # Get form data
        avatar = request.form.get('avatar')
        product_description = request.form.get('productDescription')
        avatar_script = request.form.get('avatarScript')
        email = request.form.get('email')
        
        # Validate required fields
        if not all([avatar, product_description, avatar_script, email]):
            return jsonify({'error': 'All fields are required'}), 400
        
        if avatar not in AVATAR_URLS:
            return jsonify({'error': 'Invalid avatar selection'}), 400
        
        # Validate email format
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Check if Google Drive service is available
        if not google_drive_service.is_service_available():
            return jsonify({'error': 'Google Drive service not available. Please check configuration.'}), 500
        
        # Create upload directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = str(int(time.time()))
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Check file size
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            os.remove(file_path)
            return jsonify({'error': 'File size exceeds 10MB limit'}), 400
        
        # Upload to Google Drive
        public_image_url = google_drive_service.upload_file(
            file_path, 
            unique_filename, 
            GOOGLE_DRIVE_FOLDER_ID
        )
        
        # Clean up local file
        try:
            os.remove(file_path)
        except:
            pass
        
        if not public_image_url:
            return jsonify({'error': 'Failed to upload image to Google Drive'}), 500
        
        # Prepare payload for n8n
        payload = {
            'productImageUrl': public_image_url,
            'avatar': avatar,
            'avatarImageUrl': AVATAR_URLS[avatar],
            'productDescription': product_description,
            'avatarScript': avatar_script,
            'email': email,
            'timestamp': timestamp,
            'requestId': f"req_{timestamp}_{avatar.lower()}"
        }
        
        # Send to n8n webhook
        webhook_success = send_to_n8n_webhook(payload)
        
        if webhook_success:
            return jsonify({
                'success': True,
                'message': 'Video generation request submitted successfully',
                'requestId': payload['requestId']
            }), 200
        else:
            return jsonify({'error': 'Failed to process video generation request'}), 500
            
    except Exception as e:
        print(f"Error in generate_video: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@video_generator_bp.route('/avatars', methods=['GET'])
def get_avatars():
    """
    Get list of available avatars with their image URLs
    """
    avatars = []
    for name, url in AVATAR_URLS.items():
        # Convert to thumbnail URL
        file_id = url.split('/d/')[1].split('/')[0] if '/d/' in url else None
        thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w400" if file_id else url
        
        avatars.append({
            'name': name,
            'imageUrl': thumbnail_url,
            'originalUrl': url
        })
    
    return jsonify({'avatars': avatars}), 200

@video_generator_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    google_drive_status = google_drive_service.is_service_available()
    n8n_webhook_configured = bool(N8N_WEBHOOK_URL)
    
    return jsonify({
        'status': 'healthy',
        'service': 'video-generator-api',
        'version': '1.0.0',
        'google_drive_available': google_drive_status,
        'n8n_webhook_configured': n8n_webhook_configured
    }), 200

@video_generator_bp.route('/auth-url', methods=['GET'])
def get_auth_url():
    """
    Get Google Drive authorization URL for OAuth setup
    """
    auth_url = google_drive_service.get_authorization_url()
    if auth_url:
        return jsonify({
            'authorization_url': auth_url,
            'redirect_uri': 'https://dyh6i3cqype5.manus.space/oauth/callback',
            'instructions': 'Add this redirect URI to your Google Console OAuth settings'
        }), 200
    else:
        return jsonify({'error': 'Could not generate authorization URL'}), 500

@video_generator_bp.route('/config', methods=['GET'])
def get_config():
    """
    Get configuration status
    """
    return jsonify({
        'google_drive_configured': google_drive_service.is_service_available(),
        'n8n_webhook_configured': bool(N8N_WEBHOOK_URL),
        'upload_folder': UPLOAD_FOLDER,
        'max_file_size_mb': MAX_FILE_SIZE / 1024 / 1024,
        'allowed_extensions': list(ALLOWED_EXTENSIONS)
    }), 200

