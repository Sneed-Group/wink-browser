"""
CSS Layout Engine implementation.
This module handles layout calculations for HTML elements based on the CSS box model.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from enum import Enum

from ..dom import Element, Document

logger = logging.getLogger(__name__)

class DisplayType(Enum):
    """CSS display property values."""
    BLOCK = "block"
    INLINE = "inline"
    INLINE_BLOCK = "inline-block"
    FLEX = "flex"
    GRID = "grid"
    NONE = "none"
    TABLE = "table"
    TABLE_ROW = "table-row"
    TABLE_CELL = "table-cell"

class PositionType(Enum):
    """CSS position property values."""
    STATIC = "static"
    RELATIVE = "relative"
    ABSOLUTE = "absolute"
    FIXED = "fixed"
    STICKY = "sticky"

class FloatType(Enum):
    """CSS float property values."""
    NONE = "none"
    LEFT = "left"
    RIGHT = "right"

class BoxMetrics:
    """
    Container for box model metrics.
    
    Stores measurements for content box, padding, border, and margin.
    """
    
    def __init__(self):
        """Initialize box metrics with default values."""
        # Content box dimensions
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        
        # Padding (top, right, bottom, left)
        self.padding_top: int = 0
        self.padding_right: int = 0
        self.padding_bottom: int = 0
        self.padding_left: int = 0
        
        # Border (top, right, bottom, left)
        self.border_top_width: int = 0
        self.border_right_width: int = 0
        self.border_bottom_width: int = 0
        self.border_left_width: int = 0
        
        # Margin (top, right, bottom, left)
        self.margin_top: int = 0
        self.margin_right: int = 0
        self.margin_bottom: int = 0
        self.margin_left: int = 0
        
        # Position coordinates
        self.x: int = 0
        self.y: int = 0
    
    @property
    def padding_box_width(self) -> int:
        """Get the width of the padding box."""
        if self.width is None:
            return 0
        return self.width + self.padding_left + self.padding_right
    
    @property
    def padding_box_height(self) -> int:
        """Get the height of the padding box."""
        if self.height is None:
            return 0
        return self.height + self.padding_top + self.padding_bottom
    
    @property
    def border_box_width(self) -> int:
        """Get the width of the border box."""
        return self.padding_box_width + self.border_left_width + self.border_right_width
    
    @property
    def border_box_height(self) -> int:
        """Get the height of the border box."""
        return self.padding_box_height + self.border_top_width + self.border_bottom_width
    
    @property
    def margin_box_width(self) -> int:
        """Get the width of the margin box."""
        return self.border_box_width + self.margin_left + self.margin_right
    
    @property
    def margin_box_height(self) -> int:
        """Get the height of the margin box."""
        return self.border_box_height + self.margin_top + self.margin_bottom

class LayoutBox:
    """
    Layout box for an element.
    
    Stores layout information for a DOM element.
    """
    
    def __init__(self, element: Optional[Element] = None):
        """
        Initialize a layout box for an element.
        
        Args:
            element: The DOM element to create a layout box for
        """
        self.element = element
        self.box_metrics = BoxMetrics()
        
        # Layout properties
        self.display: DisplayType = DisplayType.BLOCK
        self.position: PositionType = PositionType.STATIC
        self.float_type: FloatType = FloatType.NONE
        
        # Computed style
        self.computed_style: Dict[str, str] = {}
        
        # Child layout boxes
        self.children: List[LayoutBox] = []
        
        # Parent layout box
        self.parent: Optional[LayoutBox] = None
    
    def add_child(self, child: 'LayoutBox') -> None:
        """
        Add a child layout box.
        
        Args:
            child: The child layout box to add
        """
        self.children.append(child)
        child.parent = self

class LayoutEngine:
    """
    CSS Layout Engine.
    
    This class calculates layout for HTML elements based on CSS rules.
    """
    
    def __init__(self):
        """Initialize the layout engine."""
        logger.debug("Layout Engine initialized")
    
    def create_layout_tree(self, document: Document) -> LayoutBox:
        """
        Create a layout tree for a document.
        
        Args:
            document: The document to create a layout tree for
            
        Returns:
            The root layout box
        """
        if not document.document_element:
            # Create an empty root box
            return LayoutBox()
        
        # Create the root layout box
        root_box = self._create_layout_box(document.document_element)
        
        # Process the document tree
        self._build_layout_tree(document.document_element, root_box)
        
        return root_box
    
    def _build_layout_tree(self, element: Element, parent_box: LayoutBox) -> None:
        """
        Recursively build a layout tree from a DOM tree.
        
        Args:
            element: The current DOM element
            parent_box: The parent layout box
        """
        # Process each child element
        for child in element.children:
            # Skip elements with display:none
            if self._has_display_none(child):
                continue
            
            # Create a layout box for the child
            child_box = self._create_layout_box(child)
            
            # Add to parent
            parent_box.add_child(child_box)
            
            # Process the child's children
            self._build_layout_tree(child, child_box)
    
    def _create_layout_box(self, element: Element) -> LayoutBox:
        """
        Create a layout box for an element.
        
        Args:
            element: The DOM element
            
        Returns:
            The created layout box
        """
        box = LayoutBox(element)
        
        # Get computed style
        computed_style = self._get_computed_style(element)
        box.computed_style = computed_style
        
        # Set display type
        display_value = computed_style.get('display', 'block').lower()
        try:
            box.display = DisplayType(display_value)
        except ValueError:
            box.display = DisplayType.BLOCK
        
        # Set position type
        position_value = computed_style.get('position', 'static').lower()
        try:
            box.position = PositionType(position_value)
        except ValueError:
            box.position = PositionType.STATIC
        
        # Set float type
        float_value = computed_style.get('float', 'none').lower()
        try:
            box.float_type = FloatType(float_value)
        except ValueError:
            box.float_type = FloatType.NONE
        
        # Apply box model properties
        self._apply_box_model(box, computed_style)
        
        return box
    
    def _get_computed_style(self, element: Element) -> Dict[str, str]:
        """
        Get the computed style for an element.
        
        Args:
            element: The DOM element
            
        Returns:
            Dictionary of computed style properties
        """
        # In a full implementation, this would use the CSS parser
        # to calculate the computed style based on the cascade.
        
        # For demo purposes, we'll extract inline styles and add defaults
        computed_style = self._get_default_styles(element)
        
        # Add inline styles (highest precedence)
        inline_styles = {}
        style_attr = element.get_attribute('style')
        if style_attr:
            inline_styles = self._parse_inline_styles(style_attr)
            
            for prop_name, prop_value in inline_styles.items():
                computed_style[prop_name] = prop_value
        
        return computed_style
    
    def _get_default_styles(self, element: Element) -> Dict[str, str]:
        """
        Get default styles based on element type.
        
        Args:
            element: The DOM element
            
        Returns:
            Dictionary of default style properties
        """
        tag_name = element.tag_name.lower()
        defaults = {
            'display': 'block',
            'margin-top': '0px',
            'margin-right': '0px',
            'margin-bottom': '0px',
            'margin-left': '0px',
            'padding-top': '0px',
            'padding-right': '0px',
            'padding-bottom': '0px',
            'padding-left': '0px',
            'border-top-width': '0px',
            'border-right-width': '0px',
            'border-bottom-width': '0px',
            'border-left-width': '0px',
            'position': 'static',
            'float': 'none',
        }
        
        # Add tag-specific defaults
        if tag_name == 'body':
            defaults.update({
                'margin-top': '8px',
                'margin-right': '8px',
                'margin-bottom': '8px',
                'margin-left': '8px',
            })
        elif tag_name in ('div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            defaults.update({
                'margin-top': '1em',
                'margin-bottom': '1em',
            })
        elif tag_name == 'span':
            defaults.update({
                'display': 'inline',
            })
        
        return defaults
    
    def _parse_inline_styles(self, style_attr: str) -> Dict[str, str]:
        """
        Parse an inline style attribute.
        
        Args:
            style_attr: Style attribute value
            
        Returns:
            Dictionary of style properties
        """
        style_dict = {}
        
        # Split the style attribute by semicolons
        declarations = [decl.strip() for decl in style_attr.split(';') if decl.strip()]
        
        for declaration in declarations:
            # Split each declaration into property and value
            parts = declaration.split(':', 1)
            if len(parts) == 2:
                property_name, value = parts
                style_dict[property_name.strip().lower()] = value.strip()
        
        return style_dict
    
    def _has_display_none(self, element: Element) -> bool:
        """
        Check if an element has display:none.
        
        Args:
            element: The DOM element
            
        Returns:
            True if the element has display:none, False otherwise
        """
        style_attr = element.get_attribute('style')
        if style_attr:
            inline_styles = self._parse_inline_styles(style_attr)
            if inline_styles.get('display', '').lower() == 'none':
                return True
        
        # In a full implementation, would check the computed style
        return False
    
    def _apply_box_model(self, box: LayoutBox, computed_style: Dict[str, str]) -> None:
        """
        Apply box model properties to a layout box.
        
        Args:
            box: The layout box to update
            computed_style: The computed style dictionary
        """
        # Apply width and height
        width_value = computed_style.get('width')
        if width_value and width_value != 'auto':
            box.box_metrics.width = self._parse_dimension(width_value)
        
        height_value = computed_style.get('height')
        if height_value and height_value != 'auto':
            box.box_metrics.height = self._parse_dimension(height_value)
        
        # Apply padding
        box.box_metrics.padding_top = self._parse_dimension(computed_style.get('padding-top', '0px'))
        box.box_metrics.padding_right = self._parse_dimension(computed_style.get('padding-right', '0px'))
        box.box_metrics.padding_bottom = self._parse_dimension(computed_style.get('padding-bottom', '0px'))
        box.box_metrics.padding_left = self._parse_dimension(computed_style.get('padding-left', '0px'))
        
        # Apply border widths
        box.box_metrics.border_top_width = self._parse_dimension(computed_style.get('border-top-width', '0px'))
        box.box_metrics.border_right_width = self._parse_dimension(computed_style.get('border-right-width', '0px'))
        box.box_metrics.border_bottom_width = self._parse_dimension(computed_style.get('border-bottom-width', '0px'))
        box.box_metrics.border_left_width = self._parse_dimension(computed_style.get('border-left-width', '0px'))
        
        # Apply margins
        box.box_metrics.margin_top = self._parse_dimension(computed_style.get('margin-top', '0px'))
        box.box_metrics.margin_right = self._parse_dimension(computed_style.get('margin-right', '0px'))
        box.box_metrics.margin_bottom = self._parse_dimension(computed_style.get('margin-bottom', '0px'))
        box.box_metrics.margin_left = self._parse_dimension(computed_style.get('margin-left', '0px'))
    
    def _parse_dimension(self, value: Optional[str]) -> int:
        """
        Parse a CSS dimension value to pixels.
        
        Args:
            value: CSS dimension value (e.g., '10px', '2em')
            
        Returns:
            Integer pixel value, or 0 if the value is None or cannot be parsed
        """
        if not value:
            return 0
        
        # Extract the numeric part and unit
        match = re.match(r'^([-+]?[0-9]*\.?[0-9]+)([a-z%]*)$', value)
        if not match:
            return 0
        
        number, unit = match.groups()
        
        try:
            number_value = float(number)
            
            # Handle different units
            if unit == 'px' or unit == '':
                return int(number_value)
            elif unit == 'em':
                # Simplified: 1em = 16px
                return int(number_value * 16)
            elif unit == 'rem':
                # Simplified: 1rem = 16px
                return int(number_value * 16)
            elif unit == '%':
                # Percentage requires context, default to 0
                # In a full implementation, this would be calculated based on parent
                return 0
            elif unit == 'pt':
                # 1pt = 1.333px (approximately)
                return int(number_value * 1.333)
            
            # Default for unknown units
            return int(number_value)
            
        except ValueError:
            return 0
    
    def layout(self, layout_box: LayoutBox, container_width: int, container_height: int) -> None:
        """
        Perform layout calculations on a layout tree.
        
        Args:
            layout_box: The root layout box
            container_width: Width of the containing viewport
            container_height: Height of the containing viewport
        """
        # Recursive layout algorithm
        self._calculate_layout(layout_box, container_width, container_height, 0, 0)
    
    def _calculate_layout(self, box: LayoutBox, container_width: int, container_height: int, 
                          start_x: int, start_y: int) -> Tuple[int, int]:
        """
        Calculate layout for a box and its children.
        
        Args:
            box: The layout box to calculate
            container_width: Width of the container
            container_height: Height of the container
            start_x: Starting X position
            start_y: Starting Y position
            
        Returns:
            Tuple of (width, height) of the laid out box
        """
        # Set initial position
        box.box_metrics.x = start_x
        box.box_metrics.y = start_y
        
        # Calculate width if not explicitly set
        if box.box_metrics.width is None:
            if box.display == DisplayType.BLOCK:
                # Block elements expand to fill container width
                content_width = container_width - box.box_metrics.margin_left - box.box_metrics.margin_right
                box.box_metrics.width = content_width - box.box_metrics.padding_left - box.box_metrics.padding_right - box.box_metrics.border_left_width - box.box_metrics.border_right_width
            else:
                # Inline elements size to content
                # For simplicity, we'll set a default width
                box.box_metrics.width = 100
        
        # Layout based on display type
        if box.display == DisplayType.BLOCK:
            return self._layout_block(box, container_width, container_height)
        elif box.display == DisplayType.INLINE:
            return self._layout_inline(box, container_width, container_height)
        elif box.display == DisplayType.FLEX:
            return self._layout_flex(box, container_width, container_height)
        else:
            # Default to block layout
            return self._layout_block(box, container_width, container_height)
    
    def _layout_block(self, box: LayoutBox, container_width: int, container_height: int) -> Tuple[int, int]:
        """
        Perform block layout for a box.
        
        Args:
            box: The layout box
            container_width: Width of the container
            container_height: Height of the container
            
        Returns:
            Tuple of (width, height) of the laid out box
        """
        # Current Y position for child layout
        current_y = box.box_metrics.padding_top
        max_width = box.box_metrics.width
        
        # Layout each child
        for child in box.children:
            # Calculate child position within parent
            child_x = box.box_metrics.padding_left
            
            # For positioned elements, adjust coordinates
            if child.position == PositionType.RELATIVE:
                # Apply relative offsets (in a full implementation)
                pass
            elif child.position in (PositionType.ABSOLUTE, PositionType.FIXED):
                # For absolute/fixed positioning, we'd calculate position differently
                # Simplified for demo purposes
                pass
            
            # Layout the child
            child_width, child_height = self._calculate_layout(
                child, 
                box.box_metrics.width, 
                container_height, 
                box.box_metrics.x + child_x, 
                box.box_metrics.y + current_y
            )
            
            # Update max width
            max_width = max(max_width, child_width)
            
            # Move down for next child
            current_y += child_height + child.box_metrics.margin_top + child.box_metrics.margin_bottom
        
        # Calculate height if not explicitly set
        if box.box_metrics.height is None:
            box.box_metrics.height = current_y
        
        return (box.box_metrics.border_box_width, box.box_metrics.border_box_height)
    
    def _layout_inline(self, box: LayoutBox, container_width: int, container_height: int) -> Tuple[int, int]:
        """
        Perform inline layout for a box.
        
        Args:
            box: The layout box
            container_width: Width of the container
            container_height: Height of the container
            
        Returns:
            Tuple of (width, height) of the laid out box
        """
        # Simplified inline layout - in a full implementation, this would handle text flow
        # Current X and Y positions for child layout
        current_x = box.box_metrics.padding_left
        current_y = box.box_metrics.padding_top
        line_height = 0
        
        for child in box.children:
            # Check if we need to wrap to next line
            if (current_x + child.box_metrics.margin_box_width > box.box_metrics.width):
                current_x = box.box_metrics.padding_left
                current_y += line_height
                line_height = 0
            
            # Layout the child
            child_width, child_height = self._calculate_layout(
                child, 
                box.box_metrics.width - current_x, 
                container_height, 
                box.box_metrics.x + current_x, 
                box.box_metrics.y + current_y
            )
            
            # Move right for next child
            current_x += child_width + child.box_metrics.margin_left + child.box_metrics.margin_right
            
            # Update line height
            line_height = max(line_height, child_height + child.box_metrics.margin_top + child.box_metrics.margin_bottom)
        
        # Calculate height if not explicitly set
        if box.box_metrics.height is None:
            box.box_metrics.height = current_y + line_height
        
        return (box.box_metrics.border_box_width, box.box_metrics.border_box_height)
    
    def _layout_flex(self, box: LayoutBox, container_width: int, container_height: int) -> Tuple[int, int]:
        """
        Perform flexbox layout for a box.
        
        Args:
            box: The layout box
            container_width: Width of the container
            container_height: Height of the container
            
        Returns:
            Tuple of (width, height) of the laid out box
        """
        # Simplified flex layout - in a full implementation, this would handle flex properties
        # Get flex direction
        flex_direction = box.computed_style.get('flex-direction', 'row')
        
        if flex_direction in ('row', 'row-reverse'):
            # Current X and Y positions for child layout
            current_x = box.box_metrics.padding_left
            current_y = box.box_metrics.padding_top
            max_height = 0
            
            # Determine layout direction
            children = box.children
            if flex_direction == 'row-reverse':
                children = list(reversed(children))
            
            for child in children:
                # Layout the child
                child_width, child_height = self._calculate_layout(
                    child, 
                    container_width, 
                    container_height, 
                    box.box_metrics.x + current_x, 
                    box.box_metrics.y + current_y
                )
                
                # Move right for next child
                current_x += child_width + child.box_metrics.margin_left + child.box_metrics.margin_right
                
                # Update max height
                max_height = max(max_height, child_height + child.box_metrics.margin_top + child.box_metrics.margin_bottom)
            
            # Calculate height if not explicitly set
            if box.box_metrics.height is None:
                box.box_metrics.height = max_height
                
        else:  # column or column-reverse
            # Current X and Y positions for child layout
            current_x = box.box_metrics.padding_left
            current_y = box.box_metrics.padding_top
            max_width = 0
            
            # Determine layout direction
            children = box.children
            if flex_direction == 'column-reverse':
                children = list(reversed(children))
            
            for child in children:
                # Layout the child
                child_width, child_height = self._calculate_layout(
                    child, 
                    container_width, 
                    container_height, 
                    box.box_metrics.x + current_x, 
                    box.box_metrics.y + current_y
                )
                
                # Move down for next child
                current_y += child_height + child.box_metrics.margin_top + child.box_metrics.margin_bottom
                
                # Update max width
                max_width = max(max_width, child_width + child.box_metrics.margin_left + child.box_metrics.margin_right)
            
            # Calculate width if not explicitly set
            if box.box_metrics.width is None:
                box.box_metrics.width = max_width
        
        return (box.box_metrics.border_box_width, box.box_metrics.border_box_height)
    
    def create_layout(self, document: Document, viewport_width: int, viewport_height: int) -> LayoutBox:
        """
        Create a layout for a document with the given viewport dimensions.
        
        Args:
            document: The document to create a layout for
            viewport_width: The width of the viewport
            viewport_height: The height of the viewport
            
        Returns:
            The root layout box with calculated layout
        """
        # Create the layout tree
        root_box = self.create_layout_tree(document)
        
        # Calculate layout
        self.layout(root_box, viewport_width, viewport_height)
        
        return root_box 