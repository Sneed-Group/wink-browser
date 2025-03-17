"""
CSS Selector Engine implementation.
This module implements a CSS selector engine for DOM queries with full CSS3 selector support.
"""

import re
import logging
from typing import List, Optional, Dict, Tuple, Union, Set, Any, Callable
import cssselect

from .node import Node, NodeType

logger = logging.getLogger(__name__)

class SelectorEngine:
    """
    CSS Selector Engine for DOM queries.
    
    This class implements CSS3 selector matching for DOM elements.
    """
    
    def __init__(self):
        """Initialize the selector engine."""
        # Initialize the CSS selector parser
        self.parser = cssselect.HTMLTranslator()
        
        # Compile common regex patterns
        self._id_regex = re.compile(r'#([a-zA-Z0-9_-]+)')
        self._class_regex = re.compile(r'\.([a-zA-Z0-9_-]+)')
        self._tag_regex = re.compile(r'^([a-zA-Z0-9_-]+)')
        self._attr_regex = re.compile(r'\[([^\]]+)\]')
        
        # Cache for parsed selectors
        self._selector_cache: Dict[str, Any] = {}
        
        logger.debug("SelectorEngine initialized with full CSS3 selector support")
    
    def select(self, selector: str, root_node: Node) -> List['Element']:
        """
        Find all elements matching a CSS selector.
        
        Args:
            selector: The CSS selector string
            root_node: The root node to search from
            
        Returns:
            List of matching elements
        """
        # Check if this is a simple selector we can handle more efficiently
        simple_result = self._handle_simple_selector(selector, root_node)
        if simple_result is not None:
            return simple_result
        
        # For complex selectors, use the cssselect parser
        try:
            # Parse the selector
            parsed_selector = self._get_parsed_selector(selector)
            
            # Get all element descendants
            elements = self._get_all_element_descendants(root_node)
            
            # Filter elements by the parsed selector
            return [el for el in elements if self._matches_parsed_selector(el, parsed_selector)]
            
        except Exception as e:
            logger.error(f"Error selecting with complex selector '{selector}': {e}")
            # Fall back to simpler approach
            return self._fallback_select(selector, root_node)
    
    def matches(self, element: 'Element', selector: str) -> bool:
        """
        Check if an element matches a CSS selector.
        
        Args:
            element: The element to check
            selector: The CSS selector
            
        Returns:
            True if the element matches the selector, False otherwise
        """
        # Check if this is a simple selector we can handle more efficiently
        simple_result = self._handle_simple_element_match(element, selector)
        if simple_result is not None:
            return simple_result
        
        # For complex selectors, use the cssselect parser
        try:
            # Parse the selector
            parsed_selector = self._get_parsed_selector(selector)
            
            # Match the element against the parsed selector
            return self._matches_parsed_selector(element, parsed_selector)
            
        except Exception as e:
            logger.error(f"Error matching element with complex selector '{selector}': {e}")
            # Fall back to simpler approach
            return self._fallback_matches(element, selector)
    
    def _get_parsed_selector(self, selector: str) -> Any:
        """
        Get a parsed selector, using cache if available.
        
        Args:
            selector: The CSS selector string
            
        Returns:
            Parsed selector object
        """
        if selector not in self._selector_cache:
            try:
                # Use cssselect to parse the selector
                self._selector_cache[selector] = cssselect.parse(selector)
            except Exception as e:
                logger.error(f"Error parsing selector '{selector}': {e}")
                # Return a simple selector that won't match anything
                self._selector_cache[selector] = cssselect.parse('#no-match-placeholder')
        
        return self._selector_cache[selector]
    
    def _handle_simple_selector(self, selector: str, root_node: Node) -> Optional[List['Element']]:
        """
        Handle simple selectors efficiently without using the full parser.
        
        Args:
            selector: The CSS selector string
            root_node: The root node to search from
            
        Returns:
            List of matching elements, or None if the selector is not simple
        """
        selector = selector.strip()
        
        # ID selector
        if re.match(r'^#[a-zA-Z0-9_-]+$', selector):
            element_id = selector[1:]
            element = self._find_element_by_id(root_node, element_id)
            return [element] if element else []
        
        # Class selector
        elif re.match(r'^\.[a-zA-Z0-9_-]+$', selector):
            class_name = selector[1:]
            return self._find_elements_by_class(root_node, class_name)
        
        # Tag selector
        elif re.match(r'^[a-zA-Z0-9_-]+$', selector):
            return self._find_elements_by_tag(root_node, selector)
        
        # Not a simple selector
        return None
    
    def _handle_simple_element_match(self, element: 'Element', selector: str) -> Optional[bool]:
        """
        Check if an element matches a simple selector.
        
        Args:
            element: The element to check
            selector: The CSS selector
            
        Returns:
            True if the element matches, False if it doesn't, or None if the selector is not simple
        """
        selector = selector.strip()
        
        # ID selector
        if re.match(r'^#[a-zA-Z0-9_-]+$', selector):
            element_id = selector[1:]
            return element.id == element_id
        
        # Class selector
        elif re.match(r'^\.[a-zA-Z0-9_-]+$', selector):
            class_name = selector[1:]
            return class_name in element.class_list
        
        # Tag selector
        elif re.match(r'^[a-zA-Z0-9_-]+$', selector):
            return element.tag_name.lower() == selector.lower()
        
        # Not a simple selector
        return None
    
    def _find_element_by_id(self, root_node: Node, element_id: str) -> Optional['Element']:
        """
        Find an element by ID.
        
        Args:
            root_node: The root node to search from
            element_id: The ID to find
            
        Returns:
            The matching element, or None if not found
        """
        # For document node, check if it has a getElementById method
        if root_node.node_type == NodeType.DOCUMENT_NODE and hasattr(root_node, 'get_element_by_id'):
            return root_node.get_element_by_id(element_id)
        
        # Otherwise, search all descendants
        elements = self._get_all_element_descendants(root_node)
        for element in elements:
            if element.id == element_id:
                return element
        
        return None
    
    def _find_elements_by_class(self, root_node: Node, class_name: str) -> List['Element']:
        """
        Find elements by class name.
        
        Args:
            root_node: The root node to search from
            class_name: The class name to find
            
        Returns:
            List of matching elements
        """
        # For document or element node, check if it has a getElementsByClassName method
        if hasattr(root_node, 'get_elements_by_class_name'):
            return root_node.get_elements_by_class_name(class_name)
        
        # Otherwise, search all descendants
        elements = self._get_all_element_descendants(root_node)
        return [el for el in elements if class_name in el.class_list]
    
    def _find_elements_by_tag(self, root_node: Node, tag_name: str) -> List['Element']:
        """
        Find elements by tag name.
        
        Args:
            root_node: The root node to search from
            tag_name: The tag name to find
            
        Returns:
            List of matching elements
        """
        # For document or element node, check if it has a getElementsByTagName method
        if hasattr(root_node, 'get_elements_by_tag_name'):
            return root_node.get_elements_by_tag_name(tag_name)
        
        # Otherwise, search all descendants
        elements = self._get_all_element_descendants(root_node)
        return [el for el in elements if el.tag_name.lower() == tag_name.lower()]
    
    def _get_all_element_descendants(self, node: Node) -> List['Element']:
        """
        Get all element descendants of a node.
        
        Args:
            node: The node to get descendants from
            
        Returns:
            List of element descendants
        """
        elements = []
        
        if node.node_type == NodeType.ELEMENT_NODE:
            elements.append(node)
        
        for child in node.child_nodes:
            elements.extend(self._get_all_element_descendants(child))
        
        return elements
    
    def _matches_parsed_selector(self, element: 'Element', parsed_selector: Any) -> bool:
        """
        Check if an element matches a parsed selector.
        
        Args:
            element: The element to check
            parsed_selector: The parsed selector
            
        Returns:
            True if the element matches, False otherwise
        """
        # For simplicity, we'll implement a basic matching algorithm
        # that handles the most common selector types
        
        # Handle different selector types
        if isinstance(parsed_selector, cssselect.parser.Selector):
            # This is a complete selector, check the tree
            return self._matches_selector_tree(element, parsed_selector.tree)
        elif isinstance(parsed_selector, list):
            # List of selectors (comma-separated), match any
            return any(self._matches_parsed_selector(element, sel) for sel in parsed_selector)
        else:
            # Try to match the selector tree directly
            return self._matches_selector_tree(element, parsed_selector)
    
    def _matches_selector_tree(self, element: 'Element', selector_tree: Any) -> bool:
        """
        Match an element against a selector tree.
        
        Args:
            element: The element to check
            selector_tree: The selector tree
            
        Returns:
            True if the element matches, False otherwise
        """
        # Handle different selector tree types
        if isinstance(selector_tree, cssselect.parser.Element):
            # Element selector (tag name)
            tag = selector_tree.element
            return element.tag_name.lower() == tag.lower() if tag else True
            
        elif isinstance(selector_tree, cssselect.parser.Hash):
            # ID selector
            return element.id == selector_tree.id
            
        elif isinstance(selector_tree, cssselect.parser.Class):
            # Class selector
            return selector_tree.class_name in element.class_list
            
        elif isinstance(selector_tree, cssselect.parser.Attrib):
            # Attribute selector
            attr_name = selector_tree.attrib
            attr_value = selector_tree.value if hasattr(selector_tree, 'value') else None
            operator = selector_tree.operator if hasattr(selector_tree, 'operator') else None
            
            # Check if the attribute exists
            if not element.has_attribute(attr_name):
                return False
                
            # If no value to check, just the existence is enough
            if attr_value is None:
                return True
                
            # Get the attribute value
            element_value = element.get_attribute(attr_name)
            
            # Match based on the operator
            if operator == '=':
                return element_value == attr_value
            elif operator == '~=':
                return attr_value in element_value.split()
            elif operator == '|=':
                return element_value == attr_value or element_value.startswith(f"{attr_value}-")
            elif operator == '^=':
                return element_value.startswith(attr_value)
            elif operator == '$=':
                return element_value.endswith(attr_value)
            elif operator == '*=':
                return attr_value in element_value
            else:
                return element_value == attr_value
                
        elif isinstance(selector_tree, cssselect.parser.Pseudo):
            # Pseudo-class selector
            name = selector_tree.ident
            
            if name == 'first-child':
                return element.parent_node and element.parent_node.first_element_child == element
            elif name == 'last-child':
                return element.parent_node and element.parent_node.last_element_child == element
            elif name == 'only-child':
                return (element.parent_node and 
                        element.parent_node.first_element_child == element and 
                        element.parent_node.last_element_child == element)
            elif name == 'empty':
                return len(element.child_nodes) == 0
            elif name == 'root':
                return element.parent_node and element.parent_node.node_type == NodeType.DOCUMENT_NODE
            else:
                # Unsupported pseudo-class
                logger.warning(f"Unsupported pseudo-class: {name}")
                return False
                
        elif isinstance(selector_tree, cssselect.parser.Negation):
            # :not() selector
            return not self._matches_selector_tree(element, selector_tree.selector)
            
        elif isinstance(selector_tree, cssselect.parser.Combinator):
            # Combinator (>, +, ~, ' ')
            if not self._matches_selector_tree(element, selector_tree.selector):
                return False
                
            # Check the combinator
            combinator = selector_tree.combinator
            subselector = selector_tree.subselector
            
            if combinator == ' ':  # Descendant
                # Check if any ancestor matches
                parent = element.parent_node
                while parent and parent.node_type == NodeType.ELEMENT_NODE:
                    if self._matches_selector_tree(parent, subselector):
                        return True
                    parent = parent.parent_node
                return False
                
            elif combinator == '>':  # Child
                # Check if the parent matches
                return (element.parent_node and 
                        element.parent_node.node_type == NodeType.ELEMENT_NODE and
                        self._matches_selector_tree(element.parent_node, subselector))
                
            elif combinator == '+':  # Adjacent sibling
                # Check if the previous sibling matches
                prev = element.previous_element_sibling
                return prev and self._matches_selector_tree(prev, subselector)
                
            elif combinator == '~':  # General sibling
                # Check if any previous sibling matches
                sibling = element.previous_element_sibling
                while sibling:
                    if self._matches_selector_tree(sibling, subselector):
                        return True
                    sibling = sibling.previous_element_sibling
                return False
                
            else:
                # Unknown combinator
                logger.warning(f"Unknown combinator: {combinator}")
                return False
                
        elif isinstance(selector_tree, cssselect.parser.CombinedSelector):
            # Combined selector (multiple simple selectors)
            for selector in selector_tree.items:
                if not self._matches_selector_tree(element, selector):
                    return False
            return True
            
        else:
            # Unknown selector type
            logger.warning(f"Unknown selector type: {type(selector_tree).__name__}")
            return False
    
    def _fallback_select(self, selector: str, root_node: Node) -> List['Element']:
        """
        Fallback selector implementation for when the parser fails.
        
        Args:
            selector: The CSS selector string
            root_node: The root node to search from
            
        Returns:
            List of matching elements
        """
        elements = self._get_all_element_descendants(root_node)
        
        # Simple ID selector
        id_match = self._id_regex.search(selector)
        if id_match:
            element_id = id_match.group(1)
            return [el for el in elements if el.id == element_id]
        
        # Simple class selector
        class_match = self._class_regex.search(selector)
        if class_match:
            class_name = class_match.group(1)
            return [el for el in elements if class_name in el.class_list]
        
        # Simple tag selector
        tag_match = self._tag_regex.search(selector)
        if tag_match:
            tag_name = tag_match.group(1)
            return [el for el in elements if el.tag_name.lower() == tag_name.lower()]
        
        # Return all elements as a last resort
        return elements
    
    def _fallback_matches(self, element: 'Element', selector: str) -> bool:
        """
        Fallback implementation for element matching when the parser fails.
        
        Args:
            element: The element to check
            selector: The CSS selector string
            
        Returns:
            True if the element matches, False otherwise
        """
        # Simple ID selector
        id_match = self._id_regex.search(selector)
        if id_match:
            element_id = id_match.group(1)
            return element.id == element_id
        
        # Simple class selector
        class_match = self._class_regex.search(selector)
        if class_match:
            class_name = class_match.group(1)
            return class_name in element.class_list
        
        # Simple tag selector
        tag_match = self._tag_regex.search(selector)
        if tag_match:
            tag_name = tag_match.group(1)
            return element.tag_name.lower() == tag_name.lower()
        
        # Cannot determine match
        return False 