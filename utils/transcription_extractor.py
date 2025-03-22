import logging
import time

def extract_transcription(spotify_browser, episode_url):
    """
    Extract transcription from a Spotify episode.
    
    Args:
        spotify_browser: An initialized SpotifyBrowser instance with active login
        episode_url: URL of the Spotify episode to extract transcription from
        
    Returns:
        str: The transcription text if found, None otherwise
    """
    try:
        # Navigate to the episode page
        if not spotify_browser.navigate_to_episode(episode_url):
            logging.error(f"Failed to navigate to episode: {episode_url}")
            return None
        
        # Give the page some time to fully load
        time.sleep(3)
        
        # Find and click on the transcription button
        if not spotify_browser.find_transcription_button():
            logging.warning(f"No transcription button found for episode: {episode_url}")
            return None
        
        # Allow transcript to load
        time.sleep(2)
        
        # Extract the transcription text
        transcription = spotify_browser.extract_transcription_text()
        
        if not transcription:
            logging.warning(f"No transcription text found for episode: {episode_url}")
            return None
        
        return transcription
        
    except Exception as e:
        logging.error(f"Error extracting transcription: {str(e)}")
        return None
