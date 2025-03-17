"""
Document implementation for the DOM.
This module implements the DOM Document interface according to HTML5 specifications.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Union, Set, Tuple, Type
from bs4 import BeautifulSoup
import html5lib
import urllib.parse

from .node import Node, NodeType
from .element import Element
from .text import Text
from .comment import Comment
from .selector_engine import SelectorEngine

logger = logging.getLogger(__name__)

class Document(Node):
    """
    Document node implementation for the DOM.
    
    This class represents an HTML document with full HTML5 support.
    """
    
    def __init__(self):
        """Initialize a new HTML document."""
        super().__init__(NodeType.DOCUMENT_NODE, self)
        
        self.node_name = "#document"
        
        # Document URL and domain
        self.url: str = "about:blank"
        self._domain: Optional[str] = None
        
        # Document title
        self._title: str = ""
        
        # Document head and body elements
        self.head: Optional[Element] = None
        self.body: Optional[Element] = None
        
        # Document element (html)
        self.document_element: Optional[Element] = None
        
        # Selector engine for CSS selector parsing and matching
        self._selector_engine = SelectorEngine()
        
        # Create base structure (html, head, body)
        self._create_base_structure()
        
        # Error handling
        self._errors: List[str] = []
        
        logger.debug("HTML Document initialized with full HTML5 support")
    
    def _create_base_structure(self) -> None:
        """Create the basic HTML document structure."""
        # Create HTML element
        html = self.create_element("html")
        self.append_child(html)
        self.document_element = html
        
        # Create head element
        head = self.create_element("head")
        html.append_child(head)
        self.head = head
        
        # Create body element
        body = self.create_element("body")
        html.append_child(body)
        self.body = body
    
    @property
    def domain(self) -> str:
        """Get or set the domain of the document."""
        if self._domain is None and self.url and self.url != "about:blank":
            # Extract domain from URL
            try:
                parsed_url = urllib.parse.urlparse(self.url)
                self._domain = parsed_url.netloc
            except Exception:
                self._domain = ""
        
        return self._domain or ""
    
    @domain.setter
    def domain(self, value: str) -> None:
        # Security considerations would be implemented here
        self._domain = value
    
    @property
    def title(self) -> str:
        """Get or set the title of the document."""
        # Attempt to find title element if not cached
        if not self._title and self.head:
            title_element = self.head.query_selector("title")
            if title_element:
                self._title = title_element.text_content
        
        return self._title
    
    @title.setter
    def title(self, value: str) -> None:
        self._title = value
        
        # Update or create title element
        if self.head:
            title_element = self.head.query_selector("title")
            if title_element:
                title_element.text_content = value
            else:
                title_element = self.create_element("title")
                title_element.text_content = value
                self.head.append_child(title_element)
    
    @property
    def doctype(self) -> Optional[Node]:
        """Get the document's DOCTYPE."""
        # Check for doctype node
        for child in self.child_nodes:
            if child.node_type == NodeType.DOCUMENT_TYPE_NODE:
                return child
        
        return None
    
    def create_element(self, tag_name: str, namespace: Optional[str] = None) -> Element:
        """
        Create a new element with the specified tag name.
        
        Args:
            tag_name: The tag name of the element
            namespace: Optional namespace URI
            
        Returns:
            The new element
        """
        return Element(tag_name, namespace, self)
    
    def create_text_node(self, data: str) -> Text:
        """
        Create a new text node.
        
        Args:
            data: The text content
            
        Returns:
            The new text node
        """
        return Text(data, self)
    
    def create_comment(self, data: str) -> Comment:
        """
        Create a new comment node.
        
        Args:
            data: The comment content
            
        Returns:
            The new comment node
        """
        return Comment(data, self)
    
    def create_fragment(self, html: str) -> Node:
        """
        Create a document fragment from HTML string.
        
        Args:
            html: The HTML string
            
        Returns:
            A document fragment containing the parsed HTML
        """
        # Create a fragment node
        fragment = Node(NodeType.DOCUMENT_FRAGMENT_NODE, self)
        
        # Parse the HTML
        try:
            # Use html5lib for full HTML5 support
            parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("dom"))
            parsed = parser.parseFragment(html)
            
            # Convert parsed fragment to our DOM structure
            self._convert_parsed_nodes(parsed, fragment)
        except Exception as e:
            logger.error(f"Error parsing HTML fragment: {e}")
            self.handle_error(f"Error parsing HTML fragment: {e}")
        
        return fragment
    
    def get_element_by_id(self, element_id: str) -> Optional[Element]:
        """
        Get an element by its ID.
        
        Args:
            element_id: The ID to search for
            
        Returns:
            The element with the specified ID, or None if not found
        """
        if not self.document_element:
            return None
        
        # Use querySelector for efficient lookup
        return self.query_selector(f"#{element_id}")
    
    def get_elements_by_tag_name(self, tag_name: str) -> List[Element]:
        """
        Get all elements with the specified tag name.
        
        Args:
            tag_name: The tag name to search for
            
        Returns:
            List of matching elements
        """
        if not self.document_element:
            return []
        
        return self.document_element.get_elements_by_tag_name(tag_name)
    
    def get_elements_by_class_name(self, class_name: str) -> List[Element]:
        """
        Get all elements with the specified class name.
        
        Args:
            class_name: The class name to search for
            
        Returns:
            List of matching elements
        """
        if not self.document_element:
            return []
        
        return self.document_element.get_elements_by_class_name(class_name)
    
    def query_selector(self, selector: str) -> Optional[Element]:
        """
        Find the first element matching the specified selector.
        
        Args:
            selector: CSS selector string
            
        Returns:
            The first matching element, or None if not found
        """
        if not self.document_element:
            return None
        
        return self.query_selector_from_node(self.document_element, selector)
    
    def query_selector_all(self, selector: str) -> List[Element]:
        """
        Find all elements matching the specified selector.
        
        Args:
            selector: CSS selector string
            
        Returns:
            List of matching elements
        """
        if not self.document_element:
            return []
        
        return self.query_selector_all_from_node(self.document_element, selector)
    
    def query_selector_from_node(self, node: Node, selector: str) -> Optional[Element]:
        """
        Find the first element matching the selector in a subtree.
        
        Args:
            node: The root node of the subtree
            selector: CSS selector string
            
        Returns:
            The first matching element, or None if not found
        """
        try:
            # Use selector engine to find matching elements
            matches = self._selector_engine.select(selector, node)
            return matches[0] if matches else None
        except Exception as e:
            logger.error(f"Error in query_selector: {e}")
            self.handle_error(f"Error in query_selector: {e}")
            
            # Fallback to simpler methods
            return self._fallback_query_selector(node, selector)
    
    def query_selector_all_from_node(self, node: Node, selector: str) -> List[Element]:
        """
        Find all elements matching the selector in a subtree.
        
        Args:
            node: The root node of the subtree
            selector: CSS selector string
            
        Returns:
            List of matching elements
        """
        try:
            # Use selector engine to find matching elements
            return self._selector_engine.select(selector, node)
        except Exception as e:
            logger.error(f"Error in query_selector_all: {e}")
            self.handle_error(f"Error in query_selector_all: {e}")
            
            # Fallback to simpler methods
            return self._fallback_query_selector_all(node, selector)
    
    def element_matches(self, element: Element, selector: str) -> bool:
        """
        Check if an element matches a selector.
        
        Args:
            element: The element to check
            selector: The CSS selector
            
        Returns:
            True if the element matches the selector, False otherwise
        """
        try:
            return self._selector_engine.matches(element, selector)
        except Exception as e:
            logger.error(f"Error in element_matches: {e}")
            self.handle_error(f"Error in element_matches: {e}")
            
            # Fallback to simpler methods
            return self._fallback_element_matches(element, selector)
    
    def _fallback_query_selector(self, node: Node, selector: str) -> Optional[Element]:
        """
        Simple fallback selector implementation.
        
        Args:
            node: The root node to search from
            selector: The CSS selector string
            
        Returns:
            The first matching element, or None if not found
        """
        if not hasattr(node, 'get_elements_by_tag_name'):
            return None
        
        # Simple ID selector
        if selector.startswith('#'):
            element_id = selector[1:]
            for element in node.get_elements_by_tag_name('*'):
                if element.id == element_id:
                    return element
            return None
        
        # Simple class selector
        elif selector.startswith('.'):
            class_name = selector[1:]
            for element in node.get_elements_by_tag_name('*'):
                if class_name in element.class_list:
                    return element
            return None
        
        # Tag selector
        else:
            elements = node.get_elements_by_tag_name(selector)
            return elements[0] if elements else None
    
    def _fallback_query_selector_all(self, node: Node, selector: str) -> List[Element]:
        """
        Simple fallback selector implementation for multiple elements.
        
        Args:
            node: The root node to search from
            selector: The CSS selector string
            
        Returns:
            List of matching elements
        """
        if not hasattr(node, 'get_elements_by_tag_name'):
            return []
        
        # Simple ID selector
        if selector.startswith('#'):
            element_id = selector[1:]
            for element in node.get_elements_by_tag_name('*'):
                if element.id == element_id:
                    return [element]
            return []
        
        # Simple class selector
        elif selector.startswith('.'):
            class_name = selector[1:]
            return [element for element in node.get_elements_by_tag_name('*') 
                   if class_name in element.class_list]
        
        # Tag selector
        else:
            return node.get_elements_by_tag_name(selector)
    
    def _fallback_element_matches(self, element: Element, selector: str) -> bool:
        """
        Simple fallback implementation for element matching.
        
        Args:
            element: The element to check
            selector: The CSS selector string
            
        Returns:
            True if the element matches, False otherwise
        """
        # Simple ID selector
        if selector.startswith('#'):
            return element.id == selector[1:]
        
        # Simple class selector
        elif selector.startswith('.'):
            return selector[1:] in element.class_list
        
        # Tag selector
        else:
            return element.tag_name.lower() == selector.lower()
    
    def parse_html(self, html_content: str, base_url: Optional[str] = None) -> bool:
        """
        Parse HTML content and update this document.
        
        Args:
            html_content: The HTML content to parse
            base_url: Optional base URL for resolving relative URLs
            
        Returns:
            True if parsing was successful, False otherwise
        """
        try:
            # Clear existing content
            for child in list(self.child_nodes):
                self.remove_child(child)
            
            # Set URL if provided
            if base_url:
                self.url = base_url
            
            # Parse the HTML using html5lib
            parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("dom"))
            parsed = parser.parse(html_content)
            
            # Convert parsed document to our DOM structure
            self._convert_parsed_document(parsed)
            
            # Update head and body references
            self._update_references()
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            self.handle_error(f"Error parsing HTML: {e}")
            
            # Create minimal structure in case of failure
            self._create_base_structure()
            
            # Add error message to body
            if self.body:
                error_element = self.create_element("div")
                error_element.set_attribute("class", "parsing-error")
                error_element.text_content = f"Error parsing HTML: {e}"
                self.body.append_child(error_element)
            
            return False
    
    def _convert_parsed_document(self, parsed_doc) -> None:
        """
        Convert a parsed html5lib document to our DOM structure.
        
        Args:
            parsed_doc: The parsed document from html5lib
        """
        # Extract doctype if present
        doctype = parsed_doc.doctype
        if doctype:
            # Create and add doctype node
            doctype_name = doctype.name if hasattr(doctype, 'name') else "html"
            doctype_node = Node(NodeType.DOCUMENT_TYPE_NODE, self)
            doctype_node.node_name = f"!DOCTYPE {doctype_name}"
            self.append_child(doctype_node)
        
        # Get the root element and convert
        root = parsed_doc.documentElement
        if root:
            html_element = self._convert_element(root)
            self.append_child(html_element)
            self.document_element = html_element
            
            # Process children recursively
            for child in root.childNodes:
                self._convert_parsed_nodes(child, html_element)
    
    def _convert_parsed_nodes(self, node, parent: Node) -> None:
        """
        Recursively convert parsed nodes to our DOM structure.
        
        Args:
            node: The node from html5lib to convert
            parent: The parent node in our DOM structure
        """
        if node.nodeType == node.ELEMENT_NODE:
            # Convert element
            element = self._convert_element(node)
            parent.append_child(element)
            
            # Process children
            for child in node.childNodes:
                self._convert_parsed_nodes(child, element)
                
        elif node.nodeType == node.TEXT_NODE:
            # Convert text node
            text_node = self.create_text_node(node.nodeValue)
            parent.append_child(text_node)
            
        elif node.nodeType == node.COMMENT_NODE:
            # Convert comment node
            comment_node = self.create_comment(node.nodeValue)
            parent.append_child(comment_node)
    
    def _convert_element(self, element) -> Element:
        """
        Convert an html5lib element to our Element implementation.
        
        Args:
            element: The element from html5lib to convert
            
        Returns:
            Our Element implementation
        """
        # Create element with the same tag name
        tag_name = element.tagName.lower() if hasattr(element, 'tagName') else element.nodeName.lower()
        new_element = self.create_element(tag_name)
        
        # Copy attributes
        if hasattr(element, 'attributes'):
            for name, value in element.attributes.items():
                new_element.set_attribute(name, value)
        
        return new_element
    
    def _update_references(self) -> None:
        """Update references to important elements like head and body."""
        if self.document_element:
            # Find head element
            head = self.query_selector("head")
            if head:
                self.head = head
            else:
                # Create head if not found
                self.head = self.create_element("head")
                # Insert at the beginning of html
                self.document_element.insert_before(self.head, self.document_element.first_child)
            
            # Find body element
            body = self.query_selector("body")
            if body:
                self.body = body
            else:
                # Create body if not found
                self.body = self.create_element("body")
                # Append to html
                self.document_element.append_child(self.body)
    
    def handle_error(self, error_message: str) -> None:
        """
        Handle errors that occur during document processing.
        
        Args:
            error_message: The error message
        """
        logger.error(error_message)
        self._errors.append(error_message)
    
    def get_errors(self) -> List[str]:
        """
        Get the list of errors that occurred during document processing.
        
        Returns:
            List of error messages
        """
        return self._errors 