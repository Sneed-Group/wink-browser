"""
CSS Gradient parsing and rendering.
This module handles the parsing and rendering of CSS gradients.
"""

import re
import math
from typing import List, Tuple, Dict, Optional, Union

class GradientStop:
    """
    Represents a color stop in a gradient.
    """
    def __init__(self, color: str, position: Optional[Union[str, float]] = None):
        """
        Initialize a gradient stop.
        
        Args:
            color: The color value
            position: The position of the stop (percentage or length)
        """
        self.color = color
        self.position = position  # Either a percentage, length, or None

class Gradient:
    """
    Base class for CSS gradients.
    """
    def __init__(self, stops: List[GradientStop]):
        """
        Initialize a gradient.
        
        Args:
            stops: List of color stops
        """
        self.stops = stops
    
    def to_css(self) -> str:
        """
        Convert the gradient to a CSS string.
        
        Returns:
            CSS representation of the gradient
        """
        raise NotImplementedError("Subclasses must implement to_css")

class LinearGradient(Gradient):
    """
    Represents a CSS linear gradient.
    """
    def __init__(self, stops: List[GradientStop], angle: Optional[Union[str, float]] = None):
        """
        Initialize a linear gradient.
        
        Args:
            stops: List of color stops
            angle: The angle of the gradient (degrees or keyword)
        """
        super().__init__(stops)
        self.angle = angle or '180deg'  # Default is top to bottom
    
    def to_css(self) -> str:
        """
        Convert the linear gradient to a CSS string.
        
        Returns:
            CSS representation of the linear gradient
        """
        stops_str = ", ".join([
            f"{stop.color}" + (f" {stop.position}" if stop.position else "")
            for stop in self.stops
        ])
        
        return f"linear-gradient({self.angle}, {stops_str})"

class RadialGradient(Gradient):
    """
    Represents a CSS radial gradient.
    """
    def __init__(self, 
                 stops: List[GradientStop], 
                 shape: str = 'ellipse', 
                 size: str = 'farthest-corner',
                 position_x: str = 'center',
                 position_y: str = 'center'):
        """
        Initialize a radial gradient.
        
        Args:
            stops: List of color stops
            shape: The shape of the gradient ('circle' or 'ellipse')
            size: The size keyword
            position_x: The x position
            position_y: The y position
        """
        super().__init__(stops)
        self.shape = shape
        self.size = size
        self.position_x = position_x
        self.position_y = position_y
    
    def to_css(self) -> str:
        """
        Convert the radial gradient to a CSS string.
        
        Returns:
            CSS representation of the radial gradient
        """
        position = f"at {self.position_x} {self.position_y}"
        shape_size = f"{self.shape} {self.size}"
        
        stops_str = ", ".join([
            f"{stop.color}" + (f" {stop.position}" if stop.position else "")
            for stop in self.stops
        ])
        
        return f"radial-gradient({shape_size} {position}, {stops_str})"

