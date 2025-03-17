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
import re

import requests
from requests.adapters import HTTPAdapter

# Try to import urllib3 utilities, but handle if not available
try:
    from urllib3.util import ssl_ as urllib3_ssl
    URLLIB3_SSL_AVAILABLE = True
except ImportError:
    URLLIB3_SSL_AVAILABLE = False
    logging.warning("urllib3.util.ssl_ not available. Using standard SSL functionality.")

from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class SSLAdapter(HTTPAdapter):
    """Custom HTTPS adapter with modern SSL configuration."""
    
    def __init__(self, **kwargs):
        self.ssl_context = None
        
        # Only try to use urllib3 SSL utilities if available
        if URLLIB3_SSL_AVAILABLE:
            # Use a safer, more compatible SSL context configuration
            try:
                # Try to create an ideal secure context
                self.ssl_context = urllib3_ssl.create_urllib3_context(
                    ssl_version=ssl.PROTOCOL_TLS,
                    cert_reqs=ssl.CERT_REQUIRED,
                    options=ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
                )
                
                # Try to load the default certificates from the system
                try:
                    import certifi
                    self.ssl_context.load_verify_locations(cafile=certifi.where())
                    logger.debug("Loaded certificates from certifi")
                except ImportError:
                    logger.warning("certifi package not available, trying to use system certificates")
                    try:
                        # Try to use the system's certificate store
                        self.ssl_context.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)
                        logger.debug("Loaded system certificates")
                    except Exception as cert_error:
                        logger.warning(f"Could not load system certificates: {cert_error}")
                        # Try common certificate file locations
                        cert_paths = [
                            "/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu/Gentoo etc.
                            "/etc/pki/tls/certs/ca-bundle.crt",    # Fedora/RHEL 6
                            "/etc/ssl/ca-bundle.pem",              # OpenSUSE
                            "/etc/pki/tls/cacert.pem",             # OpenELEC
                            "/etc/ssl/cert.pem",                   # macOS, FreeBSD
                        ]
                        for cert_path in cert_paths:
                            if os.path.exists(cert_path):
                                try:
                                    self.ssl_context.load_verify_locations(cafile=cert_path)
                                    logger.debug(f"Loaded certificates from {cert_path}")
                                    break
                                except Exception:
                                    continue
            except (AttributeError, ValueError, TypeError) as e:
                logger.warning(f"Could not create custom SSL context with ideal settings: {e}")
                # Fall back to a more compatible context
                try:
                    self.ssl_context = urllib3_ssl.create_urllib3_context()
                    # Try to load default certificates
                    try:
                        self.ssl_context.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)
                    except Exception as cert_error:
                        logger.warning(f"Could not load default certificates: {cert_error}")
                except Exception as e2:
                    logger.warning(f"Could not create default SSL context either: {e2}")
                    # Don't set ssl_context at all, will use default
                    self.ssl_context = None
        else:
            logger.warning("SSL customization not available (urllib3.util.ssl_ missing)")
                
        super().__init__(**kwargs)
    
    def init_poolmanager(self, *args, **kwargs):
        # Only set custom ssl_context if we successfully created one
        if self.ssl_context:
            kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)
    
    def proxy_manager_for(self, *args, **kwargs):
        # Only set custom ssl_context if we successfully created one
        if self.ssl_context:
            kwargs['ssl_context'] = self.ssl_context
        return super().proxy_manager_for(*args, **kwargs)

