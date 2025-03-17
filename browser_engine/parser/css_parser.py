"""
CSS parser implementation.
This module is responsible for parsing CSS content.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple, Union
import cssutils

logger = logging.getLogger(__name__)

# Suppress excessive warnings from cssutils
cssutils.log.setLevel(logging.ERROR)

class CSSParser:
    """CSS parser using cssutils."""
    
    def __init__(self):
        """Initialize the CSS parser."""
        self.cssutils_parser = cssutils.CSSParser(raiseExceptions=False)
        logger.debug("CSS parser initialized")
    
    def parse(self, css_content: str) -> cssutils.css.CSSStyleSheet:
        """
        Parse CSS content.
        
        Args:
            css_content: CSS content to parse
            
        Returns:
            cssutils.css.CSSStyleSheet: Parsed CSS stylesheet
        """
        try:
            stylesheet = self.cssutils_parser.parseString(css_content)
            return stylesheet
        except Exception as e:
            logger.error(f"Error parsing CSS: {e}")
            # Return an empty stylesheet
            return cssutils.css.CSSStyleSheet()
    
    def get_rules_for_selector(self, 
                               stylesheet: cssutils.css.CSSStyleSheet, 
                               selector: str) -> List[Dict[str, str]]:
        """
        Get CSS rules that match a selector.
        
        Args:
            stylesheet: CSS stylesheet
            selector: CSS selector to match
            
        Returns:
            List[Dict[str, str]]: List of CSS rules as property-value dictionaries
        """
        matching_rules = []
        
        try:
            for rule in stylesheet.cssRules:
                # Check if it's a style rule (not an @import, @media, etc.)
                if rule.type == rule.STYLE_RULE:
                    # Check if our selector matches any of the rule's selectors
                    for rule_selector in rule.selectorList:
                        if self._selector_matches(rule_selector.selectorText, selector):
                            # Extract all properties
                            properties = {}
                            for property_name in rule.style:
                                properties[property_name] = rule.style[property_name]
                            
                            matching_rules.append(properties)
        except Exception as e:
            logger.error(f"Error processing rules for selector '{selector}': {e}")
        
        return matching_rules
    
    def _selector_matches(self, rule_selector: str, element_selector: str) -> bool:
        """
        Check if a rule selector matches an element selector.
        This is a simple implementation and doesn't handle all CSS selector cases.
        
        Args:
            rule_selector: CSS rule selector
            element_selector: Element selector to check
            
        Returns:
            bool: True if the rule selector matches the element selector
        """
        # In a real browser, this would be much more complex
        # For now, we'll do a simple exact match or basic wildcard
        return rule_selector == element_selector or rule_selector == '*'
    
    def get_all_rules(self, stylesheet: cssutils.css.CSSStyleSheet) -> Dict[str, List[Dict[str, str]]]:
        """
        Get all CSS rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet
            
        Returns:
            Dict[str, List[Dict[str, str]]]: Dictionary mapping selectors to lists of rules
        """
        all_rules = {}
        
        try:
            for rule in stylesheet.cssRules:
                if rule.type == rule.STYLE_RULE:
                    # Extract selector text
                    selector = rule.selectorText
                    
                    # Extract properties
                    properties = {}
                    for property_name in rule.style:
                        properties[property_name] = rule.style[property_name]
                    
                    # Add to dictionary
                    if selector not in all_rules:
                        all_rules[selector] = []
                    
                    all_rules[selector].append(properties)
        except Exception as e:
            logger.error(f"Error extracting all rules: {e}")
        
        return all_rules
    
    def get_media_queries(self, stylesheet: cssutils.css.CSSStyleSheet) -> Dict[str, List[Dict[str, List[Dict[str, str]]]]]:
        """
        Get all media queries from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet
            
        Returns:
            Dict[str, List[Dict[str, List[Dict[str, str]]]]]: Dictionary mapping media queries to lists of selector-rules mappings
        """
        media_queries = {}
        
        try:
            for rule in stylesheet.cssRules:
                if rule.type == rule.MEDIA_RULE:
                    media_text = rule.media.mediaText
                    
                    if media_text not in media_queries:
                        media_queries[media_text] = []
                    
                    media_rules = {}
                    
                    # Process rules inside the media query
                    for media_rule in rule.cssRules:
                        if media_rule.type == media_rule.STYLE_RULE:
                            selector = media_rule.selectorText
                            
                            # Extract properties
                            properties = {}
                            for property_name in media_rule.style:
                                properties[property_name] = media_rule.style[property_name]
                            
                            # Add to dictionary
                            if selector not in media_rules:
                                media_rules[selector] = []
                            
                            media_rules[selector].append(properties)
                    
                    media_queries[media_text].append(media_rules)
        except Exception as e:
            logger.error(f"Error extracting media queries: {e}")
        
        return media_queries
    
    def get_font_face_rules(self, stylesheet: cssutils.css.CSSStyleSheet) -> List[Dict[str, str]]:
        """
        Get all @font-face rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet
            
        Returns:
            List[Dict[str, str]]: List of font-face rules
        """
        font_face_rules = []
        
        try:
            for rule in stylesheet.cssRules:
                if rule.type == rule.FONT_FACE_RULE:
                    # Extract properties
                    properties = {}
                    for property_name in rule.style:
                        properties[property_name] = rule.style[property_name]
                    
                    font_face_rules.append(properties)
        except Exception as e:
            logger.error(f"Error extracting font-face rules: {e}")
        
        return font_face_rules
    
    def get_keyframe_rules(self, stylesheet: cssutils.css.CSSStyleSheet) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Get all @keyframes rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet
            
        Returns:
            Dict[str, Dict[str, Dict[str, str]]]: Dictionary mapping animation names to keyframes
        """
        keyframe_rules = {}
        
        try:
            for rule in stylesheet.cssRules:
                if rule.type == rule.KEYFRAMES_RULE:
                    animation_name = rule.name
                    keyframes = {}
                    
                    # Process keyframes
                    for keyframe_rule in rule.cssRules:
                        if keyframe_rule.type == keyframe_rule.KEYFRAME_RULE:
                            keytext = keyframe_rule.keyText  # e.g., "0%", "50%", "from", "to"
                            
                            # Extract properties
                            properties = {}
                            for property_name in keyframe_rule.style:
                                properties[property_name] = keyframe_rule.style[property_name]
                            
                            keyframes[keytext] = properties
                    
                    keyframe_rules[animation_name] = keyframes
        except Exception as e:
            logger.error(f"Error extracting keyframe rules: {e}")
        
        return keyframe_rules
    
    def get_import_rules(self, stylesheet: cssutils.css.CSSStyleSheet) -> List[str]:
        """
        Get all @import rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet
            
        Returns:
            List[str]: List of imported stylesheet URLs
        """
        import_rules = []
        
        try:
            for rule in stylesheet.cssRules:
                if rule.type == rule.IMPORT_RULE:
                    import_rules.append(rule.href)
        except Exception as e:
            logger.error(f"Error extracting import rules: {e}")
        
        return import_rules
    
    def get_computed_style(self, 
                           element_style: Dict[str, str], 
                           parent_style: Dict[str, str],
                           stylesheet_rules: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Calculate computed style for an element.
        
        Args:
            element_style: Inline style of the element
            parent_style: Computed style of the parent element
            stylesheet_rules: CSS rules from stylesheets that apply to this element
            
        Returns:
            Dict[str, str]: Computed style
        """
        # Start with inherited properties from parent
        computed_style = {}
        
        # List of properties that are inherited from parent
        inherited_properties = [
            'color', 'font-family', 'font-size', 'font-style', 'font-weight',
            'line-height', 'list-style', 'text-align', 'text-indent',
            'text-transform', 'visibility', 'white-space', 'word-spacing'
        ]
        
        # Copy inherited properties from parent
        for prop in inherited_properties:
            if prop in parent_style:
                computed_style[prop] = parent_style[prop]
        
        # Apply stylesheet rules (lowest specificity first)
        for rule in stylesheet_rules:
            for prop, value in rule.items():
                computed_style[prop] = value
        
        # Apply inline style (highest specificity)
        for prop, value in element_style.items():
            computed_style[prop] = value
        
        return computed_style
    
    def create_stylesheet(self) -> cssutils.css.CSSStyleSheet:
        """
        Create a new empty stylesheet.
        
        Returns:
            cssutils.css.CSSStyleSheet: Empty stylesheet
        """
        return cssutils.css.CSSStyleSheet()
    
    def add_rule(self, 
                 stylesheet: cssutils.css.CSSStyleSheet, 
                 selector: str, 
                 properties: Dict[str, str]) -> None:
        """
        Add a rule to a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet
            selector: CSS selector
            properties: Dictionary of CSS properties
        """
        try:
            # Convert properties dict to CSS text
            css_text = '; '.join([f"{prop}: {value}" for prop, value in properties.items()])
            
            # Add the rule to the stylesheet
            stylesheet.add(f'{selector} {{ {css_text} }}')
        except Exception as e:
            logger.error(f"Error adding rule to stylesheet: {e}")
    
    def get_css_string(self, stylesheet: cssutils.css.CSSStyleSheet) -> str:
        """
        Convert a stylesheet to a CSS string.
        
        Args:
            stylesheet: CSS stylesheet
            
        Returns:
            str: CSS string
        """
        return stylesheet.cssText.decode('utf-8') 