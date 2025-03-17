"""
HTML parser implementation.
This module is responsible for parsing HTML content.
"""

import logging
from typing import Optional, Dict, List, Any
from bs4 import BeautifulSoup, Tag
import html5lib

logger = logging.getLogger(__name__)

class HTMLParser:
    """HTML parser using BeautifulSoup with html5lib."""
    
    def __init__(self):
        """Initialize the HTML parser."""
        logger.debug("HTML parser initialized")
    
    def parse(self, html_content: str) -> BeautifulSoup:
        """
        Parse HTML content into a DOM.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            BeautifulSoup: Parsed DOM
        """
        try:
            # Use html5lib as the parser for better compatibility
            dom = BeautifulSoup(html_content, 'html5lib')
            return dom
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            # Return a minimal DOM with an error message
            return self._create_error_dom(str(e))
    
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
    
    def extract_images(self, dom: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract all images from a DOM.
        
        Args:
            dom: DOM to extract images from
            
        Returns:
            List[Dict[str, str]]: List of images with src, alt, and width/height
        """
        images = []
        for img in dom.find_all('img'):
            image = {
                'src': img.get('src', ''),
                'alt': img.get('alt', ''),
                'width': img.get('width', ''),
                'height': img.get('height', '')
            }
            images.append(image)
        return images
    
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