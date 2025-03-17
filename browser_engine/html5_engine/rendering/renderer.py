"""
HTML5 Renderer implementation.
This module provides a Tkinter-based renderer for displaying HTML5 content.
"""

import logging
import io
import os
import re
import tkinter as tk
from tkinter import ttk, Canvas, Text, PhotoImage, TclError
from typing import Dict, List, Optional, Tuple, Any, Union, Set, Callable
from PIL import Image, ImageTk, ImageDraw, ImageFont
import math
import threading
import queue

from ..dom import Document, Element, Node, NodeType
from ..css import LayoutEngine, LayoutBox, CSSParser, DisplayType

logger = logging.getLogger(__name__)

class HTML5Renderer:
    """
    HTML5 Renderer using Tkinter.
    
    This class renders HTML5 documents with full CSS support.
    """
    
    def __init__(self, parent: ttk.Frame):
        """
        Initialize the renderer.
        
        Args:
            parent: Parent Tkinter frame
        """
        self.parent = parent
        
        # Create the main content frame
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollbars
        self.v_scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.h_scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.HORIZONTAL)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create the canvas for rendering
        self.canvas = Canvas(
            self.main_frame,
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set,
            bg='white'
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Link scrollbars to canvas
        self.v_scrollbar.config(command=self.canvas.yview)
        self.h_scrollbar.config(command=self.canvas.xview)
        
        # Layout and CSS engines
        self.layout_engine = LayoutEngine()
        self.css_parser = CSSParser()
        
        # Document and layout tree
        self.document: Optional[Document] = None
        self.layout_tree: Optional[LayoutBox] = None
        
        # Canvas items (for cleanup)
        self.canvas_items: List[int] = []
        
        # Viewport dimensions
        self.viewport_width = 800
        self.viewport_height = 600
        
        # Zoom level (1.0 = 100%)
        self.zoom_level = 1.0
        
        # Fonts
        self._init_fonts()
        
        # Colors
        self._init_colors()
        
        # Image cache
        self.image_cache: Dict[str, PhotoImage] = {}
        
        # Event bindings
        self._init_event_bindings()
        
        # Link handling callbacks
        self.on_link_click: Optional[Callable[[str], None]] = None
        
        logger.debug("HTML5 Renderer initialized")
    
    def _init_fonts(self) -> None:
        """
        Initialize fonts for rendering.
        """
        # Initialize default fonts
        self.fonts = {
            'default': ('Arial', 12),
            'heading': ('Arial', 16, 'bold'),
            'monospace': ('Courier New', 12),
            'serif': ('Times New Roman', 12),
            'sans-serif': ('Arial', 12),
            'cursive': ('Comic Sans MS', 12),
            'fantasy': ('Impact', 12),
        }
        
        # Font style modifiers
        self.font_styles = {
            'bold': 'bold',
            'italic': 'italic',
            'underline': 'underline',
            'overstrike': 'overstrike'  # For strikethrough
        }
    
    def _init_colors(self) -> None:
        """Initialize colors for rendering."""
        self.colors = {
            'link': '#0000EE',
            'visited_link': '#551A8B',
            'active_link': '#FF0000',
            'selection': '#B5D5FF',
            'default_text': '#000000',
            'border': '#000000',
            'background': '#FFFFFF',
        }
    
    def _init_event_bindings(self) -> None:
        """Initialize event bindings for the canvas."""
        # Mouse click event binding
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        
        # Resize event binding
        self.parent.bind("<Configure>", self._on_resize)
    
    def clear(self) -> None:
        """
        Clear the renderer and reset all state.
        This is a public method that calls the internal _clear_canvas method.
        """
        self._clear_canvas()
        self.document = None
        self.layout_tree = None
        logger.debug("Renderer cleared")
    
    def _on_canvas_click(self, event) -> None:
        """
        Handle canvas click events.
        
        Args:
            event: Tkinter event object
        """
        # Find the element at the clicked position
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        element = self._find_element_at_position(x, y)
        
        if element:
            # Check for link
            if element.tag_name.lower() == 'a':
                href = element.get_attribute('href')
                if href and self.on_link_click:
                    self.on_link_click(href)
    
    def _on_resize(self, event) -> None:
        """
        Handle resize events.
        
        Args:
            event: Tkinter event object
        """
        # Update viewport dimensions
        self.viewport_width = event.width
        self.viewport_height = event.height
        
        # Re-render the document if available
        if self.document:
            self.render(self.document)
    
    def _find_element_at_position(self, x: int, y: int) -> Optional[Element]:
        """
        Find the DOM element at a given position.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            The element at the position, or None if not found
        """
        # Get canvas items at the position
        items = self.canvas.find_overlapping(x, y, x, y)
        
        for item_id in items:
            # Check if the item has an associated element
            element_id = self.canvas.itemcget(item_id, 'tags')
            if element_id and element_id.startswith('element:'):
                # Extract element ID and find in document
                id_parts = element_id.split(':')
                if len(id_parts) >= 2:
                    element_selector = id_parts[1]
                    # Find element in document
                    if self.document:
                        return self.document.query_selector(f"#{element_selector}")
        
        # No element found
        return None
    
    def render(self, document: Document, layout: Optional[LayoutBox] = None) -> None:
        """
        Render an HTML document.
        
        Args:
            document: The document to render
            layout: Optional pre-calculated layout tree
        """
        if not document:
            logger.warning("Cannot render: document is None")
            return
            
        logger.info(f"Starting rendering document: {document}")
        self.document = document
        
        # Clear previous rendering
        self._clear_canvas()
        
        # Use provided layout or create a new one
        if layout:
            logger.debug(f"Using provided layout tree: {layout}")
            self.layout_tree = layout
        else:
            logger.debug("No layout provided, creating new layout")
            # Create layout tree
            try:
                self.layout_tree = self.layout_engine.create_layout_tree(document)
                
                # Apply layout calculations
                self.layout_engine.layout(self.layout_tree, self.viewport_width, self.viewport_height)
                logger.debug(f"Created new layout tree: {self.layout_tree}")
            except Exception as e:
                logger.error(f"Error creating layout: {str(e)}")
                return
        
        # Verify layout tree before rendering
        if not self.layout_tree:
            logger.error("Cannot render: layout tree is None")
            return
            
        # Render layout tree
        try:
            self._render_layout_tree(self.layout_tree)
            
            # Configure canvas scroll region
            self._update_scroll_region()
            
            logger.debug("Document rendered successfully")
        except Exception as e:
            logger.error(f"Error rendering layout tree: {str(e)}")
    
    def _clear_canvas(self) -> None:
        """Clear the canvas and reset state."""
        # Delete all canvas items
        for item_id in self.canvas_items:
            try:
                self.canvas.delete(item_id)
            except TclError:
                pass  # Item already deleted
        
        self.canvas_items = []
        
        # Clear the image cache
        self.image_cache.clear()
    
    def _update_scroll_region(self) -> None:
        """Update the canvas scroll region based on content size."""
        if self.layout_tree:
            # Get the layout tree's width and height
            width = self.layout_tree.box_metrics.margin_box_width
            height = self.layout_tree.box_metrics.margin_box_height
            
            # Set the scroll region
            self.canvas.config(scrollregion=(0, 0, width, height))
    
    def _render_layout_tree(self, layout_box: LayoutBox) -> None:
        """
        Render a layout tree to the canvas.
        
        Args:
            layout_box: The layout box to render
        """
        if not layout_box:
            logger.error("Cannot render layout tree: layout_box is None")
            return
            
        logger.debug(f"Rendering layout box: {layout_box}")
        
        # Render this box
        if layout_box.element:
            logger.debug(f"Rendering element: {layout_box.element.tag_name}")
            self._render_element_box(layout_box)
        else:
            logger.debug("Layout box has no element, skipping rendering")
        
        # Render children
        if hasattr(layout_box, 'children') and layout_box.children:
            logger.debug(f"Rendering {len(layout_box.children)} children")
            for child in layout_box.children:
                self._render_layout_tree(child)
        else:
            logger.debug("Layout box has no children")
    
    def _render_element_box(self, layout_box: LayoutBox) -> None:
        """
        Render an element box to the canvas.
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element:
            return
        
        # Get the tag name
        tag_name = element.tag_name.lower() if hasattr(element, 'tag_name') else ""
        
        # Handle specific element types
        if tag_name == 'img':
            self._render_image_element(layout_box)
        elif tag_name == 'a':
            self._render_link_element(layout_box)
        elif tag_name in ('ul', 'ol'):
            self._render_list_element(layout_box)
        elif tag_name == 'table':
            self._render_table_element(layout_box)
        elif tag_name == 'form' or (tag_name == 'input' and not layout_box.parent.element.tag_name == 'form'):
            self._render_form_element(layout_box)
        elif tag_name == 'audio':
            self._render_audio_element(layout_box)
        elif tag_name == 'video':
            self._render_video_element(layout_box)
        elif tag_name == 'div':
            # Render div with default styling
            self._render_default_element_box(layout_box)
        elif tag_name in ('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article', 'section', 'header', 'footer', 'nav', 'aside'):
            # Render other block elements
            self._render_default_element_box(layout_box)
        elif tag_name in ('span', 'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'del', 'code'):
            # Render styled inline elements
            self._render_text_content(layout_box)
        else:
            # Default rendering for other elements
            # First render the element box
            self._render_default_element_box(layout_box)
            
            # Then render text content if the element has any
            if hasattr(element, 'text_content') and element.text_content:
                self._render_text_content(layout_box)
    
    def _render_image_element(self, layout_box: LayoutBox) -> None:
        """
        Render an image element.
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element:
            return
            
        # Get image source
        src = element.get_attribute('src') if hasattr(element, 'get_attribute') else None
        if not src:
            # No source, render placeholder
            self._render_image_placeholder(layout_box)
            return
            
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
        width = layout_box.box_metrics.width
        height = layout_box.box_metrics.height
        
        # Check if image is loaded in cache
        image = self._get_image_from_cache(src)
        if image:
            # Image is loaded, render it
            self._render_loaded_image(image, x, y, width, height, element)
        else:
            # Image not loaded, start loading and render placeholder
            self._start_image_loading(src)
            self._render_image_placeholder(layout_box)
            
    def _get_image_from_cache(self, src):
        """
        Get image from cache if available.
        
        Args:
            src: Image source URL
            
        Returns:
            Image object or None if not in cache
        """
        # In a full implementation, this would check an image cache
        # For now, we'll simulate always returning None (not cached)
        return None
        
    def _start_image_loading(self, src):
        """
        Start loading an image asynchronously.
        
        Args:
            src: Image source URL
        """
        # In a full implementation, this would start an async download
        # For now, we'll just log the attempt
        logging.info(f"Would start loading image from: {src}")
        
    def _render_loaded_image(self, image, x, y, width, height, element):
        """
        Render a loaded image.
        
        Args:
            image: The image object
            x, y: Position coordinates
            width, height: Dimensions
            element: The image element
        """
        # In a full implementation, this would draw the image on canvas
        # For now, we'll just draw a placeholder
        placeholder = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            outline='#CCCCCC',
            fill='#F0F0F0',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(placeholder)
        
        # Add an icon to indicate it's an image
        icon_text = self.canvas.create_text(
            x + width/2, y + height/2,
            text="🖼️",  # Image icon
            font=self.fonts['default'],
            fill='#888888',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(icon_text)
    
    def _render_image_placeholder(self, layout_box):
        """
        Render a placeholder for an image that is not yet loaded.
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
        width = layout_box.box_metrics.width
        height = layout_box.box_metrics.height
        
        # Draw placeholder rectangle
        placeholder = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            outline='#CCCCCC',
            fill='#F0F0F0',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(placeholder)
        
        # Add loading text
        loading_text = self.canvas.create_text(
            x + width/2, y + height/2,
            text="Loading...",
            font=self.fonts['default'],
            fill='#888888',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(loading_text)
        
        # Get alt text if available
        alt_text = element.get_attribute('alt') if hasattr(element, 'get_attribute') else None
        if alt_text:
            # Draw alt text below the loading indicator
            alt_display = self.canvas.create_text(
                x + width/2, y + height/2 + 20,
                text=f"Alt: {alt_text}",
                font=self.fonts['default'],
                fill='#555555',
                tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
            )
            self.canvas_items.append(alt_display)
    
    def _render_link_element(self, layout_box: LayoutBox) -> None:
        """
        Render a link element.
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element:
            return
        
        # Get text content
        text = element.text_content
        if not text:
            return
        
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
        
        # Get computed styles
        styles = layout_box.computed_style
        
        # Use link color
        color = styles.get('color', self.colors['link'])
        
        # Get font
        font = self.fonts['default']
        
        # Create text item with underline
        text_item = self.canvas.create_text(
            x, y,
            text=text,
            font=font,
            fill=color,
            anchor='nw',
            width=layout_box.box_metrics.width,
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(text_item)
        
        # Get text bounds
        bounds = self.canvas.bbox(text_item)
        if bounds:
            # Add underline
            x1, y1, x2, y2 = bounds
            underline = self.canvas.create_line(
                x1, y2, x2, y2,
                fill=color,
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(underline)
    
    def _render_list_element(self, layout_box: LayoutBox) -> None:
        """
        Render a list element (ul, ol, li).
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element:
            return
        
        # For simplicity, we'll only render special markers for li elements
        if element.tag_name.lower() == 'li':
            # Get box dimensions
            x = layout_box.box_metrics.x
            y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
            
            # Determine list style
            parent = element.parent_node
            is_ordered = parent and parent.tag_name.lower() == 'ol'
            
            # Find list index
            index = 1
            if is_ordered:
                index = 1
                for sibling in parent.children:
                    if sibling == element:
                        break
                    if sibling.tag_name.lower() == 'li':
                        index += 1
            
            # Create marker
            marker_text = '•' if not is_ordered else f"{index}."
            marker_item = self.canvas.create_text(
                x - 15, y,
                text=marker_text,
                font=self.fonts['default'],
                fill=self.colors['default_text'],
                anchor='nw',
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(marker_item)
    
    def _render_table_element(self, layout_box: LayoutBox) -> None:
        """
        Render a table element.
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element:
            return
        
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
        width = layout_box.box_metrics.width
        height = layout_box.box_metrics.height
        
        # Get table structure
        rows = self._get_table_rows(element)
        if not rows:
            # Empty table, just draw a border
            table_border = self.canvas.create_rectangle(
                x, y, x + width, y + height,
                outline='#CCCCCC',
                fill='',
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(table_border)
            return
        
        # Calculate cell dimensions
        num_rows = len(rows)
        # Find the maximum number of cells in any row
        num_cols = max(len(row) for row in rows)
        
        if num_cols == 0:
            return
        
        cell_width = width / num_cols
        cell_height = height / num_rows
        
        # Render table border
        table_border = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            outline='#CCCCCC',
            fill='',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(table_border)
        
        # Render cells
        for row_idx, row in enumerate(rows):
            # Calculate row position
            row_y = y + row_idx * cell_height
            
            # Render row
            for col_idx, cell in enumerate(row):
                # Calculate cell position
                cell_x = x + col_idx * cell_width
                
                # Render cell border
                cell_border = self.canvas.create_rectangle(
                    cell_x, row_y, cell_x + cell_width, row_y + cell_height,
                    outline='#CCCCCC',
                    fill='#FFFFFF',
                    tags=f'element:{cell.id}' if hasattr(cell, 'id') and cell.id else ''
                )
                self.canvas_items.append(cell_border)
                
                # Get cell content
                if hasattr(cell, 'text_content') and cell.text_content:
                    # Get alignment from cell or parent row
                    align = cell.get_attribute('align') if hasattr(cell, 'get_attribute') else None
                    if not align and hasattr(cell, 'parent_node') and cell.parent_node:
                        parent_row = cell.parent_node
                        if hasattr(parent_row, 'get_attribute'):
                            align = parent_row.get_attribute('align')
                    
                    # Default alignment
                    if not align:
                        align = 'left'
                    
                    # Set anchor based on alignment
                    if align.lower() == 'center':
                        anchor = 'center'
                        text_x = cell_x + cell_width / 2
                    elif align.lower() == 'right':
                        anchor = 'e'  # East
                        text_x = cell_x + cell_width - 5
                    else:  # left or default
                        anchor = 'w'  # West
                        text_x = cell_x + 5
                    
                    # Render cell text
                    cell_text = self.canvas.create_text(
                        text_x, row_y + cell_height / 2,
                        text=cell.text_content,
                        font=self.fonts['default'],
                        fill='#000000',
                        anchor=anchor,
                        width=cell_width - 10,  # Allow for 5px padding on each side
                        tags=f'element:{cell.id}' if hasattr(cell, 'id') and cell.id else ''
                    )
                    self.canvas_items.append(cell_text)
    
    def _get_table_rows(self, table_element):
        """
        Get table rows and cells from a table element.
        
        Args:
            table_element: The table element
            
        Returns:
            List of rows, where each row is a list of cell elements
        """
        rows = []
        
        if not hasattr(table_element, 'children'):
            return rows
        
        # First try to get rows directly from table
        table_rows = []
        for child in table_element.children:
            if hasattr(child, 'tag_name'):
                if child.tag_name.lower() == 'tr':
                    table_rows.append(child)
                elif child.tag_name.lower() in ('thead', 'tbody', 'tfoot'):
                    # Get rows from section
                    if hasattr(child, 'children'):
                        for section_child in child.children:
                            if hasattr(section_child, 'tag_name') and section_child.tag_name.lower() == 'tr':
                                table_rows.append(section_child)
        
        # Process each row
        for row in table_rows:
            cells = []
            
            # Get cells from row
            if hasattr(row, 'children'):
                for cell_elem in row.children:
                    if hasattr(cell_elem, 'tag_name') and cell_elem.tag_name.lower() in ('td', 'th'):
                        cells.append(cell_elem)
            
            if cells:
                rows.append(cells)
        
        return rows
    
    def _render_form_element(self, layout_box: LayoutBox) -> None:
        """
        Render a form element (input, button, textarea, select).
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element:
            return
        
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
        width = layout_box.box_metrics.width
        height = layout_box.box_metrics.height
        
        # Set minimum dimensions
        min_width = 100
        min_height = 25
        if width < min_width:
            width = min_width
        if height < min_height:
            height = min_height
        
        # Get form element type
        tag_name = element.tag_name.lower()
        input_type = element.get_attribute('type') if tag_name == 'input' else None
        
        # Default form element background and border
        bg_color = '#FFFFFF'
        border_color = '#CCCCCC'
        text_color = '#000000'
        
        # Get value or placeholder
        value = element.get_attribute('value') or ''
        placeholder = element.get_attribute('placeholder') or ''
        display_text = value or placeholder
        
        # Check if disabled
        is_disabled = element.has_attribute('disabled')
        if is_disabled:
            bg_color = '#F0F0F0'
            text_color = '#888888'
        
        # Render based on input type
        if tag_name == 'input':
            if input_type in (None, 'text', 'password', 'email', 'number', 'search', 'tel', 'url'):
                # Text input field
                self._render_text_input(x, y, width, height, display_text, element, 
                                       bg_color, border_color, text_color, input_type == 'password')
            elif input_type == 'checkbox':
                self._render_checkbox(x, y, element, is_disabled)
            elif input_type == 'radio':
                self._render_radio(x, y, element, is_disabled)
            elif input_type == 'range':
                self._render_range(x, y, width, height, element, is_disabled)
            elif input_type == 'button' or input_type == 'submit' or input_type == 'reset':
                self._render_button_element(x, y, width, height, value or input_type.capitalize(), 
                                          element, is_disabled)
            elif input_type == 'color':
                self._render_color_input(x, y, width, height, element, is_disabled)
            else:
                # Fallback for other input types
                self._render_text_input(x, y, width, height, f"[{input_type}]", element, 
                                       bg_color, border_color, text_color)
                
        elif tag_name == 'button':
            # Button element
            button_text = element.text_content or element.get_attribute('value') or 'Button'
            self._render_button_element(x, y, width, height, button_text, element, is_disabled)
            
        elif tag_name == 'textarea':
            # Textarea element
            text = element.text_content or value or placeholder
            self._render_textarea(x, y, width, height, text, element, is_disabled)
            
        elif tag_name == 'select':
            # Select dropdown
            selected_option_text = self._get_selected_option_text(element) or placeholder or 'Select...'
            self._render_select(x, y, width, height, selected_option_text, element, is_disabled)
    
    def _render_text_input(self, x, y, width, height, text, element, bg_color, border_color, text_color, is_password=False):
        """Render a text input field."""
        # Create input field rectangle
        input_rect = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill=bg_color,
            outline=border_color,
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(input_rect)
        
        # Create input text
        display_text = text
        if is_password and text:  # Mask password with asterisks
            display_text = '*' * len(text)
            
        if text:
            text_item = self.canvas.create_text(
                x + 5, y + height/2,  # 5px padding from left, centered vertically
                text=display_text,
                font=self.fonts['default'],
                fill=text_color,
                anchor='w',  # Left-aligned
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(text_item)
    
    def _render_audio_element(self, layout_box: LayoutBox) -> None:
        """
        Render an HTML5 audio element with controls.
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element:
            return
        
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
        width = layout_box.box_metrics.width
        height = layout_box.box_metrics.height
        
        # Set minimum height for the controls
        min_height = 35
        if height < min_height:
            height = min_height
            
        # Create background rectangle for audio control
        rect = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill='#F0F0F0',
            outline='#CCCCCC',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(rect)
        
        # Check if source exists
        has_source = False
        if element.has_children():
            for child in element.children:
                if child.tag_name.lower() == 'source' and child.has_attribute('src'):
                    has_source = True
                    break
                    
        if element.has_attribute('src'):
            has_source = True
        
        # Create play button
        play_button_width = 30
        play_button_x = x + 10
        play_button_y = y + height / 2 - 10
        
        play_button = self.canvas.create_rectangle(
            play_button_x, play_button_y,
            play_button_x + play_button_width, play_button_y + 20,
            fill='#DDDDDD' if has_source else '#AAAAAA',
            outline='#999999',
            tags=f'audio_play:{element.id}' if element.id else 'audio_play'
        )
        self.canvas_items.append(play_button)
        
        # Create play triangle
        play_icon = self.canvas.create_polygon(
            play_button_x + 8, play_button_y + 5,
            play_button_x + 8, play_button_y + 15,
            play_button_x + 22, play_button_y + 10,
            fill='#555555',
            outline='',
            tags=f'audio_play:{element.id}' if element.id else 'audio_play'
        )
        self.canvas_items.append(play_icon)
        
        # Create timeline/progress bar
        progress_x = play_button_x + play_button_width + 10
        progress_y = y + height / 2
        progress_width = width - play_button_width - 30
        
        progress_bg = self.canvas.create_rectangle(
            progress_x, progress_y - 4,
            progress_x + progress_width, progress_y + 4,
            fill='#DDDDDD',
            outline='#AAAAAA',
            tags=f'audio_progress:{element.id}' if element.id else 'audio_progress'
        )
        self.canvas_items.append(progress_bg)
        
        # Audio label - show file name or "No source"
        label_text = "Audio Player"
        if not has_source:
            label_text = "No audio source"
            
        label = self.canvas.create_text(
            progress_x + progress_width / 2, y + 10,
            text=label_text,
            font=self.fonts['default'],
            fill='#555555',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(label)
        
        # Bind events if source is available
        if has_source:
            # Implement the actual audio playback with a media library
            # This would require integration with something like pyglet or pygame
            # For now, we just create the visual elements
            pass
    
    def _render_video_element(self, layout_box: LayoutBox) -> None:
        """
        Render an HTML5 video element with controls.
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element:
            return
        
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
        width = layout_box.box_metrics.width
        height = layout_box.box_metrics.height
        
        # Set minimum dimensions
        min_width = 160
        min_height = 120
        if width < min_width:
            width = min_width
        if height < min_height:
            height = min_height
        
        # Create video viewport (black rectangle)
        viewport = self.canvas.create_rectangle(
            x, y, x + width, y + height - 30,  # Leave space for controls
            fill='#000000',
            outline='#444444',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(viewport)
        
        # Add video poster if specified
        poster_url = element.get_attribute('poster')
        if poster_url:
            # Load the poster image asynchronously
            threading.Thread(
                target=self._load_image_async,
                args=(poster_url, x, y, width, height - 30, element),
                daemon=True
            ).start()
        else:
            # Add video icon in the middle
            icon_size = min(width, height - 30) / 3
            icon_x = x + width / 2
            icon_y = y + (height - 30) / 2
            
            video_icon = self.canvas.create_oval(
                icon_x - icon_size/2, icon_y - icon_size/2,
                icon_x + icon_size/2, icon_y + icon_size/2,
                fill='',
                outline='#AAAAAA',
                width=2,
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(video_icon)
            
            # Add play triangle
            play_size = icon_size * 0.5
            play_icon = self.canvas.create_polygon(
                icon_x - play_size/3, icon_y - play_size/2,
                icon_x - play_size/3, icon_y + play_size/2,
                icon_x + play_size/2, icon_y,
                fill='#AAAAAA',
                outline='',
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(play_icon)
        
        # Create control bar
        control_y = y + height - 30
        control_bg = self.canvas.create_rectangle(
            x, control_y,
            x + width, y + height,
            fill='#222222',
            outline='',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(control_bg)
        
        # Play button
        play_button_width = 30
        play_button_x = x + 10
        play_button_y = control_y + 5
        
        play_button = self.canvas.create_rectangle(
            play_button_x, play_button_y,
            play_button_x + play_button_width, play_button_y + 20,
            fill='#444444',
            outline='#666666',
            tags=f'video_play:{element.id}' if element.id else 'video_play'
        )
        self.canvas_items.append(play_button)
        
        # Create play triangle
        play_icon = self.canvas.create_polygon(
            play_button_x + 8, play_button_y + 5,
            play_button_x + 8, play_button_y + 15,
            play_button_x + 22, play_button_y + 10,
            fill='#DDDDDD',
            outline='',
            tags=f'video_play:{element.id}' if element.id else 'video_play'
        )
        self.canvas_items.append(play_icon)
        
        # Create timeline/progress bar
        progress_x = play_button_x + play_button_width + 10
        progress_y = control_y + 15
        progress_width = width - play_button_width - 30
        
        progress_bg = self.canvas.create_rectangle(
            progress_x, progress_y - 4,
            progress_x + progress_width, progress_y + 4,
            fill='#555555',
            outline='#777777',
            tags=f'video_progress:{element.id}' if element.id else 'video_progress'
        )
        self.canvas_items.append(progress_bg)
        
        # Check for sources but don't actually play the video
        # In a real implementation, would integrate with a video playback library
        has_source = False
        if element.has_attribute('src') or any(
            child.tag_name.lower() == 'source' and child.has_attribute('src')
            for child in element.children if hasattr(element, 'children')
        ):
            has_source = True
            
        # If no source available, show message
        if not has_source:
            no_source_text = self.canvas.create_text(
                x + width / 2, y + (height - 30) / 2,
                text="No video source",
                font=self.fonts['default'],
                fill='#AAAAAA',
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(no_source_text)
    
    def zoom_in(self) -> None:
        """Zoom in by increasing the zoom level."""
        self.zoom_level = min(3.0, self.zoom_level + 0.1)
        self._apply_zoom()
    
    def zoom_out(self) -> None:
        """Zoom out by decreasing the zoom level."""
        self.zoom_level = max(0.3, self.zoom_level - 0.1)
        self._apply_zoom()
    
    def zoom_reset(self) -> None:
        """Reset zoom to 100%."""
        self.zoom_level = 1.0
        self._apply_zoom()
    
    def _apply_zoom(self) -> None:
        """Apply the current zoom level."""
        # Re-render the document with the current zoom
        if self.document:
            self.render(self.document)
    
    def set_link_click_handler(self, handler: Callable[[str], None]) -> None:
        """
        Set a handler for link click events.
        
        Args:
            handler: Function to call when a link is clicked
        """
        self.on_link_click = handler
    
    def _render_checkbox(self, x, y, element, is_disabled):
        """Render a checkbox input."""
        box_size = 16
        checked = element.has_attribute('checked')
        
        # Create checkbox box
        box_color = '#F0F0F0' if is_disabled else '#FFFFFF'
        box = self.canvas.create_rectangle(
            x, y, x + box_size, y + box_size,
            fill=box_color,
            outline='#AAAAAA',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(box)
        
        # If checked, create checkmark
        if checked:
            check_color = '#888888' if is_disabled else '#444444'
            checkmark = self.canvas.create_line(
                x + 3, y + 8, x + 6, y + 12, x + 13, y + 4,
                fill=check_color,
                width=2,
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(checkmark)
    
    def _render_radio(self, x, y, element, is_disabled):
        """Render a radio button input."""
        radius = 8
        checked = element.has_attribute('checked')
        
        # Create radio button circle
        circle_color = '#F0F0F0' if is_disabled else '#FFFFFF'
        outer_circle = self.canvas.create_oval(
            x, y, x + 2*radius, y + 2*radius,
            fill=circle_color,
            outline='#AAAAAA',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(outer_circle)
        
        # If checked, create inner dot
        if checked:
            dot_color = '#888888' if is_disabled else '#444444'
            inner_circle = self.canvas.create_oval(
                x + 4, y + 4, x + 2*radius - 4, y + 2*radius - 4,
                fill=dot_color,
                outline='',
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(inner_circle)
    
    def _render_button_element(self, x, y, width, height, text, element, is_disabled):
        """Render a button."""
        # Create button rectangle
        button_color = '#F0F0F0' if is_disabled else '#EEEEEE'
        border_color = '#CCCCCC' if is_disabled else '#AAAAAA'
        text_color = '#888888' if is_disabled else '#333333'
        
        # Create button with 3D effect
        button = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill=button_color,
            outline=border_color,
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(button)
        
        # Add 3D effect
        highlight = self.canvas.create_line(
            x, y, x + width, y,  # Top
            x, y, x, y + height,  # Left
            fill='#FFFFFF',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(highlight)
        
        shadow = self.canvas.create_line(
            x, y + height, x + width, y + height,  # Bottom
            x + width, y, x + width, y + height,  # Right
            fill='#999999',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(shadow)
        
        # Button text
        if text:
            text_item = self.canvas.create_text(
                x + width/2, y + height/2,
                text=text,
                font=self.fonts['default'],
                fill=text_color,
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(text_item)
    
    def _render_range(self, x, y, width, height, element, is_disabled):
        """Render a range input (slider)."""
        # Get attributes
        min_val = float(element.get_attribute('min') or 0)
        max_val = float(element.get_attribute('max') or 100)
        value = float(element.get_attribute('value') or min_val)
        
        # Normalize value to 0-1 range
        range_size = max_val - min_val
        if range_size <= 0:
            range_size = 100
        normalized_value = (value - min_val) / range_size
        if normalized_value < 0:
            normalized_value = 0
        if normalized_value > 1:
            normalized_value = 1
        
        # Calculate thumb position
        track_height = 6
        y_center = y + height/2
        thumb_x = x + normalized_value * width
        
        # Draw track
        track_color = '#DDDDDD' if is_disabled else '#CCCCCC'
        track = self.canvas.create_rectangle(
            x, y_center - track_height/2, x + width, y_center + track_height/2,
            fill=track_color,
            outline='',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(track)
        
        # Draw filled part of track
        filled_color = '#BBBBBB' if is_disabled else '#888888'
        filled_track = self.canvas.create_rectangle(
            x, y_center - track_height/2, thumb_x, y_center + track_height/2,
            fill=filled_color,
            outline='',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(filled_track)
        
        # Draw thumb
        thumb_radius = 8
        thumb_color = '#DDDDDD' if is_disabled else '#FFFFFF'
        thumb_border = '#BBBBBB' if is_disabled else '#999999'
        thumb = self.canvas.create_oval(
            thumb_x - thumb_radius, y_center - thumb_radius,
            thumb_x + thumb_radius, y_center + thumb_radius,
            fill=thumb_color,
            outline=thumb_border,
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(thumb)
    
    def _render_textarea(self, x, y, width, height, text, element, is_disabled):
        """Render a textarea element."""
        # Create textarea rectangle
        bg_color = '#F0F0F0' if is_disabled else '#FFFFFF'
        text_color = '#888888' if is_disabled else '#000000'
        
        textarea = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill=bg_color,
            outline='#CCCCCC',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(textarea)
        
        # Create textarea text - with line wrapping
        if text:
            # Split text into lines that fit within the width
            lines = []
            current_line = ""
            wrap_width = width - 10  # 5px padding on each side
            
            # Process each word
            for word in text.split():
                # Create a test line with the word added
                test_line = current_line + " " + word if current_line else word
                
                # Measure the test line
                test_item = self.canvas.create_text(
                    0, 0, text=test_line, font=self.fonts['default']
                )
                bbox = self.canvas.bbox(test_item)
                line_width = bbox[2] - bbox[0]
                self.canvas.delete(test_item)
                
                # Check if we need to wrap
                if line_width <= wrap_width:
                    current_line = test_line
                else:
                    # Add the current line to our list and start a new line
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            # Add the last line
            if current_line:
                lines.append(current_line)
            
            # Render each line
            line_height = 18  # Approximate line height
            max_visible_lines = int(height / line_height) - 1
            
            # Limit the number of lines to display
            visible_lines = lines[:max_visible_lines]
            
            # Render each visible line
            for i, line in enumerate(visible_lines):
                line_y = y + 5 + i * line_height
                text_item = self.canvas.create_text(
                    x + 5, line_y,
                    text=line,
                    font=self.fonts['default'],
                    fill=text_color,
                    anchor='nw',
                    tags=f'element:{element.id}' if element.id else ''
                )
                self.canvas_items.append(text_item)
            
            # If there are more lines than can be displayed, show an ellipsis
            if len(lines) > max_visible_lines:
                ellipsis = self.canvas.create_text(
                    x + width - 10, y + height - 10,
                    text="...",
                    font=self.fonts['default'],
                    fill='#999999',
                    anchor='se',
                    tags=f'element:{element.id}' if element.id else ''
                )
                self.canvas_items.append(ellipsis)
    
    def _render_select(self, x, y, width, height, selected_text, element, is_disabled):
        """Render a select dropdown."""
        # Create select rectangle
        bg_color = '#F0F0F0' if is_disabled else '#FFFFFF'
        text_color = '#888888' if is_disabled else '#000000'
        
        select = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill=bg_color,
            outline='#CCCCCC',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(select)
        
        # Create dropdown arrow
        arrow_size = 8
        arrow_x = x + width - 20
        arrow_y = y + (height - arrow_size) / 2
        
        arrow = self.canvas.create_polygon(
            arrow_x, arrow_y,
            arrow_x + arrow_size, arrow_y,
            arrow_x + arrow_size/2, arrow_y + arrow_size,
            fill='#999999',
            outline='',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(arrow)
        
        # Create selected text
        if selected_text:
            text_item = self.canvas.create_text(
                x + 5, y + height/2,
                text=selected_text,
                font=self.fonts['default'],
                fill=text_color,
                anchor='w',
                tags=f'element:{element.id}' if element.id else ''
            )
            self.canvas_items.append(text_item)
    
    def _render_color_input(self, x, y, width, height, element, is_disabled):
        """Render a color input."""
        # Get the color value
        color_value = element.get_attribute('value') or '#000000'
        
        # Create color input rectangle
        color_rect = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill='#FFFFFF',
            outline='#CCCCCC',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(color_rect)
        
        # Create color preview
        preview_size = height - 6
        preview_x = x + 3
        preview_y = y + 3
        
        preview = self.canvas.create_rectangle(
            preview_x, preview_y,
            preview_x + preview_size, preview_y + preview_size,
            fill=color_value,
            outline='#AAAAAA',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(preview)
        
        # Create color text
        text_item = self.canvas.create_text(
            preview_x + preview_size + 5, y + height/2,
            text=color_value,
            font=self.fonts['default'],
            fill='#333333',
            anchor='w',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(text_item)
    
    def _get_selected_option_text(self, select_element):
        """Get the text of the selected option in a select element."""
        # Find all option elements
        options = []
        if hasattr(select_element, 'children'):
            for child in select_element.children:
                if hasattr(child, 'tag_name') and child.tag_name.lower() == 'option':
                    options.append(child)
        
        # Find the selected option
        selected_option = None
        for option in options:
            if option.has_attribute('selected'):
                selected_option = option
                break
        
        # If no option is selected, use the first one
        if not selected_option and options:
            selected_option = options[0]
        
        # Get the text of the selected option
        if selected_option:
            if hasattr(selected_option, 'text_content') and selected_option.text_content:
                return selected_option.text_content
            return selected_option.get_attribute('value')
        
        return ""
    
    def _render_media_element(self, layout_box: LayoutBox) -> None:
        """
        Render an audio or video element.
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element or not hasattr(element, 'tag_name'):
            return
            
        # Determine if it's audio or video
        is_video = element.tag_name.lower() == 'video'
        is_audio = element.tag_name.lower() == 'audio'
        
        if not is_video and not is_audio:
            return
            
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
        width = layout_box.box_metrics.width
        height = layout_box.box_metrics.height
        
        # Get media source
        src = element.get_attribute('src') if hasattr(element, 'get_attribute') else None
        
        # Check for source child elements if no src attribute
        if not src and hasattr(element, 'children'):
            for child in element.children:
                if hasattr(child, 'tag_name') and child.tag_name.lower() == 'source':
                    if hasattr(child, 'get_attribute'):
                        src = child.get_attribute('src')
                        if src:
                            break
        
        # Get controls attribute
        controls = element.get_attribute('controls') if hasattr(element, 'get_attribute') else None
        has_controls = controls is not None
        
        # Render appropriate media element
        if is_video:
            self._render_video_element(x, y, width, height, src, has_controls, element)
        else:  # is_audio
            self._render_audio_element(x, y, width, height, src, has_controls, element)
    
    def _render_video_element(self, x, y, width, height, src, has_controls, element):
        """
        Render a video element.
        
        Args:
            x, y: Position coordinates
            width, height: Dimensions
            src: Source URL
            has_controls: Whether to show controls
            element: The video element
        """
        # Draw video container
        video_container = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            outline='#555555',
            fill='#000000',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(video_container)
        
        # Draw play icon in center
        play_icon = self.canvas.create_text(
            x + width/2, y + height/2 - 10,
            text="▶️",  # Play icon
            font=(self.fonts['default'][0], 24),
            fill='#FFFFFF',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(play_icon)
        
        # Show source name if available
        if src:
            source_text = self.canvas.create_text(
                x + width/2, y + height/2 + 20,
                text=f"Source: {src[:30]}..." if len(src) > 30 else f"Source: {src}",
                font=self.fonts['default'],
                fill='#CCCCCC',
                tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
            )
            self.canvas_items.append(source_text)
        else:
            no_source = self.canvas.create_text(
                x + width/2, y + height/2 + 20,
                text="No video source",
                font=self.fonts['default'],
                fill='#CCCCCC',
                tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
            )
            self.canvas_items.append(no_source)
        
        # Draw controls if enabled
        if has_controls:
            self._render_media_controls(x, y, width, height, element, is_video=True)
    
    def _render_audio_element(self, x, y, width, height, src, has_controls, element):
        """
        Render an audio element.
        
        Args:
            x, y: Position coordinates
            width, height: Dimensions
            src: Source URL
            has_controls: Whether to show controls
            element: The audio element
        """
        # Adjust height if no controls - audio without controls is invisible
        if not has_controls:
            # Make a minimal height element
            height = 0
            return
        
        # Draw audio container
        audio_container = self.canvas.create_rectangle(
            x, y, x + width, y + 40,  # Audio controls are typically smaller than video
            outline='#CCCCCC',
            fill='#F0F0F0',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(audio_container)
        
        # Draw speaker icon
        speaker_icon = self.canvas.create_text(
            x + 20, y + 20,
            text="🔊",  # Speaker icon
            font=self.fonts['default'],
            fill='#333333',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(speaker_icon)
        
        # Show source name if available
        if src:
            source_text = self.canvas.create_text(
                x + width/2, y + 20,
                text=f"Audio: {src[:20]}..." if len(src) > 20 else f"Audio: {src}",
                font=self.fonts['default'],
                fill='#333333',
                tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
            )
            self.canvas_items.append(source_text)
        else:
            no_source = self.canvas.create_text(
                x + width/2, y + 20,
                text="No audio source",
                font=self.fonts['default'],
                fill='#333333',
                tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
            )
            self.canvas_items.append(no_source)
        
        # Draw controls
        self._render_media_controls(x, y, width, 40, element, is_video=False)
    
    def _render_media_controls(self, x, y, width, height, element, is_video=True):
        """
        Render media controls (play button, progress bar, etc.)
        
        Args:
            x, y: Position coordinates
            width, height: Dimensions
            element: The media element
            is_video: Whether this is a video element (vs audio)
        """
        # Draw controls background at the bottom of the container
        controls_height = 30
        controls_y = y + height - controls_height if is_video else y + 10
        
        controls_bg = self.canvas.create_rectangle(
            x, controls_y, x + width, controls_y + controls_height,
            outline='',
            fill='#333333' if is_video else '#DDDDDD',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(controls_bg)
        
        # Draw play button
        play_btn_x = x + 15
        play_btn_y = controls_y + controls_height/2
        play_btn = self.canvas.create_text(
            play_btn_x, play_btn_y,
            text="▶️",
            font=self.fonts['default'],
            fill='#FFFFFF' if is_video else '#333333',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(play_btn)
        
        # Draw volume button
        volume_btn_x = x + width - 15
        volume_btn_y = controls_y + controls_height/2
        volume_btn = self.canvas.create_text(
            volume_btn_x, volume_btn_y,
            text="🔊",
            font=self.fonts['default'],
            fill='#FFFFFF' if is_video else '#333333',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(volume_btn)
        
        # Draw progress bar
        progress_bar_padding = 50  # Space for buttons on each side
        progress_bar_x = x + progress_bar_padding
        progress_bar_width = width - (2 * progress_bar_padding)
        progress_bar_y = controls_y + controls_height/2
        
        # Background track
        progress_bg = self.canvas.create_rectangle(
            progress_bar_x, progress_bar_y - 3,
            progress_bar_x + progress_bar_width, progress_bar_y + 3,
            outline='',
            fill='#555555' if is_video else '#AAAAAA',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(progress_bg)
        
        # Progress indicator (30% complete for demonstration)
        progress_width = progress_bar_width * 0.3
        progress = self.canvas.create_rectangle(
            progress_bar_x, progress_bar_y - 3,
            progress_bar_x + progress_width, progress_bar_y + 3,
            outline='',
            fill='#FF0000' if is_video else '#0066CC',  # Red for video, blue for audio
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(progress)
        
        # Progress handle
        handle = self.canvas.create_oval(
            progress_bar_x + progress_width - 5, progress_bar_y - 6,
            progress_bar_x + progress_width + 5, progress_bar_y + 6,
            outline='',
            fill='#FFFFFF',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(handle)
    
    def _render_default_element_box(self, layout_box: LayoutBox) -> None:
        """
        Render a default element box to the canvas.
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element:
            return

        # Get box dimensions
        x = layout_box.box_metrics.x
        y = layout_box.box_metrics.y
        width = layout_box.box_metrics.border_box_width
        height = layout_box.box_metrics.border_box_height
        
        # Get computed styles
        styles = layout_box.computed_style
        
        # Render background (if specified)
        self._render_background(layout_box, x, y, width, height, styles)
        
        # Render border (if specified)
        self._render_border(layout_box, x, y, width, height, styles)
        
        # Render text content
        if hasattr(element, 'text_content') and element.text_content:
            self._render_text_content(layout_box)
    
    def _render_background(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int, styles: Dict[str, str]) -> None:
        """
        Render element background.
        
        Args:
            layout_box: The layout box to render
            x: The x coordinate
            y: The y coordinate
            width: The width of the element
            height: The height of the element
            styles: The computed styles
        """
        element = layout_box.element
        if not element:
            return
        
        # Check for background-color
        background_color = styles.get('background-color')
        if background_color:
            bg_item = self.canvas.create_rectangle(
                x, y, x + width, y + height,
                fill=background_color,
                outline='',
                tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
            )
            self.canvas_items.append(bg_item)
        
        # Check for background-image
        background_image = styles.get('background-image')
        if background_image:
            self._render_background_image(layout_box, x, y, width, height, background_image)
    
    def _render_background_image(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int, background_image: str) -> None:
        """
        Render a background image.
        
        Args:
            layout_box: The layout box to render
            x: The x coordinate
            y: The y coordinate
            width: The width of the element
            height: The height of the element
            background_image: The background-image value
        """
        element = layout_box.element
        if not element:
            return
        
        # Get styles
        styles = layout_box.computed_style
        background_repeat = styles.get('background-repeat', 'repeat')
        background_position = styles.get('background-position', '0% 0%')
        background_size = styles.get('background-size', 'auto')
        
        # Check if it's a URL
        if background_image.startswith('url('):
            # Extract the URL
            url_match = re.match(r'url\(\s*[\'"]?(.*?)[\'"]?\s*\)', background_image)
            if url_match:
                image_url = url_match.group(1)
                self._render_background_url_image(layout_box, x, y, width, height, image_url, background_repeat, background_position, background_size)
        
        # Check if it's a linear gradient
        elif background_image.startswith('linear-gradient('):
            self._render_background_linear_gradient(layout_box, x, y, width, height, background_image)
        
        # Check if it's a radial gradient
        elif background_image.startswith('radial-gradient('):
            self._render_background_radial_gradient(layout_box, x, y, width, height, background_image)
    
    def _render_background_url_image(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int, 
                                    image_url: str, repeat: str, position: str, size: str) -> None:
        """
        Render a background image from a URL.
        
        Args:
            layout_box: The layout box to render
            x: The x coordinate
            y: The y coordinate
            width: The width of the element
            height: The height of the element
            image_url: The image URL
            repeat: The background-repeat value
            position: The background-position value
            size: The background-size value
        """
        element = layout_box.element
        if not element:
            return
        
        # For now, just render a placeholder
        # In a full implementation, we would load and render the actual image
        
        # Draw a placeholder with an image icon
        placeholder = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            outline='',
            fill='#F9F9F9',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(placeholder)
        
        # Add a small image icon in the corner
        icon_text = self.canvas.create_text(
            x + 10, y + 10,
            text="🖼️",  # Image icon
            font=self.fonts['default'],
            fill='#AAAAAA',
            anchor='nw',
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        self.canvas_items.append(icon_text)
    
    def _render_background_linear_gradient(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int, gradient_str: str) -> None:
        """
        Render a linear gradient background.
        
        Args:
            layout_box: The layout box to render
            x: The x coordinate
            y: The y coordinate
            width: The width of the element
            height: The height of the element
            gradient_str: The linear-gradient value
        """
        element = layout_box.element
        if not element:
            return
        
        # Simplified gradient rendering for demonstration
        # In a full implementation, we would parse the gradient and render it properly
        
        # Extract gradient parameters
        gradient_match = re.match(r'linear-gradient\(\s*(.*?)\s*\)', gradient_str)
        if not gradient_match:
            return
        
        gradient_params = gradient_match.group(1)
        
        # Split parameters by comma, handling nested commas in functions
        parts = []
        current_part = ""
        nested_level = 0
        
        for char in gradient_params:
            if char == ',' and nested_level == 0:
                parts.append(current_part.strip())
                current_part = ""
            else:
                current_part += char
                if char == '(':
                    nested_level += 1
                elif char == ')':
                    nested_level -= 1
        
        if current_part:
            parts.append(current_part.strip())
        
        # Check if we have at least two parts (direction/angle and at least one color stop)
        if len(parts) < 2:
            return
        
        # The first part might be an angle or direction
        angle = parts[0]
        
        # Default angle
        angle_degrees = 180  # top to bottom
        
        # Parse angle
        if angle.endswith('deg'):
            try:
                angle_degrees = int(angle[:-3])
            except ValueError:
                pass
        elif angle == 'to top':
            angle_degrees = 0
        elif angle == 'to right':
            angle_degrees = 90
        elif angle == 'to bottom':
            angle_degrees = 180
        elif angle == 'to left':
            angle_degrees = 270
        elif angle == 'to top right' or angle == 'to right top':
            angle_degrees = 45
        elif angle == 'to bottom right' or angle == 'to right bottom':
            angle_degrees = 135
        elif angle == 'to bottom left' or angle == 'to left bottom':
            angle_degrees = 225
        elif angle == 'to top left' or angle == 'to left top':
            angle_degrees = 315
        
        # Extract color stops
        color_stops = parts[1:]
        
        # For a simple implementation, just use the first and last color stops
        start_color = color_stops[0]
        end_color = color_stops[-1]
        
        # Remove percentage parts from colors if present
        start_color = start_color.split(' ')[0]
        end_color = end_color.split(' ')[0]
        
        # Create a simplified gradient
        if angle_degrees in (0, 180):  # Vertical gradient
            # Create multiple rectangles to simulate the gradient
            segments = 10
            segment_height = height / segments
            
            for i in range(segments):
                # Calculate interpolated color
                t = i / (segments - 1)
                color = self._interpolate_color(start_color, end_color, t if angle_degrees == 0 else 1 - t)
                
                # Create rectangle segment
                segment = self.canvas.create_rectangle(
                    x, y + i * segment_height, 
                    x + width, y + (i + 1) * segment_height,
                    outline='',
                    fill=color,
                    tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
                )
                self.canvas_items.append(segment)
        
        elif angle_degrees in (90, 270):  # Horizontal gradient
            # Create multiple rectangles to simulate the gradient
            segments = 10
            segment_width = width / segments
            
            for i in range(segments):
                # Calculate interpolated color
                t = i / (segments - 1)
                color = self._interpolate_color(start_color, end_color, t if angle_degrees == 90 else 1 - t)
                
                # Create rectangle segment
                segment = self.canvas.create_rectangle(
                    x + i * segment_width, y, 
                    x + (i + 1) * segment_width, y + height,
                    outline='',
                    fill=color,
                    tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
                )
                self.canvas_items.append(segment)
        
        else:  # Diagonal or other angles - simplify to vertical
            # Create multiple rectangles to simulate the gradient
            segments = 10
            segment_height = height / segments
            
            for i in range(segments):
                # Calculate interpolated color
                t = i / (segments - 1)
                color = self._interpolate_color(start_color, end_color, t)
                
                # Create rectangle segment
                segment = self.canvas.create_rectangle(
                    x, y + i * segment_height, 
                    x + width, y + (i + 1) * segment_height,
                    outline='',
                    fill=color,
                    tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
                )
                self.canvas_items.append(segment)
    
    def _render_background_radial_gradient(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int, gradient_str: str) -> None:
        """
        Render a radial gradient background.
        
        Args:
            layout_box: The layout box to render
            x: The x coordinate
            y: The y coordinate
            width: The width of the element
            height: The height of the element
            gradient_str: The radial-gradient value
        """
        element = layout_box.element
        if not element:
            return
        
        # Simplified radial gradient rendering
        # In a full implementation, we would parse the gradient and render it properly
        
        # Extract gradient parameters
        gradient_match = re.match(r'radial-gradient\(\s*(.*?)\s*\)', gradient_str)
        if not gradient_match:
            return
        
        gradient_params = gradient_match.group(1)
        
        # Split parameters by comma, handling nested commas in functions
        parts = []
        current_part = ""
        nested_level = 0
        
        for char in gradient_params:
            if char == ',' and nested_level == 0:
                parts.append(current_part.strip())
                current_part = ""
            else:
                current_part += char
                if char == '(':
                    nested_level += 1
                elif char == ')':
                    nested_level -= 1
        
        if current_part:
            parts.append(current_part.strip())
        
        # Check if we have at least one color stop
        if not parts:
            return
        
        # Extract color stops
        color_stops = parts
        
        # Check for shape and position in the first part
        first_part = parts[0].lower()
        if 'at ' in first_part or 'circle' in first_part or 'ellipse' in first_part:
            # First part contains shape/position, skip it for color stops
            color_stops = parts[1:]
        
        if not color_stops:
            return
        
        # For a simple implementation, just use the first and last color stops
        start_color = color_stops[0]
        end_color = color_stops[-1]
        
        # Remove percentage parts from colors if present
        start_color = start_color.split(' ')[0]
        end_color = end_color.split(' ')[0]
        
        # Create a simplified radial gradient using concentric ovals
        center_x = x + width / 2
        center_y = y + height / 2
        max_radius = min(width, height) / 2
        
        # Number of rings to draw
        rings = 8
        
        for i in range(rings):
            # Calculate interpolated color
            t = i / (rings - 1)
            color = self._interpolate_color(start_color, end_color, 1 - t)  # Inner to outer
            
            # Calculate radius for this ring
            radius = max_radius * (i / (rings - 1))
            
            # Create oval
            oval = self.canvas.create_oval(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                outline='',
                fill=color,
                tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
            )
            self.canvas_items.append(oval)
    
    def _interpolate_color(self, color1: str, color2: str, t: float) -> str:
        """
        Interpolate between two colors.
        
        Args:
            color1: The first color
            color2: The second color
            t: Interpolation factor (0-1)
            
        Returns:
            Interpolated color in hex format
        """
        # Parse colors to RGB
        rgb1 = self._parse_color_to_rgb(color1)
        rgb2 = self._parse_color_to_rgb(color2)
        
        if not rgb1 or not rgb2:
            return "#000000"  # Default to black if parsing fails
        
        # Interpolate each component
        r = int(rgb1[0] + t * (rgb2[0] - rgb1[0]))
        g = int(rgb1[1] + t * (rgb2[1] - rgb1[1]))
        b = int(rgb1[2] + t * (rgb2[2] - rgb1[2]))
        
        # Clamp to valid range
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _parse_color_to_rgb(self, color: str) -> Optional[Tuple[int, int, int]]:
        """
        Parse a CSS color to RGB components.
        
        Args:
            color: The CSS color string
            
        Returns:
            Tuple of (r, g, b) or None if parsing fails
        """
        # Handle hex colors
        if color.startswith('#'):
            if len(color) == 4:  # Short form #RGB
                r = int(color[1] + color[1], 16)
                g = int(color[2] + color[2], 16)
                b = int(color[3] + color[3], 16)
                return (r, g, b)
            elif len(color) == 7:  # Standard form #RRGGBB
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                return (r, g, b)
        
        # Handle rgb() format
        rgb_match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color)
        if rgb_match:
            r = int(rgb_match.group(1))
            g = int(rgb_match.group(2))
            b = int(rgb_match.group(3))
            return (r, g, b)
        
        # Handle rgba() format (ignore alpha)
        rgba_match = re.match(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[\d.]+\s*\)', color)
        if rgba_match:
            r = int(rgba_match.group(1))
            g = int(rgba_match.group(2))
            b = int(rgba_match.group(3))
            return (r, g, b)
        
        # Handle named colors
        named_colors = {
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'red': (255, 0, 0),
            'green': (0, 128, 0),
            'blue': (0, 0, 255),
            'yellow': (255, 255, 0),
            'purple': (128, 0, 128),
            'grey': (128, 128, 128),
            'gray': (128, 128, 128),
            'orange': (255, 165, 0),
            # Add more named colors as needed
        }
        
        if color.lower() in named_colors:
            return named_colors[color.lower()]
        
        # Return black as fallback
        return (0, 0, 0)
        
    def _render_border(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int, styles: Dict[str, str]) -> None:
        """
        Render element borders.
        
        Args:
            layout_box: The layout box to render
            x: The x coordinate
            y: The y coordinate
            width: The width of the element
            height: The height of the element
            styles: The computed styles
        """
        element = layout_box.element
        if not element:
            return
            
        # Check if any border is specified
        if (layout_box.box_metrics.border_top_width > 0 or
            layout_box.box_metrics.border_right_width > 0 or
            layout_box.box_metrics.border_bottom_width > 0 or
            layout_box.box_metrics.border_left_width > 0):
            
            # Get border colors
            border_color = styles.get('border-color', '#000000')
            border_top_color = styles.get('border-top-color', border_color)
            border_right_color = styles.get('border-right-color', border_color)
            border_bottom_color = styles.get('border-bottom-color', border_color)
            border_left_color = styles.get('border-left-color', border_color)
            
            # Draw borders
            if layout_box.box_metrics.border_top_width > 0:
                top_border = self.canvas.create_line(
                    x, y, x + width, y,
                    width=layout_box.box_metrics.border_top_width,
                    fill=border_top_color,
                    tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
                )
                self.canvas_items.append(top_border)
            
            if layout_box.box_metrics.border_right_width > 0:
                right_border = self.canvas.create_line(
                    x + width, y, x + width, y + height,
                    width=layout_box.box_metrics.border_right_width,
                    fill=border_right_color,
                    tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
                )
                self.canvas_items.append(right_border)
            
            if layout_box.box_metrics.border_bottom_width > 0:
                bottom_border = self.canvas.create_line(
                    x, y + height, x + width, y + height,
                    width=layout_box.box_metrics.border_bottom_width,
                    fill=border_bottom_color,
                    tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
                )
                self.canvas_items.append(bottom_border)
            
            if layout_box.box_metrics.border_left_width > 0:
                left_border = self.canvas.create_line(
                    x, y, x, y + height,
                    width=layout_box.box_metrics.border_left_width,
                    fill=border_left_color,
                    tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
                )
                self.canvas_items.append(left_border) 
    
    def _get_font_for_element(self, layout_box: LayoutBox) -> tuple:
        """
        Get the font to use for rendering an element.
        
        Args:
            layout_box: The layout box containing style information
            
        Returns:
            Font tuple (family, size, [style, [style, ...]])
        """
        styles = layout_box.computed_style
        
        # Default font
        font_family = 'Arial'
        font_size = 12
        font_styles = []
        
        # Process font-family
        if 'font-family' in styles:
            families = styles['font-family'].split(',')
            for family in families:
                family = family.strip().strip('"\'').lower()
                # Try to match to available fonts
                if family in ['serif', 'times', 'times new roman']:
                    font_family = 'Times New Roman'
                    break
                elif family in ['sans-serif', 'arial', 'helvetica']:
                    font_family = 'Arial'
                    break
                elif family in ['monospace', 'courier', 'courier new']:
                    font_family = 'Courier New'
                    break
                elif family in ['cursive', 'comic sans', 'comic sans ms']:
                    font_family = 'Comic Sans MS'
                    break
                elif family in ['fantasy', 'impact']:
                    font_family = 'Impact'
                    break
                # Could add more font mappings here
                # For now, just use the first specified font or fallback to Arial
                elif family:
                    font_family = family.title()  # Convert to title case for Tkinter
                    break
        
        # Process font-size
        if 'font-size' in styles:
            size_value = styles['font-size']
            # Handle absolute sizes
            if size_value in ['xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large']:
                size_map = {
                    'xx-small': 8,
                    'x-small': 10,
                    'small': 12,
                    'medium': 14,
                    'large': 16,
                    'x-large': 20,
                    'xx-large': 24
                }
                font_size = size_map.get(size_value, 12)
            else:
                # Try to parse as a numeric value
                try:
                    # Remove 'px', 'pt', etc. and convert to int
                    size = size_value.rstrip('px').rstrip('pt').rstrip('em').rstrip('rem').strip()
                    font_size = int(float(size))
                except (ValueError, AttributeError):
                    # Fallback to default size
                    font_size = 12
        
        # Process font-weight
        if 'font-weight' in styles:
            weight = styles['font-weight'].lower()
            if weight in ['bold', 'bolder', '700', '800', '900']:
                font_styles.append('bold')
        
        # Process font-style
        if 'font-style' in styles:
            style = styles['font-style'].lower()
            if style == 'italic':
                font_styles.append('italic')
        
        # Process text-decoration
        if 'text-decoration' in styles:
            decoration = styles['text-decoration'].lower()
            if 'underline' in decoration:
                font_styles.append('underline')
            if 'line-through' in decoration:
                font_styles.append('overstrike')
        
        # Special case for <strong>, <b>, <em>, <i>, <u>, <s> elements
        if layout_box.element and hasattr(layout_box.element, 'tag_name'):
            tag = layout_box.element.tag_name.lower()
            if tag in ['strong', 'b']:
                if 'bold' not in font_styles:
                    font_styles.append('bold')
            elif tag in ['em', 'i']:
                if 'italic' not in font_styles:
                    font_styles.append('italic')
            elif tag == 'u':
                if 'underline' not in font_styles:
                    font_styles.append('underline')
            elif tag in ['s', 'strike', 'del']:
                if 'overstrike' not in font_styles:
                    font_styles.append('overstrike')
        
        # Construct the font tuple
        font_tuple = (font_family, font_size)
        if font_styles:
            font_tuple += tuple(font_styles)
        
        return font_tuple
    
    def _render_text_content(self, layout_box: LayoutBox) -> None:
        """
        Render text content for an element.
        
        Args:
            layout_box: The layout box to render text for
        """
        element = layout_box.element
        if not element or not hasattr(element, 'text_content') or not element.text_content:
            return
        
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left + layout_box.box_metrics.border_left_width
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top + layout_box.box_metrics.border_top_width
        width = layout_box.box_metrics.content_width
        
        # Get styles
        styles = layout_box.computed_style
        
        # Get font
        font = self._get_font_for_element(layout_box)
        
        # Get text color
        text_color = styles.get('color', '#000000')
        
        # Get text alignment
        text_align = styles.get('text-align', 'left')
        
        # Align text horizontally
        if text_align == 'center':
            anchor = 'n'  # north (top center)
            x += width / 2
        elif text_align == 'right':
            anchor = 'ne'  # northeast (top right)
            x += width
        else:  # left or justify (we don't support true justification yet)
            anchor = 'nw'  # northwest (top left)
        
        # Create text item
        text_item = self.canvas.create_text(
            x, y,
            text=element.text_content,
            font=font,
            fill=text_color,
            anchor=anchor,
            width=width if width != 'auto' else None,  # Wrap text if width is specified
            tags=f'element:{element.id}' if hasattr(element, 'id') and element.id else ''
        )
        
        self.canvas_items.append(text_item)