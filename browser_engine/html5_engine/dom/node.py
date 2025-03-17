"""
Node implementation for the DOM.
This module implements the DOM Node interface according to HTML5 specifications.
"""

from enum import IntEnum
from typing import Dict, List, Optional, Any, Union, Set, Iterator
import weakref

class NodeType(IntEnum):
    """Node types as defined in the HTML5 specification."""
    ELEMENT_NODE = 1
    ATTRIBUTE_NODE = 2
    TEXT_NODE = 3
    CDATA_SECTION_NODE = 4
    ENTITY_REFERENCE_NODE = 5  # Legacy
    ENTITY_NODE = 6  # Legacy
    PROCESSING_INSTRUCTION_NODE = 7
    COMMENT_NODE = 8
    DOCUMENT_NODE = 9
    DOCUMENT_TYPE_NODE = 10
    DOCUMENT_FRAGMENT_NODE = 11
    NOTATION_NODE = 12  # Legacy


class Node:
    """
    Base Node implementation for the DOM.
    
    This class implements the core functionality of the DOM Node interface
    according to the HTML5 specification.
    """
    
    def __init__(self, node_type: NodeType, owner_document: Optional['Document'] = None):
        """
        Initialize a new Node.
        
        Args:
            node_type: The type of this node
            owner_document: The document that owns this node
        """
        self.node_type = node_type
        self.owner_document = owner_document
        
        # Node relationships
        self.parent_node: Optional['Node'] = None
        self.child_nodes: List['Node'] = []
        self.first_child: Optional['Node'] = None
        self.last_child: Optional['Node'] = None
        self.previous_sibling: Optional['Node'] = None
        self.next_sibling: Optional['Node'] = None
        
        # Node properties
        self.node_name: str = "#node"
        self.node_value: Optional[str] = None
        self.text_content: Optional[str] = None
        
        # Event handlers
        self._event_listeners: Dict[str, List[callable]] = {}
    
    @property
    def child_element_count(self) -> int:
        """Get the number of child elements."""
        return sum(1 for child in self.child_nodes if child.node_type == NodeType.ELEMENT_NODE)
    
    @property
    def children(self) -> List['Element']:
        """Get a list of child elements."""
        return [child for child in self.child_nodes if child.node_type == NodeType.ELEMENT_NODE]
    
    def append_child(self, child: 'Node') -> 'Node':
        """
        Append a child node to this node.
        
        Args:
            child: The node to append
            
        Returns:
            The appended node
        """
        # If child already has a parent, remove it first
        if child.parent_node:
            child.parent_node.remove_child(child)
        
        # Set parent-child relationships
        child.parent_node = self
        
        # Set sibling relationships
        if self.child_nodes:
            last_child = self.child_nodes[-1]
            last_child.next_sibling = child
            child.previous_sibling = last_child
        
        # Add to child nodes list
        self.child_nodes.append(child)
        
        # Update first_child and last_child references
        if not self.first_child:
            self.first_child = child
        self.last_child = child
        
        return child
    
    def insert_before(self, new_child: 'Node', reference_child: Optional['Node'] = None) -> 'Node':
        """
        Insert a node before a reference node.
        
        Args:
            new_child: The node to insert
            reference_child: The reference node to insert before, or None to append
            
        Returns:
            The inserted node
        """
        if reference_child is None:
            return self.append_child(new_child)
        
        if reference_child not in self.child_nodes:
            raise ValueError("Reference child not found in child nodes")
        
        # If new_child already has a parent, remove it first
        if new_child.parent_node:
            new_child.parent_node.remove_child(new_child)
        
        # Set parent-child relationships
        new_child.parent_node = self
        
        # Find reference child index
        index = self.child_nodes.index(reference_child)
        
        # Set sibling relationships
        prev_sibling = reference_child.previous_sibling
        
        # Update sibling references
        new_child.next_sibling = reference_child
        new_child.previous_sibling = prev_sibling
        reference_child.previous_sibling = new_child
        
        if prev_sibling:
            prev_sibling.next_sibling = new_child
        
        # Add to child nodes list at the correct position
        self.child_nodes.insert(index, new_child)
        
        # Update first_child reference if needed
        if index == 0:
            self.first_child = new_child
        
        return new_child
    
    def remove_child(self, child: 'Node') -> 'Node':
        """
        Remove a child node from this node.
        
        Args:
            child: The node to remove
            
        Returns:
            The removed node
        """
        if child not in self.child_nodes:
            raise ValueError("Child not found in child nodes")
        
        # Update sibling relationships
        prev_sibling = child.previous_sibling
        next_sibling = child.next_sibling
        
        if prev_sibling:
            prev_sibling.next_sibling = next_sibling
        
        if next_sibling:
            next_sibling.previous_sibling = prev_sibling
        
        # Update first_child and last_child references
        if self.first_child == child:
            self.first_child = next_sibling
        
        if self.last_child == child:
            self.last_child = prev_sibling
        
        # Remove parent reference
        child.parent_node = None
        child.previous_sibling = None
        child.next_sibling = None
        
        # Remove from child nodes list
        self.child_nodes.remove(child)
        
        return child
    
    def replace_child(self, new_child: 'Node', old_child: 'Node') -> 'Node':
        """
        Replace a child node with another node.
        
        Args:
            new_child: The replacement node
            old_child: The node to replace
            
        Returns:
            The replaced node
        """
        if old_child not in self.child_nodes:
            raise ValueError("Old child not found in child nodes")
        
        index = self.child_nodes.index(old_child)
        self.remove_child(old_child)
        
        if index == len(self.child_nodes):
            self.append_child(new_child)
        else:
            self.insert_before(new_child, self.child_nodes[index])
        
        return old_child
    
    def has_child_nodes(self) -> bool:
        """Check if this node has any child nodes."""
        return len(self.child_nodes) > 0
    
    def clone_node(self, deep: bool = False) -> 'Node':
        """
        Clone this node.
        
        Args:
            deep: Whether to clone child nodes as well
            
        Returns:
            The cloned node
        """
        # Create a new node of the same type
        clone = self.__class__(self.node_type, self.owner_document)
        
        # Copy basic properties
        clone.node_name = self.node_name
        clone.node_value = self.node_value
        clone.text_content = self.text_content
        
        # Deep clone if requested
        if deep and self.child_nodes:
            for child in self.child_nodes:
                child_clone = child.clone_node(deep=True)
                clone.append_child(child_clone)
        
        return clone
    
    def normalize(self) -> None:
        """
        Normalize the node by merging adjacent text nodes and removing empty text nodes.
        """
        # Process from end to beginning to avoid issues with node removal
        i = len(self.child_nodes) - 1
        
        while i >= 0:
            child = self.child_nodes[i]
            
            # Recursively normalize child nodes
            if child.node_type == NodeType.ELEMENT_NODE:
                child.normalize()
            
            # Remove empty text nodes
            if child.node_type == NodeType.TEXT_NODE and (child.node_value is None or child.node_value == ""):
                self.remove_child(child)
            
            # Merge adjacent text nodes
            elif (child.node_type == NodeType.TEXT_NODE and 
                  i > 0 and 
                  self.child_nodes[i-1].node_type == NodeType.TEXT_NODE):
                prev_text = self.child_nodes[i-1]
                prev_text.node_value = (prev_text.node_value or "") + (child.node_value or "")
                self.remove_child(child)
            
            i -= 1
    
    def is_equal_node(self, other: 'Node') -> bool:
        """
        Check if this node is equal to another node.
        
        Args:
            other: The node to compare with
            
        Returns:
            True if the nodes are equal, False otherwise
        """
        if not isinstance(other, Node) or self.node_type != other.node_type:
            return False
        
        if self.node_name != other.node_name or self.node_value != other.node_value:
            return False
        
        # Check child nodes
        if len(self.child_nodes) != len(other.child_nodes):
            return False
        
        for i in range(len(self.child_nodes)):
            if not self.child_nodes[i].is_equal_node(other.child_nodes[i]):
                return False
        
        return True
    
    def contains(self, other: Optional['Node']) -> bool:
        """
        Check if this node contains another node.
        
        Args:
            other: The node to check
            
        Returns:
            True if this node contains the other node, False otherwise
        """
        if other is None:
            return False
        
        if self == other:
            return True
        
        current = other.parent_node
        while current:
            if current == self:
                return True
            current = current.parent_node
        
        return False
    
    # Event methods
    def add_event_listener(self, event_type: str, listener: callable) -> None:
        """
        Add an event listener for a specific event type.
        
        Args:
            event_type: The type of event to listen for
            listener: The event listener function
        """
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        
        if listener not in self._event_listeners[event_type]:
            self._event_listeners[event_type].append(listener)
    
    def remove_event_listener(self, event_type: str, listener: callable) -> None:
        """
        Remove an event listener for a specific event type.
        
        Args:
            event_type: The type of event to remove
            listener: The event listener function to remove
        """
        if event_type in self._event_listeners and listener in self._event_listeners[event_type]:
            self._event_listeners[event_type].remove(listener)
    
    def dispatch_event(self, event: 'Event') -> bool:
        """
        Dispatch an event to this node.
        
        Args:
            event: The event to dispatch
            
        Returns:
            True if the event's default action was prevented, False otherwise
        """
        event_type = event.type
        
        # Set target and current target
        if event.target is None:
            event.target = self
        
        event.current_target = self
        
        # Call event listeners
        if event_type in self._event_listeners:
            for listener in self._event_listeners[event_type]:
                try:
                    listener(event)
                except Exception as e:
                    if self.owner_document:
                        self.owner_document.handle_error(f"Event listener error: {e}")
        
        return not event.default_prevented

    @property
    def textContent(self) -> str:
        """
        Get the text content of this node and all its descendants.
        
        Returns:
            The concatenated text content of this node and its descendants
        """
        # Initialize with empty string
        result = ""
        
        # For text nodes, return the node value
        if self.node_type == NodeType.TEXT_NODE:
            return self.node_value or ""
            
        # For other nodes, recursively get text from children
        for child in self.child_nodes:
            # Get child's text content
            if hasattr(child, 'textContent'):
                child_text = child.textContent
                # Ensure child_text is a string
                if child_text is not None:
                    if isinstance(child_text, str):
                        result += child_text
                    else:
                        # Try to convert to string if it's not already a string
                        try:
                            result += str(child_text)
                        except Exception:
                            # If conversion fails, just skip this child
                            pass
                
        return result 