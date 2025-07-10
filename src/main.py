import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.video_generator import video_generator_bp
from src.routes.admin import admin_bp
from src.routes.public import public_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')

# Enable sessions for admin panel
app.config['SESSION_TYPE'] = 'filesystem'

# Enable CORS for all routes
CORS(app)

# Register blueprints - PUBLIC PAGES FIRST (specific routes)
app.register_blueprint(public_bp, url_prefix='/')  # Public pages at root
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(video_generator_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/')  # Admin at root like before

# uncomment if you need to use database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

# RESTORE ORIGINAL CATCH-ALL ROUTE FOR REACT APP
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # Handle specific public pages first
    if path == '':
        # Check if this is a request for the home page
        # If no specific route matched, serve React app
        pass
    
    # Skip admin routes - let admin blueprint handle them
    if path.startswith('admin'):
        return "Admin route handled by blueprint", 404
        
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
