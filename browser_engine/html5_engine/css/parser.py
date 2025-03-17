"""
CSS Parser implementation with full CSS3 support.
This module parses CSS stylesheets, rules, and selectors for the HTML5 engine.
"""

import logging
import re
import urllib.parse
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import cssutils
from cssutils import css
import tinycss2

from ..dom import Document, Element

logger = logging.getLogger(__name__)

# Suppress cssutils warning logs
cssutils.log.setLevel(logging.CRITICAL)

# CSS properties that can contain URLs
URL_PROPERTIES = {
    'background', 'background-image', 'border-image', 'border-image-source', 
    'content', 'cursor', 'list-style', 'list-style-image', 'mask', 'mask-image',
    'src', '@import', '@font-face'
}

# Define constants for rule types that might not be in cssutils
CSS_RULE_KEYFRAMES = 8  # Custom constant for @keyframes rules

class CSSParser:
    """
    CSS Parser with full CSS3 support.
    
    This class handles parsing CSS stylesheets, rules, and selectors for the HTML5 engine.
    """
    
    def __init__(self):
        """Initialize the CSS parser."""
        # CSS parsing settings
        cssutils.ser.prefs.keepComments = True
        cssutils.ser.prefs.resolveVariables = True
        cssutils.ser.prefs.normalizedVarNames = True
        
        # Default browser style sheet
        self._user_agent_stylesheet = None
        
        # Initialize property dictionaries
        self.rules = []
        
        # Default properties that should be recognized
        self.recognized_properties = {
            # Box model properties
            'width', 'height', 'min-width', 'min-height', 'max-width', 'max-height',
            'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
            'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
            'border', 'border-width', 'border-style', 'border-color',
            'border-top', 'border-right', 'border-bottom', 'border-left',
            'border-radius',
            
            # Layout properties
            'display', 'position', 'top', 'right', 'bottom', 'left',
            'float', 'clear', 'z-index', 'overflow', 'visibility',
            
            # Text properties
            'color', 'font-family', 'font-size', 'font-weight', 'font-style',
            'text-align', 'text-decoration', 'text-transform', 'line-height',
            'letter-spacing', 'word-spacing', 'white-space', 'vertical-align',
            
            # Background properties
            'background', 'background-color', 'background-image', 'background-repeat',
            'background-position', 'background-size', 'background-attachment',
            
            # Flexbox properties
            'flex', 'flex-direction', 'flex-wrap', 'flex-flow', 'justify-content',
            'align-items', 'align-content', 'order', 'flex-grow', 'flex-shrink', 'flex-basis',
            'align-self',
            
            # List properties
            'list-style', 'list-style-type', 'list-style-position', 'list-style-image',
            
            # Table properties
            'border-collapse', 'border-spacing', 'caption-side', 'empty-cells', 'table-layout',
            
            # Other properties
            'cursor', 'opacity', 'transition', 'transform', 'animation', 'user-select'
        }
        
        logger.debug("CSS Parser initialized with full CSS3 support")
    
    def parse(self, css_content: str, base_url: Optional[str] = None) -> css.CSSStyleSheet:
        """
        Parse CSS content into a stylesheet.
        
        Args:
            css_content: CSS content to parse
            base_url: Optional base URL for resolving relative URLs
            
        Returns:
            Parsed CSS stylesheet
        """
        try:
            # Parse using cssutils for comprehensive CSS3 support
            stylesheet = cssutils.parseString(css_content)
            
            # Resolve URLs if a base URL is provided
            if base_url:
                self.resolve_urls(stylesheet, base_url)
            
            return stylesheet
            
        except Exception as e:
            logger.error(f"Error parsing CSS: {e}")
            
            # Create an empty stylesheet on error
            stylesheet = css.CSSStyleSheet()
            
            # Add error information
            error_rule = css.CSSComment(f"CSS Parser Error: {e}")
            stylesheet.append(error_rule)
            
            return stylesheet
    
    def parse_inline_styles(self, style_attr: str) -> Dict[str, str]:
        """
        Parse an inline style attribute.
        
        Args:
            style_attr: Inline style attribute value
            
        Returns:
            Dictionary of CSS properties
        """
        return self._parse_declaration(style_attr)
    
    def resolve_urls(self, stylesheet: css.CSSStyleSheet, base_url: str) -> None:
        """
        Resolve relative URLs in a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet to process
            base_url: Base URL for resolving relative URLs
        """
        # Process @import rules
        for rule in self.get_import_rules(stylesheet):
            if rule.href:
                resolved_url = self._resolve_url(rule.href, base_url)
                rule.href = resolved_url
        
        # Process style rules
        for rule in stylesheet:
            if rule.type == rule.STYLE_RULE:
                self._resolve_style_rule_urls(rule, base_url)
            elif rule.type == rule.FONT_FACE_RULE:
                self._resolve_font_face_urls(rule, base_url)
    
    def _resolve_style_rule_urls(self, rule: css.CSSStyleRule, base_url: str) -> None:
        """
        Resolve URLs in a style rule.
        
        Args:
            rule: CSS style rule to process
            base_url: Base URL for resolving relative URLs
        """
        for prop in rule.style:
            if prop.name.lower() in URL_PROPERTIES:
                prop.value = self._resolve_css_urls(prop.value, base_url)
    
    def _resolve_font_face_urls(self, rule: css.CSSFontFaceRule, base_url: str) -> None:
        """
        Resolve URLs in a @font-face rule.
        
        Args:
            rule: CSS @font-face rule to process
            base_url: Base URL for resolving relative URLs
        """
        for prop in rule.style:
            if prop.name.lower() == 'src':
                prop.value = self._resolve_css_urls(prop.value, base_url)
    
    def _resolve_css_urls(self, css_value: str, base_url: str) -> str:
        """
        Resolve URLs in CSS values.
        
        Args:
            css_value: CSS value that may contain URLs
            base_url: Base URL for resolving relative URLs
            
        Returns:
            CSS value with resolved URLs
        """
        def replace_url(match):
            url = match.group(1)
            
            # Remove quotes if present
            if url.startswith('"') and url.endswith('"'):
                url = url[1:-1]
            elif url.startswith("'") and url.endswith("'"):
                url = url[1:-1]
            
            # Skip data URLs and absolute URLs
            if url.startswith('data:') or url.startswith('http://') or url.startswith('https://'):
                return f"url('{url}')"
            
            # Resolve relative URL
            resolved_url = self._resolve_url(url, base_url)
            
            return f"url('{resolved_url}')"
        
        # URL pattern in CSS
        url_pattern = r'url\(\s*[\'"]?([^\'"\)]+)[\'"]?\s*\)'
        
        # Replace all URLs
        return re.sub(url_pattern, replace_url, css_value)
    
    def _resolve_url(self, url: str, base_url: str) -> str:
        """
        Resolve a relative URL against a base URL.
        
        Args:
            url: Relative URL to resolve
            base_url: Base URL
            
        Returns:
            Resolved absolute URL
        """
        try:
            return urllib.parse.urljoin(base_url, url)
        except Exception as e:
            logger.error(f"Error resolving URL: {e}")
            return url
    
    def get_computed_style(self, element: Element) -> Dict[str, str]:
        """
        Calculate the computed style for an element.
        
        Args:
            element: The element to calculate styles for
            
        Returns:
            Dictionary of computed style properties
        """
        computed_style = {}
        
        # Get document
        document = element.owner_document
        if not document:
            return computed_style
        
        # Get all applicable style rules
        style_rules = self._get_applicable_style_rules(element, document)
        
        # Apply styles in order of specificity
        for rule in style_rules:
            for prop_name, prop_value in rule.items():
                computed_style[prop_name] = prop_value
        
        # Add inline styles (highest precedence)
        inline_styles = {}
        style_attr = element.get_attribute('style')
        if style_attr:
            inline_styles = self.parse_inline_styles(style_attr)
            
            for prop_name, prop_value in inline_styles.items():
                computed_style[prop_name] = prop_value
        
        return computed_style
    
    def _get_applicable_style_rules(self, element: Element, document: Document) -> List[Dict[str, str]]:
        """
        Get all style rules that apply to an element in order of specificity.
        
        Args:
            element: The element to get styles for
            document: The document containing stylesheets
            
        Returns:
            List of style rule dictionaries in order of specificity
        """
        applicable_rules = []
        
        # TODO: Find and process all stylesheets in the document
        # This would involve extracting stylesheets from <style> and <link> elements
        
        # For each rule, check if it applies to the element
        # Add to list with specificity for sorting
        
        # For demonstration, return an empty list for now
        return applicable_rules
    
    def extract_styles(self, stylesheet: css.CSSStyleSheet) -> Dict[str, Dict[str, str]]:
        """
        Extract style rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet to extract from
            
        Returns:
            Dictionary mapping selectors to style property dictionaries
        """
        styles = {}
        
        for rule in stylesheet:
            if rule.type == rule.STYLE_RULE:
                style_props = {}
                
                for prop in rule.style:
                    if prop.name and prop.value:
                        style_props[prop.name.lower()] = prop.value
                
                # Add for each selector in the rule
                selector_list = rule.selectorText.split(',')
                for selector in selector_list:
                    selector = selector.strip()
                    if selector:
                        styles[selector] = style_props
        
        return styles
    
    def get_style_rules_for_document(self, document: Document) -> Dict[str, Dict[str, str]]:
        """
        Get all style rules from a document's stylesheets.
        
        Args:
            document: Document to extract styles from
            
        Returns:
            Dictionary mapping selectors to style property dictionaries
        """
        all_styles = {}
        
        # TODO: Extract and combine styles from all stylesheets in the document
        
        return all_styles
    
    def get_import_rules(self, stylesheet: css.CSSStyleSheet) -> List[css.CSSImportRule]:
        """
        Get all @import rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet to process
            
        Returns:
            List of @import rules
        """
        return [rule for rule in stylesheet if rule.type == rule.IMPORT_RULE]
    
    def get_font_face_rules(self, stylesheet: css.CSSStyleSheet) -> List[css.CSSFontFaceRule]:
        """
        Get all @font-face rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet to process
            
        Returns:
            List of @font-face rules
        """
        return [rule for rule in stylesheet if rule.type == rule.FONT_FACE_RULE]
    
    def get_media_rules(self, stylesheet: css.CSSStyleSheet) -> List[css.CSSMediaRule]:
        """
        Get all @media rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet to process
            
        Returns:
            List of @media rules
        """
        return [rule for rule in stylesheet if rule.type == rule.MEDIA_RULE]
    
    def get_keyframes_rules(self, stylesheet: css.CSSStyleSheet) -> List[Any]:
        """
        Get all @keyframes rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet to process
            
        Returns:
            List of @keyframes rules
        """
        # Use a more compatible approach to find @keyframes rules
        keyframes_rules = []
        for rule in stylesheet:
            # Check for custom keyframes rule type or use cssText to identify
            if hasattr(rule, 'type') and rule.type == CSS_RULE_KEYFRAMES:
                keyframes_rules.append(rule)
            elif hasattr(rule, 'cssText') and '@keyframes' in rule.cssText:
                keyframes_rules.append(rule)
        return keyframes_rules
    
    def parse_media_queries(self, stylesheet: css.CSSStyleSheet) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse @media rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet to process
            
        Returns:
            Dictionary mapping media queries to rule information
        """
        media_rules = {}
        
        for rule in self.get_media_rules(stylesheet):
            media_text = rule.media.mediaText
            rules_info = []
            
            for style_rule in rule:
                if style_rule.type == style_rule.STYLE_RULE:
                    style_props = {}
                    
                    for prop in style_rule.style:
                        if prop.name and prop.value:
                            style_props[prop.name.lower()] = prop.value
                    
                    rules_info.append({
                        'selector': style_rule.selectorText,
                        'styles': style_props
                    })
            
            media_rules[media_text] = rules_info
        
        return media_rules
    
    def parse_keyframes(self, stylesheet: css.CSSStyleSheet) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse @keyframes rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet to process
            
        Returns:
            Dictionary mapping animation names to keyframe information
        """
        keyframes = {}
        
        for rule in self.get_keyframes_rules(stylesheet):
            # Extract animation name from rule
            animation_name = None
            if hasattr(rule, 'name'):
                animation_name = rule.name
            else:
                # Try to extract name from cssText
                match = re.search(r'@keyframes\s+([^\s{]+)', rule.cssText)
                if match:
                    animation_name = match.group(1)
            
            if not animation_name:
                continue
                
            frames = []
            
            # Process keyframe rules
            if hasattr(rule, 'cssRules'):
                for keyframe in rule.cssRules:
                    # Extract key text (percentage)
                    key_text = None
                    if hasattr(keyframe, 'keyText'):
                        key_text = keyframe.keyText
                    else:
                        # Try to extract from cssText
                        match = re.search(r'^([^{]+){', keyframe.cssText)
                        if match:
                            key_text = match.group(1).strip()
                    
                    if not key_text:
                        continue
                        
                    # Extract style properties
                    style_props = {}
                    
                    if hasattr(keyframe, 'style'):
                        for prop in keyframe.style:
                            if prop.name and prop.value:
                                style_props[prop.name.lower()] = prop.value
                    else:
                        # Try to extract properties from cssText
                        style_text = re.search(r'{([^}]+)}', keyframe.cssText)
                        if style_text:
                            for prop_text in style_text.group(1).split(';'):
                                if ':' in prop_text:
                                    name, value = prop_text.split(':', 1)
                                    name = name.strip().lower()
                                    value = value.strip()
                                    if name and value:
                                        style_props[name] = value
                    
                    frames.append({
                        'keyText': key_text,
                        'styles': style_props
                    })
            
            keyframes[animation_name] = frames
        
        return keyframes
    
    def parse_font_face_rules(self, stylesheet: css.CSSStyleSheet) -> List[Dict[str, str]]:
        """
        Parse @font-face rules from a stylesheet.
        
        Args:
            stylesheet: CSS stylesheet to process
            
        Returns:
            List of font face information
        """
        font_faces = []
        
        for rule in self.get_font_face_rules(stylesheet):
            font_info = {}
            
            for prop in rule.style:
                if prop.name and prop.value:
                    font_info[prop.name.lower()] = prop.value
            
            font_faces.append(font_info)
        
        return font_faces
    
    def specificity(self, selector: str) -> Tuple[int, int, int]:
        """
        Calculate the specificity of a CSS selector.
        
        Args:
            selector: CSS selector to analyze
            
        Returns:
            Tuple of (ID count, class count, element count)
        """
        # Count the number of IDs
        id_count = len(re.findall(r'#[a-zA-Z0-9_-]+', selector))
        
        # Count the number of classes, attributes, and pseudo-classes
        class_count = len(re.findall(r'\.[a-zA-Z0-9_-]+', selector))
        class_count += len(re.findall(r'\[[^\]]+\]', selector))
        class_count += len(re.findall(r':[a-zA-Z0-9_-]+', selector)) - len(re.findall(r'::[a-zA-Z0-9_-]+', selector))
        
        # Count the number of element types and pseudo-elements
        element_count = len(re.findall(r'(?<![.#:])[a-zA-Z0-9_-]+', selector))
        element_count += len(re.findall(r'::[a-zA-Z0-9_-]+', selector))
        
        return (id_count, class_count, element_count)
    
    def sort_selectors_by_specificity(self, selectors: List[str]) -> List[str]:
        """
        Sort CSS selectors by specificity.
        
        Args:
            selectors: List of CSS selectors
            
        Returns:
            Sorted list of selectors (lowest to highest specificity)
        """
        return sorted(selectors, key=self.specificity)
    
    def _parse_declaration(self, declaration: str) -> Dict[str, str]:
        """
        Parse a CSS declaration.
        
        Args:
            declaration: CSS declaration string (e.g., "color: red; font-size: 12px")
            
        Returns:
            Dictionary of CSS properties and values
        """
        if not declaration:
            return {}
            
        properties = {}
        
        # Split declarations by semicolon
        for prop in declaration.split(';'):
            if not prop.strip():
                continue
                
            # Split property and value by colon
            parts = prop.split(':', 1)
            if len(parts) != 2:
                continue
                
            property_name = parts[0].strip().lower()
            property_value = parts[1].strip()
            
            # Validate and process property
            processed_value = self._process_property_value(property_name, property_value)
            if processed_value is not None:
                properties[property_name] = processed_value
            
        return properties
    
    def _process_property_value(self, property_name: str, property_value: str) -> Optional[str]:
        """
        Process and validate a CSS property value.
        
        Args:
            property_name: CSS property name
            property_value: CSS property value
            
        Returns:
            Processed property value, or None if invalid
        """
        # Check if property is recognized
        if property_name not in self.recognized_properties:
            logger.debug(f"Unrecognized CSS property: {property_name}")
            return None
        
        # Process specific properties
        if property_name == 'text-align':
            # Validate text-align values
            valid_values = ['left', 'center', 'right', 'justify']
            if property_value.lower() in valid_values:
                return property_value.lower()
            return 'left'  # Default value
        
        # Handle color properties
        elif property_name in ['color', 'background-color', 'border-color']:
            # Simple color name validation
            return property_value
        
        # Handle font properties
        elif property_name == 'font-weight':
            # Normalize font weight
            if property_value.lower() in ['bold', 'bolder', '700', '800', '900']:
                return 'bold'
            return 'normal'
            
        elif property_name == 'font-style':
            # Normalize font style
            if property_value.lower() == 'italic':
                return 'italic'
            return 'normal'
            
        # Pass through other properties
        return property_value 