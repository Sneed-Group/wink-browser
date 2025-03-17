"""
CSS Selector Engine.
This module handles parsing and matching CSS selectors against DOM elements.
"""

import re
from typing import List, Dict, Set, Optional, Tuple, Any, Callable, Union
from ..dom import Element

class SelectorPart:
    """
    Represents a part of a CSS selector.
    """
    def __init__(self, selector_type: str, value: str, pseudo_class: Optional[str] = None):
        """
        Initialize a selector part.
        
        Args:
            selector_type: Type of selector (tag, id, class, attribute)
            value: The selector value
            pseudo_class: Pseudo-class if any
        """
        self.selector_type = selector_type
        self.value = value
        self.pseudo_class = pseudo_class
    
    def __repr__(self):
        return f"SelectorPart({self.selector_type}, {self.value}, {self.pseudo_class})"

class Selector:
    """
    Represents a CSS selector.
    """
    def __init__(self):
        """Initialize a CSS selector."""
        self.parts: List[SelectorPart] = []
        self.specificity: Tuple[int, int, int] = (0, 0, 0)  # (id, class, tag)
    
    def add_part(self, part: SelectorPart) -> None:
        """
        Add a part to the selector.
        
        Args:
            part: The selector part to add
        """
        self.parts.append(part)
        
        # Update specificity
        if part.selector_type == 'id':
            self.specificity = (self.specificity[0] + 1, self.specificity[1], self.specificity[2])
        elif part.selector_type in ('class', 'attribute'):
            self.specificity = (self.specificity[0], self.specificity[1] + 1, self.specificity[2])
        elif part.selector_type == 'tag':
            self.specificity = (self.specificity[0], self.specificity[1], self.specificity[2] + 1)
        
        # Add 1 to class specificity for pseudo-classes
        if part.pseudo_class:
            self.specificity = (self.specificity[0], self.specificity[1] + 1, self.specificity[2])
    
    def __repr__(self):
        return f"Selector({self.parts}, specificity={self.specificity})"

class SelectorGroup:
    """
    Represents a group of CSS selectors sharing the same style declarations.
    """
    def __init__(self):
        """Initialize a selector group."""
        self.selectors: List[Selector] = []
    
    def add_selector(self, selector: Selector) -> None:
        """
        Add a selector to the group.
        
        Args:
            selector: The selector to add
        """
        self.selectors.append(selector)
    
    def matches_element(self, element: Element) -> Optional[Tuple[int, int, int]]:
        """
        Check if any selector in the group matches the element.
        
        Args:
            element: The element to check
            
        Returns:
            Specificity of the matching selector with highest specificity, or None if no match
        """
        max_specificity = None
        
        for selector in self.selectors:
            if matches_selector(selector, element):
                # Check if this selector has higher specificity
                if max_specificity is None or selector.specificity > max_specificity:
                    max_specificity = selector.specificity
        
        return max_specificity
    
    def __repr__(self):
        return f"SelectorGroup({len(self.selectors)} selectors)"

