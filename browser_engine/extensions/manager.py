"""
Extension manager implementation.
This module is responsible for loading, validating, and executing extensions.
"""

import logging
import os
import csv
import json
import re
import threading
from typing import Dict, List, Optional, Any, Callable, Set
import shutil

from browser_engine.utils.config import Config

logger = logging.getLogger(__name__)

# Blocked patterns for JavaScript security
BLOCKED_JS_PATTERNS = [
    # Infinite loops
    r'while\s*\(true\s*\)',
    r'while\s*\(\s*1\s*\)',
    r'for\s*\(\s*;;\s*\)',
    
    # Dangerous APIs
    r'eval\s*\(',
    r'Function\s*\(\s*["\']',
    r'document\.write\s*\(',
    
    # Dangerous Node.js APIs
    r'require\s*\(\s*["\']fs["\']',
    r'require\s*\(\s*["\']child_process["\']',
    r'require\s*\(\s*["\']os["\']',
    r'process\.env',
    
    # Dangerous browser APIs
    r'localStorage\.',
    r'sessionStorage\.',
    r'indexedDB\.',
    r'navigator\.geolocation',
    r'navigator\.credentials',
    
    # Network requests
    r'fetch\s*\(',
    r'XMLHttpRequest',
    
    # Crypto operations (potential for cryptojacking)
    r'crypto\.subtle',
    r'window\.crypto',
    
    # DOM manipulation that could be used for phishing
    r'document\.domain\s*=',
    r'document\.cookie\s*=',
    r'location\s*=',
    r'location\.href\s*=',
    r'location\.replace\s*\(',
    r'window\.open\s*\(',
    
    # Timing attacks
    r'performance\.now\s*\(',
]

# Allowed events for extension hooks
ALLOWED_EVENTS = {
    'page_load': "Triggered when a page is loaded",
    'page_unload': "Triggered when a page is unloaded",
    'dom_ready': "Triggered when the DOM is ready",
    'link_click': "Triggered when a link is clicked",
    'form_submit': "Triggered when a form is submitted",
    'text_select': "Triggered when text is selected",
    'context_menu': "Triggered when the context menu is opened",
    'tab_change': "Triggered when a tab is changed",
    'browser_start': "Triggered when the browser starts",
    'browser_exit': "Triggered when the browser exits",
    'bookmark_add': "Triggered when a bookmark is added",
    'download_start': "Triggered when a download starts",
    'download_complete': "Triggered when a download completes"
}

