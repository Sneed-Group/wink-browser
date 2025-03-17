"""
DOM Implementation for HTML5 engine.
This package provides a complete DOM implementation following HTML5 specifications.
"""

from .node import Node, NodeType
from .element import Element
from .attr import Attr
from .text import Text
from .comment import Comment
from .document import Document
from .selector_engine import SelectorEngine

# Define a Parser class that integrates with Document
class Parser:
    """HTML Parser for creating DOM trees from HTML content."""
    
    def __init__(self):
        """Initialize the HTML parser."""
        pass
    
    def parse(self, html_content: str, base_url: str = None) -> Document:
        """
        Parse HTML content into a Document.
        
        Args:
            html_content: The HTML content to parse
            base_url: Optional base URL for resolving relative URLs
            
        Returns:
            The parsed Document
        """
        document = Document()
        document.parse_html(html_content, base_url)
        return document

__all__ = [
    'Node', 'NodeType', 'Element', 'Attr', 'Text', 'Comment', 'Document', 'SelectorEngine', 'Parser'
] 