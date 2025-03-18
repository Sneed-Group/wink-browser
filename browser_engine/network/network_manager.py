"""
Network manager for handling HTTP requests.
This module handles network requests, caching, cookies, and connection management.
"""

import os
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any, Optional, List
import certifi

logger = logging.getLogger(__name__)

class NetworkManager:
    """
    Network manager for handling HTTP requests.
    
    This class handles network requests, caching, cookies, and connection management.
    """
    
    # Class-level instance for singleton use
    _instance = None
    
    def __new__(cls, config_manager=None):
        # Singleton pattern - return existing instance if available
        if cls._instance is None:
            cls._instance = super(NetworkManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_manager=None):
        """
        Initialize the network manager.
        
        Args:
            config_manager: The configuration manager
        """
        # Skip initialization if already done
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # Use default config manager if none provided
        if config_manager is None:
            from browser_engine.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
        
        self.config_manager = config_manager
        
        # Cache directory
        self.cache_dir = os.path.expanduser("~/.wink_browser/cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cookie jar
        self.cookie_jar = requests.cookies.RequestsCookieJar()
        
        # Create a session for reusing connections
        self.session = self._create_session()
        
        # Mark as initialized
        self._initialized = True
        
        logger.info("Network manager initialized")
    
    def _create_session(self) -> requests.Session:
        """
        Create a new requests session with appropriate configuration.
        
        Returns:
            A configured requests session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "HEAD"]
        )
        
        # Configure connection adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set up SSL verification
        try:
            # Use certifi for SSL certificates
            session.verify = certifi.where()
        except (ImportError, IOError):
            # Fall back to system certificates if certifi is not available
            session.verify = True
        
        # Set user agent
        session.headers.update({
            "User-Agent": "Wink/1.0 (MysteryOS 10.0; Myst1k; SNEED_1kb_ARCH) WinkEngine/1.0 (HTML/Markdown, like Awesome) WinkBrowser/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        })
        
        # Set cookies
        if not self.config_manager.private_mode:
            session.cookies = self.cookie_jar
        
        # Set Do Not Track header if enabled
        if self.config_manager.get_config("privacy.do_not_track", True):
            session.headers.update({
                "DNT": "1"
            })
        
        # Configure proxy if enabled
        self._configure_proxy(session)
        
        return session
    
    def _configure_proxy(self, session: requests.Session) -> None:
        """
        Configure proxy settings for the session.
        
        Args:
            session: The requests session to configure
        """
        if self.config_manager.get_config("network.proxy.enabled", False):
            proxy_type = self.config_manager.get_config("network.proxy.type", "none")
            proxy_host = self.config_manager.get_config("network.proxy.host", "")
            proxy_port = self.config_manager.get_config("network.proxy.port", 0)
            
            if proxy_type != "none" and proxy_host and proxy_port:
                proxies = {}
                
                if proxy_type == "http":
                    proxies["http"] = f"http://{proxy_host}:{proxy_port}"
                    proxies["https"] = f"http://{proxy_host}:{proxy_port}"
                elif proxy_type == "socks":
                    proxies["http"] = f"socks5://{proxy_host}:{proxy_port}"
                    proxies["https"] = f"socks5://{proxy_host}:{proxy_port}"
                
                session.proxies.update(proxies)
    
    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Perform a GET request.
        
        Args:
            url: The URL to request
            headers: Optional additional headers
            
        Returns:
            The HTTP response
        """
        logger.debug(f"GET request: {url}")
        
        # Handle special URL schemes
        if url.startswith(('about:', 'data:', 'javascript:', 'blob:')):
            # Create a dummy response for special URLs
            response = requests.Response()
            response.status_code = 200
            response.reason = "OK"
            
            if url.startswith('about:'):
                response._content = b"Special URL: about scheme"
                response.headers['Content-Type'] = 'text/html'
            elif url.startswith('data:'):
                import base64
                import urllib.parse
                
                # Try to parse data URL
                try:
                    # Format: data:[<mediatype>][;base64],<data>
                    data_parts = url[5:].split(',', 1)
                    if len(data_parts) != 2:
                        raise ValueError("Invalid data URL format")
                    
                    metadata, data = data_parts
                    
                    # Set content type
                    content_type = 'text/plain'
                    if metadata:
                        mime_parts = metadata.split(';')
                        if mime_parts[0]:
                            content_type = mime_parts[0]
                    
                    response.headers['Content-Type'] = content_type
                    
                    # Determine if base64 encoded
                    is_base64 = 'base64' in metadata
                    
                    # Decode the content
                    if is_base64:
                        response._content = base64.b64decode(data)
                    else:
                        response._content = urllib.parse.unquote(data).encode('utf-8')
                    
                except Exception as e:
                    logger.error(f"Error parsing data URL: {e}")
                    response._content = b"Error parsing data URL"
                    response.status_code = 400
                    response.reason = "Bad Request"
            
            elif url.startswith('javascript:'):
                response._content = b"JavaScript URLs are not supported"
                response.headers['Content-Type'] = 'text/plain'
            
            elif url.startswith('blob:'):
                response._content = b"Blob URLs are not supported"
                response.headers['Content-Type'] = 'text/plain'
            
            return response
        
        # Apply ad blocking if enabled
        if self.config_manager.get_config("privacy.block_ads", True):
            if self._should_block_request(url):
                logger.debug(f"Blocked request to: {url}")
                raise ValueError(f"Request blocked by ad blocker: {url}")
        
        # Create new headers dict or use empty dict if None
        request_headers = headers.copy() if headers else {}
        
        # Add key Cloudflare headers
        if "cloudflare.com" in url or any(domain in url for domain in self._known_cloudflare_sites()):
            cloudflare_headers = {
                "Upgrade-Insecure-Requests": "1",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Cache-Control": "max-age=0",
                "sec-ch-ua": '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document"
            }
            request_headers.update(cloudflare_headers)
            
            # For Cloudflare sites, always send cookies
            self.session.cookies.clear()
            self.session.cookies.update(self.cookie_jar)
        
        # If private mode, don't send cookies (except for Cloudflare sites)
        elif self.config_manager.private_mode:
            self.session.cookies.clear()
        
        # Set special options for Cloudflare
        cloudflare_options = {}
        if "cloudflare.com" in url or any(domain in url for domain in self._known_cloudflare_sites()):
            cloudflare_options["allow_redirects"] = True
            cloudflare_options["timeout"] = 60  # Longer timeout for Cloudflare challenges
        else:
            cloudflare_options["allow_redirects"] = True
            cloudflare_options["timeout"] = 30
        
        # Perform the request
        try:
            response = self.session.get(
                url,
                headers=request_headers,
                **cloudflare_options
            )
            
            # Log response info
            logger.debug(f"Response: {response.status_code} - {url}")
            
            # Save cookies if not in private mode or if Cloudflare site
            if not self.config_manager.private_mode or "cloudflare.com" in url or any(domain in url for domain in self._known_cloudflare_sites()):
                self.cookie_jar.update(response.cookies)
                
            # Handle Cloudflare server-side redirects
            if response.status_code in (503, 403) and ('cloudflare' in response.text.lower() or 'cf-ray' in response.headers):
                logger.info("Detected Cloudflare challenge, attempting to handle")
                # Simply retry once with the cookies we've received
                return self.get(url, request_headers)
                
            return response
            
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            raise
    
    def _known_cloudflare_sites(self) -> List[str]:
        """Return a list of known Cloudflare-protected domains."""
        return [
            "nodemixaholic.com",
            "discord.com",
            "cloudflareinsights.com",
            # Add other known Cloudflare sites as you encounter them
        ]
    
    def post(self, url: str, data: Any = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Perform a POST request.
        
        Args:
            url: The URL to request
            data: The data to send (dict, bytes, or file-like object)
            headers: Optional additional headers
            
        Returns:
            The HTTP response
        """
        logger.debug(f"POST request: {url}")
        
        # Apply ad blocking if enabled
        if self.config_manager.get_config("privacy.block_ads", True):
            if self._should_block_request(url):
                logger.debug(f"Blocked request to: {url}")
                raise ValueError(f"Request blocked by ad blocker: {url}")
        
        # Create new headers dict or use empty dict if None
        request_headers = headers.copy() if headers else {}
        
        # If private mode, don't send cookies
        if self.config_manager.private_mode:
            self.session.cookies.clear()
        
        # Perform the request
        response = self.session.post(
            url,
            data=data,
            headers=request_headers,
            timeout=30  # 30 second timeout
        )
        
        # Log response info
        logger.debug(f"Response: {response.status_code} - {url}")
        
        # Save cookies if not in private mode
        if not self.config_manager.private_mode:
            self.cookie_jar.update(response.cookies)
        
        return response
    
    def clear_cookies(self) -> None:
        """Clear all cookies."""
        self.cookie_jar.clear()
        self.session.cookies.clear()
    
    def clear_cache(self) -> None:
        """Clear the browser cache."""
        try:
            for file in os.listdir(self.cache_dir):
                os.remove(os.path.join(self.cache_dir, file))
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def _should_block_request(self, url: str) -> bool:
        """
        Check if a request should be blocked by the ad blocker.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the request should be blocked, False otherwise
        """
        # This is a simplistic implementation
        # In a real browser, this would check against filter lists
        
        # Block common ad domains as an example
        ad_domains = [
            "ads.", "ad.", "analytics.", "tracker.", "pixel.",
            "doubleclick.net", "googleadservices.com", "googlesyndication.com",
            "moatads.com", "adnxs.com"
        ]
        
        # Check if URL contains any ad domains
        url_lower = url.lower()
        for domain in ad_domains:
            if domain in url_lower:
                return True
        
        return False
    
    def fetch(self, url: str, resource_type: str = "script") -> Optional[str]:
        """
        Fetch a resource from a URL and return its content as a string.
        
        Args:
            url: The URL of the resource to fetch
            resource_type: The type of resource ("script", "style", "image", etc.)
            
        Returns:
            The resource content as a string, or None if the request failed
        """
        try:
            headers = {}
            
            # Set appropriate headers based on resource type
            if resource_type == "script":
                headers["Accept"] = "application/javascript, text/javascript, */*"
            elif resource_type == "style":
                headers["Accept"] = "text/css, */*"
            elif resource_type == "image":
                headers["Accept"] = "image/webp, image/apng, image/*"
            
            response = self.get(url, headers=headers)
            
            # Check for successful response
            if response.status_code == 200:
                # For scripts and stylesheets, return text content
                if resource_type in ["script", "style"]:
                    return response.text
                # For binary resources like images, return base64 encoded content
                elif resource_type == "image":
                    import base64
                    return base64.b64encode(response.content).decode('utf-8')
                # Default fallback
                else:
                    return response.text
            else:
                logger.warning(f"Failed to fetch {resource_type} from {url}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching {resource_type} from {url}: {e}")
            return None
    
    def get_decoded_text(self, response) -> str:
        """
        Get decoded text from a response with robust handling of encodings.
        
        Args:
            response: The response object
            
        Returns:
            str: The decoded text
        """
        # Check if response is None
        if response is None:
            return "<html><body><p>Error: Response was None</p></body></html>"
            
        # Check if response has content
        if not hasattr(response, 'content') or response.content is None:
            return "<html><body><p>Error: No content in response</p></body></html>"
            
        # Check for empty content
        if len(response.content) == 0:
            return "<html><body><p>Error: Empty content in response</p></body></html>"
        
        # If response already has text, use it
        if hasattr(response, 'text') and response.text is not None:
            return response.text
            
        # Try to determine encoding from Content-Type header
        content_type = response.headers.get('Content-Type', '').lower()
        charset = None
        
        # Extract charset from Content-Type header
        if 'charset=' in content_type:
            charset = content_type.split('charset=')[1].split(';')[0].strip()
        
        # Try decoding with detected charset
        if charset:
            try:
                return response.content.decode(charset, errors='replace')
            except (UnicodeDecodeError, LookupError):
                # If that fails, continue to other methods
                logger.warning(f"Failed to decode with charset {charset}")
        
        # Try UTF-8 (common default)
        try:
            return response.content.decode('utf-8', errors='replace')
        except UnicodeDecodeError:
            pass
        
        # Try ISO-8859-1 (Latin-1, another common fallback)
        try:
            return response.content.decode('iso-8859-1', errors='replace')
        except UnicodeDecodeError:
            pass
        
        # Last resort, use errors='replace' to handle any encoding
        return response.content.decode('utf-8', errors='replace') 