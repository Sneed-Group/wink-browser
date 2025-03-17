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

__all__ = [
    'Node', 'NodeType', 'Element', 'Attr', 'Text', 'Comment', 'Document', 'SelectorEngine'
] 