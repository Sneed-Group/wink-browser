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
    
    def __init__(self, config_manager):
        """
        Initialize the network manager.
        
        Args:
            config_manager: The configuration manager
        """
        self.config_manager = config_manager
        
        # Cache directory
        self.cache_dir = os.path.expanduser("~/.wink_browser/cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cookie jar
        self.cookie_jar = requests.cookies.RequestsCookieJar()
        
        # Create a session for reusing connections
        self.session = self._create_session()
        
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
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