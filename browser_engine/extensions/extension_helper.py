"""
Helper module for creating and loading example extensions.
"""

import logging
import os
import csv
import shutil
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ExtensionHelper:
    """Helper for creating and working with extensions."""
    
    @staticmethod
    def create_example_extension(extensions_dir: str, name: str) -> Optional[str]:
        """
        Create an example extension.
        
        Args:
            extensions_dir: Directory to store extensions
            name: Extension name (will be used as directory name)
            
        Returns:
            Optional[str]: Path to the created extension or None if failed
        """
        try:
            # Create extension directory
            ext_dir = os.path.join(extensions_dir, name)
            os.makedirs(ext_dir, exist_ok=True)
            
            # Create extprops.csv
            props_file = os.path.join(ext_dir, "extprops.csv")
            with open(props_file, 'w', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Key", "Value"])
                writer.writerow(["@name", name])
                writer.writerow(["@version", "1.0.0"])
                writer.writerow(["@description", f"Example {name} extension"])
                writer.writerow(["@enabled", "true"])
                writer.writerow([])
                writer.writerow(["Script", "Events"])
                writer.writerow(["main.js", "page_load,dom_ready"])
                writer.writerow(["link_handler.js", "link_click"])
            
            # Create main.js
            main_js = os.path.join(ext_dir, "main.js")
            with open(main_js, 'w', encoding='utf-8') as f:
                f.write("// Example extension script\n")
                f.write("console.log('Extension loaded: " + name + "');\n\n")
                
                f.write("// This function runs when a page loads\n")
                f.write("function onPageLoad(url) {\n")
                f.write("  console.log('Page loaded: ' + url);\n")
                f.write("  \n")
                f.write("  // Store the last visited page in extension storage\n")
                f.write("  if (API.storage && API.storage.extension) {\n")
                f.write("    API.storage.extension.set('lastVisited', url);\n")
                f.write("  }\n")
                f.write("}\n\n")
                
                f.write("// This function runs when the DOM is ready\n")
                f.write("function onDomReady(document) {\n")
                f.write("  console.log('DOM ready');\n")
                f.write("  \n")
                f.write("  // Example: Find all headings and log them\n")
                f.write("  if (API.dom && API.dom.query) {\n")
                f.write("    const headings = API.dom.query.selectAll('h1, h2, h3');\n")
                f.write("    console.log('Found ' + headings.length + ' headings');\n")
                f.write("    \n")
                f.write("    // Add a CSS class to headings if DOM modification is allowed\n")
                f.write("    if (API.dom.modify) {\n")
                f.write("      for (let i = 0; i < headings.length; i++) {\n")
                f.write("        API.dom.modify.addClass(headings[i], 'extension-styled-heading');\n")
                f.write("      }\n")
                f.write("    }\n")
                f.write("  }\n")
                f.write("}\n")
            
            # Create link_handler.js
            link_js = os.path.join(ext_dir, "link_handler.js")
            with open(link_js, 'w', encoding='utf-8') as f:
                f.write("// Example link handler script\n")
                f.write("console.log('Link handler loaded');\n\n")
                
                f.write("// This function runs when a link is clicked\n")
                f.write("function onLinkClick(link, url) {\n")
                f.write("  console.log('Link clicked: ' + url);\n")
                f.write("  \n")
                f.write("  // Example: Count link clicks\n")
                f.write("  if (API.storage && API.storage.extension) {\n")
                f.write("    const clicks = API.storage.extension.get('linkClicks') || 0;\n")
                f.write("    API.storage.extension.set('linkClicks', clicks + 1);\n")
                f.write("    \n")
                f.write("    // Show a notification after 5 clicks\n")
                f.write("    if (clicks + 1 === 5 && API.notifications && API.notifications.create) {\n")
                f.write("      API.notifications.create(\n")
                f.write("        'Link milestone',\n")
                f.write("        'You have clicked 5 links since the extension was loaded!'\n")
                f.write("      );\n")
                f.write("    }\n")
                f.write("  }\n")
                f.write("  \n")
                f.write("  // Return true to allow the link to be followed\n")
                f.write("  return true;\n")
                f.write("}\n")
            
            logger.info(f"Created example extension: {name}")
            return ext_dir
        
        except Exception as e:
            logger.error(f"Error creating example extension: {e}")
            return None
    
    @staticmethod
    def create_dark_mode_extension(extensions_dir: str) -> Optional[str]:
        """
        Create a dark mode extension.
        
        Args:
            extensions_dir: Directory to store extensions
            
        Returns:
            Optional[str]: Path to the created extension or None if failed
        """
        try:
            # Create extension directory
            ext_dir = os.path.join(extensions_dir, "dark-mode")
            os.makedirs(ext_dir, exist_ok=True)
            
            # Create extprops.csv
            props_file = os.path.join(ext_dir, "extprops.csv")
            with open(props_file, 'w', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Key", "Value"])
                writer.writerow(["@name", "Dark Mode"])
                writer.writerow(["@version", "1.0.0"])
                writer.writerow(["@description", "Adds dark mode to websites"])
                writer.writerow(["@enabled", "true"])
                writer.writerow([])
                writer.writerow(["Script", "Events"])
                writer.writerow(["dark-mode.js", "dom_ready"])
            
            # Create dark-mode.js
            main_js = os.path.join(ext_dir, "dark-mode.js")
            with open(main_js, 'w', encoding='utf-8') as f:
                f.write("// Dark Mode Extension\n")
                f.write("console.log('Dark Mode extension loaded');\n\n")
                
                f.write("// This function runs when the DOM is ready\n")
                f.write("function onDomReady(document) {\n")
                f.write("  console.log('Applying dark mode');\n\n")
                
                f.write("  // Create a style element\n")
                f.write("  const style = document.createElement('style');\n")
                f.write("  style.textContent = `\n")
                f.write("    /* Dark mode styles */\n")
                f.write("    body {\n")
                f.write("      background-color: #121212 !important;\n")
                f.write("      color: #e0e0e0 !important;\n")
                f.write("    }\n")
                f.write("    \n")
                f.write("    a {\n")
                f.write("      color: #90caf9 !important;\n")
                f.write("    }\n")
                f.write("    \n")
                f.write("    h1, h2, h3, h4, h5, h6 {\n")
                f.write("      color: #bb86fc !important;\n")
                f.write("    }\n")
                f.write("    \n")
                f.write("    input, textarea, select, button {\n")
                f.write("      background-color: #333 !important;\n")
                f.write("      color: #e0e0e0 !important;\n")
                f.write("      border-color: #666 !important;\n")
                f.write("    }\n")
                f.write("  `;\n\n")
                
                f.write("  // Add the style to the document\n")
                f.write("  document.head.appendChild(style);\n")
                f.write("  \n")
                f.write("  // Log success\n")
                f.write("  console.log('Dark mode applied');\n")
                f.write("}\n")
            
            logger.info("Created dark mode extension")
            return ext_dir
        
        except Exception as e:
            logger.error(f"Error creating dark mode extension: {e}")
            return None
    
    @staticmethod
    def create_ad_blocker_extension(extensions_dir: str) -> Optional[str]:
        """
        Create an ad blocker extension.
        
        Args:
            extensions_dir: Directory to store extensions
            
        Returns:
            Optional[str]: Path to the created extension or None if failed
        """
        try:
            # Create extension directory
            ext_dir = os.path.join(extensions_dir, "ad-blocker")
            os.makedirs(ext_dir, exist_ok=True)
            
            # Create extprops.csv
            props_file = os.path.join(ext_dir, "extprops.csv")
            with open(props_file, 'w', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Key", "Value"])
                writer.writerow(["@name", "Simple Ad Blocker"])
                writer.writerow(["@version", "1.0.0"])
                writer.writerow(["@description", "Blocks common ad elements"])
                writer.writerow(["@enabled", "true"])
                writer.writerow([])
                writer.writerow(["Script", "Events"])
                writer.writerow(["ad-blocker.js", "dom_ready"])
            
            # Create ad-blocker.js
            main_js = os.path.join(ext_dir, "ad-blocker.js")
            with open(main_js, 'w', encoding='utf-8') as f:
                f.write("// Simple Ad Blocker Extension\n")
                f.write("console.log('Ad Blocker extension loaded');\n\n")
                
                f.write("// Common ad-related selectors\n")
                f.write("const AD_SELECTORS = [\n")
                f.write("  '.ad', '.ads', '.advertisement',\n")
                f.write("  '.banner-ads', '.banner_ad',\n")
                f.write("  '.google-ad', '.GoogleAd',\n")
                f.write("  'div[id*=\"google_ads\"]',\n")
                f.write("  'div[id*=\"banner-ad\"]',\n")
                f.write("  'div[class*=\"sponsored\"]',\n")
                f.write("  'iframe[src*=\"doubleclick.net\"]',\n")
                f.write("  'div[id*=\"aswift\"]'\n")
                f.write("];\n\n")
                
                f.write("// This function runs when the DOM is ready\n")
                f.write("function onDomReady(document) {\n")
                f.write("  console.log('Checking for ad elements');\n")
                f.write("  \n")
                f.write("  let blockedCount = 0;\n")
                f.write("  \n")
                f.write("  // Try to find and hide ad elements\n")
                f.write("  AD_SELECTORS.forEach(selector => {\n")
                f.write("    if (API.dom && API.dom.query) {\n")
                f.write("      const adElements = API.dom.query.selectAll(selector);\n")
                f.write("      \n")
                f.write("      for (let i = 0; i < adElements.length; i++) {\n")
                f.write("        // Hide the element by setting display:none\n")
                f.write("        adElements[i].style.display = 'none';\n")
                f.write("        blockedCount++;\n")
                f.write("      }\n")
                f.write("    }\n")
                f.write("  });\n")
                f.write("  \n")
                f.write("  // Report results\n")
                f.write("  if (blockedCount > 0) {\n")
                f.write("    console.log(`Blocked ${blockedCount} ad elements`);\n")
                f.write("    \n")
                f.write("    // Show notification if supported\n")
                f.write("    if (API.notifications && API.notifications.create) {\n")
                f.write("      API.notifications.create(\n")
                f.write("        'Ads Blocked',\n")
                f.write("        `Blocked ${blockedCount} ad elements on this page`\n")
                f.write("      );\n")
                f.write("    }\n")
                f.write("  } else {\n")
                f.write("    console.log('No ad elements found on this page');\n")
                f.write("  }\n")
                f.write("}\n")
            
            logger.info("Created ad blocker extension")
            return ext_dir
        
        except Exception as e:
            logger.error(f"Error creating ad blocker extension: {e}")
            return None
    
    @staticmethod
    def create_all_example_extensions(extensions_dir: str) -> int:
        """
        Create all example extensions.
        
        Args:
            extensions_dir: Directory to store extensions
            
        Returns:
            int: Number of extensions created
        """
        count = 0
        
        # Create example extensions
        if ExtensionHelper.create_example_extension(extensions_dir, "hello-world"):
            count += 1
        
        if ExtensionHelper.create_dark_mode_extension(extensions_dir):
            count += 1
        
        if ExtensionHelper.create_ad_blocker_extension(extensions_dir):
            count += 1
        
        logger.info(f"Created {count} example extensions")
        return count 