class GradientParser:
    """
    Parser for CSS gradients.
    """
    def __init__(self):
        """Initialize the gradient parser."""
        pass
    
    def parse(self, gradient_str: str) -> Optional[Gradient]:
        """
        Parse a CSS gradient string.
        
        Args:
            gradient_str: The gradient string to parse
            
        Returns:
            Parsed Gradient object or None if invalid
        """
        if not gradient_str:
            return None
        
        gradient_str = gradient_str.strip()
        
        # Check for linear gradient
        linear_match = re.match(r'^linear-gradient\((.*)\)$', gradient_str)
        if linear_match:
            return self._parse_linear_gradient(linear_match.group(1))
        
        # Check for radial gradient
        radial_match = re.match(r'^radial-gradient\((.*)\)$', gradient_str)
        if radial_match:
            return self._parse_radial_gradient(radial_match.group(1))
        
        return None
    
    def _parse_linear_gradient(self, params_str: str) -> Optional[LinearGradient]:
        """
        Parse a linear gradient parameters string.
        
        Args:
            params_str: The parameters string
            
        Returns:
            LinearGradient object or None if invalid
        """
        parts = self._split_gradient_params(params_str)
        if not parts:
            return None
        
        # Check for angle/direction
        angle = None
        if parts[0].endswith('deg') or parts[0] in ('to top', 'to right', 'to bottom', 'to left', 
                                                   'to top right', 'to top left', 
                                                   'to bottom right', 'to bottom left'):
            angle = parts[0]
            parts = parts[1:]
        
        # Parse color stops
        stops = []
        for part in parts:
            stop = self._parse_color_stop(part)
            if stop:
                stops.append(stop)
        
        if not stops:
            return None
        
        return LinearGradient(stops, angle)
    
    def _parse_radial_gradient(self, params_str: str) -> Optional[RadialGradient]:
        """
        Parse a radial gradient parameters string.
        
        Args:
            params_str: The parameters string
            
        Returns:
            RadialGradient object or None if invalid
        """
        parts = self._split_gradient_params(params_str)
        if not parts:
            return None
        
        # Default values
        shape = 'ellipse'
        size = 'farthest-corner'
        position_x = 'center'
        position_y = 'center'
        
        # Parse shape and size if specified
        first_part = parts[0].lower()
        shape_match = re.search(r'\b(circle|ellipse)\b', first_part)
        if shape_match:
            shape = shape_match.group(1)
        
        size_keywords = ('closest-side', 'closest-corner', 'farthest-side', 'farthest-corner')
        for keyword in size_keywords:
            if keyword in first_part:
                size = keyword
                break
        
        # Check for position
        if 'at ' in first_part:
            pos_parts = first_part.split('at ')[1].split()
            if len(pos_parts) >= 1:
                position_x = pos_parts[0]
            if len(pos_parts) >= 2:
                position_y = pos_parts[1]
        
        # If the first part has shape/size/position, skip it for color stops
        color_parts = parts[1:] if (shape_match or any(k in first_part for k in size_keywords) or 'at ' in first_part) else parts
        
        # Parse color stops
        stops = []
        for part in color_parts:
            stop = self._parse_color_stop(part)
            if stop:
                stops.append(stop)
        
        if not stops:
            return None
        
        return RadialGradient(stops, shape, size, position_x, position_y)
    
    def _parse_color_stop(self, stop_str: str) -> Optional[GradientStop]:
        """
        Parse a color stop string.
        
        Args:
            stop_str: The color stop string
            
        Returns:
            GradientStop object or None if invalid
        """
        stop_str = stop_str.strip()
        
        # Simple case: just a color
        if re.match(r'^#[0-9a-fA-F]{3,6}$', stop_str) or stop_str in ('transparent', 'currentColor'):
            return GradientStop(stop_str)
        
        # Color with position
        color_pos_match = re.match(r'^(.*?)\s+(\d+%|\d+px|\d+em|\d+rem)$', stop_str)
        if color_pos_match:
            color = color_pos_match.group(1).strip()
            position = color_pos_match.group(2).strip()
            return GradientStop(color, position)
        
        # Function-based colors
        if stop_str.startswith('rgb(') or stop_str.startswith('rgba(') or stop_str.startswith('hsl(') or stop_str.startswith('hsla('):
            # Find the end of the color function
            end_idx = stop_str.find(')')
            if end_idx >= 0:
                color = stop_str[:end_idx+1].strip()
                rest = stop_str[end_idx+1:].strip()
                
                if rest:
                    # There's a position after the color
                    position = rest
                    return GradientStop(color, position)
                else:
                    # Just the color
                    return GradientStop(color)
        
        # If we can't parse it, assume it's a named color
        return GradientStop(stop_str)
    
    def _split_gradient_params(self, params_str: str) -> List[str]:
        """
        Split gradient parameters by comma, properly handling nested functions.
        
        Args:
            params_str: The parameters string
            
        Returns:
            List of parameter parts
        """
        if not params_str:
            return []
        
        result = []
        current = ''
        paren_level = 0
        
        for char in params_str:
            if char == ',' and paren_level == 0:
                result.append(current.strip())
                current = ''
            else:
                current += char
                if char == '(':
                    paren_level += 1
                elif char == ')':
                    paren_level -= 1
        
        if current:
            result.append(current.strip())
        
        return result

def render_gradient(gradient: Gradient, width: int, height: int) -> List[Tuple[int, int, int, int]]:
    """
    Render a gradient to a list of RGBA pixels.
    
    Args:
        gradient: The gradient to render
        width: The width of the output image
        height: The height of the output image
        
    Returns:
        List of RGBA tuples for each pixel
    """
    # This is a simplified implementation
    # A real implementation would properly handle all gradient types and parameters
    
    pixels = []
    
    if isinstance(gradient, LinearGradient):
        # Simplified: render a top-to-bottom gradient
        for y in range(height):
            # Calculate the position in the gradient (0 to 1)
            pos = y / height
            
            # Find the color at this position
            color = _interpolate_gradient_color(gradient.stops, pos)
            
            # Add pixels for this row
            pixels.extend([color] * width)
    
    elif isinstance(gradient, RadialGradient):
        # Simplified: render a centered radial gradient
        center_x = width / 2
        center_y = height / 2
        max_dist = math.sqrt(center_x**2 + center_y**2)
        
        for y in range(height):
            for x in range(width):
                # Calculate distance from center (0 to 1)
                dx = x - center_x
                dy = y - center_y
                dist = math.sqrt(dx**2 + dy**2) / max_dist
                
                # Find the color at this position
                color = _interpolate_gradient_color(gradient.stops, dist)
                
                # Add pixel
                pixels.append(color)
    
    return pixels