class SelectorParser:
    """
    Parser for CSS selectors.
    """
    def __init__(self):
        """Initialize the selector parser."""
        pass
    
    def parse(self, selector_text: str) -> SelectorGroup:
        """
        Parse a CSS selector string into a SelectorGroup.
        
        Args:
            selector_text: The selector text to parse
            
        Returns:
            Parsed SelectorGroup
        """
        # Remove whitespace around commas and normalize whitespace
        selector_text = re.sub(r'\s*,\s*', ',', selector_text)
        
        # Split into individual selectors
        selector_strings = selector_text.split(',')
        
        selector_group = SelectorGroup()
        
        for selector_string in selector_strings:
            selector = self._parse_selector(selector_string.strip())
            if selector:
                selector_group.add_selector(selector)
        
        return selector_group
    
    def _parse_selector(self, selector_string: str) -> Optional[Selector]:
        """
        Parse a single CSS selector string.
        
        Args:
            selector_string: The selector text to parse
            
        Returns:
            Parsed Selector object or None if invalid
        """
        if not selector_string:
            return None
        
        selector = Selector()
        
        # Split selector into parts (simplified parsing for demo)
        # In a full implementation, this would handle combinators (>, +, ~, space)
        
        # For now, just handle simple selectors
        # e.g., div.class#id[attr=value]:hover
        
        # Extract tag, class, id, attribute, and pseudo-class parts
        current_pos = 0
        length = len(selector_string)
        
        while current_pos < length:
            char = selector_string[current_pos]
            
            # Tag name
            if char.isalpha() or char == '*':
                start = current_pos
                while current_pos < length and (selector_string[current_pos].isalnum() or selector_string[current_pos] in '-_*'):
                    current_pos += 1
                tag_name = selector_string[start:current_pos]
                selector.add_part(SelectorPart('tag', tag_name))
            
            # Class
            elif char == '.':
                current_pos += 1  # Skip the dot
                start = current_pos
                while current_pos < length and (selector_string[current_pos].isalnum() or selector_string[current_pos] in '-_'):
                    current_pos += 1
                class_name = selector_string[start:current_pos]
                selector.add_part(SelectorPart('class', class_name))
            
            # ID
            elif char == '#':
                current_pos += 1  # Skip the hash
                start = current_pos
                while current_pos < length and (selector_string[current_pos].isalnum() or selector_string[current_pos] in '-_'):
                    current_pos += 1
                id_value = selector_string[start:current_pos]
                selector.add_part(SelectorPart('id', id_value))
            
            # Attribute
            elif char == '[':
                current_pos += 1  # Skip the opening bracket
                start = current_pos
                
                # Find the closing bracket
                while current_pos < length and selector_string[current_pos] != ']':
                    current_pos += 1
                
                if current_pos < length:
                    attr_expr = selector_string[start:current_pos]
                    current_pos += 1  # Skip the closing bracket
                    
                    # Parse attribute expression
                    if '=' in attr_expr:
                        # Attribute with value
                        attr_name, attr_value = attr_expr.split('=', 1)
                        attr_name = attr_name.strip()
                        attr_value = attr_value.strip().strip('"\'')
                        selector.add_part(SelectorPart('attribute', f"{attr_name}={attr_value}"))
                    else:
                        # Just attribute presence
                        attr_name = attr_expr.strip()
                        selector.add_part(SelectorPart('attribute', attr_name))
            
            # Pseudo-class
            elif char == ':':
                current_pos += 1  # Skip the colon
                start = current_pos
                while current_pos < length and (selector_string[current_pos].isalnum() or selector_string[current_pos] in '-_'):
                    current_pos += 1
                
                if start != current_pos:
                    pseudo_class = selector_string[start:current_pos]
                    
                    # Add to the last selector part, or create a universal selector if none exists
                    if selector.parts:
                        last_part = selector.parts[-1]
                        # Remove the last part and add it back with the pseudo-class
                        selector.parts.pop()
                        selector.add_part(SelectorPart(last_part.selector_type, last_part.value, pseudo_class))
                    else:
                        # If no parts yet, create a universal selector with the pseudo-class
                        selector.add_part(SelectorPart('tag', '*', pseudo_class))
            
            # Whitespace and other characters (skip)
            else:
                current_pos += 1
        
        return selector

def matches_selector(selector: Selector, element: Element) -> bool:
    """
    Check if an element matches a selector.
    
    Args:
        selector: The selector to check
        element: The element to match against
        
    Returns:
        True if the element matches the selector, False otherwise
    """
    # For demo purposes, we'll implement a simplified matching algorithm
    # In a full implementation, this would handle the full CSS selector syntax
    
    for part in selector.parts:
        if part.selector_type == 'tag':
            if part.value != '*' and element.tag_name.lower() != part.value.lower():
                return False
        
        elif part.selector_type == 'id':
            element_id = element.get_attribute('id')
            if not element_id or element_id != part.value:
                return False
        
        elif part.selector_type == 'class':
            element_class = element.get_attribute('class')
            if not element_class:
                return False
            
            # Check if the class is in the element's class list
            class_list = element_class.split()
            if part.value not in class_list:
                return False
        
        elif part.selector_type == 'attribute':
            # Check attribute existence or value
            if '=' in part.value:
                attr_name, attr_value = part.value.split('=', 1)
                element_attr = element.get_attribute(attr_name)
                if element_attr != attr_value:
                    return False
            else:
                # Just check attribute presence
                if not element.has_attribute(part.value):
                    return False
        
        # Check pseudo-class if present
        if part.pseudo_class:
            if not matches_pseudo_class(element, part.pseudo_class):
                return False
    
    return True

