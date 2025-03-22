import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from utils.spotify_browser import SpotifyBrowser
from utils.transcription_extractor import extract_transcription
import urllib.parse

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "spotify-transcription-app-secret")

# Global variable to store browser instance
spotify_browser = None

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    """Handle Spotify login form submission."""
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Please provide both username and password', 'danger')
        return redirect(url_for('index'))
    
    # Store credentials in session for later use
    session['spotify_username'] = username
    session['spotify_password'] = password
    
    # Try to log in to Spotify
    try:
        global spotify_browser
        # Close existing browser if one exists
        if spotify_browser:
            spotify_browser.close()
            
        # Create new browser instance and login
        spotify_browser = SpotifyBrowser()
        success = spotify_browser.login(username, password)
        
        if success:
            flash('Successfully logged in to Spotify', 'success')
            return redirect(url_for('index'))
        else:
            flash('Failed to log in to Spotify. Please check your credentials.', 'danger')
            # Clear session credentials on failure
            session.pop('spotify_username', None)
            session.pop('spotify_password', None)
            return redirect(url_for('index'))
            
    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        flash(f'Error during login: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/extract', methods=['POST'])
def extract():
    """Extract transcription from a Spotify episode URL."""
    episode_url = request.form.get('episode_url')
    
    if not episode_url:
        flash('Please provide a Spotify episode URL', 'danger')
        return redirect(url_for('index'))
    
    # Validate URL is from Spotify
    parsed_url = urllib.parse.urlparse(episode_url)
    if not (parsed_url.netloc == 'open.spotify.com' and 'episode' in parsed_url.path):
        flash('Please provide a valid Spotify episode URL (e.g., https://open.spotify.com/episode/...)', 'danger')
        return redirect(url_for('index'))
    
    # Check if user is logged in
    if 'spotify_username' not in session or 'spotify_password' not in session:
        flash('Please log in to Spotify first', 'danger')
        return redirect(url_for('index'))
    
    try:
        global spotify_browser
        # If browser not initialized or closed, create a new one and login
        if not spotify_browser or not spotify_browser.is_active():
            spotify_browser = SpotifyBrowser()
            success = spotify_browser.login(session['spotify_username'], session['spotify_password'])
            if not success:
                flash('Failed to log in to Spotify. Please try logging in again.', 'danger')
                return redirect(url_for('index'))
        
        # Extract transcription
        transcription = extract_transcription(spotify_browser, episode_url)
        
        if transcription:
            return render_template('index.html', transcription=transcription, episode_url=episode_url)
        else:
            flash('No transcription found for this episode', 'warning')
            return redirect(url_for('index'))
            
    except Exception as e:
        logging.error(f"Extraction error: {str(e)}")
        flash(f'Error during transcription extraction: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/logout', methods=['POST'])
def logout():
    """Log out from Spotify and close browser."""
    global spotify_browser
    if spotify_browser:
        try:
            spotify_browser.close()
        except Exception as e:
            logging.error(f"Error closing browser: {str(e)}")
        spotify_browser = None
    
    # Clear session data
    session.pop('spotify_username', None)
    session.pop('spotify_password', None)
    
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/api/transcription', methods=['POST'])
def api_transcription():
    """API endpoint to get transcription for a Spotify episode."""
    data = request.json
    
    if not data or 'episode_url' not in data:
        return jsonify({'error': 'Missing episode_url parameter'}), 400
    
    episode_url = data['episode_url']
    username = data.get('username')
    password = data.get('password')
    
    # Validate URL
    parsed_url = urllib.parse.urlparse(episode_url)
    if not (parsed_url.netloc == 'open.spotify.com' and 'episode' in parsed_url.path):
        return jsonify({'error': 'Invalid Spotify episode URL'}), 400
    
    # Check credentials
    if not username or not password:
        return jsonify({'error': 'Missing Spotify credentials'}), 400
    
    try:
        # Create a new browser instance for API requests to avoid conflicts
        api_browser = SpotifyBrowser(headless=True)  # Use headless mode for API
        
        # Login
        login_success = api_browser.login(username, password)
        if not login_success:
            api_browser.close()
            return jsonify({'error': 'Failed to login to Spotify'}), 401
        
        # Extract transcription
        transcription = extract_transcription(api_browser, episode_url)
        
        # Close browser
        api_browser.close()
        
        if transcription:
            return jsonify({
                'success': True,
                'episode_url': episode_url,
                'transcription': transcription
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No transcription found for this episode'
            }), 404
            
    except Exception as e:
        logging.error(f"API extraction error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error="Internal server error"), 500
