"""
Network manager for the browser.
"""

import logging
import os
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
import urllib.parse
import ssl
import socket
import json
import re

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class NetworkManager:
    """Network manager for making HTTP requests."""
    
    # Default user agents
    USER_AGENTS = {
        "default":  "Wink/1.0 (MysteryOS 10.0; Myst1k; SNEED_1kb_ARCH) WinkEngine/1.0 (HTML/Markdown, like Awesome) WinkBrowser/1.0",
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
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        # Use standard adapters with retry strategy
        http_adapter = HTTPAdapter(max_retries=retry_strategy)
        
        # Mount the adapters for both HTTP and HTTPS
        self.session.mount('http://', http_adapter)
        self.session.mount('https://', http_adapter)
        
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
        
        # Configure SSL verification (using requests' built-in functionality)
        self.session.verify = True
        
        # Try to use certifi for certificate verification if available
        try:
            import certifi
            self.session.verify = certifi.where()
            logger.debug(f"Using certifi for certificate verification: {certifi.where()}")
        except ImportError:
            # If certifi is not available, we'll rely on the system's certificates
            # which requests will handle automatically
            logger.info("certifi package not available, using system certificates")
        
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
                # Remove quotes if present
                if (charset.startswith('"') and charset.endswith('"')) or (charset.startswith("'") and charset.endswith("'")):
                    charset = charset[1:-1]
            
            # If we don't have a charset from headers, try to detect from content
            if not charset:
                # Get content bytes for detection
                content_bytes = response.content
                
                # Try to detect encoding from content BOM markers
                # Check for UTF-8 BOM
                if content_bytes.startswith(b'\xef\xbb\xbf'):
                    charset = 'utf-8-sig'
                # Check for UTF-16LE BOM
                elif content_bytes.startswith(b'\xff\xfe') and not content_bytes.startswith(b'\xff\xfe\x00\x00'):
                    charset = 'utf-16le'
                # Check for UTF-16BE BOM
                elif content_bytes.startswith(b'\xfe\xff') and not content_bytes.startswith(b'\x00\x00\xfe\xff'):
                    charset = 'utf-16be'
                # Check for UTF-32LE BOM
                elif content_bytes.startswith(b'\xff\xfe\x00\x00'):
                    charset = 'utf-32le'
                # Check for UTF-32BE BOM
                elif content_bytes.startswith(b'\x00\x00\xfe\xff'):
                    charset = 'utf-32be'
                # Check for HTML meta charset - need to check both http-equiv and charset attribute
                else:
                    # Look for meta charset in the first 8192 bytes (more robust detection)
                    try:
                        # First try ascii for basic detection
                        html_start = content_bytes[:8192].decode('ascii', errors='ignore')
                        
                        # Check for <meta charset="..."> format (HTML5)
                        meta_charset_match = re.search(r'<meta[^>]*charset=["\']?([^"\'>]+)', html_start, re.IGNORECASE)
                        if meta_charset_match:
                            charset = meta_charset_match.group(1).strip()
                        
                        # Also check for <meta http-equiv="Content-Type" content="text/html; charset=..."> format (HTML4)
                        if not charset:
                            meta_http_equiv_match = re.search(
                                r'<meta[^>]*http-equiv=["\']?content-type["\']?[^>]*content=["\']?[^;]+;\s*charset=([^"\'>]+)',
                                html_start, 
                                re.IGNORECASE
                            )
                            if meta_http_equiv_match:
                                charset = meta_http_equiv_match.group(1).strip()
                                
                        # Check for XML declaration <?xml version="1.0" encoding="..."?>
                        if not charset:
                            xml_encoding_match = re.search(r'<\?xml[^>]*encoding=["\']?([^"\'>]+)', html_start, re.IGNORECASE)
                            if xml_encoding_match:
                                charset = xml_encoding_match.group(1).strip()
                    except Exception as e:
                        logger.debug(f"Error in charset detection from HTML: {e}")
            
            # If we still don't have a charset, try response.encoding and then apparent_encoding
            if not charset:
                # Try response.encoding which might be set by requests based on HTTP headers
                charset = response.encoding
                
                # If still no charset, try to detect using chardet library via apparent_encoding
                if not charset and hasattr(response, 'apparent_encoding') and response.apparent_encoding:
                    charset = response.apparent_encoding
                    
                # Last resort, default to UTF-8
                if not charset:
                    charset = 'utf-8'
            
            # Normalize charset name
            charset = self._normalize_charset(charset)
            
            logger.debug(f"Using charset: {charset} for response from {response.url}")
            
            # Try multiple encoding strategies to ensure robust decoding
            decoded_results = []
            decode_errors = []
            
            # Check if the content is binary rather than text
            # This helps avoid decoding binary data as text
            content_type_main = content_type.split(';')[0].strip().lower() if content_type else ''
            is_likely_binary = False
            
            # Check if content type indicates binary data
            binary_types = ['image/', 'audio/', 'video/', 'application/octet-stream', 
                           'application/pdf', 'application/zip', 'application/x-', 
                           'application/vnd.', 'application/binary']
            if any(binary_type in content_type_main for binary_type in binary_types):
                is_likely_binary = True
                logger.warning(f"Content appears to be binary ({content_type_main}), decoding may produce garbled text")
            
            # If not clearly binary by content type, check content characteristics
            if not is_likely_binary:
                # Sample the first 1000 bytes for binary detection
                sample = response.content[:1000]
                if sample:
                    # Count control characters (excluding common whitespace)
                    control_chars = sum(1 for b in sample if (b < 32 or b == 127) and b not in (9, 10, 13))  # Tab, LF, CR
                    control_ratio = control_chars / len(sample)
                    
                    # If more than 20% are control characters, likely binary
                    if control_ratio > 0.2:
                        is_likely_binary = True
                        logger.warning(f"Content contains many control characters ({control_ratio:.1%}), may be binary data")
            
            # If content is likely binary, provide a clear error message rather than garbled text
            if is_likely_binary:
                logger.warning(f"Not attempting to decode likely binary content from {response.url}")
                return f"[Binary content detected of type: {content_type_main}]"
            
            # Prioritized encoding list with most common first for HTML pages
            # This is to ensure we try the most likely encodings first
            prioritized_encodings = ['utf-8', 'windows-1252', 'iso-8859-1', 'latin1']
            
            # Add the detected charset to the front if it's not already in the list
            if charset.lower() not in [enc.lower() for enc in prioritized_encodings]:
                prioritized_encodings.insert(0, charset)
            
            # Try each encoding in order
            for encoding in prioritized_encodings:
                try:
                    decoded_text = response.content.decode(encoding, errors='replace')
                    # Count replacement characters as a heuristic for decoding quality
                    replacement_chars = decoded_text.count('\ufffd')
                    replacement_ratio = replacement_chars / len(decoded_text) if decoded_text else 0
                    decoded_results.append((decoded_text, encoding, replacement_chars, replacement_ratio))
                    
                    # If we got a good result with very few replacements, use it immediately
                    if replacement_ratio < 0.01:  # Less than 1% replacement chars
                        return decoded_text
                    
                except (LookupError, UnicodeDecodeError) as e:
                    decode_errors.append(f"Encoding '{encoding}' failed: {e}")
            
            # Try language-specific encodings based on Content-Language header
            content_language = response.headers.get('Content-Language', '').lower()
            
            language_specific_encodings = []
            if 'ja' in content_language:
                language_specific_encodings.extend(['shift_jis', 'euc_jp', 'iso-2022-jp'])
            elif 'ko' in content_language:
                language_specific_encodings.extend(['euc_kr', 'cp949'])
            elif 'zh' in content_language:
                if 'zh-tw' in content_language or 'zh-hk' in content_language:
                    language_specific_encodings.extend(['big5', 'big5hkscs'])
                else:  # zh-cn or other Chinese
                    language_specific_encodings.extend(['gb2312', 'gbk', 'gb18030'])
            elif any(lang in content_language for lang in ['ru', 'uk', 'be']):
                language_specific_encodings.extend(['cp1251', 'koi8-r', 'koi8-u', 'iso-8859-5'])
            elif any(lang in content_language for lang in ['ar', 'fa', 'ur']):
                language_specific_encodings.extend(['cp1256', 'iso-8859-6'])
            elif 'th' in content_language:
                language_specific_encodings.extend(['cp874', 'tis-620'])
            elif 'tr' in content_language:
                language_specific_encodings.extend(['cp1254', 'iso-8859-9'])
            elif 'el' in content_language:
                language_specific_encodings.extend(['cp1253', 'iso-8859-7'])
            elif 'he' in content_language:
                language_specific_encodings.extend(['cp1255', 'iso-8859-8'])
            
            # Try language-specific encodings
            for encoding in language_specific_encodings:
                if encoding.lower() not in [enc.lower() for enc in prioritized_encodings]:
                    try:
                        decoded_text = response.content.decode(encoding, errors='replace')
                        replacement_chars = decoded_text.count('\ufffd')
                        replacement_ratio = replacement_chars / len(decoded_text) if decoded_text else 0
                        decoded_results.append((decoded_text, encoding, replacement_chars, replacement_ratio))
                    except (LookupError, UnicodeDecodeError) as e:
                        decode_errors.append(f"Language-specific encoding '{encoding}' failed: {e}")
            
            # Try double-decoding for mojibake cases
            # This happens when UTF-8 content was incorrectly decoded as latin1 and then re-encoded
            try:
                # Re-encode as latin1 to get back the original bytes, then decode as UTF-8
                decoded_text = response.content.decode('latin1', errors='replace').encode('latin1', errors='replace').decode('utf-8', errors='replace')
                replacement_chars = decoded_text.count('\ufffd')
                replacement_ratio = replacement_chars / len(decoded_text) if decoded_text else 0
                decoded_results.append((decoded_text, "utf-8-fixed", replacement_chars, replacement_ratio))
            except (LookupError, UnicodeDecodeError) as e:
                decode_errors.append(f"UTF-8 mojibake fix failed: {e}")
            
            # If we have results, use the one with the least replacement characters
            if decoded_results:
                # Sort by replacement character count (lower is better)
                decoded_results.sort(key=lambda x: x[2])
                best_result, best_charset, replacement_count, replacement_ratio = decoded_results[0]
                
                if best_charset != charset:
                    logger.info(f"Used fallback charset '{best_charset}' instead of '{charset}' for {response.url} (replacement chars: {replacement_count}, ratio: {replacement_ratio:.1%})")
                
                return best_result
            
            # If all decoding attempts failed, use the requests' default text
            logger.warning(f"All decoding attempts failed for {response.url}: {'; '.join(decode_errors)}")
            
            # Last resort - try UTF-8 with aggressive error handling
            try:
                return response.content.decode('utf-8', errors='ignore')
            except Exception:
                pass
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error decoding response: {e}")
            # Last resort fallback
            return response.text
    
    def _normalize_charset(self, charset: str) -> str:
        """
        Normalize charset names to standard Python encoding names.
        
        Args:
            charset: The charset name to normalize
            
        Returns:
            str: Normalized charset name
        """
        if not charset:
            return 'utf-8'  # Default to UTF-8 for None or empty
            
        charset = charset.lower().strip()
        
        # Remove quotes, spaces, and common prefixes/suffixes that aren't part of the charset name
        charset = re.sub(r'^["\' ]+|["\' ]+$', '', charset)  # Remove quotes and spaces
        charset = re.sub(r'^charset[\s=:]+', '', charset)    # Remove "charset=" prefix
        
        # Common charset name mappings
        charset_map = {
            # Japanese
            'shift_jis': 'shift_jis',
            'shift-jis': 'shift_jis',
            'sjis': 'shift_jis',
            'x-sjis': 'shift_jis',
            'ms_kanji': 'shift_jis',
            'windows-31j': 'shift_jis',
            'ms932': 'shift_jis',
            'csshiftjis': 'shift_jis',
            'euc-jp': 'euc_jp',
            'eucjp': 'euc_jp',
            'x-euc-jp': 'euc_jp',
            'iso-2022-jp': 'iso2022_jp',
            'csiso2022jp': 'iso2022_jp',
            'iso-2022-jp-2': 'iso2022_jp_2',
            'iso-2022-jp-ext': 'iso2022_jp_ext',
            'jis_encoding': 'iso2022_jp',
            'iso-ir-87': 'iso2022_jp',
            
            # Chinese
            'gb2312': 'gb2312',
            'x-gb2312': 'gb2312',
            'gb-2312': 'gb2312',
            'gbk': 'gbk', 
            'cp936': 'gbk',
            'ms936': 'gbk',
            'gb_2312-80': 'gb2312',
            'iso-ir-58': 'gb2312',
            'chinese': 'gbk',
            'csgb2312': 'gb2312',
            'csgbk': 'gbk',
            'gb18030': 'gb18030',
            'gb18030-2000': 'gb18030',
            'hz': 'hz',
            'hz-gb-2312': 'hz',
            'big5': 'big5',
            'big5-hkscs': 'big5hkscs',
            'cn-big5': 'big5',
            'csbig5': 'big5',
            'x-big5': 'big5',
            'big5-hkscs:2004': 'big5hkscs',
            'big5-hkscs:2001': 'big5hkscs',
            'big5tw': 'big5',
            'cns11643': 'big5',
            
            # Korean
            'euc-kr': 'euc_kr',
            'euckr': 'euc_kr',
            'cseuckr': 'euc_kr',
            'ks_c_5601-1987': 'euc_kr',
            'ks_c_5601': 'euc_kr',
            'ksc_5601': 'euc_kr',
            'ksc5601': 'euc_kr',
            'cp949': 'cp949',
            'uhc': 'cp949',
            'ks_c_5601-1989': 'cp949',
            'iso-2022-kr': 'iso2022_kr',
            'csiso2022kr': 'iso2022_kr',
            
            # Western European
            'iso-8859-1': 'iso-8859-1',
            'latin1': 'iso-8859-1',
            'l1': 'iso-8859-1',
            'ibm819': 'iso-8859-1',
            'cp819': 'iso-8859-1',
            'csisolatin1': 'iso-8859-1',
            'iso-ir-100': 'iso-8859-1',
            'iso-8859-15': 'iso-8859-15',
            'latin9': 'iso-8859-15',
            'l9': 'iso-8859-15',
            'csisolatin9': 'iso-8859-15',
            'iso-8859-2': 'iso-8859-2',
            'latin2': 'iso-8859-2',
            'l2': 'iso-8859-2',
            'csisolatin2': 'iso-8859-2',
            'iso-ir-101': 'iso-8859-2',
            'iso-8859-3': 'iso-8859-3',
            'latin3': 'iso-8859-3',
            'l3': 'iso-8859-3',
            'csisolatin3': 'iso-8859-3',
            'iso-ir-109': 'iso-8859-3',
            'iso-8859-4': 'iso-8859-4',
            'latin4': 'iso-8859-4',
            'l4': 'iso-8859-4',
            'csisolatin4': 'iso-8859-4',
            'iso-ir-110': 'iso-8859-4',
            'iso-8859-9': 'iso-8859-9',
            'latin5': 'iso-8859-9',
            'l5': 'iso-8859-9',
            'csisolatin5': 'iso-8859-9',
            'iso-ir-148': 'iso-8859-9',
            'iso-8859-10': 'iso-8859-10',
            'latin6': 'iso-8859-10',
            'l6': 'iso-8859-10',
            'csisolatin6': 'iso-8859-10',
            'iso-ir-157': 'iso-8859-10',
            'iso-8859-13': 'iso-8859-13',
            'latin7': 'iso-8859-13',
            'l7': 'iso-8859-13',
            'iso-8859-14': 'iso-8859-14',
            'latin8': 'iso-8859-14',
            'l8': 'iso-8859-14',
            'iso-8859-16': 'iso-8859-16',
            
            # Cyrillic
            'iso-8859-5': 'iso-8859-5',
            'cyrillic': 'iso-8859-5',
            'iso-ir-144': 'iso-8859-5',
            'koi8-r': 'koi8-r',
            'cskoi8r': 'koi8-r',
            'koi8r': 'koi8-r',
            'koi8': 'koi8-r',
            'koi8-u': 'koi8-u',
            'koi8u': 'koi8-u',
            'cp866': 'cp866',
            'ibm866': 'cp866',
            'dos-866': 'cp866',
            
            # Arabic
            'iso-8859-6': 'iso-8859-6',
            'arabic': 'iso-8859-6',
            'iso-8859-6-i': 'iso-8859-6',
            'iso-ir-127': 'iso-8859-6',
            'csiso88596i': 'iso-8859-6',
            'csiso88596e': 'iso-8859-6',
            'cp1256': 'cp1256',
            'windows-1256': 'cp1256',
            'ms-arab': 'cp1256',
            
            # Greek
            'iso-8859-7': 'iso-8859-7',
            'greek': 'iso-8859-7',
            'greek8': 'iso-8859-7',
            'iso-ir-126': 'iso-8859-7',
            'csisolatingreek': 'iso-8859-7',
            'cp1253': 'cp1253',
            'windows-1253': 'cp1253',
            'ms-greek': 'cp1253',
            
            # Hebrew
            'iso-8859-8': 'iso-8859-8',
            'hebrew': 'iso-8859-8',
            'iso-8859-8-i': 'iso-8859-8',
            'iso-ir-138': 'iso-8859-8',
            'csisolatinhebrew': 'iso-8859-8',
            'visual': 'iso-8859-8',
            'logical': 'iso-8859-8-i',
            'cp1255': 'cp1255',
            'windows-1255': 'cp1255',
            'ms-hebr': 'cp1255',
            
            # Thai
            'iso-8859-11': 'iso-8859-11',
            'tis-620': 'iso-8859-11',
            'tis620': 'iso-8859-11',
            'cstis620': 'iso-8859-11',
            'tis620-0': 'iso-8859-11',
            'tis620.2529-1': 'iso-8859-11',
            'tis620.2533-0': 'iso-8859-11',
            'cp874': 'cp874',
            'windows-874': 'cp874',
            'ms-thai': 'cp874',
            
            # Windows codepages
            'windows-1250': 'cp1250',
            'cp1250': 'cp1250',
            'ms-ee': 'cp1250',
            'windows-1251': 'cp1251',
            'cp1251': 'cp1251',
            'ms-cyrl': 'cp1251',
            'windows-1252': 'cp1252',
            'cp1252': 'cp1252',
            'ms-ansi': 'cp1252',
            'windows-1254': 'cp1254',
            'cp1254': 'cp1254',
            'ms-turk': 'cp1254',
            'windows-1257': 'cp1257',
            'cp1257': 'cp1257',
            'winbaltrim': 'cp1257',
            'ms-baltic': 'cp1257',
            'windows-1258': 'cp1258',
            'cp1258': 'cp1258',
            'ms-viet': 'cp1258',
            
            # UTF variants
            'utf8': 'utf-8',
            'utf-8': 'utf-8',
            'u8': 'utf-8',
            'utf': 'utf-8',
            'utf8mb4': 'utf-8',
            'utf-8-sig': 'utf-8-sig',
            'utf-8-bom': 'utf-8-sig',
            'utf16': 'utf-16',
            'utf-16': 'utf-16',
            'utf16le': 'utf-16-le',
            'utf-16le': 'utf-16-le',
            'utf16be': 'utf-16-be',
            'utf-16be': 'utf-16-be',
            'utf32': 'utf-32',
            'utf-32': 'utf-32',
            'utf32le': 'utf-32-le',
            'utf-32le': 'utf-32-le',
            'utf32be': 'utf-32-be',
            'utf-32be': 'utf-32-be',
            
            # IBM codepages
            'ibm037': 'cp037',
            'cp037': 'cp037',
            'csibm037': 'cp037',
            'ebcdic-cp-us': 'cp037',
            'ebcdic-cp-ca': 'cp037',
            'ibm437': 'cp437',
            'cp437': 'cp437',
            'cspc8codepage437': 'cp437',
            'dos-us': 'cp437',
            'ibm850': 'cp850',
            'cp850': 'cp850',
            'cspc850multilingual': 'cp850',
            'dos-latin1': 'cp850',
            'ibm852': 'cp852',
            'cp852': 'cp852',
            'cspcp852': 'cp852',
            'dos-latin2': 'cp852',
            'ibm855': 'cp855',
            'cp855': 'cp855',
            'csibm855': 'cp855',
            'ibm857': 'cp857',
            'cp857': 'cp857',
            'csibm857': 'cp857',
            'dos-turkish': 'cp857',
            'ibm858': 'cp858',
            'cp858': 'cp858',
            'csibm858': 'cp858',
            'dos-latin1-euro': 'cp858',
            'ibm860': 'cp860',
            'cp860': 'cp860',
            'csibm860': 'cp860',
            'dos-portuguese': 'cp860',
            'ibm861': 'cp861',
            'cp861': 'cp861',
            'csibm861': 'cp861',
            'dos-icelandic': 'cp861',
            'ibm862': 'cp862',
            'cp862': 'cp862',
            'csibm862': 'cp862',
            'dos-hebrew': 'cp862',
            'ibm863': 'cp863',
            'cp863': 'cp863',
            'csibm863': 'cp863',
            'dos-canadian-french': 'cp863',
            'ibm864': 'cp864',
            'cp864': 'cp864',
            'csibm864': 'cp864',
            'dos-arabic': 'cp864',
            'ibm865': 'cp865',
            'cp865': 'cp865',
            'csibm865': 'cp865',
            'dos-nordic': 'cp865',
            'ibm869': 'cp869',
            'cp869': 'cp869',
            'csibm869': 'cp869',
            'dos-greek2': 'cp869',
            'ibm1026': 'cp1026',
            'cp1026': 'cp1026',
            'csibm1026': 'cp1026',
            
            # Misc encodings
            'macintosh': 'mac-roman',
            'x-mac-roman': 'mac-roman',
            'mac': 'mac-roman',
            'macroman': 'mac-roman',
            'csmacintosh': 'mac-roman',
            'x-mac-japanese': 'shift_jis',
            'x-mac-chinesetrad': 'big5',
            'x-mac-korean': 'euc_kr',
            'x-mac-greek': 'mac-greek',
            'x-mac-cyrillic': 'mac-cyrillic',
            'x-mac-centraleurroman': 'mac-latin2',
            'x-mac-turkish': 'mac-turkish',
            'ascii': 'ascii',
            'us-ascii': 'ascii',
            'csascii': 'ascii',
            'x-ascii': 'ascii',
            'iso646-us': 'ascii',
            'default': 'utf-8',
            'x-user-defined': 'latin1'
        }
        
        return charset_map.get(charset, charset)

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
            
    def put(self, url: str, headers: Optional[Dict[str, str]] = None,
            data: Optional[Dict[str, Any]] = None,
            json_data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make a PUT request.
        
        Args:
            url: URL to request
            headers: Additional headers
            data: Form data
            json_data: JSON data
            
        Returns:
            requests.Response: Response object
        """
        try:
            logger.debug(f"PUT request to {url}")
            
            with self._lock:
                response = self.session.put(
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
            logger.error(f"Error making PUT request to {url}: {e}")
            raise
    
    def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Make a DELETE request.
        
        Args:
            url: URL to request
            headers: Additional headers
            
        Returns:
            requests.Response: Response object
        """
        try:
            logger.debug(f"DELETE request to {url}")
            
            with self._lock:
                response = self.session.delete(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
            
            response.raise_for_status()
            return response
        except RequestException as e:
            logger.error(f"Error making DELETE request to {url}: {e}")
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
    
    def options(self, url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Make an OPTIONS request.
        
        Args:
            url: URL to request
            headers: Additional headers
            
        Returns:
            requests.Response: Response object
        """
        try:
            logger.debug(f"OPTIONS request to {url}")
            
            with self._lock:
                response = self.session.options(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
            
            response.raise_for_status()
            return response
        except RequestException as e:
            logger.error(f"Error making OPTIONS request to {url}: {e}")
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
    
    def request(self, url: str, method: str = 'GET', headers: Optional[Dict[str, str]] = None,
               params: Optional[Dict[str, str]] = None, data: Optional[Dict[str, Any]] = None,
               json_data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make a request with the specified method.
        
        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            headers: Additional headers
            params: URL parameters
            data: Form data
            json_data: JSON data
            
        Returns:
            requests.Response: Response object
        """
        method = method.upper()
        
        if method == 'GET':
            return self.get(url, headers=headers, params=params)
        elif method == 'POST':
            return self.post(url, headers=headers, data=data, json_data=json_data)
        elif method == 'PUT':
            return self.put(url, headers=headers, data=data, json_data=json_data)
        elif method == 'DELETE':
            return self.delete(url, headers=headers)
        elif method == 'HEAD':
            return self.head(url, headers=headers)
        elif method == 'OPTIONS':
            return self.options(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}") 