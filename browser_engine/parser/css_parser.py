"""
CSS parser implementation with full support for modern CSS features.
This module is responsible for parsing and applying CSS styles to HTML elements.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Any
import cssutils
import urllib.parse

# Suppress cssutils warning logs - set to CRITICAL instead of ERROR to be even stricter
cssutils.log.setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

# CSS3 properties that contain URLs
URL_PROPERTIES = {
    'background', 'background-image', 'border-image', 'border-image-source', 
    'content', 'cursor', 'list-style', 'list-style-image', 'mask', 'mask-image',
    'src', '@import', '@font-face'
}

# Modern CSS features and properties
MODERN_CSS_PROPERTIES = {
    # Flexbox
    'flex', 'flex-basis', 'flex-direction', 'flex-flow', 'flex-grow', 'flex-shrink', 'flex-wrap',
    'align-content', 'align-items', 'align-self', 'justify-content', 'order',
    
    # Grid
    'grid', 'grid-area', 'grid-auto-columns', 'grid-auto-flow', 'grid-auto-rows',
    'grid-column', 'grid-column-end', 'grid-column-gap', 'grid-column-start',
    'grid-gap', 'grid-row', 'grid-row-end', 'grid-row-gap', 'grid-row-start',
    'grid-template', 'grid-template-areas', 'grid-template-columns', 'grid-template-rows',
    
    # Transforms and transitions
    'transform', 'transform-origin', 'transform-style', 'transition', 'transition-delay',
    'transition-duration', 'transition-property', 'transition-timing-function',
    
    # Animations
    'animation', 'animation-delay', 'animation-direction', 'animation-duration',
    'animation-fill-mode', 'animation-iteration-count', 'animation-name',
    'animation-play-state', 'animation-timing-function',
    
    # Other modern features
    'backdrop-filter', 'background-blend-mode', 'clip-path', 'filter', 'mix-blend-mode',
    'object-fit', 'object-position', 'opacity', 'pointer-events', 'shape-outside',
    'text-shadow', 'will-change'
}

class CSSParser:
    """CSS parser using cssutils with full CSS3 support."""
    
    def __init__(self):
        """Initialize the CSS parser."""
        # Configure cssutils for modern CSS
        cssutils.ser.prefs.useMinified = False
        cssutils.ser.prefs.keepComments = True
        cssutils.ser.prefs.omitLastSemicolon = False
        
        # Set up custom CSS error handling - ignore unknown properties
        cssutils.css.CSSStyleDeclaration.valid = True  # Don't validate property names
        
        logger.debug("CSS parser initialized with modern CSS support")
    
    def parse(self, css_content: str, base_url: Optional[str] = None) -> cssutils.css.CSSStyleSheet:
        """
        Parse CSS content into a stylesheet.
        
        Args:
            css_content: CSS content to parse
            base_url: Optional base URL for resolving relative URLs
            
        Returns:
            cssutils.css.CSSStyleSheet: Parsed stylesheet
        """
        try:
            # Parse the CSS content
            stylesheet = cssutils.parseString(css_content)
            
            # Resolve relative URLs if base_url is provided
            if base_url:
                self.resolve_urls(stylesheet, base_url)
                
            return stylesheet
        except Exception as e:
            logger.error(f"Error parsing CSS: {e}")
            # Return an empty stylesheet
            return cssutils.css.CSSStyleSheet()
    
    def resolve_urls(self, stylesheet: cssutils.css.CSSStyleSheet, base_url: str) -> None:
        """
        Resolve relative URLs in a stylesheet to absolute URLs.
        
        Args:
            stylesheet: CSS stylesheet
            base_url: Base URL for resolving relative URLs
        """
        # Determine if base URL is HTTPS, to ensure we upgrade HTTP URLs when appropriate
        is_https_base = base_url.startswith('https://')
        
        # Process @import rules
        for rule in stylesheet.cssRules:
            if rule.type == cssutils.css.CSSRule.IMPORT_RULE:
                if rule.href:
                    # Check if it's already an absolute URL
                    if not rule.href.startswith(('http://', 'https://', 'data:', 'file:')):
                        # It's a relative URL, resolve it
                        rule.href = urllib.parse.urljoin(base_url, rule.href)
                    # If base is HTTPS, ensure the imported CSS is also HTTPS
                    elif is_https_base and rule.href.startswith('http://'):
                        rule.href = 'https://' + rule.href[7:]
            
            # Process style rules
            elif rule.type == cssutils.css.CSSRule.STYLE_RULE:
                for property_name in rule.style:
                    property_value = rule.style[property_name]
                    if property_name in URL_PROPERTIES or 'url(' in property_value:
                        # Replace all URL references
                        new_value = self._resolve_css_urls(property_value, base_url, is_https_base)
                        rule.style[property_name] = new_value
            
            # Process @font-face rules
            elif rule.type == cssutils.css.CSSRule.FONT_FACE_RULE:
                for property_name in rule.style:
                    if property_name == 'src':
                        property_value = rule.style[property_name]
                        # Replace all URL references
                        new_value = self._resolve_css_urls(property_value, base_url, is_https_base)
                        rule.style[property_name] = new_value
    
    def _resolve_css_urls(self, css_value: str, base_url: str, upgrade_to_https: bool = False) -> str:
        """
        Resolve URLs in CSS values.
        
        Args:
            css_value: CSS property value
            base_url: Base URL for resolving relative URLs
            upgrade_to_https: Whether to upgrade HTTP URLs to HTTPS
            
        Returns:
            str: CSS value with resolved URLs
        """
        def replace_url(match):
            url = match.group(1)
            # Remove quotes if present
            if url.startswith('"') and url.endswith('"'):
                url = url[1:-1]
            elif url.startswith("'") and url.endswith("'"):
                url = url[1:-1]
                
            # Only resolve if not already absolute or special protocol
            if not url.startswith(('http://', 'https://', 'data:', 'file:', '#')):
                url = urllib.parse.urljoin(base_url, url)
            # Upgrade HTTP to HTTPS if requested and the URL is HTTP
            elif upgrade_to_https and url.startswith('http://'):
                url = 'https://' + url[7:]
                
            # Add quotes around the URL if it contains characters that need escaping
            if ' ' in url or ',' in url or '(' in url or ')' in url:
                url = f'"{url}"'
                
            return f"url({url})"
        
        # Replace URLs in CSS value
        return re.sub(r'url\(([^)]+)\)', replace_url, css_value)
    
    def extract_styles(self, stylesheet: cssutils.css.CSSStyleSheet) -> Dict[str, Dict[str, str]]:
        """
        Extract styles from a stylesheet organized by selector.
        
        Args:
            stylesheet: CSS stylesheet
            
        Returns:
            Dict[str, Dict[str, str]]: Dictionary of styles by selector
        """
        styles = {}
        
        # Process each rule in the stylesheet
        for rule in stylesheet.cssRules:
            if rule.type == cssutils.css.CSSRule.STYLE_RULE:
                # Get the selector and style properties
                selector = rule.selectorText
                properties = {}
                
                for property_name in rule.style:
                    property_value = rule.style[property_name]
                    properties[property_name] = property_value
                
                # Add to styles dictionary
                if selector in styles:
                    # Merge with existing styles
                    styles[selector].update(properties)
                else:
                    styles[selector] = properties
        
        return styles
    
    def get_computed_style(self, element_attributes: Dict[str, str], rules: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        """
        Get computed style for an element based on CSS rules and element attributes.
        
        Args:
            element_attributes: Element attributes (id, class, tag, etc.)
            rules: Dictionary of CSS rules by selector
            
        Returns:
            Dict[str, str]: Computed style for the element
        """
        computed_style = {}
        
        # Get tag name, ID, and classes from element attributes
        tag_name = element_attributes.get('tag', '').lower()
        element_id = element_attributes.get('id', '')
        classes = element_attributes.get('class', '').split()
        
        # Helper function to check if a selector matches the element
        def selector_matches(selector: str) -> bool:
            # Simple implementation for common selector patterns
            selector = selector.strip()
            
            # Check for ID selector: #id
            if selector.startswith('#'):
                return element_id and selector[1:] == element_id
            
            # Check for class selector: .class
            if selector.startswith('.'):
                return selector[1:] in classes
            
            # Check for tag selector: tag
            if selector.lower() == tag_name:
                return True
            
            # Check for tag.class selector: tag.class
            if '.' in selector and selector.split('.')[0].lower() == tag_name:
                class_name = selector.split('.')[1]
                return class_name in classes
            
            # Check for tag#id selector: tag#id
            if '#' in selector and selector.split('#')[0].lower() == tag_name:
                selector_id = selector.split('#')[1]
                return selector_id == element_id
            
            # Simple implementation for parent > child selector
            if '>' in selector:
                parts = selector.split('>')
                child_selector = parts[-1].strip()
                # Check only the child part
                return selector_matches(child_selector)
            
            # Simple implementation for descendant selector (space)
            if ' ' in selector:
                parts = selector.split()
                child_selector = parts[-1].strip()
                # Check only the last part
                return selector_matches(child_selector)
            
            # For more complex selectors, a more sophisticated approach would be needed
            return False
        
        # Apply CSS rules in order of specificity (a very simplified approach)
        # In a real browser, specificity is calculated more thoroughly
        
        # First, apply styles for tag selectors (lowest specificity)
        for selector, properties in rules.items():
            if selector.lower() == tag_name:
                computed_style.update(properties)
        
        # Next, apply styles for class selectors
        for selector, properties in rules.items():
            if selector.startswith('.') and selector[1:] in classes:
                computed_style.update(properties)
        
        # Finally, apply styles for ID selectors (highest specificity)
        for selector, properties in rules.items():
            if selector.startswith('#') and selector[1:] == element_id:
                computed_style.update(properties)
        
        # Apply more complex selectors if they match
        for selector, properties in rules.items():
            if '>' in selector or ' ' in selector or ',' in selector:
                if selector_matches(selector):
                    computed_style.update(properties)
        
        # Apply inline styles (highest precedence)
        if 'style' in element_attributes:
            inline_styles = self.parse_inline_styles(element_attributes['style'])
            computed_style.update(inline_styles)
        
        return computed_style
    
    def parse_inline_styles(self, style_attr: str) -> Dict[str, str]:
        """
        Parse inline styles from a style attribute.
        
        Args:
            style_attr: Style attribute value
            
        Returns:
            Dict[str, str]: Dictionary of CSS properties and values
        """
        styles = {}
        
        if not style_attr:
            return styles
        
        # Split by semicolons and extract property-value pairs
        for declaration in style_attr.split(';'):
            if ':' in declaration:
                property_name, property_value = declaration.split(':', 1)
                property_name = property_name.strip()
                property_value = property_value.strip()
                styles[property_name] = property_value
        
        return styles
    
    def get_style_rules_for_document(self, stylesheets: List[cssutils.css.CSSStyleSheet]) -> Dict[str, Dict[str, str]]:
        """
        Get all style rules from multiple stylesheets.
        
        Args:
            stylesheets: List of CSS stylesheets
            
        Returns:
            Dict[str, Dict[str, str]]: Dictionary of style rules by selector
        """
        all_rules = {}
        
        for stylesheet in stylesheets:
            rules = self.extract_styles(stylesheet)
            
            # Merge with existing rules
            for selector, properties in rules.items():
                if selector in all_rules:
                    all_rules[selector].update(properties)
                else:
                    all_rules[selector] = properties
        
        return all_rules
    
    def parse_media_queries(self, stylesheet: cssutils.css.CSSStyleSheet) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse media queries from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary of media queries with their rules
        """
        media_queries = {}
        
        for rule in stylesheet.cssRules:
            if rule.type == cssutils.css.CSSRule.MEDIA_RULE:
                media_text = rule.media.mediaText
                
                if media_text not in media_queries:
                    media_queries[media_text] = []
                
                # Extract style rules within this media query
                for media_rule in rule.cssRules:
                    if media_rule.type == cssutils.css.CSSRule.STYLE_RULE:
                        selector = media_rule.selectorText
                        properties = {}
                        
                        for property_name in media_rule.style:
                            property_value = media_rule.style[property_name]
                            properties[property_name] = property_value
                        
                        media_queries[media_text].append({
                            'selector': selector,
                            'properties': properties
                        })
        
        return media_queries
    
    def parse_keyframes(self, stylesheet: cssutils.css.CSSStyleSheet) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse CSS keyframes for animations from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary of keyframes by animation name
        """
        keyframes = {}
        
        for rule in stylesheet.cssRules:
            if rule.type == cssutils.css.CSSRule.KEYFRAMES_RULE:
                animation_name = rule.name
                frames = []
                
                for keyframe_rule in rule.cssRules:
                    # Extract keyframe selector (e.g., "0%", "from", "to", etc.)
                    keytext = keyframe_rule.keyText
                    properties = {}
                    
                    for property_name in keyframe_rule.style:
                        property_value = keyframe_rule.style[property_name]
                        properties[property_name] = property_value
                    
                    frames.append({
                        'keytext': keytext,
                        'properties': properties
                    })
                
                keyframes[animation_name] = frames
        
        return keyframes
    
    def parse_font_face_rules(self, stylesheet: cssutils.css.CSSStyleSheet) -> List[Dict[str, str]]:
        """
        Parse @font-face rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet
            
        Returns:
            List[Dict[str, str]]: List of font face definitions
        """
        font_faces = []
        
        for rule in stylesheet.cssRules:
            if rule.type == cssutils.css.CSSRule.FONT_FACE_RULE:
                font_face = {}
                
                for property_name in rule.style:
                    property_value = rule.style[property_name]
                    font_face[property_name] = property_value
                
                font_faces.append(font_face)
        
        return font_faces
    
    def specificity(self, selector: str) -> Tuple[int, int, int]:
        """
        Calculate the specificity of a CSS selector.
        
        The specificity is a tuple of (a, b, c) where:
        - a is the number of ID selectors
        - b is the number of class selectors, attribute selectors, and pseudo-classes
        - c is the number of element selectors and pseudo-elements
        
        Args:
            selector: CSS selector
            
        Returns:
            Tuple[int, int, int]: Specificity tuple
        """
        # Count of ID selectors
        a = len(re.findall(r'#[a-zA-Z0-9_-]+', selector))
        
        # Count of class selectors, attribute selectors, and pseudo-classes
        b = len(re.findall(r'\.[a-zA-Z0-9_-]+', selector))  # Class selectors
        b += len(re.findall(r'\[[^\]]+\]', selector))  # Attribute selectors
        b += len(re.findall(r':[a-zA-Z0-9_-]+(?!\()', selector))  # Pseudo-classes
        
        # Count of element selectors and pseudo-elements
        c = len(re.findall(r'(?:^|[\s>+~])([a-zA-Z0-9_-]+)', selector))  # Element selectors
        c += len(re.findall(r'::[a-zA-Z0-9_-]+', selector))  # Pseudo-elements
        
        return (a, b, c)
    
    def sort_selectors_by_specificity(self, selectors: List[str]) -> List[str]:
        """
        Sort CSS selectors by specificity in ascending order.
        
        Args:
            selectors: List of CSS selectors
            
        Returns:
            List[str]: Sorted list of selectors
        """
        return sorted(selectors, key=self.specificity) 