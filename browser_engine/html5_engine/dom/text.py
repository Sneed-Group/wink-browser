"""
Text node implementation for the DOM.
This module implements the DOM Text interface according to HTML5 specifications.
"""

from typing import Optional
from .node import Node, NodeType

class Text(Node):
    """
    Text node implementation for the DOM.
    
    This class represents a text node in the DOM tree.
    """
    
    def __init__(self, data: str, owner_document: Optional['Document'] = None):
        """
        Initialize a text node.
        
        Args:
            data: The text content
            owner_document: The document that owns this node
        """
        super().__init__(NodeType.TEXT_NODE, owner_document)
        
        # Ensure data is not None
        if data is None:
            data = ""
            
        self.node_name = "#text"
        self.node_value = data
        self.data = data  # Alias for node_value
        self.length = len(data)
    
    @property
    def whole_text(self) -> str:
        """
        Get the text content of this node and all its merged text node siblings.
        
        Returns:
            The concatenated text content
        """
        result = []
        
        # Get previous siblings that are text nodes
        current = self
        while current.previous_sibling and current.previous_sibling.node_type == NodeType.TEXT_NODE:
            current = current.previous_sibling
            result.insert(0, current.data)
        
        # Add this node's text
        result.append(self.data)
        
        # Get next siblings that are text nodes
        current = self
        while current.next_sibling and current.next_sibling.node_type == NodeType.TEXT_NODE:
            current = current.next_sibling
            result.append(current.data)
        
        return "".join(result)
    
    def split_text(self, offset: int) -> 'Text':
        """
        Split this text node at the specified offset.
        
        Args:
            offset: The character position to split at
            
        Returns:
            A new text node containing the text after the offset
            
        Raises:
            ValueError: If the offset is invalid
        """
        if offset < 0 or offset > self.length:
            raise ValueError("Invalid split offset")
        
        if offset == 0 or offset == self.length:
            # Nothing to split
            return self
        
        # Extract the text for the new node
        new_data = self.data[offset:]
        
        # Update this node's text
        self.data = self.data[:offset]
        self.node_value = self.data
        self.length = len(self.data)
        
        # Create a new text node with the second part
        new_node = Text(new_data, self.owner_document)
        
        # Insert the new node after this one
        if self.parent_node:
            if self.next_sibling:
                self.parent_node.insert_before(new_node, self.next_sibling)
            else:
                self.parent_node.append_child(new_node)
        
        return new_node
    
    def substring_data(self, offset: int, count: int) -> str:
        """
        Extract a substring from the text node.
        
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
        Append data to the end of the text node.
        
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
    
    def clone_node(self, deep: bool = False) -> 'Text':
        """
        Clone this text node.
        
        Args:
            deep: Not used for text nodes
            
        Returns:
            A new text node with the same content
        """
        return Text(self.data, self.owner_document) 