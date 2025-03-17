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
        self.stylesheets = []  # List of all parsed stylesheets
        self.default_style_rules = {}  # Dictionary of default style rules
        self.style_rules = {}  # Dictionary of style rules keyed by selector
        self.important_rules = {}  # Dictionary of !important rules with highest precedence
        
        # Define the CSS properties we support
        self.supported_properties = [
            # Layout properties
            'display', 'position', 'top', 'right', 'bottom', 'left',
            'float', 'clear', 'z-index', 'overflow', 'visibility',
            
            # Box model properties
            'width', 'height', 'min-width', 'min-height', 'max-width', 'max-height',
            'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
            'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
            'box-sizing',
            
            # Border properties
            'border', 'border-width', 'border-style', 'border-color',
            'border-top', 'border-right', 'border-bottom', 'border-left',
            'border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width',
            'border-top-style', 'border-right-style', 'border-bottom-style', 'border-left-style',
            'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
            'border-radius', 'border-top-left-radius', 'border-top-right-radius',
            'border-bottom-right-radius', 'border-bottom-left-radius',
            
            # Text properties
            'color', 'font', 'font-family', 'font-size', 'font-weight', 'font-style',
            'text-align', 'text-decoration', 'text-transform', 'line-height',
            'letter-spacing', 'word-spacing', 'white-space', 'direction',
            
            # Background properties
            'background', 'background-color', 'background-image', 'background-repeat',
            'background-position', 'background-size', 'background-attachment',
            
            # Table properties
            'border-collapse', 'border-spacing', 'caption-side', 'empty-cells', 'table-layout',
            
            # Flexbox properties
            'flex', 'flex-direction', 'flex-wrap', 'flex-flow', 'justify-content',
            'align-items', 'align-content', 'align-self', 'flex-grow', 'flex-shrink', 'flex-basis',
            'order',
            
            # Grid properties
            'grid', 'grid-template', 'grid-template-columns', 'grid-template-rows',
            'grid-template-areas', 'grid-area', 'grid-row', 'grid-column',
            
            # Animation and transition properties
            'transition', 'transform', 'animation',
            
            # Color and opacity
            'opacity', 'fill', 'stroke'
        ]
        
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
    
    def reset(self):
        """Reset the parser state but keep default styles."""
        self.stylesheets = []  # Clear list of stylesheets
        self.style_rules = {}  # Reset site-specific style rules
        self.important_rules = {}  # Reset important rules
        logger.debug("CSS Parser reset")
    
    def add_default_styles(self):
        """
        Add default browser styles to the parser.
        These styles will apply to all documents unless overridden by document styles.
        """
        try:
            # Clear existing default styles
            self.default_style_rules = {}
            
            # Define default styles for various HTML elements
            default_styles = """
            /* Default styles for common HTML elements */
            body {
                margin: 24px;
                line-height: 1.6;
                font-family: sans-serif;
                font-size: 16px;
                color: #000;
            }
            
            div, span, p {
                display: block;
                margin: 0;
                padding: 0;
            }
            
            span {
                display: inline;
            }
            
            h1, h2, h3, h4, h5, h6 {
                display: block;
                font-weight: bold;
                margin-top: 1.2em;
                margin-bottom: 0.8em;
                line-height: 1.3;
            }
            
            h1 {
                font-size: 2em;
                margin-top: 1em;
                margin-bottom: 0.8em;
            }
            
            h2 {
                font-size: 1.5em;
                margin-top: 0.9em;
                margin-bottom: 0.7em;
            }
            
            h3 {
                font-size: 1.17em;
                margin-top: 0.8em;
                margin-bottom: 0.6em;
            }
            
            h4 {
                font-size: 1em;
                margin-top: 0.7em;
                margin-bottom: 0.5em;
            }
            
            h5 {
                font-size: 0.83em;
                margin-top: 0.6em;
                margin-bottom: 0.4em;
            }
            
            h6 {
                font-size: 0.67em;
                margin-top: 0.5em;
                margin-bottom: 0.3em;
            }
            
            /* Navigation and link styles */
            nav {
                display: block;
                margin-bottom: 1.5em;
            }
            
            nav a {
                display: block;
                margin: 0.5em 0;
                line-height: 1.4;
            }
            
            a:link {
                color: blue;
                text-decoration: underline;
                cursor: pointer;
                display: inline;
                padding: 0.1em 0;
            }
            
            /* RFC references */
            pre {
                display: block;
                font-family: monospace;
                white-space: pre;
                margin: 1em 0;
                padding: 0.5em;
                line-height: 1.4;
            }
            
            /* Text blocks */
            p {
                margin-top: 1em;
                margin-bottom: 1em;
                line-height: 1.5;
            }
            
            /* Lists */
            ul, ol {
                margin: 1em 0;
                padding-left: 2em;
            }
            
            li {
                margin: 0.5em 0;
                line-height: 1.4;
            }
            
            /* Sidebar navigation */
            .sidebar a, nav a {
                display: block;
                margin: 0.8em 0;
                line-height: 1.4;
            }
            
            /* RFC references */
            .rfc-ref {
                display: block;
                margin: 1em 0;
            }
            
            a:visited {
                color: purple;
                text-decoration: underline;
            }
            
            a:hover {
                text-decoration: underline;
            }
            
            a:active {
                color: red;
            }
            
            img, video, canvas, object {
                display: inline-block;
                border: none;
                margin: 2em 0;
            }
            
            table {
                display: table;
                border-collapse: separate;
                border-spacing: 8px;
                border-color: gray;
                box-sizing: border-box;
                margin: 2em 0;
            }
            
            tr {
                display: table-row;
                vertical-align: inherit;
                border-color: inherit;
            }
            
            td, th {
                display: table-cell;
                vertical-align: inherit;
                border: 1px solid #ddd;
                padding: 10px;
            }
            
            input, button, textarea, select {
                display: inline-block;
                font-family: inherit;
                font-size: inherit;
                padding: 10px;
                border: 1px solid #767676;
                margin: 1.2em 0;
            }
            
            input[type="text"], input[type="password"], textarea {
                background-color: white;
            }
            
            input[type="checkbox"], input[type="radio"] {
                margin: 5px;
            }
            
            button {
                padding: 10px 20px;
                background-color: #f0f0f0;
            }
            
            code {
                font-family: monospace;
            }
            
            /* Block elements */
            article, section, nav, aside, header, footer, 
            address, blockquote, figcaption, figure, hgroup,
            main, details, summary {
                display: block;
                margin: 1.5em 0;
                padding: 0;
            }
            
            blockquote {
                margin-left: 2em;
                padding-left: 1em;
                border-left: 3px solid #ddd;
            }
            
            /* Inline elements */
            abbr, b, bdi, bdo, cite, code, data, dfn, em, i, 
            kbd, mark, q, rp, rt, ruby, s, samp, small, 
            strong, sub, sup, time, u, var, wbr {
                display: inline;
            }
            
            hr {
                display: block;
                margin-top: 2em;
                margin-bottom: 2em;
                border-style: solid;
                border-width: 1px;
                border-color: #ddd;
            }
            """
            
            # Parse the default styles and extract rules
            try:
                sheet = cssutils.parseString(default_styles)
                
                # Extract each rule and add to default_style_rules
                for rule in sheet:
                    if hasattr(rule, 'type') and rule.type == rule.STYLE_RULE:
                        selector = rule.selectorText
                        props = {}
                        for prop in rule.style:
                            if prop.name in self.supported_properties:
                                props[prop.name] = prop.value
                        if props:
                            self.default_style_rules[selector] = props
                
                logger.debug("Default browser styles added")
            except Exception as e:
                logger.error(f"Error parsing default styles: {e}")
                
        except Exception as e:
            logger.error(f"Error adding default styles: {e}")
    
    def _safe_parse_css(self, css_content: str) -> Any:
        """
        Safely parse CSS content using cssutils, with error handling.
        
        Args:
            css_content: CSS content to parse
            
        Returns:
            Parsed CSS stylesheet or None if parsing failed
        """
        if not css_content or not isinstance(css_content, str):
            logger.warning(f"Invalid CSS content type: {type(css_content)}")
            return None
            
        try:
            # Parse CSS content
            sheet = cssutils.parseString(css_content)
            
            # Validate that sheet is iterable
            if not hasattr(sheet, '__iter__'):
                logger.warning(f"Parsed CSS sheet is not iterable: {type(sheet)}")
                return None
                
            # Check if any rule is a string (which would cause errors when accessing .type)
            has_string_rules = False
            for rule in sheet:
                if isinstance(rule, str):
                    has_string_rules = True
                    logger.warning(f"CSS sheet contains string rule: {rule[:50]}...")
                    break
                    
            if has_string_rules:
                # If there are string rules, we need to handle them specially
                # For now, we'll return an empty sheet
                logger.warning("CSS sheet contains string rules, creating empty sheet")
                return cssutils.css.CSSStyleSheet()
                
            return sheet
            
        except Exception as e:
            logger.error(f"Error parsing CSS with cssutils: {e}")
            return None

    def _parse_css_manually(self, css_content: str) -> dict:
        """
        Parse CSS content manually using regex, avoiding cssutils.
        This is a fallback method when cssutils fails or returns problematic results.
        
        Args:
            css_content: CSS content to parse
            
        Returns:
            Dictionary of CSS rules by selector
        """
        if not css_content or not isinstance(css_content, str):
            return {}
            
        css_rules = {}
        
        try:
            # Use a simple regex to extract CSS rules
            # This is a basic parser but should handle simple cases
            import re
            rule_pattern = r'([^{]+){([^}]*)}'
            matches = re.findall(rule_pattern, css_content)
            
            for selector, declarations in matches:
                selector = selector.strip()
                if not selector:
                    continue
                    
                # Parse declarations
                props = {}
                for decl in declarations.split(';'):
                    if ':' not in decl:
                        continue
                        
                    prop, val = decl.split(':', 1)
                    prop = prop.strip()
                    val = val.strip()
                    
                    if prop and val:
                        props[prop] = val
                
                if props:
                    css_rules[selector] = props
                    
            return css_rules
            
        except Exception as e:
            logger.error(f"Error manually parsing CSS: {e}")
            return {}

    def parse(self, css_content: str, base_url: Optional[str] = None) -> dict:
        """
        Parse CSS content into a stylesheet.
        
        Args:
            css_content: The CSS content to parse
            base_url: Optional base URL for resolving relative URLs in the CSS
            
        Returns:
            The parsed stylesheet object
        """
        if not css_content or not css_content.strip():
            return {}
            
        stylesheet = {}
        site_rules = {}
        
        try:
            # First try to parse with cssutils
            sheet = self._safe_parse_css(css_content)
            
            # If cssutils parsing failed, use manual parsing as fallback
            if not sheet:
                logger.info("Using manual CSS parsing as fallback")
                return self._parse_css_manually(css_content)
            
            # Resolve URLs if base_url is provided
            if base_url:
                try:
                    self._resolve_urls(sheet, base_url)
                except Exception as url_err:
                    logger.error(f"Error resolving URLs in CSS: {url_err}")
            
            # Extract rules from the stylesheet
            try:
                for rule in sheet:
                    # Skip if rule is not an object or doesn't have a type attribute
                    if not rule or not hasattr(rule, 'type'):
                        continue
                        
                    # Handle style rules
                    if rule.type == cssutils.css.CSSRule.STYLE_RULE:
                        selector = rule.selectorText
                        properties = {}
                        
                        for prop in rule.style:
                            if prop.name and prop.value:
                                properties[prop.name] = prop.value
                                
                        if properties:
                            site_rules[selector] = properties
                            
                    # Handle @import rules
                    elif rule.type == cssutils.css.CSSRule.IMPORT_RULE:
                        # Import rules are handled separately
                        pass
                        
                    # Handle @media rules
                    elif rule.type == cssutils.css.CSSRule.MEDIA_RULE:
                        # Process rules inside @media
                        for media_rule in rule:
                            if hasattr(media_rule, 'type') and media_rule.type == cssutils.css.CSSRule.STYLE_RULE:
                                selector = media_rule.selectorText
                                properties = {}
                                
                                for prop in media_rule.style:
                                    if prop.name and prop.value:
                                        properties[prop.name] = prop.value
                                        
                                if properties:
                                    site_rules[selector] = properties
            except Exception as rule_err:
                logger.error(f"Error processing CSS rules: {rule_err}")
                # Fall back to manual parsing
                return self._parse_css_manually(css_content)
            
            # Return the parsed stylesheet
            return site_rules
            
        except Exception as e:
            logger.error(f"Error parsing CSS: {e}")
            # Fall back to manual parsing
            return self._parse_css_manually(css_content)
            
    def parse_inline_styles(self, style_attr: str) -> Dict[str, str]:
        """
        Parse an inline style attribute.
        
        Args:
            style_attr: Inline style attribute value
            
        Returns:
            Dictionary of CSS properties
        """
        return self._parse_declaration(style_attr)
    
    def _resolve_urls(self, stylesheet, base_url: str) -> None:
        """
        Resolve relative URLs in CSS properties to absolute URLs.
        
        Args:
            stylesheet: The CSS stylesheet object
            base_url: The base URL to resolve against
        """
        import urllib.parse
        
        for rule in stylesheet:
            # Skip if rule is not an object, is None, or doesn't have a type attribute
            if not rule or not hasattr(rule, 'type'):
                continue
                
            if rule.type == rule.STYLE_RULE:
                for prop in rule.style:
                    if prop.name in URL_PROPERTIES and prop.value:
                        # Look for url() expressions
                        url_matches = re.findall(r'url\([\'"]?([^\'"]+)[\'"]?\)', prop.value)
                        if url_matches:
                            for url_match in url_matches:
                                if not url_match.startswith(('http://', 'https://', 'data:', '//')):
                                    abs_url = urllib.parse.urljoin(base_url, url_match)
                                    prop.value = prop.value.replace(f"url({url_match})", f"url({abs_url})")
                                    prop.value = prop.value.replace(f"url('{url_match}')", f"url('{abs_url}')")
                                    prop.value = prop.value.replace(f'url("{url_match}")', f'url("{abs_url}")')
            elif rule.type == rule.IMPORT_RULE:
                # Resolve @import URLs
                if hasattr(rule, 'href') and rule.href and not rule.href.startswith(('http://', 'https://', 'data:', '//')):
                    rule.href = urllib.parse.urljoin(base_url, rule.href)
                    
    # Alias resolve_urls for backward compatibility
    resolve_urls = _resolve_urls
    
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
        
        # Calculate and sort rules by specificity
        default_rules = []
        site_rules = []
        important_rules = []
        
        # Collect matching default style rules
        for selector, props in self.default_style_rules.items():
            try:
                if document.matches_selector(element, selector):
                    specificity = self._calculate_specificity(selector)
                    default_rules.append((specificity, selector, props))
            except Exception:
                # Skip selectors that can't be processed
                pass
        
        # Sort default rules by specificity
        default_rules.sort(key=lambda x: x[0])
        
        # First apply default browser styles (lowest precedence)
        for _, selector, props in default_rules:
            for prop_name, prop_value in props.items():
                if not '!important' in str(prop_value):  # Skip important rules for now
                    computed_style[prop_name] = prop_value.replace('!important', '').strip() if isinstance(prop_value, str) else prop_value
        
        # Collect matching site style rules
        for stylesheet in self.stylesheets:
            for selector, props in stylesheet.items():
                try:
                    if document.matches_selector(element, selector):
                        specificity = self._calculate_specificity(selector)
                        site_rules.append((specificity, selector, props))
                except Exception:
                    # Skip selectors that can't be processed
                    pass
        
        # Sort site rules by specificity
        site_rules.sort(key=lambda x: x[0])
        
        # Then apply site stylesheets (higher precedence, overrides default styles)
        for _, selector, props in site_rules:
            for prop_name, prop_value in props.items():
                if not '!important' in str(prop_value):  # Skip important rules for now
                    computed_style[prop_name] = prop_value.replace('!important', '').strip() if isinstance(prop_value, str) else prop_value
        
        # Add inline styles (higher precedence than site styles, lower than !important)
        inline_styles = {}
        style_attr = element.get_attribute('style')
        if style_attr:
            inline_styles = self.parse_inline_styles(style_attr)
            
            for prop_name, prop_value in inline_styles.items():
                if not '!important' in str(prop_value):  # Skip important rules for now
                    computed_style[prop_name] = prop_value.replace('!important', '').strip() if isinstance(prop_value, str) else prop_value
        
        # Collect !important rules from all sources
        # Default !important
        for _, selector, props in default_rules:
            for prop_name, prop_value in props.items():
                if isinstance(prop_value, str) and '!important' in prop_value:
                    specificity = self._calculate_specificity(selector)
                    important_rules.append((specificity, 0, prop_name, prop_value.replace('!important', '').strip()))
        
        # Site !important
        for _, selector, props in site_rules:
            for prop_name, prop_value in props.items():
                if isinstance(prop_value, str) and '!important' in prop_value:
                    specificity = self._calculate_specificity(selector)
                    important_rules.append((specificity, 1, prop_name, prop_value.replace('!important', '').strip()))
        
        # Inline !important (highest specificity)
        for prop_name, prop_value in inline_styles.items():
            if isinstance(prop_value, str) and '!important' in prop_value:
                important_rules.append(((1, 0, 0), 2, prop_name, prop_value.replace('!important', '').strip()))
        
        # Sort important rules by specificity, then by source (0=default, 1=site, 2=inline)
        important_rules.sort(key=lambda x: (x[0], x[1]))
        
        # Apply all !important rules last (highest precedence)
        for _, _, prop_name, prop_value in important_rules:
            computed_style[prop_name] = prop_value
        
        return computed_style
        
    def _calculate_specificity(self, selector: str) -> tuple:
        """
        Calculate the specificity of a CSS selector.
        
        Args:
            selector: The CSS selector
            
        Returns:
            Tuple of (id_count, class_count, element_count)
        """
        # Count IDs
        id_count = selector.count('#')
        
        # Count classes, attributes, and pseudo-classes
        class_count = selector.count('.') + selector.count('[') + selector.count(':')
        
        # Count element names and pseudo-elements
        element_count = len(re.findall(r'[a-zA-Z0-9]+', selector.replace('#', ' ').replace('.', ' ')))
        element_count += selector.count('::')
        
        return (id_count, class_count, element_count)
    
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
    
    def _parse_declaration(self, declaration_str: str) -> Dict[str, str]:
        """
        Parse a CSS declaration string into a dictionary of property-value pairs.
        
        Args:
            declaration_str: CSS declaration string
            
        Returns:
            Dictionary of property-value pairs
        """
        if not declaration_str:
            return {}
        
        result = {}
        # Split declaration by semicolons
        declarations = declaration_str.split(';')
        
        for declaration in declarations:
            declaration = declaration.strip()
            if not declaration:
                continue
            
            # Split property and value
            parts = declaration.split(':', 1)
            if len(parts) != 2:
                continue
            
            property_name = parts[0].strip().lower()
            property_value = parts[1].strip()
            
            # Validate and normalize the property value
            normalized_value = self._normalize_property_value(property_name, property_value)
            if normalized_value is not None:
                result[property_name] = normalized_value
        
        # Process shorthand properties
        self._process_shorthand_properties(result)
        
        return result
    
    def _normalize_property_value(self, property_name: str, property_value: str) -> Optional[str]:
        """
        Validate and normalize a CSS property value.
        
        Args:
            property_name: CSS property name
            property_value: CSS property value
            
        Returns:
            Normalized value or None if invalid
        """
        # Remove extra whitespace
        value = ' '.join(property_value.split())
        
        # Handle different property types
        if property_name in ('width', 'height', 'margin', 'padding', 'left', 'right', 'top', 'bottom',
                            'margin-left', 'margin-right', 'margin-top', 'margin-bottom',
                            'padding-left', 'padding-right', 'padding-top', 'padding-bottom'):
            return self._normalize_length_value(value)
        
        elif property_name in ('color', 'background-color', 'border-color',
                             'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color'):
            return self._normalize_color_value(value)
        
        elif property_name == 'background-image':
            return self._normalize_background_image_value(value)
        
        elif property_name == 'background':
            return self._normalize_background_shorthand(value)
        
        elif property_name == 'border':
            return self._normalize_border_shorthand(value)
        
        elif property_name in ('border-width', 'border-top-width', 'border-right-width', 
                              'border-bottom-width', 'border-left-width'):
            return self._normalize_length_value(value)
            
        # Font family validation
        elif property_name == 'font-family':
            return self._normalize_font_family(value)
        
        # Font size validation
        elif property_name == 'font-size':
            return self._normalize_length_value(value)
        
        # Font weight validation
        elif property_name == 'font-weight':
            return self._normalize_font_weight(value)
        
        # Font style validation
        elif property_name == 'font-style':
            return self._normalize_font_style(value)
        
        # Text decoration validation
        elif property_name == 'text-decoration':
            return self._normalize_text_decoration(value)
        
        # Font shorthand
        elif property_name == 'font':
            return self._normalize_font_shorthand(value)
            
        elif property_name == 'display':
            valid_displays = ('block', 'inline', 'inline-block', 'flex', 'none')
            if value.lower() in valid_displays:
                return value.lower()
            return 'block'  # default
        
        elif property_name == 'position':
            valid_positions = ('static', 'relative', 'absolute', 'fixed')
            if value.lower() in valid_positions:
                return value.lower()
            return 'static'  # default
        
        elif property_name == 'text-align':
            valid_aligns = ('left', 'center', 'right', 'justify')
            if value.lower() in valid_aligns:
                return value.lower()
            return 'left'  # default
        
        # For other properties, just return as is for now
        return value
    
    def _normalize_length_value(self, value: str) -> str:
        """
        Normalize a CSS length value.
        
        Args:
            value: CSS length value
            
        Returns:
            Normalized length value
        """
        # If it's already a number, return it as pixels
        if value.isdigit():
            return f'{value}px'
        
        # Check for percentage
        if value.endswith('%'):
            try:
                float(value[:-1])
                return value
            except ValueError:
                return '0px'  # Invalid percentage
        
        # Check for various units
        units = ('px', 'em', 'rem', 'vh', 'vw', 'vmin', 'vmax', 'cm', 'mm', 'in', 'pt', 'pc')
        for unit in units:
            if value.endswith(unit):
                try:
                    float(value[:-len(unit)])
                    return value
                except ValueError:
                    return '0px'  # Invalid unit value
        
        # Named values
        if value in ('auto', 'inherit', 'initial'):
            return value
        
        # Default to pixels if no unit specified
        try:
            float(value)
            return f'{value}px'
        except ValueError:
            return '0px'
    
    def _normalize_color_value(self, value: str) -> str:
        """
        Normalize a CSS color value.
        
        Args:
            value: CSS color value
            
        Returns:
            Normalized color value
        """
        value = value.lower().strip()
        
        # Named colors
        named_colors = {
            'black': '#000000',
            'white': '#ffffff',
            'red': '#ff0000',
            'green': '#008000',
            'blue': '#0000ff',
            'yellow': '#ffff00',
            'purple': '#800080',
            'grey': '#808080',
            'gray': '#808080',
            'orange': '#ffa500',
            'transparent': 'transparent',
            # Add more named colors as needed
        }
        
        if value in named_colors:
            return named_colors[value]
        
        # Hex colors
        if value.startswith('#'):
            if len(value) == 4:  # Short form #RGB
                try:
                    int(value[1:], 16)
                    return f'#{value[1]}{value[1]}{value[2]}{value[2]}{value[3]}{value[3]}'
                except ValueError:
                    return '#000000'  # Invalid hex
            
            elif len(value) == 7:  # Standard form #RRGGBB
                try:
                    int(value[1:], 16)
                    return value
                except ValueError:
                    return '#000000'  # Invalid hex
        
        # RGB format
        rgb_match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', value)
        if rgb_match:
            r = min(255, max(0, int(rgb_match.group(1))))
            g = min(255, max(0, int(rgb_match.group(2))))
            b = min(255, max(0, int(rgb_match.group(3))))
            return f'#{r:02x}{g:02x}{b:02x}'
        
        # RGBA format (convert to hex, ignoring alpha)
        rgba_match = re.match(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)', value)
        if rgba_match:
            r = min(255, max(0, int(rgba_match.group(1))))
            g = min(255, max(0, int(rgba_match.group(2))))
            b = min(255, max(0, int(rgba_match.group(3))))
            a = min(1, max(0, float(rgba_match.group(4))))
            # If fully transparent, return 'transparent'
            if a == 0:
                return 'transparent'
            return f'#{r:02x}{g:02x}{b:02x}'
        
        # HSL format - simplified conversion
        hsl_match = re.match(r'hsl\(\s*(\d+)\s*,\s*(\d+)%\s*,\s*(\d+)%\s*\)', value)
        if hsl_match:
            h = int(hsl_match.group(1)) / 360
            s = int(hsl_match.group(2)) / 100
            l = int(hsl_match.group(3)) / 100
            # Convert HSL to RGB using a simplified algorithm
            if s == 0:
                r = g = b = int(l * 255)
            else:
                def hue_to_rgb(p, q, t):
                    if t < 0: t += 1
                    if t > 1: t -= 1
                    if t < 1/6: return p + (q - p) * 6 * t
                    if t < 1/2: return q
                    if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                    return p
                
                q = l * (1 + s) if l < 0.5 else l + s - l * s
                p = 2 * l - q
                r = int(hue_to_rgb(p, q, h + 1/3) * 255)
                g = int(hue_to_rgb(p, q, h) * 255)
                b = int(hue_to_rgb(p, q, h - 1/3) * 255)
            
            return f'#{r:02x}{g:02x}{b:02x}'
        
        # Default to black if invalid
        return '#000000'
    
    def _normalize_background_image_value(self, value: str) -> str:
        """
        Normalize a CSS background-image value.
        
        Args:
            value: CSS background-image value
            
        Returns:
            Normalized background-image value
        """
        value = value.strip()
        
        # Check for 'none'
        if value.lower() == 'none':
            return 'none'
        
        # Check for url()
        if value.startswith('url('):
            # Extract the URL
            url_match = re.match(r'url\(\s*[\'"]?(.*?)[\'"]?\s*\)', value)
            if url_match:
                return f'url({url_match.group(1)})'
            return 'none'  # Invalid URL
        
        # Check for gradients
        gradient_types = ('linear-gradient', 'radial-gradient', 'repeating-linear-gradient', 'repeating-radial-gradient')
        for gradient_type in gradient_types:
            if value.startswith(f'{gradient_type}('):
                # Find matching closing parenthesis
                nested_level = 0
                for i, char in enumerate(value):
                    if char == '(':
                        nested_level += 1
                    elif char == ')':
                        nested_level -= 1
                        if nested_level == 0:
                            # We found the matching closing parenthesis
                            return value[:i+1]
                
                # No matching closing parenthesis
                return 'none'
        
        # Unknown or invalid value
        return 'none'
    
    def _normalize_background_shorthand(self, value: str) -> str:
        """
        Normalize a CSS background shorthand value.
        
        Args:
            value: CSS background value
            
        Returns:
            Normalized background value
        """
        # For simplicity, just return the value as is
        # In a full implementation, we would expand this into its individual properties
        return value
    
    def _normalize_border_shorthand(self, value: str) -> str:
        """
        Normalize a CSS border shorthand value.
        
        Args:
            value: CSS border value
            
        Returns:
            Normalized border value
        """
        # For simplicity, just return the value as is
        # In a full implementation, we would expand this into its individual properties
        return value
    
    def _process_shorthand_properties(self, styles: Dict[str, str]) -> None:
        """
        Process shorthand properties in the styles dictionary.
        
        Args:
            styles: Dictionary of CSS properties and values
        """
        # Process 'background' shorthand
        if 'background' in styles:
            bg_value = styles['background']
            
            # Check for background-color in the shorthand
            if re.search(r'#[0-9a-fA-F]{3,6}', bg_value) or \
               re.search(r'rgb\(', bg_value) or \
               re.search(r'rgba\(', bg_value) or \
               any(color in bg_value for color in ('black', 'white', 'red', 'green', 'blue')):
                # Extract color and set background-color
                # This is a simplified approach; a real implementation would be more thorough
                color_match = re.search(r'(#[0-9a-fA-F]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)|black|white|red|green|blue)', bg_value)
                if color_match:
                    styles['background-color'] = self._normalize_color_value(color_match.group(1))
            
            # Check for background-image in the shorthand
            if 'url(' in bg_value or any(gradient in bg_value for gradient in ('linear-gradient', 'radial-gradient')):
                # Extract image/gradient and set background-image
                if 'url(' in bg_value:
                    url_match = re.search(r'url\([^)]+\)', bg_value)
                    if url_match:
                        styles['background-image'] = self._normalize_background_image_value(url_match.group(0))
                else:
                    gradient_match = re.search(r'(linear-gradient|radial-gradient)\([^)]+\)', bg_value)
                    if gradient_match:
                        styles['background-image'] = self._normalize_background_image_value(gradient_match.group(0))
        
        # Process 'border' shorthand
        if 'border' in styles:
            border_value = styles['border']
            
            # Split by space
            parts = border_value.split()
            
            # Look for width, style, and color
            for part in parts:
                # Check if it's a width
                if re.match(r'^\d+(\.\d+)?(px|em|rem|%|vh|vw)?$', part) or part in ('thin', 'medium', 'thick'):
                    styles['border-width'] = self._normalize_length_value(part)
                
                # Check if it's a style
                elif part in ('none', 'hidden', 'dotted', 'dashed', 'solid', 'double', 'groove', 'ridge', 'inset', 'outset'):
                    styles['border-style'] = part
                
                # Check if it's a color
                elif re.match(r'^#[0-9a-fA-F]{3,6}$', part) or part in ('black', 'white', 'red', 'green', 'blue', 'transparent'):
                    styles['border-color'] = self._normalize_color_value(part)

    # Add new font property normalization methods
    def _normalize_font_family(self, value: str) -> str:
        """
        Normalize a font-family value.
        
        Args:
            value: CSS font-family value
            
        Returns:
            Normalized font-family value
        """
        # Split on commas and trim whitespace
        families = [f.strip().strip('"\'') for f in value.split(',')]
        
        # Filter out empty values
        families = [f for f in families if f]
        
        if not families:
            return 'sans-serif'  # Default
        
        # Validate font family names
        valid_families = []
        generic_families = ['serif', 'sans-serif', 'monospace', 'cursive', 'fantasy', 'system-ui']
        
        for family in families:
            family_lower = family.lower()
            # Generic family name
            if family_lower in generic_families:
                valid_families.append(family_lower)
            
            # Font name with spaces
            elif '"' in family or "'" in family or " " in family:
                # Strip quotes if present
                cleaned = family.strip('"\'')
                valid_families.append(f'"{cleaned}"')
            
            # Simple font name
            else:
                valid_families.append(family)
        
        # If no valid families, return default
        if not valid_families:
            return 'sans-serif'
        
        # Join with commas
        return ', '.join(valid_families)
    
    def _normalize_font_weight(self, value: str) -> str:
        """
        Normalize a font-weight value.
        
        Args:
            value: CSS font-weight value
            
        Returns:
            Normalized font-weight value
        """
        value_lower = value.lower()
        
        # Named weights
        if value_lower in ('normal', 'bold', 'bolder', 'lighter'):
            return value_lower
        
        # Numeric weights
        try:
            weight = int(value)
            if weight >= 1 and weight <= 1000:
                return str(weight)
            elif weight < 1:
                return '100'  # Min weight
            else:
                return '900'  # Max weight
        except ValueError:
            return 'normal'  # Default
    
    def _normalize_font_style(self, value: str) -> str:
        """
        Normalize a font-style value.
        
        Args:
            value: CSS font-style value
            
        Returns:
            Normalized font-style value
        """
        value_lower = value.lower()
        
        if value_lower in ('normal', 'italic', 'oblique'):
            return value_lower
        
        return 'normal'  # Default
    
    def _normalize_text_decoration(self, value: str) -> str:
        """
        Normalize a text-decoration value.
        
        Args:
            value: CSS text-decoration value
            
        Returns:
            Normalized text-decoration value
        """
        value_lower = value.lower()
        
        # Single values
        if value_lower in ('none', 'underline', 'overline', 'line-through'):
            return value_lower
        
        # Multiple values
        valid_values = []
        for part in value_lower.split():
            if part in ('underline', 'overline', 'line-through'):
                valid_values.append(part)
        
        if not valid_values:
            return 'none'  # Default
        
        return ' '.join(valid_values)
    
    def _normalize_font_shorthand(self, value: str) -> str:
        """
        Normalize a font shorthand value.
        
        Args:
            value: CSS font value
            
        Returns:
            Normalized font value
        """
        # For simplicity, just return the value as is
        # In a full implementation, we would expand this into its individual properties
        return value

