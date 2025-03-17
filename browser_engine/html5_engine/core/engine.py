"""
HTML5Engine - Main engine class for HTML5 rendering.

This class integrates the DOM, CSS, and rendering components to provide
a complete HTML5 rendering engine.
"""

import logging
import os
import urllib.request
from typing import Dict, Optional, Tuple, Union, List, Callable
import tkinter as tk
from tkinter import ttk

from ..dom import Document, SelectorEngine
from ..css import CSSParser, LayoutEngine
from ..rendering import HTML5Renderer

class HTML5Engine:
    """
    Main HTML5 rendering engine class.
    
    This class integrates DOM parsing, CSS styling, layout calculation,
    and rendering to provide a complete HTML5 rendering engine.
    """
    
    def __init__(self, width: int = 800, height: int = 600, debug: bool = False):
        """
        Initialize the HTML5 engine.
        
        Args:
            width: Initial viewport width
            height: Initial viewport height
            debug: Enable debug logging
        """
        # Configure logging
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=log_level, 
                           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('HTML5Engine')
        
        # Store viewport dimensions
        self.viewport_width = width
        self.viewport_height = height
        
        # Initialize components
        self.document = None
        self.css_parser = CSSParser()
        self.selector_engine = SelectorEngine()
        self.layout_engine = LayoutEngine()
        
        # The renderer will be initialized later when a parent frame is available
        self.renderer = None
        
        # Event handlers
        self.on_load_handlers = []
        self.on_error_handlers = []
        
        self.logger.info("HTML5Engine initialized with viewport %dx%d", width, height)
    
    def initialize_renderer(self, parent_frame: ttk.Frame) -> None:
        """
        Initialize the renderer with a parent frame.
        
        Args:
            parent_frame: Parent Tkinter frame for rendering
        """
        self.renderer = HTML5Renderer(parent_frame)
        self.logger.info("HTML5Renderer initialized")
    
    def load_html(self, html_content: str, base_url: str = None) -> Document:
        """
        Load HTML content into the engine.
        
        Args:
            html_content: HTML content as string
            base_url: Base URL for resolving relative URLs
            
        Returns:
            The parsed Document object
        """
        self.logger.info("Loading HTML content")
        
        # Create a new document
        self.document = Document()
        
        # Parse HTML into the document
        self.document.parse_html(html_content)
        
        # Store base URL
        self.document.base_url = base_url
        
        # Process stylesheets
        self._process_stylesheets(base_url)
        
        # Calculate layout
        self._calculate_layout()
        
        # Render the document
        self._render()
        
        # Trigger load event
        self._trigger_load()
        
        return self.document
    
    def load_url(self, url: str) -> Document:
        """
        Load HTML from a URL.
        
        Args:
            url: URL to load
            
        Returns:
            The parsed Document object
        """
        self.logger.info("Loading URL: %s", url)
        
        try:
            # Fetch the URL
            with urllib.request.urlopen(url) as response:
                html_content = response.read().decode('utf-8')
                
            # Load the HTML content
            return self.load_html(html_content, url)
            
        except Exception as e:
            self.logger.error("Error loading URL: %s", str(e))
            self._trigger_error(str(e))
            raise
    
    def load_file(self, file_path: str) -> Document:
        """
        Load HTML from a local file.
        
        Args:
            file_path: Path to the HTML file
            
        Returns:
            The parsed Document object
        """
        self.logger.info("Loading file: %s", file_path)
        
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Convert file path to URL format for base URL
            base_url = f"file://{os.path.abspath(file_path)}"
            
            # Load the HTML content
            return self.load_html(html_content, base_url)
            
        except Exception as e:
            self.logger.error("Error loading file: %s", str(e))
            self._trigger_error(str(e))
            raise
    
    def resize(self, width: int, height: int) -> None:
        """
        Resize the viewport.
        
        Args:
            width: New viewport width
            height: New viewport height
        """
        self.logger.info("Resizing viewport to %dx%d", width, height)
        
        # Update renderer dimensions
        self.renderer.resize(width, height)
        
        # Recalculate layout if we have a document
        if self.document:
            self._calculate_layout()
            self._render()
    
    def on_load(self, callback: Callable[[], None]) -> None:
        """
        Register a callback for when a document is loaded.
        
        Args:
            callback: Function to call when document is loaded
        """
        self.on_load_handlers.append(callback)
    
    def on_error(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback for when an error occurs.
        
        Args:
            callback: Function to call when an error occurs
        """
        self.on_error_handlers.append(callback)
    
    def _process_stylesheets(self, base_url: Optional[str] = None) -> None:
        """
        Process all stylesheets in the document.
        
        Args:
            base_url: Base URL for resolving relative URLs
        """
        if not self.document:
            return
            
        self.logger.info("Processing stylesheets")
        
        # Process inline styles
        try:
            elements_with_style = self._find_elements_with_attribute(self.document, "style")
            for element in elements_with_style:
                style_attr = element.get_attribute("style")
                if style_attr:
                    inline_styles = self.css_parser.parse_inline_styles(style_attr)
                    if not hasattr(element, 'computed_style'):
                        element.computed_style = {}
                    element.computed_style.update(inline_styles)
        except Exception as e:
            self.logger.error(f"Error processing inline styles: {e}")
        
        # Process <style> elements
        try:
            style_elements = self._find_elements_by_tag_name(self.document, "style")
            for style_element in style_elements:
                if hasattr(style_element, 'text_content') and style_element.text_content:
                    stylesheet = self.css_parser.parse(style_element.text_content, base_url)
                    self._apply_stylesheet(stylesheet)
        except Exception as e:
            self.logger.error(f"Error processing style elements: {e}")
        
        # Process <link rel="stylesheet"> elements
        try:
            link_elements = self._find_stylesheet_links(self.document)
            for link_element in link_elements:
                href = link_element.get_attribute("href")
                if href and base_url:
                    # Resolve URL
                    if not href.startswith(('http://', 'https://', 'file://')):
                        if base_url.endswith('/'):
                            full_url = f"{base_url}{href}"
                        else:
                            full_url = f"{base_url}/{href}"
                    else:
                        full_url = href
                        
                    try:
                        # Fetch the stylesheet
                        with urllib.request.urlopen(full_url) as response:
                            css_content = response.read().decode('utf-8')
                            
                        # Parse and apply the stylesheet
                        stylesheet = self.css_parser.parse(css_content, base_url)
                        self._apply_stylesheet(stylesheet)
                        
                    except Exception as e:
                        self.logger.error(f"Error loading stylesheet {full_url}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing stylesheet links: {e}")
    
    def _find_elements_with_attribute(self, node, attribute_name):
        """Find elements with a specific attribute."""
        result = []
        
        # Check if this is an element node with the attribute
        if hasattr(node, 'node_type') and node.node_type == 1:  # ELEMENT_NODE
            if hasattr(node, 'has_attribute') and node.has_attribute(attribute_name):
                result.append(node)
        
        # Check children
        if hasattr(node, 'child_nodes'):
            for child in node.child_nodes:
                result.extend(self._find_elements_with_attribute(child, attribute_name))
        
        return result
    
    def _find_elements_by_tag_name(self, node, tag_name):
        """Find elements with a specific tag name."""
        result = []
        
        # Check if this is an element node with the matching tag
        if hasattr(node, 'node_type') and node.node_type == 1:  # ELEMENT_NODE
            if hasattr(node, 'tag_name') and node.tag_name.lower() == tag_name.lower():
                result.append(node)
        
        # Check children
        if hasattr(node, 'child_nodes'):
            for child in node.child_nodes:
                result.extend(self._find_elements_by_tag_name(child, tag_name))
        
        return result
    
    def _find_stylesheet_links(self, node):
        """Find link elements with rel="stylesheet"."""
        result = []
        
        # Check if this is a link element with rel="stylesheet"
        if (hasattr(node, 'node_type') and node.node_type == 1 and  # ELEMENT_NODE
            hasattr(node, 'tag_name') and node.tag_name.lower() == 'link'):
            if (hasattr(node, 'get_attribute') and 
                node.get_attribute('rel') and 
                node.get_attribute('rel').lower() == 'stylesheet'):
                result.append(node)
        
        # Check children
        if hasattr(node, 'child_nodes'):
            for child in node.child_nodes:
                result.extend(self._find_stylesheet_links(child))
        
        return result
    
    def _apply_stylesheet(self, stylesheet: Dict) -> None:
        """
        Apply a stylesheet to the document.
        
        Args:
            stylesheet: Parsed stylesheet
        """
        if not self.document:
            return
            
        # Extract styles from the stylesheet
        styles = self.css_parser.extract_styles(stylesheet)
        
        # Apply styles to matching elements
        for selector, properties in styles.items():
            try:
                # Find elements matching the selector
                matching_elements = self.selector_engine.select(selector, self.document)
                
                # Apply properties to each matching element
                for element in matching_elements:
                    # Merge properties into element's computed style
                    if not hasattr(element, 'computed_style'):
                        element.computed_style = {}
                    
                    # Update computed style with new properties
                    element.computed_style.update(properties)
                    
            except Exception as e:
                self.logger.error("Error applying selector %s: %s", selector, str(e))
    
    def _calculate_layout(self) -> None:
        """Calculate layout for the document."""
        if not self.document:
            self.logger.warning("Cannot calculate layout: document is missing")
            return
            
        self.logger.info("Calculating layout")
        
        # Get viewport dimensions from renderer
        if not self.renderer:
            self.logger.error("Cannot calculate layout: renderer is not initialized")
            return
            
        viewport_width = self.renderer.viewport_width
        viewport_height = self.renderer.viewport_height
        
        self.logger.debug(f"Using viewport dimensions: {viewport_width}x{viewport_height}")
        
        # Calculate layout using the layout engine
        try:
            self.layout = self.layout_engine.create_layout(
                self.document, 
                viewport_width, 
                viewport_height
            )
            self.logger.debug(f"Layout created successfully: {self.layout}")
        except Exception as e:
            self.logger.error(f"Error calculating layout: {str(e)}")
            self._trigger_error(f"Layout calculation error: {str(e)}")
    
    def _render(self) -> None:
        """Render the document."""
        if not self.document:
            self.logger.warning("Cannot render: document is missing")
            return
            
        if not hasattr(self, 'layout') or self.layout is None:
            self.logger.warning("Cannot render: layout is missing")
            return
            
        if not self.renderer:
            self.logger.error("Cannot render: renderer is not initialized")
            return
            
        self.logger.info("Rendering document")
        
        # Clear the renderer
        try:
            self.renderer.clear()
            
            # Render the document using the calculated layout
            self.logger.debug(f"Passing layout to renderer: {self.layout}")
            self.renderer.render(self.document, self.layout)
            self.logger.info("Document rendered successfully")
            
            # Trigger load event handlers
            self._trigger_load()
        except Exception as e:
            self.logger.error(f"Error rendering document: {str(e)}")
            self._trigger_error(f"Rendering error: {str(e)}")
    
    def _trigger_load(self) -> None:
        """Trigger load event handlers."""
        for handler in self.on_load_handlers:
            try:
                handler()
            except Exception as e:
                self.logger.error("Error in load handler: %s", str(e))
    
    def _trigger_error(self, error_message: str) -> None:
        """
        Trigger error event handlers.
        
        Args:
            error_message: Error message
        """
        for handler in self.on_error_handlers:
            try:
                handler(error_message)
            except Exception as e:
                self.logger.error("Error in error handler: %s", str(e)) 