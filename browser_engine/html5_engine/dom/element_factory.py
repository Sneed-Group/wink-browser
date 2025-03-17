class ElementFactory:
    """
    Factory class for creating HTML elements.
    """
    
    @classmethod
    def create_element(cls, tag_name: str, attributes: Dict[str, str] = None, document=None) -> Element:
        """
        Create an element based on tag name.
        
        Args:
            tag_name: HTML tag name
            attributes: Element attributes
            document: Parent document
            
        Returns:
            Appropriate Element subclass instance
        """
        tag_name = tag_name.lower()
        attributes = attributes or {}
        
        # Block elements
        if tag_name == 'div':
            return DivElement(tag_name, attributes, document)
        elif tag_name == 'p':
            return ParagraphElement(tag_name, attributes, document)
        elif tag_name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            return HeadingElement(tag_name, attributes, document)
        elif tag_name in ('ul', 'ol'):
            return ListElement(tag_name, attributes, document)
        elif tag_name == 'li':
            return ListItemElement(tag_name, attributes, document)
        elif tag_name == 'table':
            return TableElement(tag_name, attributes, document)
        elif tag_name in ('tr', 'thead', 'tbody', 'tfoot'):
            return TableRowElement(tag_name, attributes, document)
        elif tag_name in ('td', 'th'):
            return TableCellElement(tag_name, attributes, document)
        
        # Inline elements
        elif tag_name == 'a':
            return AnchorElement(tag_name, attributes, document)
        elif tag_name == 'img':
            return ImageElement(tag_name, attributes, document)
        elif tag_name in ('strong', 'b'):
            return StrongElement(tag_name, attributes, document)
        elif tag_name in ('em', 'i'):
            return EmphasisElement(tag_name, attributes, document)
        elif tag_name == 'u':
            return UnderlineElement(tag_name, attributes, document)
        elif tag_name in ('s', 'strike', 'del'):
            return StrikethroughElement(tag_name, attributes, document)
        elif tag_name == 'span':
            return SpanElement(tag_name, attributes, document)
        elif tag_name == 'br':
            return LineBreakElement(tag_name, attributes, document)
        
        # Form elements
        elif tag_name == 'form':
            return FormElement(tag_name, attributes, document)
        elif tag_name == 'input':
            return InputElement(tag_name, attributes, document)
        elif tag_name == 'button':
            return ButtonElement(tag_name, attributes, document)
        elif tag_name == 'textarea':
            return TextAreaElement(tag_name, attributes, document)
        elif tag_name == 'select':
            return SelectElement(tag_name, attributes, document)
        elif tag_name == 'option':
            return OptionElement(tag_name, attributes, document)
        
        # Media elements
        elif tag_name == 'audio':
            return AudioElement(tag_name, attributes, document)
        elif tag_name == 'video':
            return VideoElement(tag_name, attributes, document)
        elif tag_name == 'source':
            return SourceElement(tag_name, attributes, document)
        
        # Default
        return Element(tag_name, attributes, document)

class DivElement(Element):
    """
    HTML <div> element representation.
    
    A generic block-level container for content.
    """
    
    def __init__(self, tag_name: str, attributes: Dict[str, str] = None, document=None):
        """
        Initialize a div element.
        
        Args:
            tag_name: The tag name (should be 'div')
            attributes: Element attributes
            document: Parent document
        """
        super().__init__(tag_name, attributes, document)
        self.style['display'] = 'block'

class SpanElement(Element):
    """
    HTML <span> element representation.
    
    A generic inline container for content.
    """
    
    def __init__(self, tag_name: str, attributes: Dict[str, str] = None, document=None):
        """
        Initialize a span element.
        
        Args:
            tag_name: The tag name (should be 'span')
            attributes: Element attributes
            document: Parent document
        """
        super().__init__(tag_name, attributes, document)
        self.style['display'] = 'inline'

class StrongElement(Element):
    """
    HTML <strong> or <b> element representation.
    
    Represents strong importance, seriousness, or urgency.
    """
    
    def __init__(self, tag_name: str, attributes: Dict[str, str] = None, document=None):
        """
        Initialize a strong element.
        
        Args:
            tag_name: The tag name ('strong' or 'b')
            attributes: Element attributes
            document: Parent document
        """
        super().__init__(tag_name, attributes, document)
        self.style['display'] = 'inline'
        self.style['font-weight'] = 'bold'

class EmphasisElement(Element):
    """
    HTML <em> or <i> element representation.
    
    Marks text that has stress emphasis.
    """
    
    def __init__(self, tag_name: str, attributes: Dict[str, str] = None, document=None):
        """
        Initialize an emphasis element.
        
        Args:
            tag_name: The tag name ('em' or 'i')
            attributes: Element attributes
            document: Parent document
        """
        super().__init__(tag_name, attributes, document)
        self.style['display'] = 'inline'
        self.style['font-style'] = 'italic'

class UnderlineElement(Element):
    """
    HTML <u> element representation.
    
    Represents text that should be stylistically different,
    such as misspelled words or proper nouns in Chinese.
    """
    
    def __init__(self, tag_name: str, attributes: Dict[str, str] = None, document=None):
        """
        Initialize an underline element.
        
        Args:
            tag_name: The tag name (should be 'u')
            attributes: Element attributes
            document: Parent document
        """
        super().__init__(tag_name, attributes, document)
        self.style['display'] = 'inline'
        self.style['text-decoration'] = 'underline'

class StrikethroughElement(Element):
    """
    HTML <s>, <strike>, or <del> element representation.
    
    Represents text that is no longer correct, accurate or relevant.
    """
    
    def __init__(self, tag_name: str, attributes: Dict[str, str] = None, document=None):
        """
        Initialize a strikethrough element.
        
        Args:
            tag_name: The tag name ('s', 'strike', or 'del')
            attributes: Element attributes
            document: Parent document
        """
        super().__init__(tag_name, attributes, document)
        self.style['display'] = 'inline'
        self.style['text-decoration'] = 'line-through' 