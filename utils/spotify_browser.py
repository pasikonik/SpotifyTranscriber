import logging
import time
from playwright.sync_api import sync_playwright

class SpotifyBrowser:
    """Class to handle Spotify web browser automation."""
    
    def __init__(self, headless=False):
        """Initialize the browser with Playwright.
        
        Args:
            headless (bool): Whether to run the browser in headless mode.
        """
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._initialize_browser()
    
    def _initialize_browser(self):
        """Initialize the browser with Playwright."""
        try:
            self.playwright = sync_playwright().start()
            # Use system installed browsers by specifying the executable path
            executable_path = "/usr/bin/chromium"
            self.browser = self.playwright.chromium.launch(
                headless=self.headless, 
                executable_path=executable_path
            )
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            logging.debug("Browser initialized successfully with system Chromium")
        except Exception as e:
            logging.error(f"Failed to initialize browser: {str(e)}")
            # Try Firefox as a fallback
            try:
                executable_path = "/usr/bin/firefox-esr"
                logging.debug(f"Attempting to use Firefox at: {executable_path}")
                self.browser = self.playwright.firefox.launch(
                    headless=self.headless, 
                    executable_path=executable_path
                )
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                logging.debug("Browser initialized successfully with system Firefox")
            except Exception as e2:
                logging.error(f"Also failed with Firefox: {str(e2)}")
                self.close()
                raise
    
    def is_active(self):
        """Check if the browser is still active."""
        return self.page is not None and self.browser is not None
    
    def login(self, username, password):
        """Log in to Spotify web player.
        
        Args:
            username (str): Spotify username or email
            password (str): Spotify password
            
        Returns:
            bool: True if login was successful, False otherwise
        """
        try:
            # Navigate to Spotify login page
            self.page.goto('https://accounts.spotify.com/login')
            
            # Wait for the login form to appear
            self.page.wait_for_selector('#login-username', timeout=30000)
            
            # Fill in username and password
            self.page.fill('#login-username', username)
            self.page.fill('#login-password', password)
            
            # Click login button
            self.page.click('#login-button')
            
            # Check if login was successful by looking for typical elements on the logged-in page
            # or error messages
            try:
                # Wait for potential error message
                error_selector = '.alert.alert-warning'
                has_error = self.page.wait_for_selector(error_selector, timeout=5000, state='attached')
                if has_error:
                    error_text = self.page.text_content(error_selector)
                    logging.error(f"Login error: {error_text}")
                    return False
            except:
                # No error found, continue
                pass
            
            # Wait for redirect to web player or home page after successful login
            success_selectors = [
                'a[href="/collection"]',  # Navigation menu item
                '[data-testid="spotify-logo"]',  # Spotify logo in web player
                '[data-testid="home-active-icon"]'  # Home icon when logged in
            ]
            
            # Wait for any of the success indicators with a longer timeout
            for selector in success_selectors:
                try:
                    if self.page.wait_for_selector(selector, timeout=10000, state='visible'):
                        logging.debug("Login successful, found element: " + selector)
                        return True
                except:
                    continue
            
            # If we reach here, login might have failed or page structure changed
            logging.warning("Login result unclear, checking URL to verify")
            
            # Check if we're redirected to a Spotify URL that indicates success
            current_url = self.page.url
            if 'open.spotify.com' in current_url or 'accounts.spotify.com/en/status' in current_url:
                logging.debug(f"Login appears successful based on URL: {current_url}")
                return True
            
            logging.error(f"Login failed, current URL: {current_url}")
            return False
            
        except Exception as e:
            logging.error(f"Error during login: {str(e)}")
            return False
    
    def navigate_to_episode(self, episode_url):
        """Navigate to a Spotify episode page.
        
        Args:
            episode_url (str): URL of the Spotify episode
            
        Returns:
            bool: True if navigation was successful
        """
        try:
            # Navigate to the episode page
            self.page.goto(episode_url)
            
            # Wait for the episode page to load
            self.page.wait_for_selector('[data-testid="episode-page"]', timeout=30000)
            
            logging.debug(f"Successfully navigated to episode: {episode_url}")
            return True
        except Exception as e:
            logging.error(f"Failed to navigate to episode {episode_url}: {str(e)}")
            return False
    
    def find_transcription_button(self):
        """Find and click the transcription button for an episode.
        
        Returns:
            bool: True if the transcription was found and clicked
        """
        try:
            # Look for the transcription button (may vary based on Spotify's UI)
            transcription_selectors = [
                'button[aria-label="Show transcript"]',
                'button:has-text("Show transcript")',
                '[data-testid="transcript-button"]',
                'button:has-text("Transcript")'
            ]
            
            # Try each selector
            for selector in transcription_selectors:
                try:
                    if self.page.wait_for_selector(selector, timeout=5000, state='visible'):
                        self.page.click(selector)
                        logging.debug(f"Found and clicked transcription button with selector: {selector}")
                        
                        # Wait for transcript to load
                        time.sleep(2)
                        return True
                except:
                    continue
            
            logging.warning("Could not find transcription button")
            return False
        except Exception as e:
            logging.error(f"Error finding transcription button: {str(e)}")
            return False
    
    def extract_transcription_text(self):
        """Extract the transcription text from the currently open transcript.
        
        Returns:
            str: The extracted transcription text, or None if not found
        """
        try:
            # Wait for transcript container to be visible
            transcript_selectors = [
                '[data-testid="transcript-container"]',
                '.transcript-container',
                '[aria-label="Transcript"]',
                '.episode-transcript'
            ]
            
            transcript_container = None
            for selector in transcript_selectors:
                try:
                    element = self.page.wait_for_selector(selector, timeout=5000)
                    if element:
                        transcript_container = element
                        break
                except:
                    continue
            
            if not transcript_container:
                logging.warning("Could not find transcript container")
                return None
            
            # Extract text from all transcript items
            transcript_items = self.page.query_selector_all('[data-testid="transcript-item"]')
            
            # If specific item selector didn't work, try more generic selectors
            if not transcript_items or len(transcript_items) == 0:
                transcript_items = transcript_container.query_selector_all('div > p')
            
            if not transcript_items or len(transcript_items) == 0:
                transcript_items = transcript_container.query_selector_all('div')
            
            # Build the full transcript text
            transcript_text = ""
            for item in transcript_items:
                text = item.inner_text()
                if text and len(text.strip()) > 0:
                    transcript_text += text.strip() + "\n\n"
            
            if not transcript_text:
                # As a fallback, get all text from the container
                transcript_text = transcript_container.inner_text()
            
            return transcript_text.strip() if transcript_text else None
        
        except Exception as e:
            logging.error(f"Error extracting transcription text: {str(e)}")
            return None
    
    def close(self):
        """Close the browser and clean up resources."""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            
            logging.debug("Browser closed successfully")
        except Exception as e:
            logging.error(f"Error closing browser: {str(e)}")
