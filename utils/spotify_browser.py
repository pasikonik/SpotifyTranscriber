import logging
import time
import os
import tempfile
import requests
from urllib.parse import urlparse

# Import Playwright but handle import errors gracefully
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logging.warning("Playwright not available, falling back to manual methods")
    PLAYWRIGHT_AVAILABLE = False


class SpotifyBrowser:
    """Class to handle Spotify web browser automation with fallbacks."""
    
    def __init__(self, headless=True):
        """Initialize the browser with Playwright if available.
        
        Args:
            headless (bool): Whether to run the browser in headless mode.
        """
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.browser_mode = None
        
        # Try to initialize browser, but don't raise if it fails - we'll use fallbacks
        try:
            if PLAYWRIGHT_AVAILABLE:
                self._initialize_browser()
                self.browser_mode = "playwright"
            else:
                logging.info("Playwright not available, using request-based mode")
                self.browser_mode = "requests"
        except Exception as e:
            logging.error(f"Browser initialization failed: {str(e)}")
            logging.info("Falling back to request-based mode")
            self.browser_mode = "requests"
            
        # Initialize session for request-based fallback
        self.session = requests.Session()
    
    def _initialize_browser(self):
        """Initialize the browser with Playwright."""
        try:
            self.playwright = sync_playwright().start()
            
            # Try using Playwright's own downloaded browsers without specifying paths
            logging.debug("Attempting to use Playwright's default browser")
            
            # Try with Chromium first
            try:
                self.browser = self.playwright.chromium.launch(headless=self.headless)
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                logging.debug("Browser initialized successfully with Playwright's Chromium")
                return
            except Exception as chrome_err:
                logging.warning(f"Failed with Chromium: {str(chrome_err)}")
                
            # Try with Firefox
            try:
                self.browser = self.playwright.firefox.launch(headless=self.headless)
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                logging.debug("Browser initialized successfully with Playwright's Firefox")
                return
            except Exception as ff_err:
                logging.warning(f"Failed with Firefox: {str(ff_err)}")
                
            # Try with WebKit as last resort
            try:
                self.browser = self.playwright.webkit.launch(headless=self.headless)
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                logging.debug("Browser initialized successfully with Playwright's WebKit")
                return
            except Exception as webkit_err:
                logging.warning(f"Failed with WebKit: {str(webkit_err)}")
                
            # If we get here, all browser types failed
            raise Exception("All browser types failed to initialize")
            
        except Exception as e:
            logging.error(f"Failed to initialize any browser: {str(e)}")
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
        if self.browser_mode == "requests":
            return self._login_with_requests(username, password)
        else:
            return self._login_with_browser(username, password)
            
    def _login_with_browser(self, username, password):
        """Log in to Spotify using browser automation.
        
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
            logging.error(f"Error during login with browser: {str(e)}")
            return False
            
    def _login_with_requests(self, username, password):
        """Log in to Spotify using requests library (fallback method).
        
        Args:
            username (str): Spotify username or email
            password (str): Spotify password
            
        Returns:
            bool: True if login was successful, False otherwise
        """
        try:
            # First, get the login page to obtain CSRF token
            login_url = 'https://accounts.spotify.com/login'
            response = self.session.get(login_url)
            
            if response.status_code != 200:
                logging.error(f"Failed to access login page: {response.status_code}")
                return False
                
            # Now try to login
            login_form_url = 'https://accounts.spotify.com/api/login'
            login_data = {
                'username': username,
                'password': password,
                'remember': 'true'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://accounts.spotify.com/login'
            }
            
            response = self.session.post(login_form_url, data=login_data, headers=headers, allow_redirects=True)
            
            # Check if login was successful based on redirects or cookies
            if 'open.spotify.com' in response.url or any('spotify' in cookie.name and 'sp_dc' in cookie.name for cookie in self.session.cookies):
                logging.info("Login with requests successful")
                return True
                
            logging.error(f"Login with requests failed. Status code: {response.status_code}")
            return False
            
        except Exception as e:
            logging.error(f"Error during login with requests: {str(e)}")
            return False
    
    def navigate_to_episode(self, episode_url):
        """Navigate to a Spotify episode page.
        
        Args:
            episode_url (str): URL of the Spotify episode
            
        Returns:
            bool: True if navigation was successful
        """
        if self.browser_mode == "requests":
            return self._navigate_to_episode_with_requests(episode_url)
        else:
            return self._navigate_to_episode_with_browser(episode_url)
            
    def _navigate_to_episode_with_browser(self, episode_url):
        """Navigate to a Spotify episode page using browser automation.
        
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
            
            logging.debug(f"Successfully navigated to episode with browser: {episode_url}")
            return True
        except Exception as e:
            logging.error(f"Failed to navigate to episode with browser {episode_url}: {str(e)}")
            return False
            
    def _navigate_to_episode_with_requests(self, episode_url):
        """Navigate to a Spotify episode page using requests library.
        
        Args:
            episode_url (str): URL of the Spotify episode
            
        Returns:
            bool: True if navigation was successful
        """
        try:
            response = self.session.get(episode_url)
            if response.status_code == 200:
                logging.debug(f"Successfully navigated to episode with requests: {episode_url}")
                # Store the response content for later extraction
                self.episode_html = response.text
                return True
            else:
                logging.error(f"Failed to navigate to episode with requests: Status code {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"Error navigating to episode with requests: {str(e)}")
            return False
    
    def find_transcription_button(self):
        """Find and click the transcription button for an episode.
        
        Returns:
            bool: True if the transcription was found and clicked
        """
        if self.browser_mode == "requests":
            # In requests mode, we don't need to click a button
            # We'll extract the transcript directly from the page
            return True
        else:
            return self._find_transcription_button_with_browser()
            
    def _find_transcription_button_with_browser(self):
        """Find and click the transcription button using browser automation.
        
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
            
            logging.warning("Could not find transcription button with browser")
            return False
        except Exception as e:
            logging.error(f"Error finding transcription button with browser: {str(e)}")
            return False
    
    def extract_transcription_text(self):
        """Extract the transcription text from the currently open transcript.
        
        Returns:
            str: The extracted transcription text, or None if not found
        """
        if self.browser_mode == "requests":
            return self._extract_transcription_text_with_requests()
        else:
            return self._extract_transcription_text_with_browser()
            
    def _extract_transcription_text_with_browser(self):
        """Extract the transcription text using browser automation.
        
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
                logging.warning("Could not find transcript container with browser")
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
            logging.error(f"Error extracting transcription text with browser: {str(e)}")
            return None
            
    def _extract_transcription_text_with_requests(self):
        """Extract the transcription text using requests and HTML parsing.
        
        Returns:
            str: The extracted transcription text, or None if not found
        """
        try:
            from bs4 import BeautifulSoup
            
            if not hasattr(self, 'episode_html') or not self.episode_html:
                logging.error("No episode HTML available for extraction")
                return None
                
            soup = BeautifulSoup(self.episode_html, 'html.parser')
            
            # Try to find transcript container or items
            transcript_container = None
            
            # Look for different possible transcript container elements
            for selector in ['[data-testid="transcript-container"]', '.transcript-container', 
                            '[aria-label="Transcript"]', '.episode-transcript']:
                container = soup.select_one(selector)
                if container:
                    transcript_container = container
                    break
            
            if not transcript_container:
                logging.warning("Could not find transcript container with requests")
                # Check if we need to make another request to load the transcript
                transcript_url = None
                
                # Look for transcript links or buttons
                transcript_links = soup.select('a[href*="transcript"]')
                if transcript_links:
                    transcript_url = transcript_links[0].get('href')
                    if not transcript_url.startswith('http'):
                        transcript_url = 'https://open.spotify.com' + transcript_url
                
                if transcript_url:
                    logging.info(f"Found transcript URL, fetching: {transcript_url}")
                    response = self.session.get(transcript_url)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        # Try again to find transcript containers
                        for selector in ['[data-testid="transcript-container"]', '.transcript-container', 
                                        '[aria-label="Transcript"]', '.episode-transcript']:
                            container = soup.select_one(selector)
                            if container:
                                transcript_container = container
                                break
                                
            # Extract text from the container
            if transcript_container:
                # Try to extract items from container
                transcript_items = transcript_container.select('[data-testid="transcript-item"]')
                
                if not transcript_items:
                    transcript_items = transcript_container.select('div > p')
                    
                if not transcript_items:
                    transcript_items = transcript_container.select('div')
                
                transcript_text = ""
                for item in transcript_items:
                    text = item.get_text(strip=True)
                    if text:
                        transcript_text += text + "\n\n"
                
                if not transcript_text:
                    # As a fallback, get all text from the container
                    transcript_text = transcript_container.get_text(strip=True)
                
                return transcript_text.strip() if transcript_text else None
            
            # If we still don't have a transcript, try to find it in JSON data
            script_tags = soup.select('script[type="application/ld+json"]')
            for script in script_tags:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'transcript' in data:
                        return data['transcript']
                except:
                    pass
                    
            logging.warning("Could not extract transcript from the page")
            return None
            
        except Exception as e:
            logging.error(f"Error extracting transcription text with requests: {str(e)}")
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