def matches_pseudo_class(element: Element, pseudo_class: str) -> bool:
    """
    Check if an element matches a pseudo-class.
    
    Args:
        element: The element to check
        pseudo_class: The pseudo-class to match
        
    Returns:
        True if the element matches the pseudo-class, False otherwise
    """
    # Implement simplified pseudo-class matching
    if pseudo_class == 'first-child':
        if element.parent_node:
            for child in element.parent_node.children:
                if child.node_type == 1:  # ELEMENT_NODE
                    return child == element
    
    elif pseudo_class == 'last-child':
        if element.parent_node:
            for child in reversed(element.parent_node.children):
                if child.node_type == 1:  # ELEMENT_NODE
                    return child == element
    
    elif pseudo_class == 'nth-child(odd)':
        if element.parent_node:
            index = 0
            for child in element.parent_node.children:
                if child.node_type == 1:  # ELEMENT_NODE
                    index += 1
                    if child == element:
                        return index % 2 == 1
    
    elif pseudo_class == 'nth-child(even)':
        if element.parent_node:
            index = 0
            for child in element.parent_node.children:
                if child.node_type == 1:  # ELEMENT_NODE
                    index += 1
                    if child == element:
                        return index % 2 == 0
    
    elif pseudo_class.startswith('nth-child('):
        # Extract the n value
        n_match = re.match(r'nth-child\((\d+)\)', pseudo_class)
        if n_match:
            n = int(n_match.group(1))
            if element.parent_node:
                index = 0
                for child in element.parent_node.children:
                    if child.node_type == 1:  # ELEMENT_NODE
                        index += 1
                        if child == element:
                            return index == n
    
    elif pseudo_class == 'hover':
        # For demo purposes, assume no elements are being hovered
        return False
    
    elif pseudo_class == 'active':
        # For demo purposes, assume no elements are active
        return False
    
    elif pseudo_class == 'focus':
        # For demo purposes, assume no elements have focus
        return False
    
    elif pseudo_class == 'link':
        return element.tag_name.lower() == 'a' and element.has_attribute('href')
    
    elif pseudo_class == 'visited':
        # For demo purposes, assume no links are visited
        return False
    
    return False

def select_elements(selector_text: str, root_element: Element) -> List[Element]:
    """
    Select elements matching a CSS selector.
    
    Args:
        selector_text: The CSS selector text
        root_element: The root element to search from
        
    Returns:
        List of matching elements
    """
    parser = SelectorParser()
    selector_group = parser.parse(selector_text)
    
    matching_elements = []
    _find_matching_elements(selector_group, root_element, matching_elements)
    
    return matching_elements

def _find_matching_elements(selector_group: SelectorGroup, element: Element, matching_elements: List[Element]) -> None:
    """
    Recursively find elements matching a selector group.
    
    Args:
        selector_group: The selector group to match
        element: The current element to check
        matching_elements: List to collect matching elements
    """
    # Check if the current element matches
    if selector_group.matches_element(element) is not None:
        matching_elements.append(element)
    
    # Check children recursively
    for child in element.children:
        if hasattr(child, 'tag_name'):  # Only process element nodes
            _find_matching_elements(selector_group, child, matching_elements)

def get_element_css_classes(element: Element) -> Set[str]:
    """
    Get the CSS classes of an element.
    
    Args:
        element: The element to get classes for
        
    Returns:
        Set of class names
    """
    class_attr = element.get_attribute('class')
    if not class_attr:
        return set()
    
    return set(class_attr.split())

def has_class(element: Element, class_name: str) -> bool:
    """
    Check if an element has a specific CSS class.
    
    Args:
        element: The element to check
        class_name: The class name to look for
        
    Returns:
        True if the element has the class, False otherwise
    """
    return class_name in get_element_css_classes(element)

def add_class(element: Element, class_name: str) -> bool:
    """
    Add a CSS class to an element.
    
    Args:
        element: The element to add the class to
        class_name: The class name to add
        
    Returns:
        True if the class was added, False if it was already present
    """
    classes = get_element_css_classes(element)
    
    if class_name in classes:
        return False
    
    classes.add(class_name)
    element.set_attribute('class', ' '.join(classes))
    return True

def remove_class(element: Element, class_name: str) -> bool:
    """
    Remove a CSS class from an element.
    
    Args:
        element: The element to remove the class from
        class_name: The class name to remove
        
    Returns:
        True if the class was removed, False if it wasn't present
    """
    classes = get_element_css_classes(element)
    
    if class_name not in classes:
        return False
    
    classes.remove(class_name)
    
    if classes:
        element.set_attribute('class', ' '.join(classes))
    else:
        element.remove_attribute('class')
    
    return True

def toggle_class(element: Element, class_name: str) -> bool:
    """
    Toggle a CSS class on an element.
    
    Args:
        element: The element to toggle the class on
        class_name: The class name to toggle
        
    Returns:
        True if the class was added, False if it was removed
    """
    if has_class(element, class_name):
        remove_class(element, class_name)
        return False
    else:
        add_class(element, class_name)
        return True 