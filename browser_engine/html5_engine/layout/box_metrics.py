from typing import Union

class BoxMetrics:
    """
    Represents the CSS box model metrics for a layout box.
    
    Includes dimensions, margins, borders, and padding.
    """
    
    def __init__(self):
        # Position
        self.x: int = 0
        self.y: int = 0
        
        # Content dimensions
        self.width: Union[int, str] = 'auto'
        self.height: Union[int, str] = 'auto'
        self.content_width: Union[int, str] = 'auto'
        self.content_height: Union[int, str] = 'auto'
        
        # Padding
        self.padding_top: int = 0
        self.padding_right: int = 0
        self.padding_bottom: int = 0
        self.padding_left: int = 0
        
        # Border
        self.border_top_width: int = 0
        self.border_right_width: int = 0
        self.border_bottom_width: int = 0
        self.border_left_width: int = 0
        
        # Margin
        self.margin_top: int = 0
        self.margin_right: int = 0
        self.margin_bottom: int = 0
        self.margin_left: int = 0
        
        # Calculated box dimensions
        self.padding_box_width: Union[int, str] = 'auto'
        self.padding_box_height: Union[int, str] = 'auto'
        self.border_box_width: Union[int, str] = 'auto'
        self.border_box_height: Union[int, str] = 'auto'
        self.margin_box_width: Union[int, str] = 'auto'
        self.margin_box_height: Union[int, str] = 'auto' 