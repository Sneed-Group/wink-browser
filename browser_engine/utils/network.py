"""
Network manager for the browser.
"""

import logging
import os
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import ssl
import socket
import json

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class NetworkManager:
    """Network manager for making HTTP requests."""
    
    # Default user agents
    USER_AGENTS = {
        "default": "WinkBrowser/0.1",
        "chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "android": "Mozilla/5.0 (Linux; Android 10; SM-A205U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
        "iphone": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    }
    
    def __init__(self, private_mode: bool = False, timeout: int = 30, max_retries: int = 3):
        """
        Initialize the network manager.
        
        Args:
            private_mode: Whether to use private browsing mode (no cookies)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.private_mode = private_mode
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Create session
        self.session = requests.Session()
        
        # Configure session
        self._configure_session()
        
        # Add retry adapter
        retry_adapter = HTTPAdapter(max_retries=max_retries)
        self.session.mount('http://', retry_adapter)
        self.session.mount('https://', retry_adapter)
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        logger.debug(f"Network manager initialized (private_mode: {private_mode})")
    
    def _configure_session(self) -> None:
        """Configure the requests session."""
        # Set default headers
        self.session.headers.update({
            'User-Agent': self.USER_AGENTS["default"],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',  # Do Not Track
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        
        # Clear cookies in private mode
        if self.private_mode:
            self.session.cookies.clear()
    
    def set_user_agent(self, user_agent: str) -> None:
        """
        Set the User-Agent header.
        
        Args:
            user_agent: User agent string or key from USER_AGENTS
        """
        if user_agent in self.USER_AGENTS:
            user_agent = self.USER_AGENTS[user_agent]
        
        with self._lock:
            self.session.headers['User-Agent'] = user_agent
            logger.debug(f"User agent set to: {user_agent}")
    
    def set_do_not_track(self, enabled: bool) -> None:
        """
        Set the Do Not Track header.
        
        Args:
            enabled: Whether to enable Do Not Track
        """
        with self._lock:
            self.session.headers['DNT'] = '1' if enabled else '0'
            logger.debug(f"Do Not Track set to: {enabled}")
    
    def set_private_mode(self, enabled: bool) -> None:
        """
        Set private browsing mode.
        
        Args:
            enabled: Whether to enable private mode
        """
        if self.private_mode != enabled:
            with self._lock:
                self.private_mode = enabled
                
                # Clear cookies in private mode
                if enabled:
                    self.session.cookies.clear()
                
                logger.debug(f"Private mode set to: {enabled}")
    
    def set_timeout(self, timeout: int) -> None:
        """
        Set request timeout.
        
        Args:
            timeout: Timeout in seconds
        """
        with self._lock:
            self.timeout = timeout
            logger.debug(f"Timeout set to: {timeout}")
    
    def get(self, url: str, headers: Optional[Dict[str, str]] = None, 
             params: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Make a GET request.
        
        Args:
            url: URL to request
            headers: Additional headers
            params: URL parameters
            
        Returns:
            requests.Response: Response object
        """
        try:
            logger.debug(f"GET request to {url}")
            
            with self._lock:
                response = self.session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout,
                    allow_redirects=True
                )
            
            response.raise_for_status()
            return response
        except RequestException as e:
            logger.error(f"Error making GET request to {url}: {e}")
            raise
    
    def post(self, url: str, headers: Optional[Dict[str, str]] = None,
             data: Optional[Dict[str, Any]] = None, 
             json_data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make a POST request.
        
        Args:
            url: URL to request
            headers: Additional headers
            data: Form data
            json_data: JSON data
            
        Returns:
            requests.Response: Response object
        """
        try:
            logger.debug(f"POST request to {url}")
            
            with self._lock:
                response = self.session.post(
                    url,
                    headers=headers,
                    data=data,
                    json=json_data,
                    timeout=self.timeout,
                    allow_redirects=True
                )
            
            response.raise_for_status()
            return response
        except RequestException as e:
            logger.error(f"Error making POST request to {url}: {e}")
            raise
    
    def head(self, url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Make a HEAD request.
        
        Args:
            url: URL to request
            headers: Additional headers
            
        Returns:
            requests.Response: Response object
        """
        try:
            logger.debug(f"HEAD request to {url}")
            
            with self._lock:
                response = self.session.head(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
            
            response.raise_for_status()
            return response
        except RequestException as e:
            logger.error(f"Error making HEAD request to {url}: {e}")
            raise
    
    def download_file(self, url: str, output_path: str, 
                       headers: Optional[Dict[str, str]] = None,
                       progress_callback: Optional[Any] = None) -> bool:
        """
        Download a file.
        
        Args:
            url: URL to download
            output_path: Path to save the file
            headers: Additional headers
            progress_callback: Callback function for progress updates
            
        Returns:
            bool: True if download was successful
        """
        try:
            logger.debug(f"Downloading file from {url} to {output_path}")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Make a streaming request
            with self._lock:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    stream=True
                )
            
            response.raise_for_status()
            
            # Get total file size
            total_size = int(response.headers.get('content-length', 0))
            
            # Download the file
            with open(output_path, 'wb') as f:
                downloaded = 0
                start_time = time.time()
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Call progress callback if provided
                        if progress_callback and total_size > 0:
                            progress = downloaded / total_size
                            elapsed = time.time() - start_time
                            progress_callback(progress, downloaded, total_size, elapsed)
            
            logger.debug(f"Downloaded {downloaded} bytes to {output_path}")
            return True
        except RequestException as e:
            logger.error(f"Error downloading file from {url}: {e}")
            
            # Remove partially downloaded file
            if os.path.exists(output_path):
                os.unlink(output_path)
            
            return False
    
    def clear_cookies(self) -> None:
        """Clear all cookies."""
        with self._lock:
            self.session.cookies.clear()
            logger.debug("Cookies cleared")
    
    def get_cookies(self) -> List[Dict[str, Any]]:
        """
        Get all cookies.
        
        Returns:
            List[Dict[str, Any]]: List of cookies
        """
        with self._lock:
            cookies = []
            for domain, domain_cookies in self.session.cookies._cookies.items():
                for path, path_cookies in domain_cookies.items():
                    for name, cookie in path_cookies.items():
                        cookies.append({
                            'domain': domain,
                            'path': path,
                            'name': name,
                            'value': cookie.value,
                            'secure': cookie.secure,
                            'expires': cookie.expires
                        })
            return cookies
    
    def set_cookie(self, domain: str, name: str, value: str, 
                    path: str = '/', secure: bool = False, 
                    expires: Optional[int] = None) -> None:
        """
        Set a cookie.
        
        Args:
            domain: Cookie domain
            name: Cookie name
            value: Cookie value
            path: Cookie path
            secure: Whether the cookie is secure
            expires: Expiration timestamp
        """
        if self.private_mode:
            logger.warning("Cannot set cookies in private mode")
            return
        
        with self._lock:
            self.session.cookies.set(
                name,
                value,
                domain=domain,
                path=path,
                secure=secure,
                expires=expires
            )
            logger.debug(f"Cookie set: {domain}:{name}={value}")
    
    def delete_cookie(self, domain: str, name: str, path: str = '/') -> bool:
        """
        Delete a cookie.
        
        Args:
            domain: Cookie domain
            name: Cookie name
            path: Cookie path
            
        Returns:
            bool: True if cookie was deleted
        """
        with self._lock:
            if domain in self.session.cookies._cookies:
                if path in self.session.cookies._cookies[domain]:
                    if name in self.session.cookies._cookies[domain][path]:
                        del self.session.cookies._cookies[domain][path][name]
                        logger.debug(f"Cookie deleted: {domain}:{name}")
                        return True
            
            logger.debug(f"Cookie not found: {domain}:{name}")
            return False
    
    def close(self) -> None:
        """Close the session."""
        with self._lock:
            self.session.close()
            logger.debug("Network manager closed") 