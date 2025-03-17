"""
Attr implementation for the DOM.
This module implements the DOM Attr interface according to HTML5 specifications.
"""

from typing import Optional

class Attr:
    """
    Attribute node implementation for the DOM.
    
    This class represents an attribute of an Element node.
    """
    
    def __init__(self, name: str, value: str, owner_element: Optional['Element'] = None):
        """
        Initialize a new attribute.
        
        Args:
            name: The attribute name
            value: The attribute value
            owner_element: The element that owns this attribute
        """
        self.name = name.lower()
        self.value = value
        self.owner_element = owner_element
        
        # HTML5 namespace support
        self.namespace_uri: Optional[str] = None
        self.prefix: Optional[str] = None
        self.local_name = self.name
        
        # Handle namespaced attributes
        if ':' in name:
            self.prefix, self.local_name = name.split(':', 1)
            
            # Set namespace URI based on prefix
            if self.prefix == 'xml':
                self.namespace_uri = 'http://www.w3.org/XML/1998/namespace'
            elif self.prefix == 'xlink':
                self.namespace_uri = 'http://www.w3.org/1999/xlink'
            elif self.prefix == 'xmlns' or name == 'xmlns':
                self.namespace_uri = 'http://www.w3.org/2000/xmlns/'
    
    @property
    def specified(self) -> bool:
        """
        Check if the attribute was explicitly specified.
        
        Returns:
            Always True for HTML5 (legacy property)
        """
        return True  # Always true in HTML5
    
    def clone(self) -> 'Attr':
        """
        Clone this attribute.
        
        Returns:
            A new Attr instance with the same name and value
        """
        attr = Attr(self.name, self.value)
        attr.namespace_uri = self.namespace_uri
        attr.prefix = self.prefix
        attr.local_name = self.local_name
        return attr 