def _interpolate_gradient_color(stops: List[GradientStop], position: float) -> Tuple[int, int, int, int]:
    """
    Interpolate a color for a given position in the gradient.
    
    Args:
        stops: List of gradient stops
        position: Position in the gradient (0 to 1)
        
    Returns:
        RGBA color tuple
    """
    # This is a simplified implementation
    # A real implementation would properly handle color spaces and handle stops with explicit positions
    
    # Default colors at endpoints if no stops
    if not stops:
        return (0, 0, 0, 255)  # Black
    
    # If only one stop, use its color throughout
    if len(stops) == 1:
        return _parse_color_to_rgba(stops[0].color)
    
    # Find the stops to interpolate between
    for i in range(len(stops) - 1):
        # Determine stop positions (simplified: assume equally spaced)
        stop1_pos = i / (len(stops) - 1)
        stop2_pos = (i + 1) / (len(stops) - 1)
        
        if position <= stop2_pos:
            # Found the stops to interpolate between
            color1 = _parse_color_to_rgba(stops[i].color)
            color2 = _parse_color_to_rgba(stops[i + 1].color)
            
            # Calculate interpolation factor
            if stop2_pos == stop1_pos:  # Avoid division by zero
                factor = 0
            else:
                factor = (position - stop1_pos) / (stop2_pos - stop1_pos)
            
            # Interpolate each color component
            r = int(color1[0] + factor * (color2[0] - color1[0]))
            g = int(color1[1] + factor * (color2[1] - color1[1]))
            b = int(color1[2] + factor * (color2[2] - color1[2]))
            a = int(color1[3] + factor * (color2[3] - color1[3]))
            
            return (r, g, b, a)
    
    # If position is beyond the last stop, use the last stop's color
    return _parse_color_to_rgba(stops[-1].color)

def _parse_color_to_rgba(color: str) -> Tuple[int, int, int, int]:
    """
    Parse a CSS color string to an RGBA tuple.
    
    Args:
        color: CSS color string
        
    Returns:
        RGBA tuple
    """
    # This is a simplified implementation
    # A real implementation would handle all CSS color formats
    
    # Default to black if parsing fails
    default = (0, 0, 0, 255)
    
    # Handle hex colors
    if color.startswith('#'):
        if len(color) == 4:  # #RGB
            r = int(color[1] + color[1], 16)
            g = int(color[2] + color[2], 16)
            b = int(color[3] + color[3], 16)
            return (r, g, b, 255)
        elif len(color) == 7:  # #RRGGBB
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            return (r, g, b, 255)
    
    # Handle rgb/rgba
    rgb_match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color)
    if rgb_match:
        r = min(255, max(0, int(rgb_match.group(1))))
        g = min(255, max(0, int(rgb_match.group(2))))
        b = min(255, max(0, int(rgb_match.group(3))))
        return (r, g, b, 255)
    
    rgba_match = re.match(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)', color)
    if rgba_match:
        r = min(255, max(0, int(rgba_match.group(1))))
        g = min(255, max(0, int(rgba_match.group(2))))
        b = min(255, max(0, int(rgba_match.group(3))))
        a = min(255, max(0, int(float(rgba_match.group(4)) * 255)))
        return (r, g, b, a)
    
    # Handle named colors (simplified)
    named_colors = {
        'black': (0, 0, 0, 255),
        'white': (255, 255, 255, 255),
        'red': (255, 0, 0, 255),
        'green': (0, 128, 0, 255),
        'blue': (0, 0, 255, 255),
        'yellow': (255, 255, 0, 255),
        'purple': (128, 0, 128, 255),
        'orange': (255, 165, 0, 255),
        'gray': (128, 128, 128, 255),
        'transparent': (0, 0, 0, 0),
    }
    
    return named_colors.get(color.lower(), default) 