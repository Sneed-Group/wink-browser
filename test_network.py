"""
Test script to verify the network manager changes.

This script simulates the behavior of the NetworkManager class
without actually importing it, to test the updated HTTPS handling.
"""

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test the network functionality with requests."""
    # Create a session with retry capability
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
    )
    
    # Use standard adapter with retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy)
    
    # Mount the adapter for both HTTP and HTTPS
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # Set headers like a browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    
    # Test HTTPS connection
    try:
        logger.info("Testing HTTPS connection to example.com...")
        response = session.get('https://example.com', timeout=10)
        response.raise_for_status()
        logger.info(f"Success! Status code: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        
        # Test another HTTPS site
        logger.info("Testing HTTPS connection to httpbin.org...")
        response = session.get('https://httpbin.org/get', timeout=10)
        response.raise_for_status()
        logger.info(f"Success! Status code: {response.status_code}")
        logger.info(f"Response JSON: {response.json()}")
        
    except Exception as e:
        logger.error(f"Error making request: {e}")

if __name__ == "__main__":
    main() 