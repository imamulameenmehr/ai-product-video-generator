import os
import json
import time
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from src.services.google_drive import google_drive_service

admin_bp = Blueprint('admin', __name__)

# Admin password
ADMIN_PASSWORD = "PrysmosLLC@Hadi031!"

# Simple in-memory log storage (in production, use a proper logging system)
admin_logs = []

def add_log(level, message, details=None):
    """Add a log entry"""
    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'level': level,
        'message': message,
        'details': details or {}
    }
    admin_logs.append(log_entry)
    # Keep only last 100 logs
    if len(admin_logs) > 100:
        admin_logs.pop(0)

def check_admin_auth():
    """Check if user is authenticated for admin access"""
    return session.get('admin_authenticated', False)

def require_admin_auth(f):
    """Decorator to require admin authentication"""
    def decorated_function(*args, **kwargs):
        if not check_admin_auth():
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            session.permanent = True
            flash('Successfully logged in to admin dashboard', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Invalid password', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    flash('Successfully logged out', 'success')
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/admin')
@require_admin_auth
def admin_dashboard():
    """Admin dashboard"""
    # Get system status
    google_drive_status = google_drive_service.is_service_available()
    n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL', '')
    n8n_configured = bool(n8n_webhook_url)
    
    # Get Google auth status
    google_auth_status = google_drive_service.is_authenticated()
    
    status_data = {
        'google_drive_configured': google_drive_status,
        'google_auth_connected': google_auth_status,
        'n8n_webhook_configured': n8n_configured,
        'n8n_webhook_url': n8n_webhook_url,
        'total_logs': len(admin_logs)
    }
    
    return render_template('admin/dashboard.html', status=status_data)

@admin_bp.route('/admin/google-auth')
@require_admin_auth
def google_auth_page():
    """Google authentication management page"""
    # Get the current host for redirect URI
    redirect_uri = f"{request.scheme}://{request.host}/admin/google-callback"
    auth_url = google_drive_service.get_authorization_url(redirect_uri)
    google_auth_status = google_drive_service.is_authenticated()
    
    return render_template('admin/google_auth.html', 
                         auth_url=auth_url, 
                         auth_status=google_auth_status,
                         redirect_uri=redirect_uri)

@admin_bp.route('/admin/google-connect')
def google_connect():
    """Initiate Google OAuth"""
    try:
        redirect_uri = f"{request.scheme}://{request.host}/admin/google-callback"
        auth_url = google_drive_service.get_authorization_url(redirect_uri)
        
        if auth_url:
            add_log('INFO', 'Google OAuth initiated', {'redirect_uri': redirect_uri})
            return redirect(auth_url)
        else:
            add_log('ERROR', 'Failed to generate Google OAuth URL')
            flash('Failed to generate Google OAuth URL. Check credentials file.', 'error')
            return redirect(url_for('admin.google_auth_page'))
    except Exception as e:
        add_log('ERROR', 'Google OAuth error', {'error': str(e)})
        flash(f'Google OAuth error: {str(e)}', 'error')
        return redirect(url_for('admin.google_auth_page'))

@admin_bp.route('/admin/google-callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Get authorization code from callback
        authorization_code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            add_log('ERROR', 'Google OAuth error', {'error': error})
            flash(f'Google OAuth error: {error}', 'error')
            return redirect(url_for('admin.google_auth_page'))
        
        if not authorization_code:
            add_log('ERROR', 'No authorization code received')
            flash('No authorization code received from Google', 'error')
            return redirect(url_for('admin.google_auth_page'))
        
        # Handle OAuth callback
        redirect_uri = f"{request.scheme}://{request.host}/admin/google-callback"
        success = google_drive_service.handle_oauth_callback(authorization_code, redirect_uri)
        
        if success:
            add_log('SUCCESS', 'Google Drive connected successfully')
            flash('Google Drive connected successfully!', 'success')
        else:
            add_log('ERROR', 'Failed to complete Google OAuth')
            flash('Failed to complete Google OAuth. Please try again.', 'error')
        
        return redirect(url_for('admin.admin_dashboard'))
        
    except Exception as e:
        add_log('ERROR', 'Google OAuth callback error', {'error': str(e)})
        flash(f'Google OAuth callback error: {str(e)}', 'error')
        return redirect(url_for('admin.google_auth_page'))

@admin_bp.route('/admin/google-disconnect', methods=['POST'])
def google_disconnect():
    """Disconnect Google OAuth"""
    try:
        success = google_drive_service.disconnect()
        if success:
            add_log('INFO', 'Google Drive disconnected')
            flash('Google Drive disconnected successfully', 'info')
        else:
            add_log('ERROR', 'Failed to disconnect Google Drive')
            flash('Failed to disconnect Google Drive', 'error')
        
        return redirect(url_for('admin.google_auth_page'))
    except Exception as e:
        add_log('ERROR', 'Google disconnect error', {'error': str(e)})
        flash(f'Error disconnecting: {str(e)}', 'error')
        return redirect(url_for('admin.google_auth_page'))

@admin_bp.route('/admin/webhook')
def webhook_management():
    """Webhook management page"""
    current_webhook = os.getenv('N8N_WEBHOOK_URL', '')
    return render_template('admin/webhook.html', webhook_url=current_webhook)

@admin_bp.route('/admin/webhook/update', methods=['POST'])
def update_webhook():
    """Update webhook URL"""
    try:
        new_webhook_url = request.form.get('webhook_url', '').strip()
        
        if new_webhook_url:
            # In a real application, you'd update the environment variable
            # For now, we'll just log it
            add_log('INFO', 'Webhook URL updated', {'new_url': new_webhook_url})
            flash(f'Webhook URL updated to: {new_webhook_url}', 'success')
        else:
            add_log('WARNING', 'Webhook URL cleared')
            flash('Webhook URL cleared', 'warning')
        
        return redirect(url_for('admin.webhook_management'))
    except Exception as e:
        add_log('ERROR', 'Webhook update error', {'error': str(e)})
        flash(f'Error updating webhook: {str(e)}', 'error')
        return redirect(url_for('admin.webhook_management'))

@admin_bp.route('/admin/webhook/test', methods=['POST'])
def test_webhook():
    """Test webhook connectivity"""
    try:
        webhook_url = os.getenv('N8N_WEBHOOK_URL')
        if not webhook_url:
            add_log('ERROR', 'No webhook URL configured for testing')
            flash('No webhook URL configured', 'error')
            return redirect(url_for('admin.webhook_management'))
        
        # Test payload
        test_payload = {
            'test': True,
            'timestamp': datetime.now().isoformat(),
            'message': 'Test from admin panel'
        }
        
        import requests
        response = requests.post(webhook_url, json=test_payload, timeout=10)
        
        if response.status_code == 200:
            add_log('SUCCESS', 'Webhook test successful', {'status_code': response.status_code})
            flash('Webhook test successful!', 'success')
        else:
            add_log('WARNING', 'Webhook test returned non-200 status', {'status_code': response.status_code})
            flash(f'Webhook test returned status: {response.status_code}', 'warning')
            
    except Exception as e:
        add_log('ERROR', 'Webhook test failed', {'error': str(e)})
        flash(f'Webhook test failed: {str(e)}', 'error')
    
    return redirect(url_for('admin.webhook_management'))

@admin_bp.route('/admin/logs')
def view_logs():
    """View system logs"""
    # Get filter parameters
    level_filter = request.args.get('level', 'ALL')
    limit = int(request.args.get('limit', 50))
    
    # Filter logs
    filtered_logs = admin_logs
    if level_filter != 'ALL':
        filtered_logs = [log for log in admin_logs if log['level'] == level_filter]
    
    # Limit results
    filtered_logs = filtered_logs[-limit:]
    filtered_logs.reverse()  # Show newest first
    
    return render_template('admin/logs.html', 
                         logs=filtered_logs, 
                         current_filter=level_filter,
                         current_limit=limit)

@admin_bp.route('/admin/logs/clear', methods=['POST'])
def clear_logs():
    """Clear all logs"""
    global admin_logs
    admin_logs = []
    add_log('INFO', 'Logs cleared by admin')
    flash('Logs cleared successfully', 'success')
    return redirect(url_for('admin.view_logs'))

@admin_bp.route('/admin/api/status')
def api_status():
    """API endpoint for system status"""
    google_drive_status = google_drive_service.is_service_available()
    google_auth_status = google_drive_service.is_authenticated()
    n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL', '')
    
    return jsonify({
        'google_drive_configured': google_drive_status,
        'google_auth_connected': google_auth_status,
        'n8n_webhook_configured': bool(n8n_webhook_url),
        'n8n_webhook_url': n8n_webhook_url,
        'total_logs': len(admin_logs),
        'timestamp': datetime.now().isoformat()
    })

# Initialize some sample logs
add_log('INFO', 'Admin panel initialized')
add_log('INFO', 'System startup completed')

