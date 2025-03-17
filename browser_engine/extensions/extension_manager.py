"""
Extension manager for browser extensions.
This module handles loading, managing, and running browser extensions.
"""

import os
import logging
import json
import csv
from typing import Dict, List, Optional, Any, Callable

logger = logging.getLogger(__name__)

class ExtensionManager:
    """
    Extension manager for browser extensions.
    
    This class handles loading, enabling/disabling, and executing browser extensions.
    """
    
    def __init__(self, config_manager):
        """
        Initialize the extension manager.
        
        Args:
            config_manager: The configuration manager
        """
        self.config_manager = config_manager
        
        # Extensions directory
        self.extensions_dir = os.path.expanduser("~/.wink_browser/extensions")
        os.makedirs(self.extensions_dir, exist_ok=True)
        
        # Loaded extensions
        self.extensions: Dict[str, Dict[str, Any]] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Load extensions if enabled
        if self.config_manager.get_config("extensions.enabled", True):
            self.load_extensions()
        
        logger.info("Extension manager initialized")
    
    def load_extensions(self) -> None:
        """Load all extensions from the extensions directory."""
        try:
            # Get list of extension directories
            for item in os.listdir(self.extensions_dir):
                ext_dir = os.path.join(self.extensions_dir, item)
                if os.path.isdir(ext_dir):
                    self._load_extension(ext_dir)
            
            logger.info(f"Loaded {len(self.extensions)} extensions")
        except Exception as e:
            logger.error(f"Error loading extensions: {e}")
    
    def _load_extension(self, extension_dir: str) -> bool:
        """
        Load an extension from a directory.
        
        Args:
            extension_dir: Path to the extension directory
            
        Returns:
            True if the extension was loaded successfully, False otherwise
        """
        try:
            # Check for extension properties file
            props_file = os.path.join(extension_dir, "extprops.csv")
            if not os.path.exists(props_file):
                logger.warning(f"No extprops.csv found in {extension_dir}")
                return False
            
            # Parse extension properties
            extension_info = {
                "id": os.path.basename(extension_dir),
                "path": extension_dir,
                "enabled": False,
                "name": "",
                "version": "",
                "description": "",
                "scripts": {}
            }
            
            # Read extension properties file
            with open(props_file, 'r', encoding='utf-8') as f:
                # Read CSV file
                reader = csv.reader(f)
                
                # Read metadata section (Key, Value pairs)
                in_metadata = True
                for row in reader:
                    if len(row) == 0:
                        # Empty row indicates end of metadata section
                        in_metadata = False
                        continue
                    
                    if in_metadata and len(row) >= 2:
                        key, value = row[0], row[1]
                        
                        # Handle metadata properties
                        if key.startswith('@'):
                            key = key[1:]  # Remove @ prefix
                            
                            if key == 'name':
                                extension_info['name'] = value
                            elif key == 'version':
                                extension_info['version'] = value
                            elif key == 'description':
                                extension_info['description'] = value
                            elif key == 'enabled':
                                extension_info['enabled'] = value.lower() == 'true'
                    
                    # Script section (Script, Events)
                    elif not in_metadata and len(row) >= 2:
                        script, events = row[0], row[1]
                        
                        # Add script and its events
                        event_list = [e.strip() for e in events.split(',')]
                        extension_info['scripts'][script] = event_list
            
            # If name is not set, use directory name
            if not extension_info['name']:
                extension_info['name'] = extension_info['id']
            
            # Add to loaded extensions
            self.extensions[extension_info['id']] = extension_info
            
            logger.debug(f"Loaded extension: {extension_info['name']} v{extension_info['version']}")
            return True
        except Exception as e:
            logger.error(f"Error loading extension from {extension_dir}: {e}")
            return False
    
    def get_extensions(self) -> List[Dict[str, Any]]:
        """
        Get all loaded extensions.
        
        Returns:
            List of extension information dictionaries
        """
        return list(self.extensions.values())
    
    def get_extension(self, extension_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific extension.
        
        Args:
            extension_id: ID of the extension
            
        Returns:
            Extension information or None if not found
        """
        return self.extensions.get(extension_id)
    
    def is_extension_enabled(self, extension_id: str) -> bool:
        """
        Check if an extension is enabled.
        
        Args:
            extension_id: ID of the extension
            
        Returns:
            True if the extension is enabled, False otherwise
        """
        extension = self.extensions.get(extension_id)
        return extension is not None and extension.get('enabled', False)
    
    def enable_extension(self, extension_id: str) -> bool:
        """
        Enable an extension.
        
        Args:
            extension_id: ID of the extension
            
        Returns:
            True if the extension was enabled, False otherwise
        """
        if extension_id in self.extensions:
            self.extensions[extension_id]['enabled'] = True
            self._update_extension_props(extension_id)
            logger.info(f"Enabled extension: {self.extensions[extension_id]['name']}")
            return True
        return False
    
    def disable_extension(self, extension_id: str) -> bool:
        """
        Disable an extension.
        
        Args:
            extension_id: ID of the extension
            
        Returns:
            True if the extension was disabled, False otherwise
        """
        if extension_id in self.extensions:
            self.extensions[extension_id]['enabled'] = False
            self._update_extension_props(extension_id)
            logger.info(f"Disabled extension: {self.extensions[extension_id]['name']}")
            return True
        return False
    
    def _update_extension_props(self, extension_id: str) -> bool:
        """
        Update the extension properties file.
        
        Args:
            extension_id: ID of the extension
            
        Returns:
            True if the properties were updated, False otherwise
        """
        try:
            extension = self.extensions.get(extension_id)
            if not extension:
                return False
            
            props_file = os.path.join(extension['path'], "extprops.csv")
            
            # Read existing file
            rows = []
            with open(props_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    rows.append(row)
            
            # Update enabled property
            for i, row in enumerate(rows):
                if len(row) >= 2 and row[0] == '@enabled':
                    rows[i][1] = 'true' if extension['enabled'] else 'false'
                    break
            
            # Write updated file
            with open(props_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            
            return True
        except Exception as e:
            logger.error(f"Error updating extension properties for {extension_id}: {e}")
            return False
    
    def trigger_event(self, event_name: str, event_data: Any = None) -> None:
        """
        Trigger an extension event.
        
        Args:
            event_name: Name of the event to trigger
            event_data: Data to pass to the event handlers
        """
        # Skip if extensions are disabled
        if not self.config_manager.get_config("extensions.enabled", True):
            return
        
        # Find extensions that handle this event
        for ext_id, extension in self.extensions.items():
            # Skip disabled extensions
            if not extension.get('enabled', False):
                continue
            
            # Check if extension handles this event
            scripts_to_run = []
            for script, events in extension.get('scripts', {}).items():
                if event_name in events:
                    scripts_to_run.append(script)
            
            # Run the scripts
            for script in scripts_to_run:
                self._run_extension_script(ext_id, script, event_name, event_data)
    
    def _run_extension_script(self, extension_id: str, script: str, 
                              event_name: str, event_data: Any = None) -> None:
        """
        Run an extension script.
        
        Args:
            extension_id: ID of the extension
            script: Name of the script to run
            event_name: Name of the event that triggered the script
            event_data: Data to pass to the script
        """
        try:
            extension = self.extensions.get(extension_id)
            if not extension:
                return
            
            # Construct path to script
            script_path = os.path.join(extension['path'], script)
            if not os.path.exists(script_path):
                logger.warning(f"Script not found: {script_path}")
                return
            
            # In a real implementation, we would execute the script here
            # For this example, we'll just log that it would run
            logger.info(f"Would run script {script} for extension {extension['name']} on event {event_name}")
            
            # Example of running a JavaScript script:
            # from browser_engine.javascript.engine import JavaScriptEngine
            # js_engine = JavaScriptEngine()
            # js_engine.execute_file(script_path, {
            #     'event': event_name,
            #     'data': event_data,
            #     'extension': extension
            # })
        except Exception as e:
            logger.error(f"Error running extension script {script} for {extension_id}: {e}")
    
    def create_example_extension(self) -> bool:
        """
        Create an example extension.
        
        Returns:
            True if the extension was created, False otherwise
        """
        try:
            # Create example extension directory
            example_dir = os.path.join(self.extensions_dir, "example_extension")
            os.makedirs(example_dir, exist_ok=True)
            
            # Create extension properties file
            props_file = os.path.join(example_dir, "extprops.csv")
            with open(props_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Key', 'Value'])
                writer.writerow(['@name', 'Example Extension'])
                writer.writerow(['@version', '1.0.0'])
                writer.writerow(['@description', 'An example extension for Wink Browser'])
                writer.writerow(['@enabled', 'true'])
                writer.writerow([])
                writer.writerow(['Script', 'Events'])
                writer.writerow(['main.js', 'page_load,dom_ready'])
                writer.writerow(['links.js', 'link_click'])
            
            # Create main.js script
            main_js = os.path.join(example_dir, "main.js")
            with open(main_js, 'w', encoding='utf-8') as f:
                f.write('// Example extension main script\n')
                f.write('console.log("Example extension loaded");\n\n')
                f.write('// Handle page load event\n')
                f.write('function onPageLoad(data) {\n')
                f.write('    console.log("Page loaded:", data.url);\n')
                f.write('}\n\n')
                f.write('// Handle DOM ready event\n')
                f.write('function onDOMReady(data) {\n')
                f.write('    console.log("DOM ready:", data.url);\n')
                f.write('}\n\n')
                f.write('// Register event handlers\n')
                f.write('if (event === "page_load") {\n')
                f.write('    onPageLoad(data);\n')
                f.write('} else if (event === "dom_ready") {\n')
                f.write('    onDOMReady(data);\n')
                f.write('}\n')
            
            # Create links.js script
            links_js = os.path.join(example_dir, "links.js")
            with open(links_js, 'w', encoding='utf-8') as f:
                f.write('// Example extension link handler script\n')
                f.write('console.log("Link handler loaded");\n\n')
                f.write('// Handle link click event\n')
                f.write('function onLinkClick(data) {\n')
                f.write('    console.log("Link clicked:", data.url);\n')
                f.write('    // You can modify the URL or prevent navigation\n')
                f.write('    return true; // Allow navigation\n')
                f.write('}\n\n')
                f.write('// Register event handler\n')
                f.write('if (event === "link_click") {\n')
                f.write('    onLinkClick(data);\n')
                f.write('}\n')
            
            # Load the new extension
            self._load_extension(example_dir)
            
            logger.info("Created example extension")
            return True
        except Exception as e:
            logger.error(f"Error creating example extension: {e}")
            return False 