class ExtensionManager:
    """Manager for browser extensions."""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the extension manager.
        
        Args:
            config: Configuration object
        """
        self.config = config or Config()
        
        # Get extensions directory from config or use default
        self.extensions_dir = self.config.get(
            "extensions.directory", 
            os.path.join(os.path.expanduser("~"), ".wink_browser", "extensions")
        )
        
        # Ensure the extensions directory exists
        os.makedirs(self.extensions_dir, exist_ok=True)
        
        # Store loaded extensions
        self.extensions: Dict[str, Dict[str, Any]] = {}
        
        # Store event listeners
        self.event_listeners: Dict[str, List[Dict[str, Any]]] = {
            event: [] for event in ALLOWED_EVENTS
        }
        
        # Thread lock for thread safety
        self._lock = threading.Lock()
        
        # Security settings
        self.js_filter_enabled = self.config.get("extensions.security.js_filter", True)
        self.allow_network_access = self.config.get("extensions.security.allow_network", False)
        
        # Load extensions
        self.load_extensions()
        
        logger.debug(f"Extension manager initialized (dir: {self.extensions_dir})")
    
    def load_extensions(self) -> None:
        """Load all extensions from the extensions directory."""
        try:
            with self._lock:
                # Clear existing extensions
                self.extensions = {}
                
                # Reset event listeners
                self.event_listeners = {event: [] for event in ALLOWED_EVENTS}
                
                # List extension directories
                if not os.path.exists(self.extensions_dir):
                    logger.debug(f"Extensions directory does not exist: {self.extensions_dir}")
                    return
                
                for entry in os.listdir(self.extensions_dir):
                    ext_path = os.path.join(self.extensions_dir, entry)
                    
                    # Skip if not a directory
                    if not os.path.isdir(ext_path):
                        continue
                    
                    # Check for extension properties file
                    props_file = os.path.join(ext_path, "extprops.csv")
                    if not os.path.exists(props_file):
                        logger.warning(f"Extension {entry} does not have an extprops.csv file")
                        continue
                    
                    # Load the extension
                    self._load_extension(entry, ext_path)
            
            logger.info(f"Loaded {len(self.extensions)} extensions")
        except Exception as e:
            logger.error(f"Error loading extensions: {e}")
    
    def _load_extension(self, ext_id: str, ext_path: str) -> None:
        """
        Load a single extension.
        
        Args:
            ext_id: Extension ID
            ext_path: Path to the extension directory
        """
        try:
            logger.debug(f"Loading extension: {ext_id}")
            
            # Extension metadata
            extension = {
                "id": ext_id,
                "path": ext_path,
                "name": ext_id,
                "version": "unknown",
                "description": "",
                "enabled": True,
                "scripts": {}
            }
            
            # Parse properties file
            props_file = os.path.join(ext_path, "extprops.csv")
            extension_info = {}
            script_info = []
            
            with open(props_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)  # Skip header row
                
                for row in reader:
                    if len(row) < 2:
                        continue
                    
                    # Check if this is a metadata or script entry
                    if row[0].startswith("@"):
                        # Metadata entry
                        key = row[0][1:]  # Remove @ prefix
                        value = row[1]
                        extension_info[key] = value
                    else:
                        # Script entry
                        script_file = row[0]
                        if len(row) > 1:
                            events = row[1].split(",")
                            script_info.append((script_file, events))
            
            # Update extension metadata
            if "name" in extension_info:
                extension["name"] = extension_info["name"]
            if "version" in extension_info:
                extension["version"] = extension_info["version"]
            if "description" in extension_info:
                extension["description"] = extension_info["description"]
            if "enabled" in extension_info:
                extension["enabled"] = extension_info["enabled"].lower() == "true"
            
            # Load and validate scripts
            for script_file, events in script_info:
                script_path = os.path.join(ext_path, script_file)
                
                # Check if script exists
                if not os.path.exists(script_path):
                    logger.warning(f"Script {script_file} does not exist for extension {ext_id}")
                    continue
                
                # Read script content
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
                
                # Validate script
                if not self._validate_script(script_content):
                    logger.warning(f"Script {script_file} for extension {ext_id} failed validation")
                    continue
                
                # Store script info
                extension["scripts"][script_file] = {
                    "path": script_path,
                    "events": [e.strip() for e in events if e.strip() in ALLOWED_EVENTS],
                    "content": script_content
                }
                
                # Register event listeners
                for event in extension["scripts"][script_file]["events"]:
                    self.event_listeners[event].append({
                        "extension": ext_id,
                        "script": script_file
                    })
            
            # Store extension
            self.extensions[ext_id] = extension
            
            logger.debug(f"Loaded extension {ext_id} with {len(extension['scripts'])} scripts")
        
        except Exception as e:
            logger.error(f"Error loading extension {ext_id}: {e}")
    
    def _validate_script(self, script_content: str) -> bool:
        """
        Validate a script for security issues.
        
        Args:
            script_content: JavaScript code to validate
            
        Returns:
            bool: True if the script is safe, False otherwise
        """
        if not self.js_filter_enabled:
            return True
        
        # Check for blocked patterns
        for pattern in BLOCKED_JS_PATTERNS:
            if re.search(pattern, script_content):
                logger.warning(f"Script contains blocked pattern: {pattern}")
                return False
        
        # Additional checks can be added here
        
        return True
    
    def trigger_event(self, event: str, context: Dict[str, Any] = None) -> None:
        """
        Trigger an event for all registered extensions.
        
        Args:
            event: Event name
            context: Event context (variables available to scripts)
        """
        if event not in ALLOWED_EVENTS:
            logger.warning(f"Invalid event: {event}")
            return
        
        context = context or {}
        
        # Skip if no listeners
        if not self.event_listeners[event]:
            return
        
        logger.debug(f"Triggering event {event} for {len(self.event_listeners[event])} listeners")
        
        # Execute scripts for this event
        for listener in self.event_listeners[event]:
            ext_id = listener["extension"]
            script_file = listener["script"]
            
            # Skip if extension is disabled
            if not self.extensions[ext_id]["enabled"]:
                continue
            
            # Get script content
            script_content = self.extensions[ext_id]["scripts"][script_file]["content"]
            
            # Execute script
            self._execute_script(ext_id, script_file, script_content, context)
    
    def _execute_script(self, ext_id: str, script_file: str, script_content: str, context: Dict[str, Any]) -> None:
        """
        Execute a script.
        
        Args:
            ext_id: Extension ID
            script_file: Script file name
            script_content: JavaScript code
            context: Execution context
        """
        try:
            # In a real implementation, we would execute the script in a sandboxed environment
            # For now, we'll just log that it would be executed
            logger.debug(f"Executing script {script_file} for extension {ext_id}")
            
            # TODO: Implement actual script execution using the JS engine
            # This would involve:
            # 1. Creating a sandboxed context
            # 2. Injecting safe APIs
            # 3. Executing the script
            # 4. Handling any errors
            
        except Exception as e:
            logger.error(f"Error executing script {script_file} for extension {ext_id}: {e}")
    
    def install_extension(self, ext_path: str) -> Optional[str]:
        """
        Install an extension from a directory.
        
        Args:
            ext_path: Path to the extension directory
            
        Returns:
            Optional[str]: Extension ID if installation was successful, None otherwise
        """
        try:
            # Get the extension ID from the directory name
            ext_id = os.path.basename(ext_path)
            
            # Check if the extension already exists
            target_path = os.path.join(self.extensions_dir, ext_id)
            if os.path.exists(target_path):
                logger.warning(f"Extension {ext_id} already exists")
                return None
            
            # Check for extension properties file
            props_file = os.path.join(ext_path, "extprops.csv")
            if not os.path.exists(props_file):
                logger.warning(f"Extension {ext_id} does not have an extprops.csv file")
                return None
            
            # Copy the extension to the extensions directory
            shutil.copytree(ext_path, target_path)
            
            # Load the extension
            self._load_extension(ext_id, target_path)
            
            logger.info(f"Installed extension: {ext_id}")
            
            return ext_id
        
        except Exception as e:
            logger.error(f"Error installing extension: {e}")
            return None
    
    def uninstall_extension(self, ext_id: str) -> bool:
        """
        Uninstall an extension.
        
        Args:
            ext_id: Extension ID
            
        Returns:
            bool: True if the extension was uninstalled, False otherwise
        """
        try:
            # Check if the extension exists
            if ext_id not in self.extensions:
                logger.warning(f"Extension {ext_id} does not exist")
                return False
            
            # Get the extension path
            ext_path = self.extensions[ext_id]["path"]
            
            # Remove the extension directory
            shutil.rmtree(ext_path)
            
            # Remove from loaded extensions
            with self._lock:
                del self.extensions[ext_id]
                
                # Remove from event listeners
                for event in self.event_listeners:
                    self.event_listeners[event] = [
                        listener for listener in self.event_listeners[event]
                        if listener["extension"] != ext_id
                    ]
            
            logger.info(f"Uninstalled extension: {ext_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error uninstalling extension: {e}")
            return False
    
    def enable_extension(self, ext_id: str) -> bool:
        """
        Enable an extension.
        
        Args:
            ext_id: Extension ID
            
        Returns:
            bool: True if the extension was enabled, False otherwise
        """
        if ext_id not in self.extensions:
            logger.warning(f"Extension {ext_id} does not exist")
            return False
        
        with self._lock:
            self.extensions[ext_id]["enabled"] = True
        
        logger.info(f"Enabled extension: {ext_id}")
        
        return True
    
    def disable_extension(self, ext_id: str) -> bool:
        """
        Disable an extension.
        
        Args:
            ext_id: Extension ID
            
        Returns:
            bool: True if the extension was disabled, False otherwise
        """
        if ext_id not in self.extensions:
            logger.warning(f"Extension {ext_id} does not exist")
            return False
        
        with self._lock:
            self.extensions[ext_id]["enabled"] = False
        
        logger.info(f"Disabled extension: {ext_id}")
        
        return True
    
    def get_extensions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all loaded extensions.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of extension IDs to extension info
        """
        with self._lock:
            return {ext_id: {
                "id": ext["id"],
                "name": ext["name"],
                "version": ext["version"],
                "description": ext["description"],
                "enabled": ext["enabled"],
                "scripts": list(ext["scripts"].keys())
            } for ext_id, ext in self.extensions.items()}
    
    def get_extension(self, ext_id: str) -> Optional[Dict[str, Any]]:
        """
        Get info for a specific extension.
        
        Args:
            ext_id: Extension ID
            
        Returns:
            Optional[Dict[str, Any]]: Extension info or None if not found
        """
        with self._lock:
            if ext_id not in self.extensions:
                return None
            
            ext = self.extensions[ext_id]
            return {
                "id": ext["id"],
                "name": ext["name"],
                "version": ext["version"],
                "description": ext["description"],
                "enabled": ext["enabled"],
                "scripts": list(ext["scripts"].keys())
            }
    
    def create_extension_structure(self, ext_dir: str, name: str, description: str) -> bool:
        """
        Create a new extension structure.
        
        Args:
            ext_dir: Directory to create the extension in
            name: Extension name
            description: Extension description
            
        Returns:
            bool: True if the extension was created, False otherwise
        """
        try:
            # Create the extension directory
            os.makedirs(ext_dir, exist_ok=True)
            
            # Create the properties file
            props_file = os.path.join(ext_dir, "extprops.csv")
            with open(props_file, 'w', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Key", "Value"])
                writer.writerow(["@name", name])
                writer.writerow(["@version", "1.0.0"])
                writer.writerow(["@description", description])
                writer.writerow(["@enabled", "true"])
                writer.writerow([])
                writer.writerow(["Script", "Events"])
                writer.writerow(["main.js", "page_load,dom_ready"])
            
            # Create the main script file
            script_file = os.path.join(ext_dir, "main.js")
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write("// Example extension script\n")
                f.write("console.log('Extension loaded');\n\n")
                f.write("// This function will run when a page loads\n")
                f.write("function onPageLoad() {\n")
                f.write("  console.log('Page loaded');\n")
                f.write("}\n\n")
                f.write("// This function will run when the DOM is ready\n")
                f.write("function onDomReady() {\n")
                f.write("  console.log('DOM ready');\n")
                f.write("}\n")
            
            logger.info(f"Created extension structure in {ext_dir}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error creating extension structure: {e}")
            return False 