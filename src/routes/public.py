from flask import Blueprint, render_template, redirect, url_for

# Create blueprint for public pages
public_bp = Blueprint('public', __name__, template_folder='../templates/public')

@public_bp.route('/home')
def home():
    """Home/Landing page"""
    return render_template('public/home.html')

@public_bp.route('/features')
def features():
    """Features page"""
    return render_template('public/features.html')

@public_bp.route('/about')
def about():
    """About page"""
    return render_template('public/about.html')

@public_bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('public/contact.html')

@public_bp.route('/landing')
def landing():
    """Alternative landing page route"""
    return render_template('public/home.html')

# Additional utility routes
@public_bp.route('/privacy')
def privacy():
    """Privacy policy page - redirect to contact for now"""
    return redirect(url_for('public.contact'))

@public_bp.route('/terms')
def terms():
    """Terms of service page - redirect to contact for now"""
    return redirect(url_for('public.contact'))

@public_bp.route('/help')
def help():
    """Help page - redirect to contact for now"""
    return redirect(url_for('public.contact'))

