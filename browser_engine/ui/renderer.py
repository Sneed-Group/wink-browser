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
        
        # Track processed text nodes to prevent duplicates
        self.processed_text_nodes = set()
        
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
        # Using larger linespace to prevent text overlap
        self.content_view = tk.Text(
            self.main_frame,
            wrap=tk.WORD,
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set,
            padx=15,
            pady=15,
            font=("Arial", int(12 * self.zoom_level)),
            spacing1=8,    # More aggressive spacing between lines
            spacing2=2,    # Added spacing within lines
            spacing3=8,    # More spacing after paragraphs
            exportselection=0  # Prevent selection conflicts
        )
        self.content_view.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Connect scrollbars
        self.v_scrollbar.config(command=self.content_view.yview)
        self.h_scrollbar.config(command=self.content_view.xview)
        
        # Configure tags for styling
        self._configure_text_tags()
        
        # Make it read-only for now
        self.content_view.config(state=tk.DISABLED)
        
        # Store tags that have been applied to track overlaps
        self.applied_tags = {}
        
        # Create counters to ensure unique IDs
        self.tag_counter = 0
    
    def _configure_text_tags(self) -> None:
        """Configure text tags for styling."""
        # Clear any existing tags to prevent conflicts
        for tag in self.content_view.tag_names():
            if tag != "sel":  # Don't remove the selection tag
                self.content_view.tag_delete(tag)
        
        # Reset applied tags tracking and counter
        self.applied_tags = {}
        self.tag_counter = 0
        
        # Calculate font sizes with a bit more space to prevent overlap
        # Base sizes for different elements
        base_font_size = int(12 * self.zoom_level)
        heading1_size = int(24 * self.zoom_level)
        heading2_size = int(20 * self.zoom_level)
        heading3_size = int(16 * self.zoom_level)
        
        # Larger line spacing calculation to prevent overlaps
        def calc_spacing(font_size):
            return int(font_size * 1.2)  # Increased spacing multiplier
        
        # Configure base tags for element types
        self.content_view.tag_configure(
            "h1", 
            font=("Arial", heading1_size, "bold"),
            spacing1=calc_spacing(heading1_size),
            spacing3=calc_spacing(heading1_size),
            lmargin1=0,
            lmargin2=0
        )
        
        self.content_view.tag_configure(
            "h2", 
            font=("Arial", heading2_size, "bold"),
            spacing1=calc_spacing(heading2_size),
            spacing3=calc_spacing(heading2_size),
            lmargin1=0,
            lmargin2=0
        )
        
        self.content_view.tag_configure(
            "h3", 
            font=("Arial", heading3_size, "bold"),
            spacing1=calc_spacing(heading3_size),
            spacing3=calc_spacing(heading3_size),
            lmargin1=0,
            lmargin2=0
        )
        
        self.content_view.tag_configure(
            "p", 
            font=("Arial", base_font_size),
            spacing1=calc_spacing(base_font_size),
            spacing3=calc_spacing(base_font_size),
            lmargin1=0,
            lmargin2=0
        )
        
        # Inline tags with unique font settings but no spacing adjustments
        self.content_view.tag_configure(
            "a", 
            font=("Arial", base_font_size, "underline"),
            foreground="blue",
            lmargin1=0,
            lmargin2=0
        )
        
        self.content_view.tag_configure(
            "bold", 
            font=("Arial", base_font_size, "bold"),
            lmargin1=0,
            lmargin2=0
        )
        
        self.content_view.tag_configure(
            "italic", 
            font=("Arial", base_font_size, "italic"),
            lmargin1=0,
            lmargin2=0
        )
        
        self.content_view.tag_configure(
            "code", 
            font=("Courier", base_font_size),
            background="#f0f0f0",
            lmargin1=0,
            lmargin2=0
        )
        
        self.content_view.tag_configure(
            "pre", 
            font=("Courier", base_font_size),
            background="#f0f0f0",
            spacing1=calc_spacing(base_font_size),
            spacing3=calc_spacing(base_font_size),
            wrap=tk.NONE,
            lmargin1=0,
            lmargin2=0
        )
        
        # Creating a tag for normal text to ensure consistent rendering
        self.content_view.tag_configure(
            "normal",
            font=("Arial", base_font_size),
            lmargin1=0,
            lmargin2=0
        )
    
    def update(self) -> None:
        """Update the content view with the current page."""
        # Clear the content
        self.content_view.config(state=tk.NORMAL)
        self.content_view.delete(1.0, tk.END)
        
        # Reset all tags and styling
        self._configure_text_tags()
        
        # Clear processed nodes tracking
        self.processed_text_nodes.clear()
        self.applied_tags.clear()
        self.tag_counter = 0
        
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
        # Clear any previously tracked tags
        self.applied_tags = {}
        
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
            # Only render the text if it's directly in the body or another container,
            # and not inside an element that will render it with get_text()
            parent_name = element.parent.name if element.parent else None
            safe_to_render = parent_name in ('body', 'div', 'span', 'td', 'th', 'li', 'blockquote', 'section', 'article', 'aside')
            
            if element.string and element.string.strip() and safe_to_render:
                # Get the text with whitespace trimmed
                text = element.string.strip()
                
                # Create a unique identifier for this text node
                text_id = f"{id(element)}_{text}"
                
                # Skip if this text was already processed
                if text_id in self.processed_text_nodes:
                    return
                
                # Get a unique tag identifier for this text
                self.tag_counter += 1
                tag_name = f"normal_{self.tag_counter}"
                
                # Create a custom tag for this specific text
                self.content_view.tag_configure(
                    tag_name, 
                    font=("Arial", int(12 * self.zoom_level))
                )
                
                # Mark position to apply tag
                start_index = self.content_view.index(tk.INSERT)
                
                # Insert the text
                self.content_view.insert(tk.END, text + " ")  # Add space after text
                
                # Apply the tag to ONLY this text
                end_index = self.content_view.index(tk.INSERT)
                self.content_view.tag_add(tag_name, start_index, end_index)
                
                # Track this tag
                self.applied_tags[start_index] = tag_name
                
                # Mark this text node as processed
                self.processed_text_nodes.add(text_id)
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
        elif element.name == 'input':
            self._render_input(element)
        elif element.name == 'button':
            self._render_button(element)
        elif element.name == 'select':
            self._render_select(element)
        elif element.name == 'form':
            self._render_form(element)
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
        elif element.name in ('script', 'style', 'meta', 'link', 'head', 'option'):
            # Skip these elements when processed directly (option is handled by _render_select)
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
        # Create a unique tag for this specific heading
        self.tag_counter += 1
        unique_tag = f"{tag}_{self.tag_counter}"
        
        # Configure the sizing based on heading level
        if tag == "h1":
            font_size = int(24 * self.zoom_level)
        elif tag == "h2":
            font_size = int(20 * self.zoom_level)
        else:  # h3 or other headings
            font_size = int(16 * self.zoom_level)
            
        # Configure a unique tag for this heading
        self.content_view.tag_configure(
            unique_tag,
            font=("Arial", font_size, "bold"),
            spacing1=int(font_size * 1.2),
            spacing3=int(font_size * 1.2),
            lmargin1=0,
            lmargin2=0
        )
        
        # Add spacing before heading
        self.content_view.insert(tk.END, "\n\n")
        
        # Get current position for tag application
        current_line = self.content_view.index(tk.INSERT).split('.')[0]
        start_index = f"{current_line}.0"
        
        # Insert the heading text
        heading_text = element.get_text().strip()
        self.content_view.insert(tk.END, heading_text)
        
        # Get end position
        end_index = self.content_view.index(tk.INSERT)
        
        # Add spacing after heading
        self.content_view.insert(tk.END, "\n\n")
        
        # Apply the unique tag
        self.content_view.tag_add(unique_tag, start_index, end_index)
        self.applied_tags[start_index] = unique_tag
    
    def _render_paragraph(self, element) -> None:
        """
        Render a paragraph element.
        
        Args:
            element: Paragraph element
        """
        # Get a unique tag identifier for this paragraph
        self.tag_counter += 1
        tag_name = f"p_{self.tag_counter}"
        
        # Configure this specific paragraph tag
        self.content_view.tag_configure(
            tag_name,
            font=("Arial", int(12 * self.zoom_level)),
            spacing1=int(12 * self.zoom_level * 1.2),
            spacing3=int(12 * self.zoom_level * 1.2),
            lmargin1=0,
            lmargin2=0
        )
        
        # Add spacing before paragraph on a separate line
        self.content_view.insert(tk.END, "\n")
        
        # Start the paragraph on a fresh line
        current_line = self.content_view.index(tk.INSERT).split('.')[0]
        start_index = f"{current_line}.0"
        
        # Extract all text content directly from the paragraph 
        para_text = element.get_text().strip()
        if para_text:
            self.content_view.insert(tk.END, para_text)
        else:
            # Handle any nested elements if there's no direct text
            for child in element.children:
                if child.name is not None:
                    self._render_element(child)
        
        # Get end position before adding spacing
        current_pos = self.content_view.index(tk.INSERT)
        end_index = current_pos
        
        # Add spacing after paragraph on a separate line
        self.content_view.insert(tk.END, "\n")
        
        # Only apply tag if there was content
        if start_index != end_index:
            self.content_view.tag_add(tag_name, start_index, end_index)
            self.applied_tags[start_index] = tag_name
    
    def _render_link(self, element) -> None:
        """
        Render a link element.
        
        Args:
            element: Link element
        """
        href = element.get('href', '')
        
        # Get link text and strip whitespace
        link_text = element.get_text().strip() or href
        if not link_text:
            return  # Skip empty links
        
        # Mark the start position for tagging
        start_index = self.content_view.index(tk.INSERT)
        
        # Insert the link text
        self.content_view.insert(tk.END, link_text)
        
        # Calculate end position
        end_index = self.content_view.index(tk.INSERT)
        
        # Apply the tag - only to the actual link text
        if start_index != end_index:
            self.content_view.tag_add('a', start_index, end_index)
        
        # Bind the click event
        def on_link_click(event):
            logger.info(f"Link clicked: {href}")
            if href:
                self.engine.load_url(href)
        
        # Bind click event to the tag
        self.content_view.tag_bind('a', '<Button-1>', on_link_click)
        
        # Track this tag application
        self.applied_tags[start_index] = 'a'
    
    def _render_image(self, element) -> None:
        """
        Render an image element.
        
        Args:
            element: Image element
        """
        # Ensure there's a newline before standalone images
        parent_name = element.parent.name if element.parent else None
        if parent_name not in ('a', 'button', 'span'):
            current_pos = self.content_view.index(tk.INSERT)
            if not current_pos.endswith('.0'):  # If not already at line start
                self.content_view.insert(tk.END, '\n')
        
        alt_text = element.get('alt', '[Image]')
        src = element.get('src', '')
        
        # In a real browser, we would load and display the image
        # For now, just show the alt text
        self.content_view.insert(tk.END, f"[Image: {alt_text}]")
        
        # Ensure there's a newline after standalone images
        if parent_name not in ('a', 'button', 'span'):
            self.content_view.insert(tk.END, '\n')
    
    def _render_div(self, element) -> None:
        """
        Render a div element.
        
        Args:
            element: Div element
        """
        # Insert a newline before div to ensure proper spacing
        current_pos = self.content_view.index(tk.INSERT)
        if not current_pos.endswith('.0'):  # If not already at line start
            self.content_view.insert(tk.END, '\n')
            
        # Process children
        for child in element.children:
            self._render_element(child)
        
        # Insert a newline after div to ensure proper spacing
        self.content_view.insert(tk.END, '\n')
    
    def _render_formatted_text(self, element, tag: str) -> None:
        """
        Render formatted text (bold, italic, etc.).
        
        Args:
            element: Element with the formatted text
            tag: Text tag to apply
        """
        # Get the text content
        text = element.get_text().strip()
        if not text:
            return  # Skip empty elements
        
        # Mark the start position for tagging
        start_index = self.content_view.index(tk.INSERT)
        
        # Insert the text
        self.content_view.insert(tk.END, text)
        
        # Calculate end position
        end_index = self.content_view.index(tk.INSERT)
        
        # Apply the tag only to the content
        if start_index != end_index:
            self.content_view.tag_add(tag, start_index, end_index)
        
        # Track this tag application
        self.applied_tags[start_index] = tag
    
    def _render_preformatted(self, element) -> None:
        """
        Render preformatted text.
        
        Args:
            element: Preformatted text element
        """
        # Ensure there's a line break before preformatted text
        current_pos = self.content_view.index(tk.INSERT)
        if not current_pos.endswith('.0'):
            self.content_view.insert(tk.END, '\n')
            
        # Mark the start position for tagging
        start_index = self.content_view.index(tk.INSERT)
        
        # Process children if any
        has_children = False
        for child in element.children:
            self._render_element(child)
            has_children = True
        
        # If no children were processed, insert the text directly
        if not has_children:
            # Preserve exact whitespace in preformatted text
            pre_text = element.get_text()
            self.content_view.insert(tk.END, pre_text)
        
        # Add newlines after the content
        self.content_view.insert(tk.END, '\n\n')
        
        # Apply the tag - don't include the trailing newlines in the tag
        end_index = self.content_view.index(f"{start_index} lineend +{len(element.get_text().splitlines())-1} lines")
        
        # Only apply the tag if there was actual content
        if start_index != end_index:
            self.content_view.tag_add('pre', start_index, end_index)
    
    def _render_list(self, element, marker: Optional[str] = None, ordered: bool = False) -> None:
        """
        Render a list element.
        
        Args:
            element: List element
            marker: List item marker (bullet, etc.)
            ordered: Whether the list is ordered
        """
        # Ensure there's a newline before lists
        current_pos = self.content_view.index(tk.INSERT)
        if not current_pos.endswith('.0'):  # If not already at line start
            self.content_view.insert(tk.END, '\n')
        
        # Process all li elements
        counter = 1
        for li in element.find_all('li', recursive=False):
            if ordered:
                # For ordered lists, use numbers
                prefix = f"{counter}. "
                counter += 1
            else:
                # For unordered lists, use the marker (default: bullet)
                prefix = marker or "• "
            
            # Insert the prefix
            self.content_view.insert(tk.END, prefix)
            
            # Process li children
            for child in li.children:
                self._render_element(child)
            
            # Ensure there's a newline after each list item
            current_pos = self.content_view.index(tk.INSERT)
            if not current_pos.endswith('.0'):
                self.content_view.insert(tk.END, '\n')
        
        # Add an extra newline after the list for spacing
        self.content_view.insert(tk.END, '\n')
    
    def _render_input(self, element) -> None:
        """
        Render an input element.
        
        Args:
            element: Input element
        """
        input_type = element.get('type', 'text').lower()
        placeholder = element.get('placeholder', '')
        value = element.get('value', '')
        name = element.get('name', '')
        
        # Render different types of inputs
        if input_type == 'text':
            display_text = f"[Text Input: {placeholder or name or 'text'}]"
            if value:
                display_text = f"[Text Input: {value}]"
            self.content_view.insert(tk.END, display_text)
        elif input_type == 'password':
            self.content_view.insert(tk.END, f"[Password Input]")
        elif input_type == 'submit':
            self.content_view.insert(tk.END, f"[Submit Button: {value or 'Submit'}]")
        elif input_type == 'button':
            self.content_view.insert(tk.END, f"[Button: {value or name or 'Button'}]")
        elif input_type == 'checkbox':
            checked = "✓" if element.get('checked') is not None else "□"
            self.content_view.insert(tk.END, f"{checked} ")
        elif input_type == 'radio':
            selected = "⚫" if element.get('checked') is not None else "○"
            self.content_view.insert(tk.END, f"{selected} ")
        elif input_type == 'hidden':
            # Don't render hidden inputs
            pass
        elif input_type == 'search':
            self.content_view.insert(tk.END, f"[Search Box: {placeholder or 'Search...'}]")
        else:
            # For other input types (file, date, etc.)
            self.content_view.insert(tk.END, f"[{input_type.capitalize()} Input]")

    def _render_button(self, element) -> None:
        """
        Render a button element.
        
        Args:
            element: Button element
        """
        # Get button text
        button_text = element.get_text().strip()
        if not button_text:
            button_text = element.get('value', 'Button')
        
        # Render button
        self.content_view.insert(tk.END, f"[Button: {button_text}]")

    def _render_form(self, element) -> None:
        """
        Render a form element.
        
        Args:
            element: Form element
        """
        # Process form children
        for child in element.children:
            self._render_element(child)
    
    def _render_select(self, element) -> None:
        """
        Render a select dropdown.
        
        Args:
            element: Select element
        """
        # Get attributes
        name = element.get('name', '')
        
        # Find selected option if any
        selected_option = element.find('option', selected=True)
        if not selected_option:
            selected_option = element.find('option')  # Get first option
        
        # Get display text
        if selected_option:
            display_text = selected_option.get_text()
        else:
            display_text = name or "Select"
        
        # Get count of options
        option_count = len(element.find_all('option'))
        
        # Render select
        self.content_view.insert(tk.END, f"[Dropdown: {display_text} ▼ ({option_count} options)]")

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