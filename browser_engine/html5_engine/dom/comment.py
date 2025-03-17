"""
Comment node implementation for the DOM.
This module implements the DOM Comment interface according to HTML5 specifications.
"""

from typing import Optional
from .node import Node, NodeType

class Comment(Node):
    """
    Comment node implementation for the DOM.
    
    This class represents a comment node in the DOM tree.
    """
    
    def __init__(self, data: str, owner_document: Optional['Document'] = None):
        """
        Initialize a comment node.
        
        Args:
            data: The comment text
            owner_document: The document that owns this node
        """
        super().__init__(NodeType.COMMENT_NODE, owner_document)
        
        # Ensure data is not None
        if data is None:
            data = ""
            
        self.node_name = "#comment"
        self.node_value = data
        self.data = data  # Alias for node_value
        self.length = len(data)
    
    def substring_data(self, offset: int, count: int) -> str:
        """
        Extract a substring from the comment data.
        
        Args:
            offset: Starting offset
            count: Number of characters to extract
            
        Returns:
            The extracted substring
            
        Raises:
            ValueError: If the offset or count is invalid
        """
        if offset < 0 or offset > self.length:
            raise ValueError("Invalid substring offset")
        
        end = min(offset + count, self.length)
        return self.data[offset:end]
    
    def append_data(self, data: str) -> None:
        """
        Append data to the end of the comment.
        
        Args:
            data: Data to append
        """
        self.data += data
        self.node_value = self.data
        self.length = len(self.data)
    
    def insert_data(self, offset: int, data: str) -> None:
        """
        Insert data at the specified offset.
        
        Args:
            offset: Position to insert at
            data: Data to insert
            
        Raises:
            ValueError: If the offset is invalid
        """
        if offset < 0 or offset > self.length:
            raise ValueError("Invalid insert offset")
        
        self.data = self.data[:offset] + data + self.data[offset:]
        self.node_value = self.data
        self.length = len(self.data)
    
    def delete_data(self, offset: int, count: int) -> None:
        """
        Delete data from the specified range.
        
        Args:
            offset: Starting offset
            count: Number of characters to delete
            
        Raises:
            ValueError: If the offset is invalid
        """
        if offset < 0 or offset > self.length:
            raise ValueError("Invalid delete offset")
        
        end = min(offset + count, self.length)
        self.data = self.data[:offset] + self.data[end:]
        self.node_value = self.data
        self.length = len(self.data)
    
    def replace_data(self, offset: int, count: int, data: str) -> None:
        """
        Replace data in the specified range.
        
        Args:
            offset: Starting offset
            count: Number of characters to replace
            data: Replacement data
            
        Raises:
            ValueError: If the offset is invalid
        """
        if offset < 0 or offset > self.length:
            raise ValueError("Invalid replace offset")
        
        end = min(offset + count, self.length)
        self.data = self.data[:offset] + data + self.data[end:]
        self.node_value = self.data
        self.length = len(self.data)
    
    def clone_node(self, deep: bool = False) -> 'Comment':
        """
        Clone this comment node.
        
        Args:
            deep: Not used for comment nodes
            
        Returns:
            A new comment node with the same content
        """
        return Comment(self.data, self.owner_document) 