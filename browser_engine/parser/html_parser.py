"""
HTML parser implementation.
This module is responsible for parsing HTML content with full HTML5 support.
"""

import logging
from typing import Optional, Dict, List, Any, Tuple, Set
from bs4 import BeautifulSoup, Tag
import html5lib
import re
import urllib.parse

logger = logging.getLogger(__name__)

# Set of HTML5 void elements (self-closing tags)
HTML5_VOID_ELEMENTS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr'
}

# Set of HTML5 media elements
HTML5_MEDIA_ELEMENTS = {
    'audio', 'video', 'picture', 'img', 'svg', 'canvas'
}

class HTMLParser:
    """HTML parser using BeautifulSoup with html5lib for full HTML5 support."""
    
    def __init__(self):
        """Initialize the HTML parser."""
        logger.debug("HTML parser initialized with full HTML5 support")
    
    def parse(self, html_content: str, base_url: Optional[str] = None) -> BeautifulSoup:
        """
        Parse HTML content into a DOM tree.
        
        Args:
            html_content: HTML content to parse
            base_url: Optional base URL for resolving relative URLs
            
        Returns:
            BeautifulSoup: Parsed DOM
        """
        try:
            # Use html5lib as the parser for better HTML5 compatibility
            dom = BeautifulSoup(html_content, 'html5lib')
            
            # Add base URL to the dom for reference
            if base_url:
                self._set_base_url(dom, base_url)
                
            return dom
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            # Return a minimal DOM with an error message
            return self._create_error_dom(str(e))
    
    def _set_base_url(self, dom: BeautifulSoup, base_url: str) -> None:
        """
        Set the base URL for the document.
        
        Args:
            dom: BeautifulSoup DOM
            base_url: Base URL to set
        """
        # Check if there's already a base tag
        base_tag = dom.find('base')
        if base_tag:
            # Update the href attribute
            base_tag['href'] = base_url
        else:
            # Create a new base tag
            head = dom.find('head')
            if head:
                new_base = dom.new_tag('base', href=base_url)
                head.insert(0, new_base)
            else:
                # Create a head element if it doesn't exist
                head = dom.new_tag('head')
                new_base = dom.new_tag('base', href=base_url)
                head.append(new_base)
                
                # Insert head at the beginning of the document
                if dom.html:
                    dom.html.insert(0, head)
                else:
                    html = dom.new_tag('html')
                    html.append(head)
                    dom.append(html)
    
    def _create_error_dom(self, error_message: str) -> BeautifulSoup:
        """
        Create a minimal DOM with an error message.
        
        Args:
            error_message: Error message to display
            
        Returns:
            BeautifulSoup: Error DOM
        """
        error_html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>Parsing Error</title>
            </head>
            <body>
                <h1>Error Parsing HTML</h1>
                <p>There was an error parsing the HTML content:</p>
                <pre>{error_message}</pre>
            </body>
        </html>
        """
        return BeautifulSoup(error_html, 'html5lib')
    
    def get_elements_by_tag(self, dom: BeautifulSoup, tag_name: str) -> List[Tag]:
        """
        Get all elements by tag name.
        
        Args:
            dom: DOM to search
            tag_name: Tag name to find
            
        Returns:
            List[Tag]: List of matching elements
        """
        return dom.find_all(tag_name)
    
    def get_element_by_id(self, dom: BeautifulSoup, element_id: str) -> Optional[Tag]:
        """
        Get an element by ID.
        
        Args:
            dom: DOM to search
            element_id: Element ID to find
            
        Returns:
            Optional[Tag]: Matching element or None
        """
        return dom.find(id=element_id)
    
    def get_elements_by_class(self, dom: BeautifulSoup, class_name: str) -> List[Tag]:
        """
        Get elements by class name.
        
        Args:
            dom: DOM to search
            class_name: Class name to find
            
        Returns:
            List[Tag]: List of matching elements
        """
        return dom.find_all(class_=class_name)
    
    def get_elements_by_selector(self, dom: BeautifulSoup, css_selector: str) -> List[Tag]:
        """
        Get elements by CSS selector.
        
        Args:
            dom: DOM to search
            css_selector: CSS selector
            
        Returns:
            List[Tag]: List of matching elements
        """
        try:
            return dom.select(css_selector)
        except Exception as e:
            logger.error(f"Error in CSS selector '{css_selector}': {e}")
            return []
    
    def get_attribute(self, element: Tag, attribute_name: str) -> Optional[str]:
        """
        Get an attribute value from an element.
        
        Args:
            element: Element to get attribute from
            attribute_name: Name of the attribute
            
        Returns:
            Optional[str]: Attribute value or None
        """
        return element.get(attribute_name)
    
    def extract_links(self, dom: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract all links from a DOM.
        
        Args:
            dom: DOM to extract links from
            
        Returns:
            List[Dict[str, str]]: List of links with href, text, and title
        """
        links = []
        for a in dom.find_all('a', href=True):
            link = {
                'href': a['href'],
                'text': a.get_text(strip=True),
                'title': a.get('title', '')
            }
            links.append(link)
        return links
    
    def extract_forms(self, dom: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract all forms from a DOM.
        
        Args:
            dom: DOM to extract forms from
            
        Returns:
            List[Dict[str, Any]]: List of forms with action, method, and fields
        """
        forms = []
        for form in dom.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get').upper(),
                'fields': []
            }
            
            # Extract fields
            for input_field in form.find_all(['input', 'textarea', 'select']):
                field = {
                    'name': input_field.get('name', ''),
                    'type': input_field.get('type', 'text') if input_field.name == 'input' else input_field.name,
                    'value': input_field.get('value', '')
                }
                form_data['fields'].append(field)
            
            forms.append(form_data)
        
        return forms
    
    def extract_images(self, dom: BeautifulSoup, base_url: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Extract all images from the DOM.
        
        Args:
            dom: BeautifulSoup DOM
            base_url: Optional base URL for resolving relative URLs
            
        Returns:
            List[Dict[str, str]]: List of image information dictionaries
        """
        images = []
        
        # Find all img elements
        for img in dom.find_all('img'):
            src = self.get_attribute(img, 'src')
            if src:
                # Convert relative URLs to absolute URLs if base_url is provided
                if base_url and not src.startswith(('http://', 'https://', 'data:', 'file:')):
                    src = urllib.parse.urljoin(base_url, src)
                
                # Extract image information
                image_info = {
                    'src': src,
                    'alt': self.get_attribute(img, 'alt') or '',
                    'width': self.get_attribute(img, 'width') or '',
                    'height': self.get_attribute(img, 'height') or '',
                    'title': self.get_attribute(img, 'title') or '',
                    'loading': self.get_attribute(img, 'loading') or 'auto',
                    'id': self.get_attribute(img, 'id') or '',
                    'class': self.get_attribute(img, 'class') or ''
                }
                images.append(image_info)
        
        # Find all picture elements and their source and img children
        for picture in dom.find_all('picture'):
            img = picture.find('img')
            if img:
                src = self.get_attribute(img, 'src')
                if src:
                    # Convert relative URLs to absolute URLs if base_url is provided
                    if base_url and not src.startswith(('http://', 'https://', 'data:', 'file:')):
                        src = urllib.parse.urljoin(base_url, src)
                    
                    # Extract image information
                    image_info = {
                        'src': src,
                        'alt': self.get_attribute(img, 'alt') or '',
                        'width': self.get_attribute(img, 'width') or '',
                        'height': self.get_attribute(img, 'height') or '',
                        'title': self.get_attribute(img, 'title') or '',
                        'loading': self.get_attribute(img, 'loading') or 'auto',
                        'id': self.get_attribute(img, 'id') or '',
                        'class': self.get_attribute(img, 'class') or '',
                        'is_picture': True,
                        'sources': []
                    }
                    
                    # Extract source elements
                    for source in picture.find_all('source'):
                        srcset = self.get_attribute(source, 'srcset')
                        if srcset:
                            # Convert relative URLs to absolute URLs if base_url is provided
                            if base_url:
                                srcset_parts = []
                                for srcset_part in srcset.split(','):
                                    url_and_size = srcset_part.strip().split(' ')
                                    url = url_and_size[0]
                                    if not url.startswith(('http://', 'https://', 'data:', 'file:')):
                                        url = urllib.parse.urljoin(base_url, url)
                                    srcset_parts.append(f"{url} {' '.join(url_and_size[1:])}")
                                srcset = ', '.join(srcset_parts)
                            
                            source_info = {
                                'srcset': srcset,
                                'media': self.get_attribute(source, 'media') or '',
                                'type': self.get_attribute(source, 'type') or '',
                                'sizes': self.get_attribute(source, 'sizes') or ''
                            }
                            image_info['sources'].append(source_info)
                    
                    images.append(image_info)
        
        # Find images in CSS background properties
        for element in dom.find_all(style=True):
            style = self.get_attribute(element, 'style')
            if style:
                # Extract background-image URLs
                background_match = re.search(r'background(-image)?:\s*url\([\'"]?([^\'"\)]+)[\'"]?\)', style)
                if background_match:
                    background_url = background_match.group(2)
                    # Convert relative URLs to absolute URLs if base_url is provided
                    if base_url and not background_url.startswith(('http://', 'https://', 'data:', 'file:')):
                        background_url = urllib.parse.urljoin(base_url, background_url)
                    
                    # Extract image information
                    image_info = {
                        'src': background_url,
                        'alt': '',
                        'width': '',
                        'height': '',
                        'title': '',
                        'loading': 'auto',
                        'id': self.get_attribute(element, 'id') or '',
                        'class': self.get_attribute(element, 'class') or '',
                        'is_background': True
                    }
                    images.append(image_info)
        
        return images

    def extract_media(self, dom: BeautifulSoup, base_url: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all media elements (audio, video) from the DOM.
        
        Args:
            dom: BeautifulSoup DOM
            base_url: Optional base URL for resolving relative URLs
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary of media lists by type
        """
        media = {
            'audio': [],
            'video': [],
            'iframe': []
        }
        
        # Extract audio elements
        for audio in dom.find_all('audio'):
            src = self.get_attribute(audio, 'src')
            if src:
                # Convert relative URLs to absolute URLs if base_url is provided
                if base_url and not src.startswith(('http://', 'https://', 'data:', 'file:')):
                    src = urllib.parse.urljoin(base_url, src)
                
                # Extract audio information
                audio_info = {
                    'src': src,
                    'controls': 'controls' in audio.attrs,
                    'autoplay': 'autoplay' in audio.attrs,
                    'loop': 'loop' in audio.attrs,
                    'muted': 'muted' in audio.attrs,
                    'preload': self.get_attribute(audio, 'preload') or 'auto',
                    'id': self.get_attribute(audio, 'id') or '',
                    'class': self.get_attribute(audio, 'class') or '',
                    'sources': []
                }
                
                # Extract source elements
                for source in audio.find_all('source'):
                    source_src = self.get_attribute(source, 'src')
                    if source_src:
                        # Convert relative URLs to absolute URLs if base_url is provided
                        if base_url and not source_src.startswith(('http://', 'https://', 'data:', 'file:')):
                            source_src = urllib.parse.urljoin(base_url, source_src)
                        
                        source_info = {
                            'src': source_src,
                            'type': self.get_attribute(source, 'type') or ''
                        }
                        audio_info['sources'].append(source_info)
                
                media['audio'].append(audio_info)
        
        # Extract video elements
        for video in dom.find_all('video'):
            src = self.get_attribute(video, 'src')
            if src:
                # Convert relative URLs to absolute URLs if base_url is provided
                if base_url and not src.startswith(('http://', 'https://', 'data:', 'file:')):
                    src = urllib.parse.urljoin(base_url, src)
                
                # Extract video information
                video_info = {
                    'src': src,
                    'controls': 'controls' in video.attrs,
                    'autoplay': 'autoplay' in video.attrs,
                    'loop': 'loop' in video.attrs,
                    'muted': 'muted' in video.attrs,
                    'poster': self.get_attribute(video, 'poster') or '',
                    'width': self.get_attribute(video, 'width') or '',
                    'height': self.get_attribute(video, 'height') or '',
                    'preload': self.get_attribute(video, 'preload') or 'auto',
                    'id': self.get_attribute(video, 'id') or '',
                    'class': self.get_attribute(video, 'class') or '',
                    'sources': []
                }
                
                # Convert poster URL to absolute URL if base_url is provided
                if base_url and video_info['poster'] and not video_info['poster'].startswith(('http://', 'https://', 'data:', 'file:')):
                    video_info['poster'] = urllib.parse.urljoin(base_url, video_info['poster'])
                
                # Extract source elements
                for source in video.find_all('source'):
                    source_src = self.get_attribute(source, 'src')
                    if source_src:
                        # Convert relative URLs to absolute URLs if base_url is provided
                        if base_url and not source_src.startswith(('http://', 'https://', 'data:', 'file:')):
                            source_src = urllib.parse.urljoin(base_url, source_src)
                        
                        source_info = {
                            'src': source_src,
                            'type': self.get_attribute(source, 'type') or ''
                        }
                        video_info['sources'].append(source_info)
                
                media['video'].append(video_info)
        
        # Extract iframe elements
        for iframe in dom.find_all('iframe'):
            src = self.get_attribute(iframe, 'src')
            if src:
                # Convert relative URLs to absolute URLs if base_url is provided
                if base_url and not src.startswith(('http://', 'https://', 'data:', 'file:')):
                    src = urllib.parse.urljoin(base_url, src)
                
                # Extract iframe information
                iframe_info = {
                    'src': src,
                    'width': self.get_attribute(iframe, 'width') or '',
                    'height': self.get_attribute(iframe, 'height') or '',
                    'id': self.get_attribute(iframe, 'id') or '',
                    'class': self.get_attribute(iframe, 'class') or '',
                    'allowfullscreen': 'allowfullscreen' in iframe.attrs
                }
                
                media['iframe'].append(iframe_info)
        
        return media

    def extract_meta_data(self, dom: BeautifulSoup) -> Dict[str, str]:
        """
        Extract metadata from a DOM.
        
        Args:
            dom: DOM to extract metadata from
            
        Returns:
            Dict[str, str]: Dictionary of metadata
        """
        metadata = {}
        
        # Title
        title = dom.find('title')
        if title:
            metadata['title'] = title.get_text(strip=True)
        
        # Meta tags
        for meta in dom.find_all('meta'):
            name = meta.get('name', '')
            content = meta.get('content', '')
            
            if name and content:
                metadata[name] = content
                
            # OpenGraph tags
            property_attr = meta.get('property', '')
            if property_attr.startswith('og:') and content:
                metadata[property_attr] = content
        
        return metadata
    
    def extract_all_text(self, dom: BeautifulSoup) -> str:
        """
        Extract all text from a DOM.
        
        Args:
            dom: DOM to extract text from
            
        Returns:
            str: Plain text content
        """
        # Remove script and style elements
        for script in dom(['script', 'style']):
            script.extract()
        
        # Get text
        text = dom.get_text(separator=' ', strip=True)
        return text
    
    def create_element(self, tag_name: str, attrs: Dict[str, str] = None) -> Tag:
        """
        Create a new HTML element.
        
        Args:
            tag_name: Tag name
            attrs: Dictionary of attributes
            
        Returns:
            Tag: New element
        """
        return BeautifulSoup('', 'html5lib').new_tag(tag_name, attrs=attrs or {})

    def resolve_urls(self, dom: BeautifulSoup, base_url: str) -> BeautifulSoup:
        """
        Resolve all relative URLs in the DOM to absolute URLs.
        
        Args:
            dom: BeautifulSoup DOM
            base_url: Base URL for resolving relative URLs
            
        Returns:
            BeautifulSoup: DOM with resolved URLs
        """
        # Check if there's a base tag that might override the base_url
        base_tag = dom.find('base')
        if base_tag and base_tag.get('href'):
            base_url = base_tag['href']
        
        # URL attributes by tag
        url_attributes = {
            'a': ['href'],
            'img': ['src', 'srcset'],
            'video': ['src', 'poster'],
            'audio': ['src'],
            'source': ['src', 'srcset'],
            'link': ['href'],
            'script': ['src'],
            'iframe': ['src'],
            'embed': ['src'],
            'object': ['data'],
            'form': ['action'],
            'input': ['src'],
            'track': ['src'],
            'area': ['href']
        }
        
        # Process each element with URL attributes
        for tag, attrs in url_attributes.items():
            for element in dom.find_all(tag):
                for attr in attrs:
                    if element.has_attr(attr):
                        value = element[attr]
                        
                        # Handle srcset attribute differently (comma-separated list of URLs)
                        if attr == 'srcset':
                            srcset_parts = []
                            for srcset_part in value.split(','):
                                url_and_size = srcset_part.strip().split(' ', 1)
                                url = url_and_size[0]
                                if not url.startswith(('http://', 'https://', 'data:', 'file:', '#')):
                                    url = urllib.parse.urljoin(base_url, url)
                                if len(url_and_size) > 1:
                                    srcset_parts.append(f"{url} {url_and_size[1]}")
                                else:
                                    srcset_parts.append(url)
                            element[attr] = ', '.join(srcset_parts)
                        else:
                            # Regular URL attribute
                            if value and not value.startswith(('http://', 'https://', 'data:', 'file:', '#', 'javascript:', 'mailto:')):
                                element[attr] = urllib.parse.urljoin(base_url, value)
        
        # Handle style attributes and inline CSS (background-image, etc.)
        for element in dom.find_all(style=True):
            style = element['style']
            # Extract and replace URLs in CSS
            element['style'] = self._resolve_css_urls(style, base_url)
        
        # Handle inline style elements
        for style in dom.find_all('style'):
            if style.string:
                style.string = self._resolve_css_urls(style.string, base_url)
        
        return dom
    
    def _resolve_css_urls(self, css: str, base_url: str) -> str:
        """
        Resolve URLs in CSS content.
        
        Args:
            css: CSS content
            base_url: Base URL for resolving relative URLs
            
        Returns:
            str: CSS with resolved URLs
        """
        def replace_url(match):
            url = match.group(1)
            # Remove quotes if present
            if url.startswith('"') and url.endswith('"'):
                url = url[1:-1]
            elif url.startswith("'") and url.endswith("'"):
                url = url[1:-1]
                
            # Only resolve if not already absolute or special protocol
            if not url.startswith(('http://', 'https://', 'data:', 'file:', '#')):
                url = urllib.parse.urljoin(base_url, url)
                
            return f"url({url})"
        
        # Replace URLs in CSS
        return re.sub(r'url\(([^)]+)\)', replace_url, css) 