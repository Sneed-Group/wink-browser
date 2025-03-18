"""
Markdown-based DOM creation mode.
This module implements a DOM creation mode that converts HTML to markdown and back to HTML.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from bs4 import BeautifulSoup
import html2text
import markdown
from .document import Document
from .node import NodeType

logger = logging.getLogger(__name__)

class MarkdownDOMCreator:
    """
    Creates a DOM by converting HTML to markdown and back to HTML.
    This provides a clean slate for DOM creation while preserving structure.
    """
    
    def __init__(self):
        """Initialize the Markdown DOM Creator."""
        self.html2text_converter = html2text.HTML2Text()
        self.html2text_converter.ignore_links = False
        self.html2text_converter.ignore_images = False
        self.html2text_converter.ignore_tables = False
        self.html2text_converter.body_width = 0  # No wrapping
        self.html2text_converter.unicode_snob = True  # Preserve Unicode
        self.html2text_converter.ul_item_mark = '-'  # Consistent list markers
        
        self.markdown_converter = markdown.Markdown(
            extensions=['tables', 'fenced_code', 'attr_list']
        )
    
    def create_dom(self, html_content: str, base_url: Optional[str] = None) -> Document:
        """
        Create a new DOM from HTML content using markdown conversion.
        
        Args:
            html_content: The HTML content to process
            base_url: Optional base URL for resolving relative URLs
            
        Returns:
            A new Document object with the processed content
        """
        # Step 1: Clean up previous page's elements
        # This is handled by creating a new Document instance
        document = Document()
        
        # Step 2: Extract text content and structure
        soup = BeautifulSoup(html_content, 'html5lib')
        text_map = self._extract_text_content(soup)
        
        # Step 3: Convert HTML to markdown
        markdown_content = self.html2text_converter.handle(html_content)
        logger.debug(f"Markdown content:\n{markdown_content}")
        
        # Step 4: Convert markdown back to HTML with equivalent classes and IDs
        processed_html = self.markdown_converter.convert(markdown_content)
        logger.debug(f"Processed HTML:\n{processed_html}")
        
        # Step 5: Parse the processed HTML into a DOM
        document.parse_html(processed_html, base_url)
        
        # Step 6: Restore text content
        self._restore_text_content(document, text_map)
        
        # Step 7: Insert missing videos/audio
        self._insert_media_elements(document)
        
        # Step 8: Apply CSS and JS
        self._apply_styles_and_scripts(document)
        
        # Step 9: Collect garbage (original HTML is discarded)
        # This is handled automatically by Python's garbage collection
        
        return document
    
    def _extract_text_content(self, soup: BeautifulSoup) -> Dict[Tuple[str, int], str]:
        """
        Extract text content from elements with their path information.
        
        Args:
            soup: BeautifulSoup object of the HTML
            
        Returns:
            Dictionary mapping element identifiers to their text content
        """
        text_map = {}
        
        def get_element_path(element) -> Tuple[str, int]:
            """Get a unique identifier for an element based on its path and position."""
            if not element.parent:
                return (element.name, 0)
            
            siblings = element.parent.find_all(element.name, recursive=False)
            position = siblings.index(element)
            return (element.name, position)
        
        for element in soup.find_all():
            # Skip script and style elements
            if element.name in ('script', 'style'):
                continue
                
            # Get direct text content (excluding child element text)
            texts = []
            for content in element.contents:
                if isinstance(content, str):
                    text = content.strip()
                    if text:
                        texts.append(text)
            
            if texts:
                path = get_element_path(element)
                text_map[path] = ' '.join(texts)
                logger.debug(f"Extracted text from {path}: {text_map[path]}")
        
        return text_map
    
    def _restore_text_content(self, document: Document, text_map: Dict[Tuple[str, int], str]) -> None:
        """
        Restore text content to elements in the document.
        
        Args:
            document: The document to restore text to
            text_map: Dictionary mapping element identifiers to their text content
        """
        def process_element(element, parent_count=None):
            """Process an element and its children to restore text content."""
            if not hasattr(element, 'tag_name'):
                return
            
            # Skip script and style elements
            if element.tag_name in ('script', 'style'):
                return
            
            # Count siblings with same tag name
            siblings = []
            if element.parent_node:
                for child in element.parent_node.child_nodes:
                    if hasattr(child, 'tag_name') and child.tag_name == element.tag_name:
                        siblings.append(child)
            position = siblings.index(element) if element in siblings else 0
            
            # Try to find matching text content
            key = (element.tag_name, position)
            if key in text_map:
                logger.debug(f"Restoring text to {key}: {text_map[key]}")
                element.text_content = text_map[key]
            
            # Process children
            for child in element.child_nodes:
                process_element(child)
        
        # Start processing from the document element
        if document.document_element:
            process_element(document.document_element)
    
    def _insert_media_elements(self, document: Document) -> None:
        """
        Insert missing video and audio elements.
        
        Args:
            document: The document to process
        """
        if not document.body:
            return
            
        # Find all links that might be media files
        for element in document.body.get_elements_by_tag_name('a'):
            href = element.get_attribute('href')
            if not href:
                continue
                
            # Check if it's a media file
            if any(href.lower().endswith(ext) for ext in ['.mp4', '.webm', '.ogg', '.mp3', '.wav']):
                # Create appropriate media element
                if any(href.lower().endswith(ext) for ext in ['.mp4', '.webm', '.ogg']):
                    media_element = document.create_element('video')
                    media_element.set_attribute('controls', '')
                else:
                    media_element = document.create_element('audio')
                    media_element.set_attribute('controls', '')
                
                # Set source
                source = document.create_element('source')
                source.set_attribute('src', href)
                source.set_attribute('type', self._get_media_type(href))
                media_element.append_child(source)
                
                # Replace the link with the media element
                element.parent_node.replace_child(media_element, element)
    
    def _get_media_type(self, url: str) -> str:
        """
        Get the MIME type for a media URL.
        
        Args:
            url: The media URL
            
        Returns:
            The MIME type string
        """
        ext = url.lower().split('.')[-1]
        types = {
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'ogg': 'video/ogg',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav'
        }
        return types.get(ext, '')
    
    def _apply_styles_and_scripts(self, document: Document) -> None:
        """
        Apply CSS and JavaScript to the document.
        
        Args:
            document: The document to process
        """
        # Apply CSS first
        self._apply_css(document)
        
        # Then apply JavaScript
        self._apply_javascript(document)
    
    def _apply_css(self, document: Document) -> None:
        """
        Apply CSS to the document.
        
        Args:
            document: The document to process
        """
        # Find all style elements
        style_elements = document.get_elements_by_tag_name('style')
        
        # Create a new style element for all styles
        combined_style = document.create_element('style')
        combined_css = []
        
        # Collect all CSS
        for style_element in style_elements:
            if hasattr(style_element, 'style_content'):
                combined_css.append(style_element.style_content)
        
        # Set the combined CSS
        if combined_css:
            combined_style.style_content = '\n'.join(combined_css)
            document.head.append_child(combined_style)
    
    def _apply_javascript(self, document: Document) -> None:
        """
        Apply JavaScript to the document.
        
        Args:
            document: The document to process
        """
        # Find all script elements
        script_elements = document.get_elements_by_tag_name('script')
        
        # Create a new script element for all scripts
        combined_script = document.create_element('script')
        combined_js = []
        
        # Collect all JavaScript
        for script_element in script_elements:
            if hasattr(script_element, 'script_content'):
                combined_js.append(script_element.script_content)
        
        # Set the combined JavaScript
        if combined_js:
            combined_script.script_content = '\n'.join(combined_js)
            document.body.append_child(combined_script) 