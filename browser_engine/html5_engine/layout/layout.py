import re
import math
from typing import Dict, List, Optional, Tuple, Union

from .box_metrics import BoxMetrics

class LayoutBox:
    """
    Represents a box in the layout tree.
    
    Contains information about an element's layout, including position, size, and margins.
    """
    
    def __init__(self, element=None, display: str = 'block', parent=None):
        """
        Initialize a layout box.
        
        Args:
            element: The DOM element
            display: Initial display property
            parent: Parent layout box
        """
        self.element = element
        self.parent = parent
        self.children: List['LayoutBox'] = []
        self.computed_style: Dict[str, str] = {}
        self.display = display
        self.box_metrics = BoxMetrics()
        
        # Set default display based on element tag if present
        if element and hasattr(element, 'tag_name'):
            # Block elements
            if element.tag_name.lower() in ('div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                         'ul', 'ol', 'li', 'table', 'tr', 'td', 'th',
                                         'form', 'fieldset', 'hr', 'pre', 'blockquote',
                                         'article', 'section', 'header', 'footer', 'nav', 'aside'):
                self.display = 'block'
            # Inline elements
            elif element.tag_name.lower() in ('span', 'a', 'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'del',
                                           'small', 'sub', 'sup', 'code', 'kbd', 'samp', 'var', 'cite', 'q', 'dfn',
                                           'abbr', 'time', 'mark', 'ruby', 'rt', 'rp', 'bdi', 'bdo', 'br', 'wbr'):
                self.display = 'inline'
            # Inline-block elements
            elif element.tag_name.lower() in ('img', 'input', 'button', 'textarea', 'select', 'label'):
                self.display = 'inline-block'
            # Default to inheriting from parent or block
            else:
                if parent:
                    self.display = parent.display
                else:
                    self.display = 'block'
    
    def add_child(self, child: 'LayoutBox') -> None:
        """
        Add a child layout box.
        
        Args:
            child: The child layout box to add
        """
        self.children.append(child)
        child.parent = self
    
    def compute_styles(self, parent_styles: Dict[str, str] = None) -> None:
        """
        Compute styles for this layout box and its children.
        
        Args:
            parent_styles: Inherited styles from parent element
        """
        if parent_styles is None:
            parent_styles = {}
        
        # Inherit parent styles for relevant properties
        inherited_properties = [
            'color', 'font-family', 'font-size', 'font-weight', 'line-height',
            'text-align', 'text-indent', 'visibility'
        ]
        
        self.computed_style = {}
        
        # Inherit styles from parent
        for prop in inherited_properties:
            if prop in parent_styles:
                self.computed_style[prop] = parent_styles[prop]
        
        # Apply element's own styles if it has any
        if self.element and hasattr(self.element, 'style'):
            for prop, value in self.element.style.items():
                self.computed_style[prop] = value
        
        # Update display property from computed styles
        if 'display' in self.computed_style:
            self.display = self.computed_style['display']
        
        # Compute box metrics based on styles
        self._compute_box_metrics()
        
        # Recursively compute styles for children
        for child in self.children:
            child.compute_styles(self.computed_style)
    
    def _compute_box_metrics(self) -> None:
        """
        Compute box metrics based on computed styles.
        """
        # Default values
        self.box_metrics.width = self._parse_dimension_value(self.computed_style.get('width', 'auto'))
        self.box_metrics.height = self._parse_dimension_value(self.computed_style.get('height', 'auto'))
        
        # Parse margin properties
        self.box_metrics.margin_top = self._parse_dimension_value(self.computed_style.get('margin-top', '0'))
        self.box_metrics.margin_right = self._parse_dimension_value(self.computed_style.get('margin-right', '0'))
        self.box_metrics.margin_bottom = self._parse_dimension_value(self.computed_style.get('margin-bottom', '0'))
        self.box_metrics.margin_left = self._parse_dimension_value(self.computed_style.get('margin-left', '0'))
        
        # Parse padding properties
        self.box_metrics.padding_top = self._parse_dimension_value(self.computed_style.get('padding-top', '0'))
        self.box_metrics.padding_right = self._parse_dimension_value(self.computed_style.get('padding-right', '0'))
        self.box_metrics.padding_bottom = self._parse_dimension_value(self.computed_style.get('padding-bottom', '0'))
        self.box_metrics.padding_left = self._parse_dimension_value(self.computed_style.get('padding-left', '0'))
        
        # Parse border properties
        self.box_metrics.border_top_width = self._parse_dimension_value(self.computed_style.get('border-top-width', '0'))
        self.box_metrics.border_right_width = self._parse_dimension_value(self.computed_style.get('border-right-width', '0'))
        self.box_metrics.border_bottom_width = self._parse_dimension_value(self.computed_style.get('border-bottom-width', '0'))
        self.box_metrics.border_left_width = self._parse_dimension_value(self.computed_style.get('border-left-width', '0'))
        
        # If there's a border shorthand, parse it
        if 'border-width' in self.computed_style:
            width = self._parse_dimension_value(self.computed_style.get('border-width', '0'))
            self.box_metrics.border_top_width = width
            self.box_metrics.border_right_width = width
            self.box_metrics.border_bottom_width = width
            self.box_metrics.border_left_width = width
        
        # If there's a border shorthand, it takes precedence
        if 'border' in self.computed_style:
            # Extract border width from the shorthand (simplified approach)
            border_value = self.computed_style['border']
            match = re.search(r'(\d+)(px|em|rem|%)?', border_value)
            if match:
                border_width = int(match.group(1))
                self.box_metrics.border_top_width = border_width
                self.box_metrics.border_right_width = border_width
                self.box_metrics.border_bottom_width = border_width
                self.box_metrics.border_left_width = border_width
        
        # Compute content dimensions
        if self.box_metrics.width != 'auto':
            self.box_metrics.content_width = self.box_metrics.width
        else:
            # For now, default to auto width handling during layout
            self.box_metrics.content_width = 'auto'
        
        if self.box_metrics.height != 'auto':
            self.box_metrics.content_height = self.box_metrics.height
        else:
            # For now, default to auto height handling during layout
            self.box_metrics.content_height = 'auto'
        
        # Update box dimensions
        self._update_box_dimensions()
    
    def _update_box_dimensions(self) -> None:
        """
        Update box dimensions based on content, padding, border, and margin.
        """
        # Padding box dimensions
        if self.box_metrics.content_width != 'auto':
            self.box_metrics.padding_box_width = (
                self.box_metrics.content_width + 
                self.box_metrics.padding_left + 
                self.box_metrics.padding_right
            )
        else:
            self.box_metrics.padding_box_width = 'auto'
            
        if self.box_metrics.content_height != 'auto':
            self.box_metrics.padding_box_height = (
                self.box_metrics.content_height + 
                self.box_metrics.padding_top + 
                self.box_metrics.padding_bottom
            )
        else:
            self.box_metrics.padding_box_height = 'auto'
        
        # Border box dimensions
        if self.box_metrics.padding_box_width != 'auto':
            self.box_metrics.border_box_width = (
                self.box_metrics.padding_box_width + 
                self.box_metrics.border_left_width + 
                self.box_metrics.border_right_width
            )
        else:
            self.box_metrics.border_box_width = 'auto'
            
        if self.box_metrics.padding_box_height != 'auto':
            self.box_metrics.border_box_height = (
                self.box_metrics.padding_box_height + 
                self.box_metrics.border_top_width + 
                self.box_metrics.border_bottom_width
            )
        else:
            self.box_metrics.border_box_height = 'auto'
        
        # Margin box dimensions
        if self.box_metrics.border_box_width != 'auto':
            self.box_metrics.margin_box_width = (
                self.box_metrics.border_box_width + 
                self.box_metrics.margin_left + 
                self.box_metrics.margin_right
            )
        else:
            self.box_metrics.margin_box_width = 'auto'
            
        if self.box_metrics.border_box_height != 'auto':
            self.box_metrics.margin_box_height = (
                self.box_metrics.border_box_height + 
                self.box_metrics.margin_top + 
                self.box_metrics.margin_bottom
            )
        else:
            self.box_metrics.margin_box_height = 'auto'
    
    def _parse_dimension_value(self, value: str) -> Union[int, str]:
        """
        Parse a CSS dimension value.
        
        Args:
            value: CSS dimension value (e.g., "10px", "50%", "auto")
            
        Returns:
            Integer pixel value or 'auto'
        """
        if not value or value == 'auto':
            return 'auto'
        
        # Handle percentage values - for now just return as pixels (would need context to calculate properly)
        if value.endswith('%'):
            try:
                # Default to a percentage of an assumed container width of 800px
                return int(float(value[:-1]) * 8)  # 1% = 8px (of 800px)
            except ValueError:
                return 0
        
        # Handle pixel values
        if value.endswith('px'):
            try:
                return int(float(value[:-2]))
            except ValueError:
                return 0
        
        # Handle em values - assume 1em = 16px
        if value.endswith('em'):
            try:
                return int(float(value[:-2]) * 16)
            except ValueError:
                return 0
        
        # Handle rem values - assume 1rem = 16px
        if value.endswith('rem'):
            try:
                return int(float(value[:-3]) * 16)
            except ValueError:
                return 0
        
        # Handle unitless values as pixels
        try:
            return int(float(value))
        except ValueError:
            return 0
    
    def layout(self, container_width: int, x: int = 0, y: int = 0) -> None:
        """
        Perform layout calculations for this box and its children.
        
        Args:
            container_width: Width of the containing block
            x: Initial x position
            y: Initial y position
        """
        # Set initial position
        self.box_metrics.x = x
        self.box_metrics.y = y
        
        # Handle positioning
        position = self.computed_style.get('position', 'static')
        
        if position == 'relative':
            # Apply relative offsets if specified
            left = self._parse_dimension_value(self.computed_style.get('left', '0'))
            right = self._parse_dimension_value(self.computed_style.get('right', '0'))
            top = self._parse_dimension_value(self.computed_style.get('top', '0'))
            bottom = self._parse_dimension_value(self.computed_style.get('bottom', '0'))
            
            if left != 'auto':
                self.box_metrics.x += left
            elif right != 'auto':
                # Only apply right if left is not specified
                self.box_metrics.x -= right
            
            if top != 'auto':
                self.box_metrics.y += top
            elif bottom != 'auto':
                # Only apply bottom if top is not specified
                self.box_metrics.y -= bottom
        
        # Compute content dimensions
        self._calculate_width(container_width)
        
        # Handle different display types
        if self.display == 'inline':
            self._layout_inline(container_width)
        elif self.display == 'inline-block':
            self._layout_inline_block(container_width)
        elif self.display == 'flex':
            self._layout_flex(container_width)
        else:  # Default to block
            self._layout_block(container_width)
        
        # Calculate height based on content and specified height
        self._calculate_height()
    
    def _calculate_width(self, container_width: int) -> None:
        """
        Calculate the width of this box based on CSS properties and container width.
        
        Args:
            container_width: Width of the containing block
        """
        # Handle width based on display type
        if self.display == 'block' or self.display == 'flex':
            if self.box_metrics.content_width == 'auto':
                # For block elements, default to full width of container minus margins
                total_margin = self.box_metrics.margin_left + self.box_metrics.margin_right
                total_padding = self.box_metrics.padding_left + self.box_metrics.padding_right
                total_border = self.box_metrics.border_left_width + self.box_metrics.border_right_width
                
                # Content width fills available space
                self.box_metrics.content_width = container_width - total_margin - total_padding - total_border
        
        elif self.display == 'inline' or self.display == 'inline-block':
            if self.box_metrics.content_width == 'auto':
                # For inline elements, content determines width
                # For simplicity, use a default width based on content
                if self.element and hasattr(self.element, 'text_content') and self.element.text_content:
                    # Approximate width based on text length (very simple approach)
                    text_length = len(self.element.text_content)
                    font_size = self._parse_dimension_value(self.computed_style.get('font-size', '16px'))
                    # Rough estimate: each character is about 0.6 times the font size width
                    self.box_metrics.content_width = int(text_length * font_size * 0.6)
                else:
                    # Default minimum width for empty inline elements
                    self.box_metrics.content_width = 10
        
        # Update box dimensions after calculating content width
        self._update_box_dimensions()
    
    def _calculate_height(self) -> None:
        """
        Calculate the height of this box based on CSS properties and content.
        """
        if self.box_metrics.content_height == 'auto':
            # Calculate height based on children
            if self.children:
                max_child_bottom = 0
                
                for child in self.children:
                    child_bottom = child.box_metrics.y + child.box_metrics.margin_box_height
                    max_child_bottom = max(max_child_bottom, child_bottom)
                
                # Content height is the distance from the top of the content box to the bottom of the last child
                content_top = self.box_metrics.y + self.box_metrics.margin_top + self.box_metrics.border_top_width + self.box_metrics.padding_top
                self.box_metrics.content_height = max(0, max_child_bottom - content_top)
            else:
                # For elements with text content but no children
                if self.element and hasattr(self.element, 'text_content') and self.element.text_content:
                    # Approximate height based on text content and line height
                    font_size = self._parse_dimension_value(self.computed_style.get('font-size', '16px'))
                    line_height_value = self.computed_style.get('line-height', '1.2')
                    
                    try:
                        line_height_multiplier = float(line_height_value)
                    except ValueError:
                        # If line-height has units, parse it as a dimension
                        line_height = self._parse_dimension_value(line_height_value)
                        if line_height == 'auto':
                            line_height = int(font_size * 1.2)  # Default
                    else:
                        line_height = int(font_size * line_height_multiplier)
                    
                    # Calculate how many lines the text might need
                    if self.box_metrics.content_width != 'auto' and self.box_metrics.content_width > 0:
                        # Rough estimate: each character is about 0.6 times the font size width
                        chars_per_line = int(self.box_metrics.content_width / (font_size * 0.6))
                        if chars_per_line < 1:
                            chars_per_line = 1
                        
                        text_length = len(self.element.text_content)
                        num_lines = max(1, math.ceil(text_length / chars_per_line))
                        
                        self.box_metrics.content_height = num_lines * line_height
                    else:
                        # Default to one line if we can't calculate width
                        self.box_metrics.content_height = line_height
                else:
                    # Empty element with no explicit height
                    self.box_metrics.content_height = 0
        
        # Update box dimensions after calculating content height
        self._update_box_dimensions()
    
    def _layout_block(self, container_width: int) -> None:
        """
        Perform layout for block elements.
        
        Args:
            container_width: Width of the containing block
        """
        # Current y position for laying out children
        current_y = self.box_metrics.y + self.box_metrics.margin_top + self.box_metrics.border_top_width + self.box_metrics.padding_top
        
        # Adjust x for content area
        content_x = self.box_metrics.x + self.box_metrics.margin_left + self.box_metrics.border_left_width + self.box_metrics.padding_left
        
        # Available width for children
        if self.box_metrics.content_width == 'auto':
            child_container_width = container_width - self.box_metrics.margin_left - self.box_metrics.margin_right
        else:
            child_container_width = self.box_metrics.content_width
        
        # Layout children
        for child in self.children:
            child.layout(child_container_width, content_x, current_y)
            
            # Move down for next child
            current_y += child.box_metrics.margin_box_height
    
    def _layout_inline(self, container_width: int) -> None:
        """
        Perform layout for inline elements.
        
        Args:
            container_width: Width of the containing block
        """
        # For now, inline elements don't affect their children's layout much
        # They will flow within their parent's content area
        
        # Current x position for laying out children
        content_x = self.box_metrics.x + self.box_metrics.margin_left + self.box_metrics.border_left_width + self.box_metrics.padding_left
        content_y = self.box_metrics.y + self.box_metrics.margin_top + self.box_metrics.border_top_width + self.box_metrics.padding_top
        
        # Layout children (simplified for now)
        for child in self.children:
            child.layout(container_width, content_x, content_y)
            
            # Move right for next child
            content_x += child.box_metrics.margin_box_width
    
    def _layout_inline_block(self, container_width: int) -> None:
        """
        Perform layout for inline-block elements.
        
        Args:
            container_width: Width of the containing block
        """
        # Inline-block is a hybrid: it flows inline but lays out its contents like a block
        
        # Adjust for content area
        content_x = self.box_metrics.x + self.box_metrics.margin_left + self.box_metrics.border_left_width + self.box_metrics.padding_left
        content_y = self.box_metrics.y + self.box_metrics.margin_top + self.box_metrics.border_top_width + self.box_metrics.padding_top
        
        # Available width for children
        if self.box_metrics.content_width == 'auto':
            # Default to a reasonable width if not specified
            child_container_width = 100  # A default value
            self.box_metrics.content_width = child_container_width
            self._update_box_dimensions()
        else:
            child_container_width = self.box_metrics.content_width
        
        # Current y within the content box
        current_y = content_y
        
        # Layout children
        for child in self.children:
            child.layout(child_container_width, content_x, current_y)
            
            # Move down for next child (block layout)
            current_y += child.box_metrics.margin_box_height
    
    def _layout_flex(self, container_width: int) -> None:
        """
        Perform layout for flex container elements.
        
        Args:
            container_width: Width of the containing block
        """
        # Get flex properties
        flex_direction = self.computed_style.get('flex-direction', 'row')
        justify_content = self.computed_style.get('justify-content', 'flex-start')
        align_items = self.computed_style.get('align-items', 'stretch')
        flex_wrap = self.computed_style.get('flex-wrap', 'nowrap')
        
        # Adjust for content area
        content_x = self.box_metrics.x + self.box_metrics.margin_left + self.box_metrics.border_left_width + self.box_metrics.padding_left
        content_y = self.box_metrics.y + self.box_metrics.margin_top + self.box_metrics.border_top_width + self.box_metrics.padding_top
        
        # Available width and height for children
        child_container_width = self.box_metrics.content_width
        
        # Current positions for layout
        current_x = content_x
        current_y = content_y
        
        # For row layout, calculate total flex grow factor and total width used
        if flex_direction == 'row':
            # First pass: layout children and collect flex information
            total_flex_grow = 0
            total_fixed_width = 0
            
            for child in self.children:
                # Get flex properties
                flex_grow = float(self.computed_style.get('flex-grow', '0'))
                
                # Layout child with temporary width
                child.layout(child_container_width, current_x, current_y)
                
                # Collect information for flexible sizing
                if 'flex-grow' in child.computed_style:
                    total_flex_grow += float(child.computed_style['flex-grow'])
                
                if child.box_metrics.content_width != 'auto':
                    total_fixed_width += child.box_metrics.margin_box_width
            
            # Calculate available space for flexible items
            available_space = max(0, child_container_width - total_fixed_width)
            
            # Second pass: adjust sizes and positions based on flex properties
            current_x = content_x
            
            for child in self.children:
                # Adjust width for flexible items
                if 'flex-grow' in child.computed_style and total_flex_grow > 0:
                    flex_grow = float(child.computed_style['flex-grow'])
                    flex_width = int(available_space * (flex_grow / total_flex_grow))
                    
                    if child.box_metrics.content_width == 'auto':
                        child.box_metrics.content_width = flex_width
                        child._update_box_dimensions()
                
                # Position child
                child.box_metrics.x = current_x
                
                # Move to next position
                current_x += child.box_metrics.margin_box_width
        
        elif flex_direction == 'column':
            # Similar logic for column layout
            # First pass: layout children and collect flex information
            total_flex_grow = 0
            total_fixed_height = 0
            
            for child in self.children:
                # Layout child with temporary height
                child.layout(child_container_width, current_x, current_y)
                
                # Collect information for flexible sizing
                if 'flex-grow' in child.computed_style:
                    total_flex_grow += float(child.computed_style['flex-grow'])
                
                if child.box_metrics.content_height != 'auto':
                    total_fixed_height += child.box_metrics.margin_box_height
            
            # For now, we don't know the container height, so we can't calculate available space accurately
            # In a real implementation, we would need to handle this better
            
            # Second pass: just position children
            current_y = content_y
            
            for child in self.children:
                # Position child
                child.box_metrics.x = content_x
                child.box_metrics.y = current_y
                
                # Move to next position
                current_y += child.box_metrics.margin_box_height 