class CSSPropertyParser:
    """
    Parser for CSS properties.
    Responsible for parsing and validating individual CSS properties.
    """
    
    def __init__(self):
        """Initialize the CSS property parser."""
        # Define valid color formats
        self.color_formats = {
            'hex': r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$',
            'rgb': r'^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$',
            'rgba': r'^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(0?\.\d+|[01])\s*\)$',
            'named': r'^(black|silver|gray|white|maroon|red|purple|fuchsia|green|lime|olive|yellow|navy|blue|teal|aqua|orange|aliceblue|antiquewhite|aquamarine|azure|beige|bisque|blanchedalmond|blueviolet|brown|burlywood|cadetblue|chartreuse|chocolate|coral|cornflowerblue|cornsilk|crimson|cyan|darkblue|darkcyan|darkgoldenrod|darkgray|darkgreen|darkgrey|darkkhaki|darkmagenta|darkolivegreen|darkorange|darkorchid|darkred|darksalmon|darkseagreen|darkslateblue|darkslategray|darkslategrey|darkturquoise|darkviolet|deeppink|deepskyblue|dimgray|dimgrey|dodgerblue|firebrick|floralwhite|forestgreen|gainsboro|ghostwhite|gold|goldenrod|greenyellow|grey|honeydew|hotpink|indianred|indigo|ivory|khaki|lavender|lavenderblush|lawngreen|lemonchiffon|lightblue|lightcoral|lightcyan|lightgoldenrodyellow|lightgray|lightgreen|lightgrey|lightpink|lightsalmon|lightseagreen|lightskyblue|lightslategray|lightslategrey|lightsteelblue|lightyellow|limegreen|linen|magenta|mediumaquamarine|mediumblue|mediumorchid|mediumpurple|mediumseagreen|mediumslateblue|mediumspringgreen|mediumturquoise|mediumvioletred|midnightblue|mintcream|mistyrose|moccasin|navajowhite|oldlace|olivedrab|orangered|orchid|palegoldenrod|palegreen|paleturquoise|palevioletred|papayawhip|peachpuff|peru|pink|plum|powderblue|rosybrown|royalblue|saddlebrown|salmon|sandybrown|seagreen|seashell|sienna|skyblue|slateblue|slategray|slategrey|snow|springgreen|steelblue|tan|thistle|tomato|turquoise|violet|wheat|whitesmoke|yellowgreen|rebeccapurple|transparent)$',
        }
        
        # Define valid URL formats
        self.url_format = r'^url\(\s*[\'"]?(.*?)[\'"]?\s*\)$'
        
        # Define valid gradient formats (simplified)
        self.gradient_formats = {
            'linear': r'^linear-gradient\(([^)]+)\)$',
            'radial': r'^radial-gradient\(([^)]+)\)$',
        }
        
        # Define common units for dimensions
        self.dimension_units = ['px', 'em', 'rem', '%', 'vh', 'vw', 'pt', 'pc', 'in', 'cm', 'mm', 'ex', 'ch']
    
    def parse_color(self, color_value):
        """
        Parse and validate a CSS color value.
        
        Args:
            color_value: The color value to parse
            
        Returns:
            Validated color string or None if invalid
        """
        if not color_value:
            return None
            
        color_value = color_value.strip().lower()
        
        # Check each color format
        for format_name, regex in self.color_formats.items():
            if re.match(regex, color_value):
                return color_value
        
        # If no match found, it's an invalid color
        return None
    
    def parse_url(self, url_value):
        """
        Parse and validate a CSS URL value.
        
        Args:
            url_value: The URL value to parse
            
        Returns:
            Extracted URL or None if invalid
        """
        if not url_value:
            return None
            
        url_value = url_value.strip()
        match = re.match(self.url_format, url_value)
        
        if match:
            return match.group(1)
        
        return None
    
    def parse_gradient(self, gradient_value):
        """
        Parse and validate a CSS gradient value.
        
        Args:
            gradient_value: The gradient value to parse
            
        Returns:
            Validated gradient string or None if invalid
        """
        if not gradient_value:
            return None
            
        gradient_value = gradient_value.strip()
        
        # Check each gradient format
        for format_name, regex in self.gradient_formats.items():
            match = re.match(regex, gradient_value)
            if match:
                # For a complete implementation, we would further parse the gradient parameters
                return gradient_value
        
        return None
    
    def parse_background(self, bg_value):
        """
        Parse a CSS background shorthand property.
        
        Args:
            bg_value: The background value to parse
            
        Returns:
            Dictionary of parsed background properties
        """
        result = {
            'background-color': None,
            'background-image': None,
            'background-repeat': 'repeat',
            'background-position': '0% 0%',
            'background-size': 'auto',
            'background-attachment': 'scroll',
        }
        
        if not bg_value:
            return result
            
        # Split the shorthand value into individual components
        components = self._split_background_components(bg_value)
        
        for component in components:
            component = component.strip()
            
            # Try to parse as color
            color = self.parse_color(component)
            if color:
                result['background-color'] = color
                continue
                
            # Try to parse as URL
            url = self.parse_url(component)
            if url:
                result['background-image'] = f'url({url})'
                continue
                
            # Try to parse as gradient
            gradient = self.parse_gradient(component)
            if gradient:
                result['background-image'] = gradient
                continue
                
            # Check for repeat values
            if component in ('repeat', 'repeat-x', 'repeat-y', 'no-repeat'):
                result['background-repeat'] = component
                continue
                
            # Check for attachment values
            if component in ('scroll', 'fixed', 'local'):
                result['background-attachment'] = component
                continue
                
            # Position could be more complex (e.g., "center center", "50% 50%")
            # This is a simplified implementation
            if component in ('top', 'bottom', 'left', 'right', 'center') or '%' in component:
                result['background-position'] = component
                continue
                
            # Size could also be more complex
            if component in ('cover', 'contain'):
                result['background-size'] = component
                continue
        
        return result
    
    def _split_background_components(self, bg_value):
        """
        Split a background shorthand value into its components.
        This is a simplified implementation.
        
        Args:
            bg_value: The background value to split
            
        Returns:
            List of background components
        """
        # Handle special case for gradients
        if 'gradient(' in bg_value:
            # Find the gradient part and treat it as a single component
            gradient_start = bg_value.find('gradient(')
            if gradient_start >= 0:
                # Find the matching closing parenthesis
                open_parens = 1
                for i in range(gradient_start + 9, len(bg_value)):
                    if bg_value[i] == '(':
                        open_parens += 1
                    elif bg_value[i] == ')':
                        open_parens -= 1
                        if open_parens == 0:
                            # We found the matching closing parenthesis
                            gradient_end = i + 1
                            gradient_part = bg_value[gradient_start-7:gradient_end]  # include 'linear-' or 'radial-'
                            rest = bg_value[:gradient_start-7] + ' ' + bg_value[gradient_end:]
                            components = [comp.strip() for comp in rest.split() if comp.strip()]
                            components.append(gradient_part)
                            return components
        
        # Simple splitting for non-gradient cases
        return [comp.strip() for comp in bg_value.split() if comp.strip()] 