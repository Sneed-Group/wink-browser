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
        """Initialize a new Document object."""
        super().__init__(NodeType.DOCUMENT_NODE)
        self.document_element: Optional[Element] = None
        self._doctype: Optional[str] = None  # Changed to _doctype (private)
        self.head: Optional[Element] = None
        self.body: Optional[Element] = None
        self.title: str = ""
        self.url: str = None  # Initialize to None instead of "about:blank"
        self.readyState: str = "loading"
        self.referrer: str = ""
        self.cookie: str = ""
        self._domain: Optional[str] = None
        self.characterSet: str = "UTF-8"
        self.contentType: str = "text/html"
        
        # Element collections
        self._elements_by_id: Dict[str, Element] = {}
        self._elements_by_tag: Dict[str, List[Element]] = {}
        self._elements_by_class: Dict[str, List[Element]] = {}
        self._forms: List[Element] = []
        self._images: List[Element] = []
        self._links: List[Element] = []
        self._scripts: List[Element] = []
        self._stylesheets: List[Element] = []
        
        # Register default event listeners
        self._event_listeners = {}
        
        # JavaScript environment
        self._js_environment = None
        
        # Selector engine for CSS selector parsing and matching
        self._selector_engine = SelectorEngine()
        
        # Create base structure (html, head, body)
        self._create_base_structure()
        
        # Error handling
        self._errors: List[str] = []
        
        # Add JavaScript-style aliases for common methods
        self.querySelector = self.query_selector
        self.querySelectorAll = self.query_selector_all
        self.getElementById = self.get_element_by_id
        self.getElementsByTagName = self.get_elements_by_tag_name
        self.getElementsByClassName = self.get_elements_by_class_name
        
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
        """
        Get the domain of the current document.
        
        Returns:
            str: The domain of the document
        """
        if self._domain:
            return self._domain
            
        # If domain is not set, try to extract it from the URL
        if self.url and self.url != "about:blank":
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(self.url)
                return parsed_url.netloc
            except:
                # Return empty string if domain can't be parsed
                return ""
                
        return ""
    
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
    
    @doctype.setter
    def doctype(self, value):
        """Set the document's DOCTYPE."""
        # If value is a Node, replace/add it directly
        if isinstance(value, Node) and value.node_type == NodeType.DOCUMENT_TYPE_NODE:
            # Remove existing doctype nodes
            for child in list(self.child_nodes):
                if child.node_type == NodeType.DOCUMENT_TYPE_NODE:
                    self.remove_child(child)
            
            # Add the new doctype node
            if self.first_child:
                self.insert_before(value, self.first_child)
            else:
                self.append_child(value)
        elif value is not None:
            # If value is a string or other non-Node, store it in _doctype
            self._doctype = value
            
            # We could also create a doctype node, but that's more complex
            # and depends on how the doctype value is formatted
            logger.debug(f"DOCTYPE value set: {value}")
        else:
            # Handle None value - remove existing doctype nodes
            for child in list(self.child_nodes):
                if child.node_type == NodeType.DOCUMENT_TYPE_NODE:
                    self.remove_child(child)
            self._doctype = None
    
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
        # Add debug logging
        logger.debug(f"Document.get_elements_by_tag_name('{tag_name}') called")
        logger.debug(f"document_element exists: {self.document_element is not None}")
        
        if not self.document_element:
            logger.warning(f"Cannot find elements by tag name '{tag_name}': document_element is None")
            return []
        
        # Check if document_element has the method
        if not hasattr(self.document_element, 'get_elements_by_tag_name'):
            logger.error(f"document_element has no 'get_elements_by_tag_name' method")
            return []
        
        # Call the method and log the result
        result = self.document_element.get_elements_by_tag_name(tag_name)
        logger.debug(f"Found {len(result)} elements with tag name '{tag_name}'")
        return result
    
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
        # Handle special cases for common elements
        selector_lower = selector.lower()
        
        # Direct access to head
        if selector_lower == 'head' and hasattr(self, 'head') and self.head:
            logger.debug("querySelector('head') - returning direct head reference")
            return self.head
            
        # Direct access to body
        if selector_lower == 'body' and hasattr(self, 'body') and self.body:
            logger.debug("querySelector('body') - returning direct body reference")
            return self.body
            
        # Direct search for title in head
        if selector_lower == 'title' and hasattr(self, 'head') and self.head:
            for child in self.head.child_nodes:
                if hasattr(child, 'tag_name') and child.tag_name.lower() == 'title':
                    logger.debug("querySelector('title') - found in head")
                    return child
        
        # Normal selector processing
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
        # Handle special cases for common elements
        selector_lower = selector.lower()
        
        # Direct access to head
        if selector_lower == 'head' and hasattr(self, 'head') and self.head:
            logger.debug("querySelectorAll('head') - returning direct head reference")
            return [self.head]
            
        # Direct access to body
        if selector_lower == 'body' and hasattr(self, 'body') and self.body:
            logger.debug("querySelectorAll('body') - returning direct body reference")
            return [self.body]
            
        # Direct search for title in head
        if selector_lower == 'title' and hasattr(self, 'head') and self.head:
            for child in self.head.child_nodes:
                if hasattr(child, 'tag_name') and child.tag_name.lower() == 'title':
                    logger.debug("querySelectorAll('title') - found in head")
                    return [child]
        
        if not self.document_element:
            return []
        
        try:
            # Special case for style elements to avoid 'str' object has no attribute 'type' error
            if selector.lower() == 'style':
                # Find all style elements manually
                result = []
                
                def find_style_elements(node):
                    if hasattr(node, 'tag_name') and node.tag_name.lower() == 'style':
                        result.append(node)
                    
                    if hasattr(node, 'child_nodes'):
                        for child in node.child_nodes:
                            find_style_elements(child)
                
                find_style_elements(self.document_element)
                return result
            
            # Get matching elements
            elements = self.query_selector_all_from_node(self.document_element, selector)
            
            # Validate the elements to ensure they are all proper Element objects
            valid_elements = []
            for element in elements:
                if not isinstance(element, Element):
                    logger.warning(f"querySelectorAll returned non-Element object: {type(element)}")
                    continue
                valid_elements.append(element)
                
            return valid_elements
        except Exception as e:
            # Log error and return empty list on failure
            logger.error(f"Error in query_selector_all: {e}")
            return []
    
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
            # Validate input
            if html_content is None:
                logger.error("Cannot parse None HTML content")
                self.handle_error("Cannot parse None HTML content")
                return False
            
            # Ensure html_content is a string
            if not isinstance(html_content, str):
                # Try to convert bytes to string if needed
                try:
                    html_content = html_content.decode('utf-8', errors='replace')
                except (AttributeError, UnicodeDecodeError) as e:
                    logger.error(f"Error decoding HTML content: {e}")
                    self.handle_error(f"Error decoding HTML content: {e}")
                    return False
            
            # Ensure we have content to parse
            if not html_content.strip():
                logger.warning("Empty HTML content provided")
                html_content = "<html><body><p>Empty page</p></body></html>"
            
            # Clear existing content
            for child in list(self.child_nodes):
                self.remove_child(child)
            
            # Reset collections and references
            self._elements_by_id = {}
            self._elements_by_tag = {}
            self._elements_by_class = {}
            self._forms = []
            self._images = []
            self._links = []
            self._scripts = []
            self._stylesheets = []
            self.document_element = None
            self.head = None
            self.body = None
            
            # Set URL if provided
            if base_url:
                self.url = base_url
            
            # Debug: Print first 100 chars of HTML content
            logger.debug(f"Parsing HTML content (first 100 chars): {html_content[:100]}...")
            
            # Parse the HTML using html5lib
            try:
                parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("dom"))
                parsed = parser.parse(html_content)
                
                # Convert parsed document to our DOM structure
                self._convert_parsed_document(parsed)
                
                # Update head and body references
                self._update_references()
                
                # Debug: Check document structure after parsing
                logger.debug(f"Document structure after parsing:")
                logger.debug(f"- document_element: {self.document_element is not None}")
                if self.document_element:
                    logger.debug(f"- document_element tag: {self.document_element.tag_name}")
                logger.debug(f"- head: {self.head is not None}")
                logger.debug(f"- body: {self.body is not None}")
                
                # If we still don't have head or body, create them
                if not self.head or not self.body:
                    logger.warning("Missing head or body after parsing, creating base structure")
                    self._create_base_structure()
                
                return True
            except Exception as e:
                logger.error(f"Error in HTML parser: {e}")
                self.handle_error(f"Error in HTML parser: {e}")
                
                # Create minimal structure in case of failure
                self._create_base_structure()
                
                # Add error message to body
                if self.body:
                    error_element = self.create_element("div")
                    error_element.set_attribute("class", "parsing-error")
                    error_element.text_content = f"Error parsing HTML: {e}"
                    self.body.append_child(error_element)
                
                return False
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}", exc_info=True)
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
        # Check if parsed_doc is None
        if parsed_doc is None:
            logger.error("Parsed document is None, cannot convert to DOM structure")
            self.handle_error("Error: Parsed document is None")
            # Create minimal structure
            self._create_base_structure()
            return
            
        # Debug parsed document
        logger.debug(f"PARSE DEBUG: parsed_doc type: {type(parsed_doc)}")
        logger.debug(f"PARSE DEBUG: parsed_doc has documentElement: {hasattr(parsed_doc, 'documentElement')}")
        if hasattr(parsed_doc, 'documentElement'):
            logger.debug(f"PARSE DEBUG: documentElement type: {type(parsed_doc.documentElement)}")
            
        # Extract doctype if present
        doctype_obj = parsed_doc.doctype if hasattr(parsed_doc, 'doctype') else None
        if doctype_obj:
            # Create and add doctype node using the setter method
            doctype_name = doctype_obj.name if hasattr(doctype_obj, 'name') else "html"
            doctype_node = Node(NodeType.DOCUMENT_TYPE_NODE, self)
            doctype_node.node_name = f"!DOCTYPE {doctype_name}"
            # Use the setter
            self.doctype = doctype_node
        
        # Get the root element and convert
        root = getattr(parsed_doc, 'documentElement', None)
        if root:
            logger.debug(f"PARSE DEBUG: Found root element: {root}")
            logger.debug(f"PARSE DEBUG: Root element tag name: {getattr(root, 'tagName', 'unknown')}")
            
            html_element = self._convert_element(root)
            logger.debug(f"PARSE DEBUG: Converted HTML element: {html_element}")
            logger.debug(f"PARSE DEBUG: HTML element tag_name: {html_element.tag_name}")
            
            self.append_child(html_element)
            self.document_element = html_element
            logger.debug(f"PARSE DEBUG: Set document_element: {self.document_element}")
            
            # Process children recursively
            if hasattr(root, 'childNodes'):
                logger.debug(f"PARSE DEBUG: Root has {len(root.childNodes)} child nodes")
                for child in root.childNodes:
                    self._convert_parsed_nodes(child, html_element)
            
            logger.debug(f"PARSE DEBUG: After conversion, document_element has {len(html_element.child_nodes)} children")
        else:
            # No root element found, create a basic structure
            logger.warning("No document element found in parsed document, creating basic structure")
            self._create_base_structure()
            
            # Add error message to body
            if self.body:
                error_element = self.create_element("div")
                error_element.set_attribute("class", "parsing-error")
                error_element.text_content = "Error: No document element found in parsed HTML"
                self.body.append_child(error_element)
    
    def _convert_parsed_nodes(self, node, parent: Node) -> None:
        """
        Recursively convert parsed nodes to our DOM structure.
        
        Args:
            node: The parsed node from html5lib
            parent: The parent node in our DOM structure
        """
        # Check if node is None
        if node is None:
            logger.warning("Attempted to convert None node")
            return
            
        # Check if node has required attributes
        if not hasattr(node, 'nodeType'):
            logger.warning(f"Node has no nodeType attribute: {type(node)}")
            return
            
        # Get node type safely
        node_type = getattr(node, 'nodeType', None)
        
        # Skip certain nodes that might cause text duplication
        if node_type == getattr(node, 'TEXT_NODE', 3):  # 3 is the standard value for TEXT_NODE
            # Create a text node
            text_content = getattr(node, 'nodeValue', '')
            if text_content and text_content.strip():
                text_node = self.create_text_node(text_content)
                parent.append_child(text_node)
        elif node_type == getattr(node, 'COMMENT_NODE', 8):  # 8 is the standard value for COMMENT_NODE
            # Create a comment node
            comment_content = getattr(node, 'nodeValue', '')
            comment_node = self.create_comment(comment_content)
            parent.append_child(comment_node)
        elif node_type == getattr(node, 'ELEMENT_NODE', 1):  # 1 is the standard value for ELEMENT_NODE
            # Create an element node
            element = self._convert_element(node)
            parent.append_child(element)
            
            # Process children recursively
            child_nodes = getattr(node, 'childNodes', [])
            if child_nodes:
                for child in child_nodes:
                    self._convert_parsed_nodes(child, element)
    
    def _convert_element(self, element) -> Element:
        """
        Convert an html5lib element to our Element implementation.
        
        Args:
            element: The element from html5lib to convert
            
        Returns:
            Our Element implementation
        """
        # Check if element is None
        if element is None:
            logger.warning("Attempted to convert None element")
            return self.create_element("div")  # Return a default element
            
        # Create element with the same tag name
        if hasattr(element, 'tagName'):
            tag_name = element.tagName.lower()
        elif hasattr(element, 'nodeName'):
            tag_name = element.nodeName.lower()
        else:
            logger.warning("Element has no tagName or nodeName")
            tag_name = "div"  # Default tag
            
        new_element = self.create_element(tag_name)
        
        # Copy attributes
        if hasattr(element, 'attributes') and element.attributes is not None:
            for name, value in element.attributes.items():
                if name is not None and value is not None:  # Extra safety check
                    new_element.set_attribute(name, value)
        
        # Special handling for script and style elements - they should not display their content as text
        if tag_name in ('script', 'style'):
            # Store the content in a special property to be used by the parsers
            # but don't add it as text content that would be rendered
            if hasattr(element, 'childNodes') and element.childNodes:
                content = ""
                for child in element.childNodes:
                    if hasattr(child, 'nodeType') and child.nodeType == getattr(child, 'TEXT_NODE', 3):
                        content += getattr(child, 'nodeValue', '')
                
                if tag_name == 'script':
                    new_element.script_content = content
                elif tag_name == 'style':
                    new_element.style_content = content
                    # Also set textContent for CSS parser compatibility
                    new_element.text_content = content
        
        return new_element
    
    def _update_references(self) -> None:
        """Update references to important elements like head and body."""
        if self.document_element:
            # Find head element using direct child search
            head = None
            body = None
            
            # Directly search for head and body as children of html
            for child in self.document_element.child_nodes:
                if hasattr(child, 'tag_name'):
                    if child.tag_name.lower() == 'head':
                        head = child
                    elif child.tag_name.lower() == 'body':
                        body = child
            
            # If head not found, try querySelector
            if not head:
                head = self.querySelector("head")
            
            # If still not found, create head
            if not head:
                logger.debug("Creating head element - not found in document")
                head = self.create_element("head")
                # Insert at the beginning of html
                self.document_element.insert_before(head, self.document_element.first_child)
            
            # Set head reference
            self.head = head
            
            # If body not found, try querySelector
            if not body:
                body = self.querySelector("body")
            
            # If still not found, create body
            if not body:
                logger.debug("Creating body element - not found in document")
                body = self.create_element("body")
                # Append to html
                self.document_element.append_child(body)
            
            # Set body reference
            self.body = body
            
            # Log the result
            logger.debug(f"Updated references - head: {self.head is not None}, body: {self.body is not None}")
    
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
        
    def debug_structure(self) -> str:
        """
        Generate a debug representation of the document structure.
        
        Returns:
            A string representation of the document structure
        """
        result = ["Document Structure:"]
        result.append(f"URL: {self.url}")
        result.append(f"Title: {self.title}")
        result.append(f"Has doctype: {self.doctype is not None}")
        result.append(f"Has document_element: {self.document_element is not None}")
        result.append(f"Has head: {self.head is not None}")
        result.append(f"Has body: {self.body is not None}")
        
        # Count elements
        element_count = 0
        text_count = 0
        comment_count = 0
        
        def count_nodes(node):
            nonlocal element_count, text_count, comment_count
            if node.node_type == NodeType.ELEMENT_NODE:
                element_count += 1
                for child in node.child_nodes:
                    count_nodes(child)
            elif node.node_type == NodeType.TEXT_NODE:
                text_count += 1
            elif node.node_type == NodeType.COMMENT_NODE:
                comment_count += 1
        
        # Count from document element
        if self.document_element:
            count_nodes(self.document_element)
        
        result.append(f"Element count: {element_count}")
        result.append(f"Text node count: {text_count}")
        result.append(f"Comment count: {comment_count}")
        
        # Check for specific elements
        if self.document_element:
            result.append("\nElement tree (first 10 levels):")
            
            def print_element_tree(element, level=0, max_level=10):
                if level > max_level:
                    return
                
                indent = "  " * level
                tag = element.tag_name if hasattr(element, 'tag_name') else element.node_name
                result.append(f"{indent}{tag}")
                
                if element.node_type == NodeType.ELEMENT_NODE:
                    for child in element.child_nodes:
                        if child.node_type == NodeType.ELEMENT_NODE:
                            print_element_tree(child, level + 1, max_level)
            
            print_element_tree(self.document_element)
        
        return "\n".join(result) 