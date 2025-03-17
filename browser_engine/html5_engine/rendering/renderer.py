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
        """Initialize fonts for rendering."""
        self.fonts = {
            'default': ('Helvetica', 12),
            'default_bold': ('Helvetica', 12, 'bold'),
            'default_italic': ('Helvetica', 12, 'italic'),
            'default_bold_italic': ('Helvetica', 12, 'bold italic'),
            'monospace': ('Courier', 12),
            'monospace_bold': ('Courier', 12, 'bold'),
            'monospace_italic': ('Courier', 12, 'italic'),
            'monospace_bold_italic': ('Courier', 12, 'bold italic'),
            'h1': ('Helvetica', 24, 'bold'),
            'h2': ('Helvetica', 20, 'bold'),
            'h3': ('Helvetica', 16, 'bold'),
            'h4': ('Helvetica', 14, 'bold'),
            'h5': ('Helvetica', 12, 'bold'),
            'h6': ('Helvetica', 10, 'bold'),
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
            logger.warning("Cannot render element box: element is None")
            return
        
        logger.debug(f"Rendering element box for {element.tag_name}")
        
        # Get box dimensions
        x = layout_box.box_metrics.x
        y = layout_box.box_metrics.y
        width = layout_box.box_metrics.border_box_width
        height = layout_box.box_metrics.border_box_height
        
        logger.debug(f"Box dimensions: x={x}, y={y}, width={width}, height={height}")
        
        # Get computed styles
        styles = layout_box.computed_style
        logger.debug(f"Computed styles: {styles}")
        
        # Render background (if specified)
        background_color = styles.get('background-color')
        if background_color:
            logger.debug(f"Rendering background with color: {background_color}")
            bg_item = self.canvas.create_rectangle(
                x, y, x + width, y + height,
                fill=background_color,
                outline='',
                tags=f'element:{element.id}' if element.id else ''
            )
            logger.debug(f"Created background item with ID: {bg_item}")
            self.canvas_items.append(bg_item)
        else:
            logger.debug("No background color specified")
        
        # Render border (if specified)
        if (layout_box.box_metrics.border_top_width > 0 or
            layout_box.box_metrics.border_right_width > 0 or
            layout_box.box_metrics.border_bottom_width > 0 or
            layout_box.box_metrics.border_left_width > 0):
            
            border_color = styles.get('border-color', self.colors['border'])
            
            # Simplified border rendering (in a full implementation, would handle border styles)
            if layout_box.box_metrics.border_top_width > 0:
                top_border = self.canvas.create_line(
                    x, y, x + width, y,
                    width=layout_box.box_metrics.border_top_width,
                    fill=border_color
                )
                self.canvas_items.append(top_border)
            
            if layout_box.box_metrics.border_right_width > 0:
                right_border = self.canvas.create_line(
                    x + width, y, x + width, y + height,
                    width=layout_box.box_metrics.border_right_width,
                    fill=border_color
                )
                self.canvas_items.append(right_border)
            
            if layout_box.box_metrics.border_bottom_width > 0:
                bottom_border = self.canvas.create_line(
                    x, y + height, x + width, y + height,
                    width=layout_box.box_metrics.border_bottom_width,
                    fill=border_color
                )
                self.canvas_items.append(bottom_border)
            
            if layout_box.box_metrics.border_left_width > 0:
                left_border = self.canvas.create_line(
                    x, y, x, y + height,
                    width=layout_box.box_metrics.border_left_width,
                    fill=border_color
                )
                self.canvas_items.append(left_border)
        
        # Render content based on element type
        tag_name = element.tag_name.lower()
        
        if tag_name in ('div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span'):
            self._render_text_element(layout_box)
            
        elif tag_name == 'img':
            self._render_image_element(layout_box)
            
        elif tag_name == 'a':
            self._render_link_element(layout_box)
            
        elif tag_name in ('ul', 'ol', 'li'):
            self._render_list_element(layout_box)
            
        elif tag_name == 'table':
            self._render_table_element(layout_box)
            
        elif tag_name in ('input', 'button', 'textarea', 'select'):
            self._render_form_element(layout_box)
    
    def _render_text_element(self, layout_box: LayoutBox) -> None:
        """
        Render a text element.
        
        Args:
            layout_box: The layout box to render
        """
        element = layout_box.element
        if not element:
            logger.warning("Cannot render text element: element is None")
            return
        
        # Get text content
        text = element.text_content
        if not text:
            logger.debug(f"No text content for element {element.tag_name}")
            return
        
        logger.debug(f"Rendering text element: '{text[:30]}...' if len(text) > 30 else text")
        
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
        
        # Determine font
        tag_name = element.tag_name.lower()
        font_key = 'default'
        
        if tag_name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            font_key = tag_name
        
        # Get computed styles
        styles = layout_box.computed_style
        
        # Apply font style
        font_weight = styles.get('font-weight', 'normal')
        font_style = styles.get('font-style', 'normal')
        
        if font_weight == 'bold' and font_style == 'italic':
            font_key += '_bold_italic'
        elif font_weight == 'bold':
            font_key += '_bold'
        elif font_style == 'italic':
            font_key += '_italic'
        
        # Get font
        font = self.fonts.get(font_key, self.fonts['default'])
        
        # Get text color
        color = styles.get('color', self.colors['default_text'])
        
        logger.debug(f"Creating text with font: {font}, color: {color}")
        
        # Calculate available width for text wrapping
        available_width = layout_box.box_metrics.width
        
        # Split text into lines that fit within the available width
        lines = []
        current_line = ""
        words = text.split()
        
        # Create a temporary canvas text item to measure text dimensions
        for word in words:
            test_line = current_line + " " + word if current_line else word
            # Create a test text item to check dimensions
            test_item = self.canvas.create_text(0, 0, text=test_line, font=font, anchor='nw')
            bbox = self.canvas.bbox(test_item)
            self.canvas.delete(test_item)
            
            if bbox and (bbox[2] - bbox[0]) <= available_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Render each line with proper vertical spacing
        line_height = 0
        current_y = y
        
        for i, line in enumerate(lines):
            # Create text item for this line
            try:
                text_item = self.canvas.create_text(
                    x, current_y,
                    text=line,
                    font=font,
                    fill=color,
                    anchor='nw',
                    tags=f'element:{element.id}' if element.id else ''
                )
                
                # Get line dimensions for calculating next line position
                bbox = self.canvas.bbox(text_item)
                if bbox:
                    # Use actual line height for spacing
                    if i == 0:
                        line_height = max(bbox[3] - bbox[1], 1.2 * self.fonts['default'][1])
                    
                    # Move to next line position
                    current_y += line_height
                
                # Apply text-align CSS property
                text_align = styles.get('text-align', 'left')
                if text_align in ('center', 'right') and bbox:
                    line_width = bbox[2] - bbox[0]
                    if text_align == 'center':
                        # Move text to center position
                        new_x = x + (available_width - line_width) / 2
                        self.canvas.coords(text_item, new_x, bbox[1])
                    elif text_align == 'right':
                        # Move text to right-aligned position
                        new_x = x + available_width - line_width
                        self.canvas.coords(text_item, new_x, bbox[1])
                
                logger.debug(f"Created text item with ID: {text_item}")
                self.canvas_items.append(text_item)
            except Exception as e:
                logger.error(f"Error creating text item: {str(e)}")
    
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
        src = element.get_attribute('src')
        if not src:
            return
        
        # Get box dimensions
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top
        width = layout_box.box_metrics.width
        height = layout_box.box_metrics.height
        
        # In a full implementation, we would load and display the image
        # For demonstration, we'll show a placeholder
        
        # Create placeholder
        placeholder = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill='#CCCCCC',
            outline='#999999',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(placeholder)
        
        # Add alt text if available
        alt_text = element.get_attribute('alt') or 'Image'
        text_item = self.canvas.create_text(
            x + width // 2, y + height // 2,
            text=alt_text,
            font=self.fonts['default'],
            fill='#666666',
            tags=f'element:{element.id}' if element.id else ''
        )
        self.canvas_items.append(text_item)
    
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
        # In a full implementation, would render tables
        # Simplified for demonstration
        pass
    
    def _render_form_element(self, layout_box: LayoutBox) -> None:
        """
        Render a form element (input, button, textarea, select).
        
        Args:
            layout_box: The layout box to render
        """
        # In a full implementation, would render form elements
        # Simplified for demonstration
        pass
    
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