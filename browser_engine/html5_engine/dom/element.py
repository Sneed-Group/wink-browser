"""
Element implementation for the DOM.
This module implements the DOM Element interface according to HTML5 specifications.
"""

from typing import Dict, List, Optional, Any, Union, Set
import re
from .node import Node, NodeType
from .attr import Attr

class Element(Node):
    """
    Element node implementation for the DOM.
    
    This class implements HTML elements with full HTML5 support.
    """
    
    def __init__(self, 
                tag_name: str, 
                namespace: Optional[str] = None,
                owner_document: Optional['Document'] = None):
        """
        Initialize a new Element.
        
        Args:
            tag_name: Name of the element tag (e.g., "div", "span")
            namespace: Optional namespace URI
            owner_document: The document that owns this element
        """
        super().__init__(NodeType.ELEMENT_NODE, owner_document)
        
        self.tag_name = tag_name.lower()
        self.namespace_uri = namespace
        self.node_name = tag_name.upper() if namespace is None else tag_name
        
        # Element attributes
        self.attributes: Dict[str, Attr] = {}
        
        # Element style
        self._style: Dict[str, str] = {}
        self._computed_style: Dict[str, str] = {}
        
        # Element class list
        self._class_list: Set[str] = set()
        
        # Element dataset (data-* attributes)
        self._dataset: Dict[str, str] = {}
        
        # Flag for whether this is a void element (self-closing)
        self.is_void_element = self.tag_name in {
            'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
            'link', 'meta', 'param', 'source', 'track', 'wbr'
        }
    
    @property
    def id(self) -> str:
        """Get or set the ID of the element."""
        return self.get_attribute('id') or ""
    
    @id.setter
    def id(self, value: str) -> None:
        self.set_attribute('id', value)
    
    @property
    def class_name(self) -> str:
        """Get or set the class attribute of the element."""
        return self.get_attribute('class') or ""
    
    @class_name.setter
    def class_name(self, value: str) -> None:
        self.set_attribute('class', value)
        # Update class list
        self._update_class_list()
    
    @property
    def class_list(self) -> Set[str]:
        """Get the set of classes applied to this element."""
        # Ensure class list is up-to-date
        self._update_class_list()
        return self._class_list
    
    def _update_class_list(self) -> None:
        """Update internal class list from the class attribute."""
        class_attr = self.get_attribute('class') or ""
        self._class_list = {cls for cls in class_attr.split() if cls}
    
    @property
    def inner_html(self) -> str:
        """Get or set the HTML content of the element."""
        result = []
        for child in self.child_nodes:
            if child.node_type == NodeType.ELEMENT_NODE:
                element = child
                # Handle void elements
                if getattr(element, 'is_void_element', False):
                    result.append(f"<{element.tag_name}{self._format_attributes(element)}>")
                else:
                    result.append(f"<{element.tag_name}{self._format_attributes(element)}>{element.inner_html}</{element.tag_name}>")
            elif child.node_type == NodeType.TEXT_NODE:
                result.append(child.node_value or "")
            elif child.node_type == NodeType.COMMENT_NODE:
                result.append(f"<!--{child.node_value}-->")
        
        return "".join(result)
    
    @inner_html.setter
    def inner_html(self, html: str) -> None:
        """Set the HTML content of the element."""
        # Remove all existing children
        for child in list(self.child_nodes):
            self.remove_child(child)
        
        # Parse and add new content
        if self.owner_document and html:
            fragment = self.owner_document.create_fragment(html)
            while fragment.child_nodes:
                # Move each child from the fragment to this element
                child = fragment.child_nodes[0]
                fragment.remove_child(child)
                self.append_child(child)
    
    @property
    def outer_html(self) -> str:
        """Get the outer HTML of the element, including the element itself."""
        if self.is_void_element:
            return f"<{self.tag_name}{self._format_attributes(self)}>"
        else:
            return f"<{self.tag_name}{self._format_attributes(self)}>{self.inner_html}</{self.tag_name}>"
    
    @property
    def text_content(self) -> str:
        """Get or set the text content of the element."""
        result = []
        for child in self.child_nodes:
            if child.node_type == NodeType.TEXT_NODE:
                result.append(child.node_value or "")
            elif child.node_type == NodeType.ELEMENT_NODE:
                result.append(child.text_content or "")
        
        return "".join(result)
    
    @text_content.setter
    def text_content(self, text: str) -> None:
        """Set the text content of the element."""
        # Remove all existing children
        for child in list(self.child_nodes):
            self.remove_child(child)
        
        # Create and add a new text node
        if self.owner_document and text:
            text_node = self.owner_document.create_text_node(text)
            self.append_child(text_node)
    
    @property
    def style(self) -> Dict[str, str]:
        """Get the element's style."""
        # Parse style attribute if needed
        style_attr = self.get_attribute('style')
        if style_attr:
            # Parse inline style
            self._style = self._parse_style_attribute(style_attr)
        
        return self._style
    
    def set_style(self, property_name: str, value: str) -> None:
        """
        Set a style property.
        
        Args:
            property_name: CSS property name
            value: CSS property value
        """
        # Convert camelCase to kebab-case
        kebab_property = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', property_name).lower()
        
        # Update style dictionary
        self._style[kebab_property] = value
        
        # Update style attribute
        self._update_style_attribute()
    
    def _parse_style_attribute(self, style_attr: str) -> Dict[str, str]:
        """
        Parse a CSS style attribute string.
        
        Args:
            style_attr: CSS style attribute string
            
        Returns:
            Dictionary of CSS properties
        """
        style_dict = {}
        
        # Split the style attribute by semicolons
        declarations = [decl.strip() for decl in style_attr.split(';') if decl.strip()]
        
        for declaration in declarations:
            # Split each declaration into property and value
            parts = declaration.split(':', 1)
            if len(parts) == 2:
                property_name, value = parts
                style_dict[property_name.strip()] = value.strip()
        
        return style_dict
    
    def _update_style_attribute(self) -> None:
        """Update the style attribute from the style dictionary."""
        if self._style:
            style_str = "; ".join(f"{prop}: {value}" for prop, value in self._style.items())
            self.set_attribute('style', style_str)
        else:
            self.remove_attribute('style')
    
    @property
    def dataset(self) -> Dict[str, str]:
        """Get the element's dataset (data-* attributes)."""
        # Update dataset from attributes
        self._update_dataset()
        return self._dataset
    
    def _update_dataset(self) -> None:
        """Update the dataset from data-* attributes."""
        self._dataset = {}
        for name, attr in self.attributes.items():
            if name.startswith('data-'):
                # Convert kebab-case to camelCase (data-foo-bar → fooBar)
                key = re.sub(r'-([a-z])', lambda m: m.group(1).upper(), name[5:])
                self._dataset[key] = attr.value
    
    def has_attribute(self, name: str) -> bool:
        """
        Check if the element has the specified attribute.
        
        Args:
            name: The attribute name
            
        Returns:
            True if the attribute exists, False otherwise
        """
        return name in self.attributes
    
    def get_attribute(self, name: str) -> Optional[str]:
        """
        Get the value of an attribute.
        
        Args:
            name: The attribute name
            
        Returns:
            The attribute value, or None if the attribute doesn't exist
        """
        return self.attributes[name].value if name in self.attributes else None
    
    def get_attribute_node(self, name: str) -> Optional[Attr]:
        """
        Get an attribute node.
        
        Args:
            name: The attribute name
            
        Returns:
            The attribute node, or None if the attribute doesn't exist
        """
        return self.attributes.get(name)
    
    def set_attribute(self, name: str, value: str) -> None:
        """
        Set an attribute value.
        
        Args:
            name: The attribute name
            value: The attribute value
        """
        if name in self.attributes:
            self.attributes[name].value = value
        else:
            attr = Attr(name, value, self)
            self.attributes[name] = attr
            
        # Special handling for certain attributes
        if name == 'class':
            self._update_class_list()
        elif name == 'style':
            self._style = self._parse_style_attribute(value)
        elif name.startswith('data-'):
            self._update_dataset()
    
    def set_attribute_node(self, attr: Attr) -> Attr:
        """
        Set an attribute node.
        
        Args:
            attr: The attribute node to set
            
        Returns:
            The added attribute node
        """
        old_attr = self.attributes.get(attr.name)
        attr.owner_element = self
        self.attributes[attr.name] = attr
        
        # Special handling for certain attributes
        if attr.name == 'class':
            self._update_class_list()
        elif attr.name == 'style':
            self._style = self._parse_style_attribute(attr.value)
        elif attr.name.startswith('data-'):
            self._update_dataset()
        
        return old_attr
    
    def remove_attribute(self, name: str) -> None:
        """
        Remove an attribute.
        
        Args:
            name: The attribute name
        """
        if name in self.attributes:
            attr = self.attributes.pop(name)
            attr.owner_element = None
            
            # Special handling for certain attributes
            if name == 'class':
                self._class_list.clear()
            elif name == 'style':
                self._style.clear()
            elif name.startswith('data-'):
                self._update_dataset()
    
    def has_attributes(self) -> bool:
        """Check if the element has any attributes."""
        return bool(self.attributes)
    
    def get_elements_by_tag_name(self, tag_name: str) -> List['Element']:
        """
        Get all descendant elements with the given tag name.
        
        Args:
            tag_name: The tag name to match (case-insensitive)
            
        Returns:
            List of matching elements
        """
        tag_name_lower = tag_name.lower()
        result = []
        
        # Special case for "*" which matches all elements
        match_all = tag_name == "*"
        
        def collect_elements(node: Node) -> None:
            if node.node_type == NodeType.ELEMENT_NODE:
                element = node
                if match_all or element.tag_name.lower() == tag_name_lower:
                    result.append(element)
                
                # Recursively check children
                for child in node.child_nodes:
                    collect_elements(child)
        
        # Start the recursion with this element's children
        for child in self.child_nodes:
            collect_elements(child)
        
        return result
    
    def get_elements_by_class_name(self, class_name: str) -> List['Element']:
        """
        Get all descendant elements with the given class name.
        
        Args:
            class_name: The class name to match
            
        Returns:
            List of matching elements
        """
        result = []
        
        def collect_elements(node: Node) -> None:
            if node.node_type == NodeType.ELEMENT_NODE:
                element = node
                # Update class list before checking
                element._update_class_list()
                if class_name in element._class_list:
                    result.append(element)
                
                # Recursively check children
                for child in node.child_nodes:
                    collect_elements(child)
        
        # Start the recursion with this element's children
        for child in self.child_nodes:
            collect_elements(child)
        
        return result
    
    def matches(self, selector: str) -> bool:
        """
        Check if the element matches a CSS selector.
        
        Args:
            selector: The CSS selector string
            
        Returns:
            True if the element matches the selector, False otherwise
        """
        if self.owner_document:
            # Use the document's selector engine for proper matching
            return self.owner_document.element_matches(self, selector)
        
        # Simple fallback for basic selectors
        if selector.startswith('#'):
            # ID selector
            return self.id == selector[1:]
        elif selector.startswith('.'):
            # Class selector
            return selector[1:] in self.class_list
        elif selector == self.tag_name:
            # Tag selector
            return True
        
        return False
    
    def closest(self, selector: str) -> Optional['Element']:
        """
        Find the closest ancestor element (or self) that matches a selector.
        
        Args:
            selector: The CSS selector string
            
        Returns:
            The matching element or None if no match is found
        """
        current: Optional[Element] = self
        
        while current:
            if current.matches(selector):
                return current
            
            parent = current.parent_node
            if parent and parent.node_type == NodeType.ELEMENT_NODE:
                current = parent
            else:
                current = None
        
        return None
    
    def query_selector(self, selector: str) -> Optional['Element']:
        """
        Find the first descendant element that matches a selector.
        
        Args:
            selector: The CSS selector string
            
        Returns:
            The first matching element or None if no match is found
        """
        if self.owner_document:
            return self.owner_document.query_selector_from_node(self, selector)
        
        # Simple fallback implementation
        result = self.query_selector_all(selector)
        return result[0] if result else None
    
    def query_selector_all(self, selector: str) -> List['Element']:
        """
        Find all descendant elements that match a selector.
        
        Args:
            selector: The CSS selector string
            
        Returns:
            List of matching elements
        """
        if self.owner_document:
            return self.owner_document.query_selector_all_from_node(self, selector)
        
        # Simple fallback for basic selectors
        if selector.startswith('#'):
            # ID selector
            element_id = selector[1:]
            for element in self.get_elements_by_tag_name('*'):
                if element.id == element_id:
                    return [element]
            return []
        elif selector.startswith('.'):
            # Class selector
            class_name = selector[1:]
            return self.get_elements_by_class_name(class_name)
        else:
            # Tag selector or other (fallback to tag)
            return self.get_elements_by_tag_name(selector)
    
    def clone_node(self, deep: bool = False) -> 'Element':
        """
        Clone this element.
        
        Args:
            deep: Whether to clone child nodes as well
            
        Returns:
            The cloned element
        """
        # Create a new element with the same tag
        clone = type(self)(self.tag_name, self.namespace_uri, self.owner_document)
        
        # Copy attributes
        for name, attr in self.attributes.items():
            clone.set_attribute(name, attr.value)
        
        # Deep clone if requested
        if deep and self.child_nodes:
            for child in self.child_nodes:
                child_clone = child.clone_node(deep=True)
                clone.append_child(child_clone)
        
        return clone
    
    def _format_attributes(self, element: 'Element') -> str:
        """
        Format element attributes as an HTML attribute string.
        
        Args:
            element: Element to format attributes for
            
        Returns:
            Formatted attribute string
        """
        result = []
        for name, attr in element.attributes.items():
            value = attr.value
            # Boolean attributes can be specified with just the attribute name
            if value == "":
                result.append(f" {name}")
            else:
                # Escape quotes
                escaped_value = value.replace('"', '&quot;')
                result.append(f' {name}="{escaped_value}"')
        
        return "".join(result) 