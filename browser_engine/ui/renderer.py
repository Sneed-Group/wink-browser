"""
Renderer implementation for Tkinter.
This module contains the renderer that displays web content.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
import io
from typing import Optional, Dict, List, Any
from PIL import Image, ImageTk

from browser_engine.core.engine import BrowserEngine

logger = logging.getLogger(__name__)

class TkRenderer:
    """Tkinter-based web content renderer."""
    
    def __init__(self, parent: ttk.Frame, engine: BrowserEngine):
        """
        Initialize the renderer.
        
        Args:
            parent: Parent Tkinter frame
            engine: Browser engine instance
        """
        self.parent = parent
        self.engine = engine
        
        # Zoom level (1.0 = 100%)
        self.zoom_level = 1.0
        
        # Create the main content view
        self._create_content_view()
        
        logger.info("Renderer initialized")
    
    def _create_content_view(self) -> None:
        """Create the content view widget."""
        # Create a frame with scrollbars
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create vertical scrollbar
        self.v_scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create horizontal scrollbar
        self.h_scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.HORIZONTAL)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create the text widget for content display
        self.content_view = tk.Text(
            self.main_frame,
            wrap=tk.WORD,
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set,
            padx=10,
            pady=10,
            font=("Arial", int(12 * self.zoom_level))
        )
        self.content_view.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Connect scrollbars
        self.v_scrollbar.config(command=self.content_view.yview)
        self.h_scrollbar.config(command=self.content_view.xview)
        
        # Configure tags for styling
        self._configure_text_tags()
        
        # Make it read-only for now
        self.content_view.config(state=tk.DISABLED)
    
    def _configure_text_tags(self) -> None:
        """Configure text tags for styling."""
        self.content_view.tag_configure(
            "h1", 
            font=("Arial", int(24 * self.zoom_level), "bold"),
            spacing1=10,
            spacing3=10
        )
        
        self.content_view.tag_configure(
            "h2", 
            font=("Arial", int(20 * self.zoom_level), "bold"),
            spacing1=8,
            spacing3=8
        )
        
        self.content_view.tag_configure(
            "h3", 
            font=("Arial", int(16 * self.zoom_level), "bold"),
            spacing1=6,
            spacing3=6
        )
        
        self.content_view.tag_configure(
            "p", 
            font=("Arial", int(12 * self.zoom_level)),
            spacing1=4,
            spacing3=4
        )
        
        self.content_view.tag_configure(
            "a", 
            font=("Arial", int(12 * self.zoom_level), "underline"),
            foreground="blue"
        )
        
        self.content_view.tag_configure(
            "bold", 
            font=("Arial", int(12 * self.zoom_level), "bold")
        )
        
        self.content_view.tag_configure(
            "italic", 
            font=("Arial", int(12 * self.zoom_level), "italic")
        )
        
        self.content_view.tag_configure(
            "code", 
            font=("Courier", int(12 * self.zoom_level)),
            background="#f0f0f0"
        )
        
        self.content_view.tag_configure(
            "pre", 
            font=("Courier", int(12 * self.zoom_level)),
            background="#f0f0f0",
            spacing1=6,
            spacing3=6,
            wrap=tk.NONE
        )
    
    def update(self) -> None:
        """Update the content view with the current page."""
        # Clear the content
        self.content_view.config(state=tk.NORMAL)
        self.content_view.delete(1.0, tk.END)
        
        # Get the DOM from the engine
        dom = self.engine.dom
        if not dom:
            self.content_view.config(state=tk.DISABLED)
            return
        
        if self.engine.text_only_mode:
            # In text-only mode, just show the plain text
            plain_text = self.engine.get_plain_text()
            self.content_view.insert(tk.END, plain_text)
        else:
            # Render the HTML content
            self._render_dom(dom)
        
        # Make it read-only again
        self.content_view.config(state=tk.DISABLED)
        
        # Scroll to the top
        self.content_view.yview_moveto(0)
    
    def _render_dom(self, dom) -> None:
        """
        Render the DOM in the content view.
        
        Args:
            dom: BeautifulSoup DOM object
        """
        # This is a simplified implementation of HTML rendering
        # In a real browser, this would be much more complex
        
        # Extract the body content
        body = dom.find('body')
        if not body:
            body = dom  # If no body tag, use the entire document
        
        # Process the body's child elements
        for element in body.children:
            self._render_element(element)
    
    def _render_element(self, element) -> None:
        """
        Render an HTML element.
        
        Args:
            element: BeautifulSoup element
        """
        # Skip comment nodes and other non-element nodes
        if element.name is None:
            # This is a text node, render it as plain text
            if element.string and element.string.strip():
                self.content_view.insert(tk.END, element.string)
            return
        
        # Handle different HTML elements
        if element.name == 'h1':
            self._render_heading(element, 'h1')
        elif element.name == 'h2':
            self._render_heading(element, 'h2')
        elif element.name == 'h3':
            self._render_heading(element, 'h3')
        elif element.name in ('h4', 'h5', 'h6'):
            self._render_heading(element, 'h3')  # Simplify by using h3 style
        elif element.name == 'p':
            self._render_paragraph(element)
        elif element.name == 'a':
            self._render_link(element)
        elif element.name == 'img':
            self._render_image(element)
        elif element.name == 'div':
            self._render_div(element)
        elif element.name in ('b', 'strong'):
            self._render_formatted_text(element, 'bold')
        elif element.name in ('i', 'em'):
            self._render_formatted_text(element, 'italic')
        elif element.name == 'code':
            self._render_formatted_text(element, 'code')
        elif element.name == 'pre':
            self._render_preformatted(element)
        elif element.name == 'br':
            self.content_view.insert(tk.END, '\n')
        elif element.name == 'hr':
            self.content_view.insert(tk.END, '\n' + '-' * 80 + '\n')
        elif element.name == 'ul':
            self._render_list(element, '• ')
        elif element.name == 'ol':
            self._render_list(element, None, ordered=True)
        elif element.name == 'li':
            # Individual list items are handled by render_list
            pass
        elif element.name in ('script', 'style', 'meta', 'link', 'head'):
            # Skip these elements
            pass
        else:
            # For any other element, just render its children
            for child in element.children:
                self._render_element(child)
    
    def _render_heading(self, element, tag: str) -> None:
        """
        Render a heading element.
        
        Args:
            element: Heading element
            tag: Tag name (h1, h2, etc.)
        """
        # Insert the heading text with appropriate tag
        start_index = self.content_view.index(tk.INSERT)
        self.content_view.insert(tk.END, element.get_text() + '\n\n')
        end_index = self.content_view.index(tk.INSERT)
        
        # Apply the tag
        self.content_view.tag_add(tag, start_index, end_index)
    
    def _render_paragraph(self, element) -> None:
        """
        Render a paragraph element.
        
        Args:
            element: Paragraph element
        """
        # Insert the paragraph text with appropriate tag
        start_index = self.content_view.index(tk.INSERT)
        
        # Process children (may contain links, bold text, etc.)
        has_children = False
        for child in element.children:
            self._render_element(child)
            has_children = True
        
        # Ensure paragraph ends with a newline
        current_index = self.content_view.index(tk.INSERT)
        if has_children and not current_index.endswith('.0'):
            self.content_view.insert(tk.END, '\n\n')
        elif not has_children:
            self.content_view.insert(tk.END, element.get_text() + '\n\n')
        
        end_index = self.content_view.index(tk.INSERT)
        
        # Apply the tag
        self.content_view.tag_add('p', start_index, end_index)
    
    def _render_link(self, element) -> None:
        """
        Render a link element.
        
        Args:
            element: Link element
        """
        href = element.get('href', '')
        text = element.get_text() or href
        
        # Insert the link text with appropriate tag
        start_index = self.content_view.index(tk.INSERT)
        self.content_view.insert(tk.END, text)
        end_index = self.content_view.index(tk.INSERT)
        
        # Apply the tag
        self.content_view.tag_add('a', start_index, end_index)
        
        # Bind the click event
        # In a real browser, clicking a link would navigate to it
        # For now, we just log a message
        def on_link_click(event):
            logger.info(f"Link clicked: {href}")
            if href:
                # Try to navigate to the link
                # In a real browser, we would handle relative URLs properly
                self.engine.load_url(href)
        
        # Bind click event to the tag
        self.content_view.tag_bind('a', '<Button-1>', on_link_click)
    
    def _render_image(self, element) -> None:
        """
        Render an image element.
        
        Args:
            element: Image element
        """
        # In a real browser, we would download and display the image
        # For this simplified implementation, we just show a placeholder
        alt_text = element.get('alt', '[Image]')
        self.content_view.insert(tk.END, f'[Image: {alt_text}]')
    
    def _render_div(self, element) -> None:
        """
        Render a div element.
        
        Args:
            element: Div element
        """
        # Process all children
        for child in element.children:
            self._render_element(child)
    
    def _render_formatted_text(self, element, tag: str) -> None:
        """
        Render formatted text (bold, italic, etc.).
        
        Args:
            element: Element with the formatted text
            tag: Text tag to apply
        """
        start_index = self.content_view.index(tk.INSERT)
        self.content_view.insert(tk.END, element.get_text())
        end_index = self.content_view.index(tk.INSERT)
        
        # Apply the tag
        self.content_view.tag_add(tag, start_index, end_index)
    
    def _render_preformatted(self, element) -> None:
        """
        Render preformatted text.
        
        Args:
            element: Preformatted text element
        """
        start_index = self.content_view.index(tk.INSERT)
        self.content_view.insert(tk.END, element.get_text() + '\n\n')
        end_index = self.content_view.index(tk.INSERT)
        
        # Apply the tag
        self.content_view.tag_add('pre', start_index, end_index)
    
    def _render_list(self, element, marker: Optional[str] = None, ordered: bool = False) -> None:
        """
        Render a list element.
        
        Args:
            element: List element
            marker: Bullet marker for unordered lists
            ordered: Whether this is an ordered list
        """
        # Indent the list
        self.content_view.insert(tk.END, '\n')
        
        # Process list items
        item_number = 1
        for item in element.find_all('li', recursive=False):
            prefix = f"{item_number}. " if ordered else marker
            item_number += 1
            
            self.content_view.insert(tk.END, f"    {prefix}")
            
            # Process item content
            start_pos = len(prefix) + 4  # 4 spaces for indentation
            for child in item.children:
                self._render_element(child)
            
            self.content_view.insert(tk.END, '\n')
        
        self.content_view.insert(tk.END, '\n')
    
    def zoom_in(self) -> None:
        """Increase the zoom level."""
        if self.zoom_level < 3.0:  # Limit maximum zoom
            self.zoom_level += 0.1
            self._update_font_sizes()
            logger.debug(f"Zoom in: {self.zoom_level:.1f}")
    
    def zoom_out(self) -> None:
        """Decrease the zoom level."""
        if self.zoom_level > 0.5:  # Limit minimum zoom
            self.zoom_level -= 0.1
            self._update_font_sizes()
            logger.debug(f"Zoom out: {self.zoom_level:.1f}")
    
    def zoom_reset(self) -> None:
        """Reset zoom to default level."""
        self.zoom_level = 1.0
        self._update_font_sizes()
        logger.debug("Zoom reset")
    
    def _update_font_sizes(self) -> None:
        """Update font sizes based on zoom level."""
        # Update the base font size
        self.content_view.config(font=("Arial", int(12 * self.zoom_level)))
        
        # Update all the tag font sizes
        self._configure_text_tags()
        
        # Refresh the view to apply changes
        self.update() 