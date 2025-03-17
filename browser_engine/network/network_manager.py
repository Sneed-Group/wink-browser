"""
Network manager for handling HTTP requests.
This module handles network requests, caching, cookies, and connection management.
"""

import os
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any, Optional
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
            "User-Agent": "WinkBrowser/1.0 (Python)"
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
        
        # If private mode, don't send cookies
        if self.config_manager.private_mode:
            self.session.cookies.clear()
        
        # Perform the request
        response = self.session.get(
            url,
            headers=request_headers,
            timeout=30  # 30 second timeout
        )
        
        # Log response info
        logger.debug(f"Response: {response.status_code} - {url}")
        
        # Save cookies if not in private mode
        if not self.config_manager.private_mode:
            self.cookie_jar.update(response.cookies)
        
        return response
    
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