class NetworkManager:
    """Network manager for making HTTP requests."""
    
    # Default user agents
    USER_AGENTS = {
        "default": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Wink/0.1",
        "chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "android": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.104 Mobile Safari/537.36",
        "iphone": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
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
        
        # Add retry adapter with proper SSL configuration
        # Create custom HTTPS adapter with modern SSL configuration
        https_adapter = SSLAdapter(max_retries=max_retries)
        http_adapter = HTTPAdapter(max_retries=max_retries)
        
        self.session.mount('http://', http_adapter)
        self.session.mount('https://', https_adapter)
        
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
        
        # Configure SSL verification
        self.session.verify = True  # Enable SSL certificate verification
        
        # Try to use certifi for certificate verification if available
        try:
            import certifi
            self.session.verify = certifi.where()
            logger.debug(f"Using certifi for certificate verification: {certifi.where()}")
        except ImportError:
            # If certifi is not available, try to find system certificates
            logger.warning("certifi package not available, using system certificates")
            # On macOS, the default location is /etc/ssl/cert.pem
            if os.path.exists("/etc/ssl/cert.pem"):
                self.session.verify = "/etc/ssl/cert.pem"
                logger.debug("Using macOS system certificates")
        
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
    
    def get_decoded_text(self, response: requests.Response) -> str:
        """
        Get properly decoded text from a response by respecting the content encoding.
        
        Args:
            response: The response object
            
        Returns:
            str: Properly decoded text content
        """
        try:
            # First, try to get the encoding from the Content-Type header
            content_type = response.headers.get('Content-Type', '')
            charset = None
            
            # Extract charset from Content-Type
            if 'charset=' in content_type.lower():
                charset = content_type.lower().split('charset=')[-1].split(';')[0].strip()
            
            # If we don't have a charset from headers, try to detect from content
            if not charset:
                # First few bytes for detection
                content_bytes = response.content
                
                # Try to detect encoding from content
                # Check for UTF-8 BOM
                if content_bytes.startswith(b'\xef\xbb\xbf'):
                    charset = 'utf-8-sig'
                # Check for UTF-16LE BOM
                elif content_bytes.startswith(b'\xff\xfe'):
                    charset = 'utf-16le'
                # Check for UTF-16BE BOM
                elif content_bytes.startswith(b'\xfe\xff'):
                    charset = 'utf-16be'
                # Check for HTML meta charset
                else:
                    # Look for meta charset in the first 1024 bytes
                    # This is a simple approach, a real browser would do more sophisticated detection
                    html_start = content_bytes[:1024].decode('ascii', errors='ignore')
                    meta_charset_match = re.search(r'<meta[^>]*charset=["\']?([^"\'>]+)', html_start, re.IGNORECASE)
                    
                    if meta_charset_match:
                        charset = meta_charset_match.group(1).strip()
            
            # If we still don't have a charset, use the response.apparent_encoding
            if not charset:
                charset = response.apparent_encoding or 'utf-8'
            
            logger.debug(f"Using charset: {charset} for response from {response.url}")
            
            # Decode the content with the determined charset
            if charset:
                try:
                    return response.content.decode(charset, errors='replace')
                except (LookupError, UnicodeDecodeError) as e:
                    logger.warning(f"Error decoding with {charset}: {e}. Falling back to apparent_encoding.")
                    # Fall back to apparent_encoding if the specified charset fails
                    return response.content.decode(response.apparent_encoding or 'utf-8', errors='replace')
            
            # If all else fails, use response.text (which uses response.encoding)
            return response.text
            
        except Exception as e:
            logger.error(f"Error decoding response: {e}")
            # Last resort fallback
            return response.text

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
            
            # Add a text_decoded property to the response with properly decoded text
            response.text_decoded = self.get_decoded_text(response)
            
            return response
        except (requests.exceptions.SSLError, ssl.SSLError, requests.exceptions.ConnectionError) as e:
            # Handle SSL errors and connection errors that might be SSL-related
            ssl_error_message = str(e)
            logger.error(f"SSL/Connection Error making GET request to {url}: {ssl_error_message}")
            
            # Only retry without verification for SSL-specific errors
            if ('SSL' in ssl_error_message or 'certificate' in ssl_error_message.lower() or 
                'handshake' in ssl_error_message.lower()):
                # For SSL errors, we might want to retry with verification disabled as a fallback
                # Only do this for development/testing - NOT recommended for production use
                logger.warning("Retrying without SSL verification as fallback...")
                try:
                    with self._lock:
                        response = self.session.get(
                            url,
                            headers=headers,
                            params=params,
                            timeout=self.timeout,
                            allow_redirects=True,
                            verify=False  # Disable verification as fallback
                        )
                    response.raise_for_status()
                    return response
                except Exception as retry_error:
                    logger.error(f"Error retrying request without SSL verification: {retry_error}")
                    raise
            raise
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
        except (requests.exceptions.SSLError, ssl.SSLError, requests.exceptions.ConnectionError) as e:
            # Handle SSL errors and connection errors that might be SSL-related
            ssl_error_message = str(e)
            logger.error(f"SSL/Connection Error making POST request to {url}: {ssl_error_message}")
            
            # Only retry without verification for SSL-specific errors
            if ('SSL' in ssl_error_message or 'certificate' in ssl_error_message.lower() or 
                'handshake' in ssl_error_message.lower()):
                # For SSL errors, we might want to retry with verification disabled as a fallback
                # Only do this for development/testing - NOT recommended for production use
                logger.warning("Retrying without SSL verification as fallback...")
                try:
                    with self._lock:
                        response = self.session.post(
                            url,
                            headers=headers,
                            data=data,
                            json=json_data,
                            timeout=self.timeout,
                            allow_redirects=True,
                            verify=False  # Disable verification as fallback
                        )
                    response.raise_for_status()
                    return response
                except Exception as retry_error:
                    logger.error(f"Error retrying POST request without SSL verification: {retry_error}")
                    raise
            raise
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
        except (requests.exceptions.SSLError, ssl.SSLError, requests.exceptions.ConnectionError) as e:
            # Handle SSL errors and connection errors that might be SSL-related
            ssl_error_message = str(e)
            logger.error(f"SSL/Connection Error making HEAD request to {url}: {ssl_error_message}")
            
            # Only retry without verification for SSL-specific errors
            if ('SSL' in ssl_error_message or 'certificate' in ssl_error_message.lower() or 
                'handshake' in ssl_error_message.lower()):
                # For SSL errors, we might want to retry with verification disabled as a fallback
                # Only do this for development/testing - NOT recommended for production use
                logger.warning("Retrying without SSL verification as fallback...")
                try:
                    with self._lock:
                        response = self.session.head(
                            url,
                            headers=headers,
                            timeout=self.timeout,
                            allow_redirects=True,
                            verify=False  # Disable verification as fallback
                        )
                    response.raise_for_status()
                    return response
                except Exception as retry_error:
                    logger.error(f"Error retrying HEAD request without SSL verification: {retry_error}")
                    raise
            raise
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
        except (requests.exceptions.SSLError, ssl.SSLError, requests.exceptions.ConnectionError) as e:
            # Handle SSL errors and connection errors that might be SSL-related
            ssl_error_message = str(e)
            logger.error(f"SSL/Connection Error downloading file from {url}: {ssl_error_message}")
            
            # Only retry without verification for SSL-specific errors
            if ('SSL' in ssl_error_message or 'certificate' in ssl_error_message.lower() or 
                'handshake' in ssl_error_message.lower()):
                # For SSL errors, we might want to retry with verification disabled as a fallback
                # Only do this for development/testing - NOT recommended for production use
                logger.warning("Retrying download without SSL verification as fallback...")
                
                try:
                    # Make a streaming request without SSL verification
                    with self._lock:
                        response = self.session.get(
                            url,
                            headers=headers,
                            timeout=self.timeout,
                            stream=True,
                            verify=False  # Disable verification as fallback
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
                except Exception as retry_error:
                    logger.error(f"Error downloading file from {url} (retry): {retry_error}")
                    
                    # Remove partially downloaded file
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                    
                    return False
            
            # Remove partially downloaded file
            if os.path.exists(output_path):
                os.unlink(output_path)
                
            return False
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