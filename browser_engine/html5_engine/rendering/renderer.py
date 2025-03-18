"""
HTML5 Renderer implementation.
This module provides a Tkinter-based renderer for displaying HTML5 content.
"""

import logging
import os
import re
import tkinter as tk
from tkinter import ttk, Canvas, Text, PhotoImage, TclError, font as tkfont
from typing import Dict, List, Optional, Tuple, Any, Union, Set, Callable
from PIL import Image, ImageTk, ImageDraw, ImageFont
import math
import threading
import queue
import urllib.request
import urllib.parse
import urllib.error
import base64
import time
import io
from bs4.element import Comment

from ..dom import Document, Element, Node, NodeType
from ..css import LayoutEngine, LayoutBox, CSSParser, DisplayType, BoxType

logger = logging.getLogger(__name__)

# Dictionary of named colors to their hex values
NAMED_COLORS = {
    'black': '#000000',
    'silver': '#c0c0c0',
    'gray': '#808080',
    'white': '#ffffff',
    'maroon': '#800000',
    'red': '#ff0000',
    'purple': '#800080',
    'fuchsia': '#ff00ff',
    'green': '#008000',
    'lime': '#00ff00',
    'olive': '#808000',
    'yellow': '#ffff00',
    'navy': '#000080',
    'blue': '#0000ff',
    'teal': '#008080',
    'aqua': '#00ffff',
    'orange': '#ffa500',
    'aliceblue': '#f0f8ff',
    'antiquewhite': '#faebd7',
    'aquamarine': '#7fffd4',
    'azure': '#f0ffff',
    'beige': '#f5f5dc',
    'bisque': '#ffe4c4',
    'blanchedalmond': '#ffebcd',
    'blueviolet': '#8a2be2',
    'brown': '#a52a2a',
    'burlywood': '#deb887',
    'cadetblue': '#5f9ea0',
    'chartreuse': '#7fff00',
    'chocolate': '#d2691e',
    'coral': '#ff7f50',
    'cornflowerblue': '#6495ed',
    'cornsilk': '#fff8dc',
    'crimson': '#dc143c',
    'cyan': '#00ffff',
    'darkblue': '#00008b',
    'darkcyan': '#008b8b',
    'darkgoldenrod': '#b8860b',
    'darkgray': '#a9a9a9',
    'darkgreen': '#006400',
    'darkgrey': '#a9a9a9',
    'darkkhaki': '#bdb76b',
    'darkmagenta': '#8b008b',
    'darkolivegreen': '#556b2f',
    'darkorange': '#ff8c00',
    'darkorchid': '#9932cc',
    'darkred': '#8b0000',
    'darksalmon': '#e9967a',
    'darkseagreen': '#8fbc8f',
    'darkslateblue': '#483d8b',
    'darkslategray': '#2f4f4f',
    'darkslategrey': '#2f4f4f',
    'darkturquoise': '#00ced1',
    'darkviolet': '#9400d3',
    'deeppink': '#ff1493',
    'deepskyblue': '#00bfff',
    'dimgray': '#696969',
    'dimgrey': '#696969',
    'dodgerblue': '#1e90ff',
    'firebrick': '#b22222',
    'floralwhite': '#fffaf0',
    'forestgreen': '#228b22',
    'gainsboro': '#dcdcdc',
    'ghostwhite': '#f8f8ff',
    'gold': '#ffd700',
    'goldenrod': '#daa520',
    'greenyellow': '#adff2f',
    'grey': '#808080',
    'honeydew': '#f0fff0',
    'hotpink': '#ff69b4',
    'indianred': '#cd5c5c',
    'indigo': '#4b0082',
    'ivory': '#fffff0',
    'khaki': '#f0e68c',
    'lavender': '#e6e6fa',
    'lavenderblush': '#fff0f5',
    'lawngreen': '#7cfc00',
    'lemonchiffon': '#fffacd',
    'lightblue': '#add8e6',
    'lightcoral': '#f08080',
    'lightcyan': '#e0ffff',
    'lightgoldenrodyellow': '#fafad2',
    'lightgray': '#d3d3d3',
    'lightgreen': '#90ee90',
    'lightgrey': '#d3d3d3',
    'lightpink': '#ffb6c1',
    'lightsalmon': '#ffa07a',
    'lightseagreen': '#20b2aa',
    'lightskyblue': '#87cefa',
    'lightslategray': '#778899',
    'lightslategrey': '#778899',
    'lightsteelblue': '#b0c4de',
    'lightyellow': '#ffffe0',
    'limegreen': '#32cd32',
    'linen': '#faf0e6',
    'magenta': '#ff00ff',
    'mediumaquamarine': '#66cdaa',
    'mediumblue': '#0000cd',
    'mediumorchid': '#ba55d3',
    'mediumpurple': '#9370db',
    'mediumseagreen': '#3cb371',
    'mediumslateblue': '#7b68ee',
    'mediumspringgreen': '#00fa9a',
    'mediumturquoise': '#48d1cc',
    'mediumvioletred': '#c71585',
    'midnightblue': '#191970',
    'mintcream': '#f5fffa',
    'mistyrose': '#ffe4e1',
    'moccasin': '#ffe4b5',
    'navajowhite': '#ffdead',
    'oldlace': '#fdf5e6',
    'olivedrab': '#6b8e23',
    'orangered': '#ff4500',
    'orchid': '#da70d6',
    'palegoldenrod': '#eee8aa',
    'palegreen': '#98fb98',
    'paleturquoise': '#afeeee',
    'palevioletred': '#db7093',
    'papayawhip': '#ffefd5',
    'peachpuff': '#ffdab9',
    'peru': '#cd853f',
    'pink': '#ffc0cb',
    'plum': '#dda0dd',
    'powderblue': '#b0e0e6',
    'rosybrown': '#bc8f8f',
    'royalblue': '#4169e1',
    'saddlebrown': '#8b4513',
    'salmon': '#fa8072',
    'sandybrown': '#f4a460',
    'seagreen': '#2e8b57',
    'seashell': '#fff5ee',
    'sienna': '#a0522d',
    'skyblue': '#87ceeb',
    'slateblue': '#6a5acd',
    'slategray': '#708090',
    'slategrey': '#708090',
    'snow': '#fffafa',
    'springgreen': '#00ff7f',
    'steelblue': '#4682b4',
    'tan': '#d2b48c',
    'thistle': '#d8bfd8',
    'tomato': '#ff6347',
    'turquoise': '#40e0d0',
    'violet': '#ee82ee',
    'wheat': '#f5deb3',
    'whitesmoke': '#f5f5f5',
    'yellowgreen': '#9acd32'
}

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
        self.engine = None
        self.document = None
        
        # Create scrolled canvas
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas with scrollbars
        self.canvas = tk.Canvas(
            self.frame,
            bg='white',
            highlightthickness=0
        )
        
        # Create scrollbars
        self.v_scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL)
        self.h_scrollbar = ttk.Scrollbar(self.frame, orient=tk.HORIZONTAL)
        
        # Configure scrollbars
        self.v_scrollbar.config(command=self.canvas.yview)
        self.h_scrollbar.config(command=self.canvas.xview)
        self.canvas.config(
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set
        )
        
        # Grid layout
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        
        # Initialize state
        self.viewport_width = 800
        self.viewport_height = 600
        self.zoom_level = 1.0
        self.processed_nodes = set()
        self.canvas_items = []
        self.current_y = 10
        self.image_cache = {}
        
        # Initialize fonts and colors
        self._init_fonts()
        self._init_colors()
        self._init_event_bindings()
        
        logger.info("HTML5Renderer initialized")
        
        # Layout and CSS engines
        self.layout_engine = LayoutEngine()
        self.css_parser = CSSParser()
        
        # Initialize JavaScript engine if available
        try:
            from browser_engine.html5_engine.js.engine import JSEngine
            self.js_engine = JSEngine()
            logger.debug("JavaScript engine initialized")
        except ImportError:
            logger.warning("JavaScript engine not available")
            self.js_engine = None
        
        # Document and layout tree
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
        
        # Initialize for drag scrolling
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_scroll_x = 0
        self._drag_scroll_y = 0
        
        # Debug options
        self.draw_debug_boxes = False
        self.is_debug_mode = False  # Initialize is_debug_mode
        
        # Event bindings
        self._init_event_bindings()
        
        # Link handling callbacks
        self.on_link_click: Optional[Callable[[str], None]] = None
        
        # Track processed nodes to prevent duplicates
        self.processed_nodes = set()
    
    def _init_fonts(self) -> None:
        """Initialize fonts for rendering."""
        self.fonts = {
            'default': ('Arial', 12),
            'h1': ('Arial', 24, 'bold'),
            'h2': ('Arial', 20, 'bold'),
            'h3': ('Arial', 16, 'bold'),
            'h4': ('Arial', 14, 'bold'),
            'h5': ('Arial', 12, 'bold'),
            'h6': ('Arial', 10, 'bold'),
            'code': ('Courier', 12),
            'pre': ('Courier', 12),
            'link': ('Arial', 12, 'underline')
        }
        
    def _init_colors(self) -> None:
        """Initialize colors for rendering."""
        self.colors = {
            'text': '#000000',
            'link': '#0000EE',
            'visited_link': '#551A8B',
            'background': '#FFFFFF',
            'border': '#000000',
            'button': '#E0E0E0',
            'button_hover': '#D0D0D0',
            'button_active': '#C0C0C0',
            'input_border': '#767676',
            'input_background': '#FFFFFF',
            'code_background': '#F0F0F0'
        }
        
    def _init_event_bindings(self) -> None:
        """Initialize event bindings."""
        # Mouse wheel scrolling
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)  # Windows
        self.canvas.bind("<Button-4>", self._on_mousewheel)    # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mousewheel)    # Linux scroll down
        
        # Window resize
        self.parent.bind("<Configure>", self._on_resize)
        
    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling."""
        # Determine scroll direction and amount
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            # Scroll up
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            # Scroll down
            self.canvas.yview_scroll(1, "units")
            
    def _on_resize(self, event) -> None:
        """Handle window resize events."""
        # Only process if size actually changed
        if hasattr(self, 'last_width') and hasattr(self, 'last_height'):
            if event.width == self.last_width and event.height == self.last_height:
                return
                
        self.last_width = event.width
        self.last_height = event.height
        
        # Update viewport dimensions
        self.viewport_width = event.width
        self.viewport_height = event.height
        
        # Re-render content if we have a document
        if hasattr(self, 'document') and self.document:
            self.render(self.document)
    
    def set_engine(self, engine) -> None:
        """
        Set the HTML5Engine reference.
        
        Args:
            engine: The HTML5Engine instance
        """
        self.engine = engine
        
        # Initialize engines if available
        if hasattr(engine, 'css_parser'):
            self.css_parser = engine.css_parser
        if hasattr(engine, 'layout_engine'):
            self.layout_engine = engine.layout_engine
        if hasattr(engine, 'js_engine'):
            self.js_engine = engine.js_engine
            
        logger.debug("HTML5Engine reference set in renderer")
    
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
        Render a document to the canvas.
        
        Args:
            document: The DOM document to render
            layout: Optional pre-computed layout box
        """
        # Store document reference
        self.document = document
        
        # Check if document is valid
        if not document:
            logger.error("Cannot render null document")
            self._show_error_message("No document to render")
            return
            
        # More extensive document validation
        if not hasattr(document, 'document_element') or document.document_element is None:
            logger.error("Document has no document_element")
            self._show_error_message("Document has no structure to render")
            return
            
        # Log document information
        url_str = document.url if hasattr(document, 'url') else 'unknown'
        logger.info(f"Rendering document: {url_str}")
        
        # Clear any existing content and state
        self._clear_canvas()
        self.processed_nodes = set()  # Use a set for better performance
        self.canvas_items.clear()
        
        # Process all styles first
        self._process_all_styles(document)
        
        # Render using layout if provided
        if layout:
            self._render_layout_tree(layout)
        else:
            # Fallback to direct rendering if no layout provided
            self._fallback_direct_render(document)
        
        # Update scroll region
        self._update_scroll_region()
        
        logger.info("Document rendered successfully")
        
    def _fallback_direct_render(self, document):
        """
        Fallback method to render document content directly when normal rendering fails.
        
        Args:
            document: The document to render
        """
        if not document or not hasattr(document, 'document_element'):
            return
            
        logger.info("Using fallback direct rendering")
        
        # Get the body element
        body = document.getElementsByTagName('body')[0] if document.getElementsByTagName('body') else document.document_element
        
        # Initialize rendering state
        self.current_y = 10
        
        # Start rendering from body
        self._fallback_direct_render_element(body)
    
    def _fallback_direct_render_element(self, element: Element) -> None:
        """
        Render an element directly without layout calculations.
        
        Args:
            element: The element to render
        """
        # Skip if already processed
        if element in self.processed_nodes:
            return
            
        self.processed_nodes.add(element)
        
        # Handle text nodes
        if hasattr(element, 'node_type') and element.node_type == 3:  # TEXT_NODE
            if hasattr(element, 'data') and element.data.strip():
                text = element.data.strip()
                if text:
                    self.canvas.create_text(
                        10, self.current_y,
                        text=text,
                        anchor='w',
                        font=('Arial', 12)
                    )
                    self.current_y += 20
            return
            
        # Handle element nodes
        if hasattr(element, 'tag_name'):
            tag_name = element.tag_name.lower()
            
            # Handle headings
            if tag_name.startswith('h') and len(tag_name) == 2:
                size = {'h1': 24, 'h2': 20, 'h3': 16, 'h4': 14, 'h5': 12, 'h6': 10}.get(tag_name, 12)
                text = self._extract_text_content(element)
                if text:
                    self.canvas.create_text(
                        10, self.current_y,
                        text=text,
                        anchor='w',
                        font=('Arial', size, 'bold')
                    )
                    self.current_y += size + 10
                    
            # Handle paragraphs
            elif tag_name == 'p':
                text = self._extract_text_content(element)
                if text:
                    self.canvas.create_text(
                        10, self.current_y,
                        text=text,
                        anchor='w',
                        font=('Arial', 12)
                    )
                    self.current_y += 20
                    
            # Handle links
            elif tag_name == 'a':
                href = element.get_attribute('href') if hasattr(element, 'get_attribute') else None
                text = self._extract_text_content(element)
                if text:
                    item = self.canvas.create_text(
                        10, self.current_y,
                        text=text,
                        anchor='w',
                        font=('Arial', 12),
                        fill='blue',
                        underline=True
                    )
                    if href:
                        self.canvas.tag_bind(item, '<Button-1>', lambda e, url=href: self._on_link_click(e, url))
                    self.current_y += 20
            
            # Process child elements for block elements
            if tag_name in {'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'table'}:
                if hasattr(element, 'child_nodes'):
                    for child in element.child_nodes:
                        self._fallback_direct_render_element(child)
                    # Add extra spacing after block elements
                    self.current_y += 10
    
    def _render_horizontal_rule(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int) -> None:
        """
        Render a horizontal rule element.
        
        Args:
            layout_box: The layout box for the hr element
            x: X coordinate
            y: Y coordinate
            width: Width of the element
            height: Height of the element
        """
        # Create a horizontal line
        line = self.canvas.create_line(
            x, y + height // 2, 
            x + width, y + height // 2,
            fill="#cccccc",
            width=1
        )
        self.canvas_items.append(line)
        
    def _make_link_clickable(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int) -> None:
        """
        Make a link element clickable.
        
        Args:
            layout_box: The layout box for the link element
            x: X coordinate
            y: Y coordinate
            width: Width of the element
            height: Height of the element
        """
        if not layout_box.element:
            return
            
        # Get the href attribute
        href = layout_box.element.get_attribute('href') if hasattr(layout_box.element, 'get_attribute') else None
        
        if not href:
            return
            
        # Create a clickable area
        clickable_area = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill='',
            outline='',
            tags=('link', href)
        )
        self.canvas_items.append(clickable_area)
        
        # Bind click event to the area
        self.canvas.tag_bind(clickable_area, '<Button-1>', lambda event, url=href: self._on_link_click(event, url))
        
        # Change cursor to hand when hovering over the link
        self.canvas.tag_bind(clickable_area, '<Enter>', lambda event: self.canvas.config(cursor='hand2'))
        self.canvas.tag_bind(clickable_area, '<Leave>', lambda event: self.canvas.config(cursor=''))
        
    def _on_link_click(self, event, url: str) -> None:
        """
        Handle link click events.
        
        Args:
            event: The click event
            url: The URL to navigate to
        """
        # Call the link click callback if registered
        if self.on_link_click:
            self.on_link_click(url)
            
    def _render_image(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int) -> None:
        """
        Render an image element.
        
        Args:
            layout_box: The layout box for the image element
            x: X coordinate
            y: Y coordinate
            width: Width of the element
            height: Height of the element
        """
        if not layout_box.element:
            return
            
        # Get the src attribute
        src = layout_box.element.get_attribute('src') if hasattr(layout_box.element, 'get_attribute') else None
        
        if not src:
            # Render a placeholder if no src
            self._render_image_placeholder(layout_box, x, y, width, height, layout_box.element)
            return
            
        # Check if image is already in cache
        if src in self.image_cache:
            # Use cached image
            image = self.image_cache[src]
            image_item = self.canvas.create_image(x, y, image=image, anchor='nw')
            self.canvas_items.append(image_item)
        else:
            # Start loading the image
            self._start_image_loading(src)
            
            # Render placeholder while loading
            self._render_image_placeholder(layout_box, x, y, width, height, layout_box.element)
    
    def _render_button_element(self, x, y, width, height, text, element, is_disabled=False):
        """
        Render a button element.
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Width of the button
            height: Height of the button
            text: Button text
            element: The button element
            is_disabled: Whether the button is disabled
        """
        # Determine colors based on disabled state
        if is_disabled:
            bg_color = '#e0e0e0'
            text_color = '#a0a0a0'
            border_color = '#c0c0c0'
        else:
            bg_color = '#f0f0f0'
            text_color = '#000000'
            border_color = '#c0c0c0'
            
        # Create button with rounded corners
        button = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill=bg_color,
            outline=border_color,
            width=1
        )
        self.canvas_items.append(button)
        
        # Add text
        text_item = self.canvas.create_text(
            x + width // 2, y + height // 2,
            text=text,
            fill=text_color,
            anchor='center',
            font=('Arial', 10)
        )
        self.canvas_items.append(text_item)
        
        # Make button clickable if not disabled
        if not is_disabled:
            clickable_area = self.canvas.create_rectangle(
                x, y, x + width, y + height,
                fill='',
                outline='',
                tags=('button', str(id(element)))
            )
            self.canvas_items.append(clickable_area)
            
            # Change cursor to hand when hovering over the button
            self.canvas.tag_bind(clickable_area, '<Enter>', lambda event: self.canvas.config(cursor='hand2'))
            self.canvas.tag_bind(clickable_area, '<Leave>', lambda event: self.canvas.config(cursor=''))
    
    def _render_border(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int) -> None:
        """
        Render the border of an element.
        
        Args:
            layout_box: The layout box to render the border for.
            x: The x coordinate of the top-left corner.
            y: The y coordinate of the top-left corner.
            width: The width of the element.
            height: The height of the element.
        """
        if not layout_box or not layout_box.element:
            return
            
        # Get the computed style for the element
        style = layout_box.computed_style
        if not style:
            return
            
        # Get border properties
        border_top_width = self._parse_size(style.get('border-top-width', '0px'))
        border_right_width = self._parse_size(style.get('border-right-width', '0px'))
        border_bottom_width = self._parse_size(style.get('border-bottom-width', '0px'))
        border_left_width = self._parse_size(style.get('border-left-width', '0px'))
        
        # If no borders, return early
        if border_top_width == 0 and border_right_width == 0 and border_bottom_width == 0 and border_left_width == 0:
            return
            
        # Get border colors
        border_top_color = style.get('border-top-color', 'black')
        border_right_color = style.get('border-right-color', 'black')
        border_bottom_color = style.get('border-bottom-color', 'black')
        border_left_color = style.get('border-left-color', 'black')
        
        # Convert colors to Tkinter format
        border_top_color = self._convert_color(border_top_color)
        border_right_color = self._convert_color(border_right_color)
        border_bottom_color = self._convert_color(border_bottom_color)
        border_left_color = self._convert_color(border_left_color)
        
        # Get border styles
        border_top_style = style.get('border-top-style', 'none')
        border_right_style = style.get('border-right-style', 'none')
        border_bottom_style = style.get('border-bottom-style', 'none')
        border_left_style = style.get('border-left-style', 'none')
        
        # Draw borders if they have width and are not 'none'
        try:
            # Top border
            if border_top_width > 0 and border_top_style != 'none':
                top_border = self.canvas.create_line(
                    x, y, x + width, y,
                    width=border_top_width,
                    fill=border_top_color
                )
                self.canvas_items.append(top_border)
                
            # Right border
            if border_right_width > 0 and border_right_style != 'none':
                right_border = self.canvas.create_line(
                    x + width, y, x + width, y + height,
                    width=border_right_width,
                    fill=border_right_color
                )
                self.canvas_items.append(right_border)
                
            # Bottom border
            if border_bottom_width > 0 and border_bottom_style != 'none':
                bottom_border = self.canvas.create_line(
                    x, y + height, x + width, y + height,
                    width=border_bottom_width,
                    fill=border_bottom_color
                )
                self.canvas_items.append(bottom_border)
                
            # Left border
            if border_left_width > 0 and border_left_style != 'none':
                left_border = self.canvas.create_line(
                    x, y, x, y + height,
                    width=border_left_width,
                    fill=border_left_color
                )
                self.canvas_items.append(left_border)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error rendering border: {e}")
            # Continue with rendering even if border fails
    
    def _convert_color(self, color: str) -> str:
        """
        Convert a CSS color to a format Tkinter can understand.
        
        Args:
            color: The CSS color to convert.
            
        Returns:
            The color in a format Tkinter can understand.
        """
        if not color:
            return 'black'
            
        # Handle named colors
        if color in NAMED_COLORS:
            return NAMED_COLORS[color]
            
        # Handle hex colors
        if color.startswith('#'):
            # Ensure it's a valid hex color
            if len(color) == 4:  # #RGB format
                r = color[1] * 2
                g = color[2] * 2
                b = color[3] * 2
                return f"#{r}{g}{b}"
            return color
            
        # Handle rgb() format
        if color.startswith('rgb('):
            # Extract the RGB values
            rgb_values = color[4:-1].split(',')
            if len(rgb_values) == 3:
                r = int(rgb_values[0].strip())
                g = int(rgb_values[1].strip())
                b = int(rgb_values[2].strip())
                return f"#{r:02x}{g:02x}{b:02x}"
                
        # Default to black if color format is not recognized
        return 'black'
    
    def _parse_size(self, size: str) -> int:
        """
        Parse a CSS size value into pixels.
        
        Args:
            size: The CSS size value to parse.
            
        Returns:
            The size in pixels.
        """
        if not size:
            return 0
            
        # Remove whitespace
        size = size.strip()
        
        # Handle pixel values
        if size.endswith('px'):
            try:
                return int(float(size[:-2]))
            except ValueError:
                return 0
                
        # Handle em values (assume 1em = 16px)
        if size.endswith('em'):
            try:
                return int(float(size[:-2]) * 16)
            except ValueError:
                return 0
                
        # Handle rem values (assume 1rem = 16px)
        if size.endswith('rem'):
            try:
                return int(float(size[:-3]) * 16)
            except ValueError:
                return 0
                
        # Handle percentage values (assume percentage of parent width)
        if size.endswith('%'):
            try:
                # Default to 0 as we don't have parent width information here
                return 0
            except ValueError:
                return 0
                
        # Handle numeric values without units (assume pixels)
        try:
            return int(float(size))
        except ValueError:
            return 0

    def _calculate_dimension(self, value, container_dimension: int, element_type: str = None, dimension_type: str = 'width', layout_box=None) -> int:
        """
        Calculate a dimension value, handling 'auto' and percentages.
        
        Args:
            value: The dimension value to calculate
            container_dimension: The dimension of the containing block
            element_type: Type of element ('block', 'inline', etc.)
            dimension_type: Type of dimension ('width' or 'height')
            layout_box: The layout box being calculated
            
        Returns:
            Calculated dimension in pixels
        """
        try:
            # Handle numeric values
            if isinstance(value, (int, float)):
                return int(value)
            
            # Handle string values
            if isinstance(value, str):
                # Handle 'auto'
                if value == 'auto':
                    if dimension_type == 'width':
                        if element_type == 'block':
                            # Block elements take full container width minus margins, padding, and borders
                            if layout_box:
                                # Get all box model properties
                                margin_left = layout_box.box_metrics.margin_left
                                margin_right = layout_box.box_metrics.margin_right
                                padding_left = layout_box.box_metrics.padding_left
                                padding_right = layout_box.box_metrics.padding_right
                                border_left = layout_box.box_metrics.border_left_width
                                border_right = layout_box.box_metrics.border_right_width
                                
                                # Convert string values to float, handling 'auto' as 0
                                if isinstance(margin_left, str):
                                    margin_left = 0 if margin_left == 'auto' else float(margin_left)
                                if isinstance(margin_right, str):
                                    margin_right = 0 if margin_right == 'auto' else float(margin_right)
                                if isinstance(padding_left, str):
                                    padding_left = 0 if padding_left == 'auto' else float(padding_left)
                                if isinstance(padding_right, str):
                                    padding_right = 0 if padding_right == 'auto' else float(padding_right)
                                if isinstance(border_left, str):
                                    border_left = 0 if border_left == 'auto' else float(border_left)
                                if isinstance(border_right, str):
                                    border_right = 0 if border_right == 'auto' else float(border_right)
                                
                                # Calculate total box model properties
                                total_margin = margin_left + margin_right
                                total_padding = padding_left + padding_right
                                total_border = border_left + border_right
                                
                                # Content width fills available space
                                return int(container_dimension - total_margin - total_padding - total_border)
                            return int(container_dimension * 0.95)  # 95% of container if no metrics
                        else:
                            # Inline elements use percentage of container
                            return int(container_dimension * 0.8)  # 80% of container width
                    else:  # height
                        if layout_box and layout_box.children:
                            # Calculate based on children
                            total_height = 0
                            for child in layout_box.children:
                                if isinstance(child.box_metrics.margin_box_height, (int, float)):
                                    total_height += child.box_metrics.margin_box_height
                            if total_height > 0:
                                return total_height
                        # Default to aspect ratio based on width
                        width = self._calculate_dimension(layout_box.box_metrics.content_width, container_dimension, element_type, 'width', layout_box) if layout_box else container_dimension
                        return int(width * 0.6)  # Default aspect ratio
                
                # Handle percentage values
                if value.endswith('%'):
                    try:
                        percentage = float(value[:-1]) / 100
                        return int(container_dimension * percentage)
                    except (ValueError, TypeError):
                        pass
                
                # Try converting numeric string
                try:
                    return int(value)
                except (ValueError, TypeError):
                    pass
            
            # Fallback values
            if dimension_type == 'width':
                return int(container_dimension * 0.8)  # 80% of container
            else:  # height
                width = self._calculate_dimension(layout_box.box_metrics.content_width, container_dimension, element_type, 'width', layout_box) if layout_box else container_dimension
                return int(width * 0.6)  # Default aspect ratio
                
        except Exception as e:
            logger.error(f"Error calculating {dimension_type}: {e}")
            # Ultimate fallback
            if dimension_type == 'width':
                return int(container_dimension * 0.8)
            return int(container_dimension * 0.5)

    def _render_text_content(self, layout_box):
        """
        Render text content for a layout box.
        
        Args:
            layout_box: The layout box containing text to render
        """
        try:
            if not layout_box or not layout_box.element:
                return
                
            element = layout_box.element
            
            # Skip script and style tags
            if hasattr(element, 'tag_name') and element.tag_name.lower() in ('script', 'style'):
                return
                
            # Create a unique identifier for this element
            element_id = f"{id(element)}"
            
            # Skip if this element was already rendered
            if element_id in self.processed_nodes:
                return
            
            # Mark element as processed
            self.processed_nodes.add(element_id)
            
            # Get text content
            text = None
            if hasattr(element, 'text_content'):
                text = element.text_content
            elif hasattr(element, 'textContent'):
                text = element.textContent
            elif hasattr(element, 'text'):
                text = element.text
                
            if not text:
                # Try to get text from child nodes
                text = self._extract_text_content(element)
                
            if not text or not text.strip():
                return
                
            # Get positioning from box metrics
            x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left + layout_box.box_metrics.border_left_width
            y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top + layout_box.box_metrics.border_top_width
            
            # Get font settings from computed style
            font_family = "Arial"  # Default font
            font_size = 12  # Default size
            font_weight = "normal"
            font_style = "normal"
            
            if hasattr(layout_box, 'computed_style'):
                font_family = layout_box.computed_style.get('font-family', font_family)
                font_size_str = layout_box.computed_style.get('font-size', str(font_size))
                font_weight = layout_box.computed_style.get('font-weight', font_weight)
                font_style = layout_box.computed_style.get('font-style', font_style)
                
                # Convert font size to integer
                try:
                    if isinstance(font_size_str, str):
                        if font_size_str.endswith('px'):
                            font_size = int(font_size_str[:-2])
                        else:
                            font_size = int(font_size_str)
                    else:
                        font_size = int(font_size_str)
                except (ValueError, TypeError):
                    font_size = 12  # Fallback to default size
            
            # Create font configuration
            font_config = (font_family, font_size)
            
            if font_weight == 'bold':
                font_config = (font_family, font_size, 'bold')
            if font_style == 'italic':
                if len(font_config) == 2:
                    font_config = (font_family, font_size, 'italic')
                else:
                    font_config = (font_family, font_size, 'bold italic')
            
            # Text color from computed style
            color = "#000000"
            if hasattr(layout_box, 'computed_style'):
                color = layout_box.computed_style.get('color', color)
            
            # Get element tag for specific adjustments
            tag_name = element.tag_name.lower() if hasattr(element, 'tag_name') else ''
            
            # Calculate available width for text wrapping
            element_type = 'block' if layout_box.display == 'block' else 'inline'
            available_width = self._calculate_dimension(
                layout_box.box_metrics.content_width,
                self.viewport_width,
                element_type,
                'width',
                layout_box
            )
            
            if available_width <= 0:
                available_width = None  # Let text flow naturally if no width constraint
            
            # Create text with proper wrapping
            text_item = self.canvas.create_text(
                x, y,
                text=text.strip(),
                font=font_config,
                fill=color,
                anchor="nw",
                width=available_width,
                tags=("text", tag_name)  # Add tags for better management
            )
            
            # Store the text item for later reference
            self.canvas_items.append(text_item)
            
            # Update layout box height based on text dimensions
            bbox = self.canvas.bbox(text_item)
            if bbox:
                text_height = bbox[3] - bbox[1]
                layout_box.box_metrics.content_height = max(layout_box.box_metrics.content_height, text_height)
            
        except Exception as e:
            logger.error(f"Error in text rendering: {e}")
    
    def _render_image_placeholder(self, layout_box, x, y, width, height, element):
        """
        Render a placeholder for an image that is loading or failed to load.
        
        Args:
            layout_box: The layout box of the image element
            x: X coordinate
            y: Y coordinate
            width: Width of the image
            height: Height of the image
            element: The image element
        """
        try:
            # Create a rectangle as placeholder
            rect_item = self.canvas.create_rectangle(
                x, y, x + width, y + height,
                fill="#f0f0f0",
                outline="#cccccc"
            )
            self.canvas_items.append(rect_item)
            
            # Add an icon or text to indicate loading
            text_item = self.canvas.create_text(
                x + width/2, y + height/2,
                text="Loading...",
                font=("Arial", 10),
                fill="#666666"
            )
            self.canvas_items.append(text_item)
            
            # If alt text is available, display it
            if hasattr(element, 'getAttribute'):
                alt_text = element.getAttribute('alt')
                if alt_text:
                    alt_item = self.canvas.create_text(
                        x + width/2, y + height/2 + 15,
                        text=alt_text,
                        font=("Arial", 9),
                        fill="#333333"
                    )
                    self.canvas_items.append(alt_item)
                    
            logging.debug(f"Rendered image placeholder at ({x}, {y}) with dimensions {width}x{height}")
        except Exception as e:
            logging.error(f"Error rendering image placeholder: {e}")

    def _render_form_element(self, layout_box: LayoutBox, x: int, y: int, width: int, height: int) -> None:
        """
        Render a form element (input, button, textarea, select).
        
        Args:
            layout_box: The layout box for the form element
            x: X coordinate
            y: Y coordinate
            width: Width of the element
            height: Height of the element
        """
        element = layout_box.element
        if not element or not hasattr(element, 'tag_name'):
            return
            
        # Get positioning information from layout box
        x = layout_box.box_metrics.x + layout_box.box_metrics.padding_left + layout_box.box_metrics.border_left_width
        y = layout_box.box_metrics.y + layout_box.box_metrics.padding_top + layout_box.box_metrics.border_top_width
        
        # Get width and height from box metrics, with fallbacks
        width = layout_box.box_metrics.content_width
        height = layout_box.box_metrics.content_height
        
        # Ensure width and height are numeric and positive
        if width == 'auto' or not isinstance(width, (int, float)) or width <= 0:
            width = 200  # Default width for form elements
        if height == 'auto' or not isinstance(height, (int, float)) or height <= 0:
            height = 30  # Default height for form elements
            
        # Limit width to viewport
        width = min(width, self.viewport_width - 40)
            
        tag_name = element.tag_name.lower()
        
        # Get attributes
        element_type = element.get_attribute('type') if hasattr(element, 'get_attribute') else None
        element_value = element.get_attribute('value') if hasattr(element, 'get_attribute') else None
        element_placeholder = element.get_attribute('placeholder') if hasattr(element, 'get_attribute') else None
        element_name = element.get_attribute('name') if hasattr(element, 'get_attribute') else None
        
        # Default values
        if not element_type and tag_name == 'input':
            element_type = 'text'  # Default input type is text
        if not element_value:
            element_value = ''
            
        # Different dimensions based on input type
        if tag_name == 'input' and element_type in ['submit', 'button', 'reset']:
            # Buttons are typically shorter but taller
            if int(width) > 150:
                width = 150
            height = max(height, 32)  # Ensure buttons have enough height
        elif tag_name == 'textarea':
            # Textareas are typically larger
            height = max(height, 100)
            width = max(width, 250)
        elif tag_name == 'select':
            # Select dropdown needs enough height for the arrow
            height = max(height, 32)
        
        # Ensure minimum height for all form elements
        height = max(height, 24)
        
        # Set the height back to the layout box to ensure proper layout
        layout_box.box_metrics.content_height = height
        layout_box._update_box_dimensions()
        
        # Log the form element rendering
        logger.debug(f"Rendered form element {tag_name} at ({x}, {y}) with dimensions {width}x{height}")
        
        # Render different form elements
        try:
            if tag_name == 'input':
                # Handle different input types
                if element_type in ['text', 'password', 'email', 'number', 'tel', 'url', None]:
                    # Create a rectangle to represent a text input
                    input_rect = self.canvas.create_rectangle(
                        x, y, x + width, y + height,
                        outline="#cccccc",
                        fill="#ffffff"
                    )
                    self.canvas_items.append(input_rect)
                    
                    # Add text content (value or placeholder)
                    text_content = element_value if element_value else element_placeholder if element_placeholder else ''
                    text_color = "#333333" if element_value else "#999999"  # Gray for placeholder
                    
                    text_item = self.canvas.create_text(
                        x + 5, y + (height // 2),
                        text=text_content,
                        font=("Arial", 12),
                        fill=text_color,
                        anchor="w"  # West anchor (left-middle)
                    )
                    self.canvas_items.append(text_item)
                    
                elif element_type in ['submit', 'button', 'reset']:
                    # Create a button
                    button_text = element_value if element_value else element_type.capitalize()
                    
                    button = self._render_button_element(
                        x, y, width, height, 
                        button_text, 
                        element
                    )
                    
                elif element_type == 'checkbox':
                    # Create a checkbox
                    checkbox_size = min(16, height)
                    checkbox = self.canvas.create_rectangle(
                        x, y + (height - checkbox_size) // 2, 
                        x + checkbox_size, y + (height + checkbox_size) // 2,
                        outline="#333333",
                        fill="#ffffff"
                    )
                    self.canvas_items.append(checkbox)
                    
                    # Add a check mark if checked
                    is_checked = element.get_attribute('checked') if hasattr(element, 'get_attribute') else False
                    if is_checked:
                        checkmark = self.canvas.create_line(
                            x + 3, y + (height) // 2,
                            x + 7, y + (height + checkbox_size) // 2 - 3,
                            x + checkbox_size - 3, y + (height - checkbox_size) // 2 + 3,
                            fill="#333333",
                            width=2
                        )
                        self.canvas_items.append(checkmark)
                    
                    # Add label if there's text
                    if element_value:
                        label = self.canvas.create_text(
                            x + checkbox_size + 5, y + height // 2,
                            text=element_value,
                            font=("Arial", 12),
                            fill="#333333",
                            anchor="w"
                        )
                        self.canvas_items.append(label)
                        
                elif element_type == 'radio':
                    # Create a radio button
                    radio_size = min(16, height)
                    radio = self.canvas.create_oval(
                        x, y + (height - radio_size) // 2, 
                        x + radio_size, y + (height + radio_size) // 2,
                        outline="#333333",
                        fill="#ffffff"
                    )
                    self.canvas_items.append(radio)
                    
                    # Add a dot if checked
                    is_checked = element.get_attribute('checked') if hasattr(element, 'get_attribute') else False
                    if is_checked:
                        dot_size = radio_size - 6
                        dot = self.canvas.create_oval(
                            x + 3, y + (height - dot_size) // 2, 
                            x + 3 + dot_size, y + (height + dot_size) // 2,
                            outline="",
                            fill="#333333"
                        )
                        self.canvas_items.append(dot)
                    
                    # Add label if there's text
                    if element_value:
                        label = self.canvas.create_text(
                            x + radio_size + 5, y + height // 2,
                            text=element_value,
                            font=("Arial", 12),
                            fill="#333333",
                            anchor="w"
                        )
                        self.canvas_items.append(label)
                        
                else:
                    # Default input rendering
                    input_rect = self.canvas.create_rectangle(
                        x, y, x + width, y + height,
                        outline="#cccccc",
                        fill="#ffffff"
                    )
                    self.canvas_items.append(input_rect)
                
            elif tag_name == 'button':
                # Render button
                button_text = ''
                if hasattr(element, 'text_content') and element.text_content:
                    button_text = element.text_content
                elif element_value:
                    button_text = element_value
                else:
                    button_text = "Button"
                    
                self._render_button_element(
                    x, y, width, height, 
                    button_text, 
                    element
                )
                
            elif tag_name == 'select':
                # Create a select dropdown
                select_rect = self.canvas.create_rectangle(
                    x, y, x + width, y + height,
                    outline="#cccccc",
                    fill="#ffffff"
                )
                self.canvas_items.append(select_rect)
                
                # Add dropdown arrow
                arrow_x = x + width - 20
                arrow_y = y + height // 2
                arrow = self.canvas.create_polygon(
                    arrow_x, arrow_y - 5,
                    arrow_x + 10, arrow_y - 5,
                    arrow_x + 5, arrow_y + 5,
                    fill="#333333"
                )
                self.canvas_items.append(arrow)
                
                # Add selected option text if available
                selected_text = ''
                if hasattr(element, 'value') and element.value:
                    selected_text = element.value
                elif element_value:
                    selected_text = element_value
                elif hasattr(element, 'child_nodes'):
                    # Try to find selected option
                    for child in element.child_nodes:
                        if hasattr(child, 'tag_name') and child.tag_name.lower() == 'option':
                            # Check if this option is selected
                            is_selected = child.get_attribute('selected') if hasattr(child, 'get_attribute') else False
                            if is_selected:
                                if hasattr(child, 'text_content'):
                                    selected_text = child.text_content
                                break
                    
                    # If no selected option found, use first option
                    if not selected_text:
                        for child in element.child_nodes:
                            if hasattr(child, 'tag_name') and child.tag_name.lower() == 'option':
                                if hasattr(child, 'text_content'):
                                    selected_text = child.text_content
                                break
                
                # Render selected text
                if selected_text:
                    text_item = self.canvas.create_text(
                        x + 5, y + height // 2,
                        text=selected_text,
                        font=("Arial", 12),
                        fill="#333333",
                        anchor="w"
                    )
                    self.canvas_items.append(text_item)
                
            elif tag_name == 'textarea':
                # Create a textarea
                textarea_rect = self.canvas.create_rectangle(
                    x, y, x + width, y + height,
                    outline="#cccccc",
                    fill="#ffffff"
                )
                self.canvas_items.append(textarea_rect)
                
                # Add text content
                text_content = ''
                if hasattr(element, 'text_content') and element.text_content:
                    text_content = element.text_content
                elif hasattr(element, 'value') and element.value:
                    text_content = element.value
                elif element_value:
                    text_content = element_value
                elif element_placeholder:
                    text_content = element_placeholder
                    
                text_item = self.canvas.create_text(
                    x + 5, y + 5,
                    text=text_content,
                    font=("Arial", 12),
                    fill="#333333" if text_content != element_placeholder else "#999999",
                    anchor="nw",
                    width=width - 10  # Allow text wrapping
                )
                self.canvas_items.append(text_item)
        except Exception as e:
            logger.error(f"Error rendering form element: {e}")
            # Render a basic fallback to at least show something
            fallback_rect = self.canvas.create_rectangle(
                x, y, x + width, y + height,
                outline="#ff0000",
                fill="#ffeeee"
            )
            self.canvas_items.append(fallback_rect)
            
            fallback_text = self.canvas.create_text(
                x + width // 2, y + height // 2,
                text=f"{tag_name}",
                font=("Arial", 9),
                fill="#ff0000"
            )
            self.canvas_items.append(fallback_text)

    def _layout_box(self, layout_box: LayoutBox, x: int, y: int, container_width: int) -> None:
        """
        Apply layout to a single box and its children.
        
        Args:
            layout_box: Layout box to apply layout to
            x: X position
            y: Y position
            container_width: Width of containing box
        """
        try:
            # Set position
            layout_box.box_metrics.x = x
            layout_box.box_metrics.y = y
            
            # Calculate width
            if isinstance(layout_box.box_metrics.content_width, str):
                if layout_box.box_metrics.content_width == 'auto':
                    # Default to fill container
                    layout_box.box_metrics.content_width = container_width - layout_box.box_metrics.margin_left - layout_box.box_metrics.margin_right
                else:
                    # Try to convert numeric string to int
                    try:
                        layout_box.box_metrics.content_width = int(layout_box.box_metrics.content_width)
                    except ValueError:
                        # If conversion fails, default to container width
                        layout_box.box_metrics.content_width = container_width - layout_box.box_metrics.margin_left - layout_box.box_metrics.margin_right
            
            # Update box dimensions
            layout_box._update_box_dimensions()
            
            # Layout children
            if layout_box.display == 'block':
                self._layout_block_children(layout_box, container_width)
            elif layout_box.display == 'inline':
                self._layout_inline_children(layout_box, container_width)
            else:
                # Default to block layout
                self._layout_block_children(layout_box, container_width)
            
            # Calculate height based on children
            if isinstance(layout_box.box_metrics.content_height, str):
                if layout_box.box_metrics.content_height == 'auto':
                    height = 0
                    for child in layout_box.children:
                        child_bottom = child.box_metrics.y + child.box_metrics.margin_box_height - layout_box.box_metrics.y
                        height = max(height, child_bottom)
                    layout_box.box_metrics.content_height = height
                else:
                    # Try to convert numeric string to int
                    try:
                        layout_box.box_metrics.content_height = int(layout_box.box_metrics.content_height)
                    except ValueError:
                        # If conversion fails, calculate based on children
                        height = 0
                        for child in layout_box.children:
                            child_bottom = child.box_metrics.y + child.box_metrics.margin_box_height - layout_box.box_metrics.y
                            height = max(height, child_bottom)
                        layout_box.box_metrics.content_height = height
            
            layout_box._update_box_dimensions()
            
        except Exception as e:
            logger.error(f"Error during layout: {e}")
            # Set safe default values
            layout_box.box_metrics.content_width = container_width
            layout_box.box_metrics.content_height = 0
            layout_box._update_box_dimensions()

    def _extract_text_content(self, element) -> str:
        """
        Extract text content from an element, handling both direct text nodes and nested elements.
        
        Args:
            element: The element to extract text from
            
        Returns:
            str: The extracted text content
        """
        if not element:
            return ""
            
        # Handle text nodes directly
        if hasattr(element, 'node_type') and element.node_type == 3:  # TEXT_NODE
            return element.data.strip() if hasattr(element, 'data') else ""
            
        # Handle element nodes
        if not hasattr(element, 'child_nodes'):
            return ""
            
        # Collect text from child nodes
        text_parts = []
        for child in element.child_nodes:
            # Skip if already processed
            if child in self.processed_nodes:
                continue
                
            # Mark as processed
            self.processed_nodes.add(child)
            
            # Extract text based on node type
            if hasattr(child, 'node_type'):
                if child.node_type == 3:  # TEXT_NODE
                    if hasattr(child, 'data') and child.data.strip():
                        text_parts.append(child.data.strip())
                elif child.node_type == 1:  # ELEMENT_NODE
                    # For inline elements, include their text content
                    if hasattr(child, 'tag_name') and child.tag_name.lower() in {'span', 'a', 'strong', 'em', 'b', 'i', 'u', 'code'}:
                        text_parts.append(self._extract_text_content(child))
                        
        return " ".join(text_parts).strip()

    def _clear_canvas(self) -> None:
        """Clear the canvas and reset state."""
        # Delete all canvas items
        for item_id in self.canvas_items:
            try:
                self.canvas.delete(item_id)
            except tk.TclError:
                pass  # Item already deleted
        
        self.canvas_items = []
        self.processed_nodes = set()
        self.current_y = 10
        self.image_cache.clear()
        
        # Clear the canvas
        self.canvas.delete("all")
        
    def render_elements(self, document: Document, head: Optional[Element] = None, body: Optional[Element] = None, base_url: Optional[str] = None) -> None:
        """
        Render document elements directly.
        
        Args:
            document: The document to render
            head: Optional head element
            body: Optional body element
            base_url: Optional base URL for resolving relative URLs
        """
        if not document:
            logger.error("Cannot render null document")
            return
            
        # Clear existing content
        self._clear_canvas()
        
        # Get the body or document element if not provided
        if not body:
            if hasattr(document, 'getElementsByTagName'):
                body_elements = document.getElementsByTagName('body')
                if body_elements:
                    body = body_elements[0]
        
        if not body and hasattr(document, 'document_element'):
            body = document.document_element
            
        if not body:
            logger.error("No body or document element found")
            return
            
        # Start rendering from body
        self._fallback_direct_render_element(body)
        
        # Update scroll region
        self._update_scroll_region()

    def _update_scroll_region(self) -> None:
        """Update the canvas scroll region based on content."""
        # Get bounding box of all items
        bbox = self.canvas.bbox("all")
        
        if bbox:
            # Add some padding
            padding = 20
            x1, y1, x2, y2 = bbox
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 += padding
            y2 += padding
            
            # Configure scroll region
            self.canvas.configure(scrollregion=(x1, y1, x2, y2))
            
            # Ensure minimum width and height
            min_width = max(x2 - x1, self.viewport_width)
            min_height = max(y2 - y1, self.viewport_height)
            
            # Update canvas size if needed
            self.canvas.configure(width=min_width, height=min_height)
        else:
            # If no items, set default scroll region
            self.canvas.configure(scrollregion=(0, 0, self.viewport_width, self.viewport_height))
            self.canvas.configure(width=self.viewport_width, height=self.viewport_height)

    def _process_all_styles(self, document: Document) -> None:
        """
        Process all styles in the document before rendering.
        
        Args:
            document: The document to process styles for
        """
        if not document or not document.document_element:
            return
            
        # Process default styles
        if self.engine and hasattr(self.engine, 'css_parser'):
            self.engine.css_parser.add_default_styles()
            
        # Process inline styles
        for element in document.get_elements_by_tag_name('*'):
            style_attr = element.get_attribute('style')
            if style_attr:
                try:
                    if self.engine and hasattr(self.engine, 'css_parser'):
                        computed_style = self.engine.css_parser.parse_inline_styles(style_attr)
                        element.computed_style.update(computed_style)
                except Exception as e:
                    logger.error(f"Error processing inline styles: {e}")
                    
        # Process stylesheet links
        for link in document.get_elements_by_tag_name('link'):
            if (link.get_attribute('rel') == 'stylesheet' and 
                link.get_attribute('href')):
                try:
                    if self.engine:
                        self.engine.load_stylesheet(link.get_attribute('href'))
                except Exception as e:
                    logger.error(f"Error loading stylesheet: {e}")
                    
        # Process style elements
        for style in document.get_elements_by_tag_name('style'):
            try:
                if self.engine and hasattr(self.engine, 'css_parser'):
                    css_text = style.text_content
                    if css_text:
                        parsed_styles = self.engine.css_parser.parse(css_text)
                        # Apply styles to matching elements
                        for selector, properties in parsed_styles.items():
                            matching_elements = document.query_selector_all(selector)
                            for element in matching_elements:
                                element.computed_style.update(properties)
            except Exception as e:
                logger.error(f"Error processing style element: {e}")
                
        logger.debug("Styles processed successfully")

    def _render_layout_tree(self, layout_box: LayoutBox) -> None:
        """
        Render a layout tree to the canvas.
        
        Args:
            layout_box: The root layout box to render
        """
        if not layout_box:
            logger.error("Cannot render null layout box")
            return
            
        # Skip if already processed
        if layout_box in self.processed_nodes:
            return
            
        self.processed_nodes.add(layout_box)
        
        # Get box metrics
        x = layout_box.box_metrics.x
        y = layout_box.box_metrics.y
        width = layout_box.box_metrics.content_width
        height = layout_box.box_metrics.content_height
        
        # Convert any string dimensions to numbers
        if isinstance(width, str):
            width = int(float(width)) if width != 'auto' else self.viewport_width
        if isinstance(height, str):
            height = int(float(height)) if height != 'auto' else 0
            
        # Render background and borders if present
        if hasattr(layout_box, 'computed_style'):
            # Render background
            bg_color = layout_box.computed_style.get('background-color', '')
            if bg_color:
                bg = self.canvas.create_rectangle(
                    x, y, x + width, y + height,
                    fill=self._convert_color(bg_color),
                    outline=''
                )
                self.canvas_items.append(bg)
                
            # Render borders
            self._render_border(layout_box, x, y, width, height)
            
        # Render content based on element type
        if layout_box.element:
            tag_name = layout_box.element.tag_name.lower() if hasattr(layout_box.element, 'tag_name') else ''
            
            if tag_name == 'img':
                self._render_image(layout_box, x, y, width, height)
            elif tag_name == 'hr':
                self._render_horizontal_rule(layout_box, x, y, width, height)
            elif tag_name == 'a':
                self._make_link_clickable(layout_box, x, y, width, height)
            elif tag_name in {'input', 'button', 'textarea', 'select'}:
                self._render_form_element(layout_box, x, y, width, height)
            else:
                # Render text content for text-containing elements
                self._render_text_content(layout_box)
                
        # Recursively render children
        for child in layout_box.children:
            self._render_layout_tree(child)