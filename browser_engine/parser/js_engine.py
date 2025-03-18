"""
JavaScript engine implementation with support for executing JavaScript in a pure Python environment.
This module is responsible for executing JavaScript code in the browser using dukpy instead of a browser-based technology.
"""

import logging
import os
import json
import re
import threading
import tempfile
from typing import Dict, List, Optional, Any, Callable, Union, Set
import traceback
import time
from pathlib import Path
import concurrent.futures

# Import dukpy instead of js2py
try:
    import dukpy
    DUKPY_AVAILABLE = True
except ImportError:
    DUKPY_AVAILABLE = False
    logging.warning("dukpy not available. JavaScript execution will be limited.")

logger = logging.getLogger(__name__)

# Set of modern JavaScript features supported by dukpy (based on duktape)
MODERN_JS_FEATURES = {
    # ES5 features (fully supported)
    'strict_mode', 'json', 'array_methods', 'string_methods',
    
    # ES5.1/ES6 features (at least partially supported)
    'const_let', 'template_literals', 'arrow_functions',
    'classes', 'promises', 'symbols', 'typed_arrays',
    
    # Limited or not supported
    # 'async_await', 'generators', 'iterators', 'modules',
    # 'proxies', 'reflect_api'
}

class JSEngine:
    """JavaScript engine using dukpy for JavaScript execution in a pure Python environment."""
    
    def __init__(self, 
                 sandbox: bool = True, 
                 timeout: int = 5000, 
                 enable_modern_js: bool = True,
                 cache_dir: Optional[str] = None):
        """
        Initialize the JavaScript engine.
        
        Args:
            sandbox: Whether to run JavaScript in a sandbox (limited effect with dukpy)
            timeout: Default timeout for JavaScript execution (in milliseconds)
            enable_modern_js: Whether to enable modern JavaScript features
            cache_dir: Directory to use for caching JavaScript files
        """
        self.sandbox = sandbox
        self.timeout = timeout
        self.enable_modern_js = enable_modern_js
        
        # Create cache directory if not provided
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), 'wink_browser', 'js_cache')
        
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_dir = cache_dir
        
        # Check if dukpy is available
        self.dukpy_available = DUKPY_AVAILABLE
        
        # Result callback for asynchronous operations
        self.result_callback = None
        
        # Create a dedicated lock for js engine operations
        self.js_lock = threading.Lock()
        
        # Thread pool for handling JavaScript execution
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Create interpreter instances - one global and others per thread
        if DUKPY_AVAILABLE:
            self.global_interpreter = dukpy.JSInterpreter()
            
            # Set up basic browser-like environment
            self._setup_browser_env(self.global_interpreter)
        
        logger.debug(f"JavaScript engine initialized with dukpy (sandbox={sandbox}, timeout={timeout}ms)")
    
    def _setup_browser_env(self, interpreter):
        """Set up a basic browser-like environment in the interpreter."""
        # Basic window object
        window_setup = """
        var window = {
            setTimeout: function(callback, delay) { return 0; },
            setInterval: function(callback, delay) { return 0; },
            clearTimeout: function() {},
            clearInterval: function() {},
            location: {
                href: "about:blank",
                protocol: "about:",
                host: "",
                pathname: "blank"
            },
            console: {
                log: function(msg) { print(msg); return msg; },
                error: function(msg) { print("ERROR: " + msg); return msg; },
                warn: function(msg) { print("WARNING: " + msg); return msg; }
            }
        };
        
        // Make window properties available in global scope
        for (var key in window) {
            this[key] = window[key];
        }
        """
        
        # Basic document object
        document_setup = """
        var document = {
            getElementById: function(id) {
                return {
                    value: "",
                    innerHTML: "",
                    style: {},
                    addEventListener: function() {}
                };
            },
            getElementsByTagName: function() {
                return [];
            },
            getElementsByClassName: function() {
                return [];
            },
            querySelector: function() {
                return null;
            },
            querySelectorAll: function() {
                return [];
            },
            createElement: function() {
                return {
                    appendChild: function() {},
                    style: {}
                };
            },
            body: {
                appendChild: function() {},
                innerHTML: "",
                style: {}
            },
            head: {
                appendChild: function() {}
            },
            addEventListener: function() {}
        };
        """
        
        # Execute the setup scripts
        interpreter.evaljs(window_setup)
        interpreter.evaljs(document_setup)
    
    def execute_js(self, js_code: str, callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute JavaScript code using dukpy.
        
        Args:
            js_code: JavaScript code to execute
            callback: Callback function to call with the result
            
        Returns:
            The result of the JavaScript execution, or None if executed asynchronously
        """
        if not self.dukpy_available:
            logger.warning("JavaScript execution not available: dukpy not installed")
            result = {"error": "JavaScript execution not available"}
            if callback:
                callback(result)
            return result
        
        if callback:
            # Execute asynchronously
            self.result_callback = callback
            threading.Thread(target=self._execute_js_thread, args=(js_code,), daemon=True).start()
            return None
        else:
            # Execute synchronously
            return self._execute_js_sync(js_code)
    
    def _execute_js_thread(self, js_code: str) -> None:
        """Execute JavaScript code in a separate thread."""
        try:
            result = self._execute_js_sync(js_code)
        except Exception as e:
            logger.error(f"Error executing JavaScript: {e}")
            traceback.print_exc()
            result = {"error": str(e)}
        
        if self.result_callback:
            try:
                self.result_callback(result)
            except Exception as callback_error:
                logger.error(f"Error in JavaScript callback: {callback_error}")
    
    def _execute_js_sync(self, js_code: str) -> Dict[str, Any]:
        """Execute JavaScript code synchronously."""
        start_time = time.time()
        
        try:
            with self.js_lock:
                # Create thread-local interpreter
                interpreter = dukpy.JSInterpreter()
                self._setup_browser_env(interpreter)
                
                # Execute the JavaScript code
                result = interpreter.evaljs(js_code)
                
                execution_time = (time.time() - start_time) * 1000
                logger.debug(f"JavaScript executed in {execution_time:.2f}ms")
                
                return {"result": result}
        except Exception as e:
            logger.error(f"Error executing JavaScript code with dukpy: {e}")
            execution_time = (time.time() - start_time) * 1000
            logger.debug(f"JavaScript execution failed after {execution_time:.2f}ms")
            return {"error": str(e)}
    
    def execute_js_with_dom(self, 
                       js_code: str, 
                       html_content: str, 
                       callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute JavaScript code with a DOM environment.
        This is a simplified version for dukpy which doesn't have full DOM support.
        
        Args:
            js_code: JavaScript code to execute
            html_content: HTML content to create a DOM from
            callback: Callback function to call with the result
            
        Returns:
            The result of the JavaScript execution, or None if executed asynchronously
        """
        if not self.dukpy_available:
            logger.warning("JavaScript execution not available: dukpy not installed")
            result = {"error": "JavaScript execution not available"}
            if callback:
                callback(result)
            return result
        
        # We use a simple approach: create a document.innerHTML property with the HTML content
        dom_setup = f"""
        // Store HTML content
        document.innerHTML = {json.dumps(html_content)};
        
        // Simple DOM parsing support - just store content, no actual parsing
        document.body.innerHTML = document.innerHTML;
        """
        
        # Combine the DOM setup with the user's JavaScript code
        combined_js = dom_setup + "\n" + js_code
        
        if callback:
            # Execute asynchronously
            self.result_callback = callback
            threading.Thread(target=self._execute_js_with_dom_thread, 
                             args=(combined_js, html_content), 
                             daemon=True).start()
            return None
        else:
            # Execute synchronously
            return self._execute_js_with_dom_sync(combined_js, html_content)
    
    def _execute_js_with_dom_thread(self, js_code: str, html_content: str) -> None:
        """Execute JavaScript code with DOM in a separate thread."""
        try:
            result = self._execute_js_with_dom_sync(js_code, html_content)
        except Exception as e:
            logger.error(f"Error executing JavaScript with DOM: {e}")
            traceback.print_exc()
            result = {"error": str(e)}
        
        if self.result_callback:
            try:
                self.result_callback(result)
            except Exception as callback_error:
                logger.error(f"Error in JavaScript callback: {callback_error}")
    
    def _execute_js_with_dom_sync(self, js_code: str, html_content: str) -> Dict[str, Any]:
        """Execute JavaScript code with DOM synchronously."""
        # This implementation is simplified as dukpy doesn't provide a full DOM environment
        return self._execute_js_sync(js_code)
    
    def execute_event_handlers(self, 
                          event_type: str, 
                          target_selector: str, 
                          html_content: Optional[str] = None,
                          callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute event handlers for a specific event.
        This is a simplified version for dukpy without full DOM support.
        
        Args:
            event_type: Type of event (e.g., "click", "submit")
            target_selector: CSS selector for the target element
            html_content: HTML content to create a DOM from
            callback: Callback function to call with the result
            
        Returns:
            The result of the JavaScript execution, or None if executed asynchronously
        """
        if not self.dukpy_available:
            logger.warning("JavaScript execution not available: dukpy not installed")
            result = {"error": "JavaScript execution not available"}
            if callback:
                callback(result)
            return result
        
        # Create a simple event handler execution script
        event_script = f"""
        // Simple event simulation
        var event = {{
            type: "{event_type}",
            target: document.querySelector("{target_selector}") || {{
                value: "",
                checked: false,
                tagName: "DIV",
                getAttribute: function() {{ return ""; }},
                id: ""
            }},
            preventDefault: function() {{}},
            stopPropagation: function() {{}}
        }};
        
        // Log the event for debugging
        console.log("Simulating " + event.type + " event on " + "{target_selector}");
        
        // Return event info
        event;
        """
        
        if callback:
            # Execute asynchronously
            self.result_callback = callback
            threading.Thread(target=self._execute_event_handlers_thread, 
                             args=(event_type, target_selector, html_content), 
                             daemon=True).start()
            return None
        else:
            # Execute synchronously
            return self._execute_event_handlers_sync(event_type, target_selector, html_content)
    
    def _execute_event_handlers_thread(self, 
                                  event_type: str, 
                                  target_selector: str, 
                                  html_content: Optional[str]) -> None:
        """Execute event handlers in a separate thread."""
        try:
            result = self._execute_event_handlers_sync(event_type, target_selector, html_content)
        except Exception as e:
            logger.error(f"Error executing event handlers: {e}")
            traceback.print_exc()
            result = {"error": str(e)}
        
        if self.result_callback:
            try:
                self.result_callback(result)
            except Exception as callback_error:
                logger.error(f"Error in event handler callback: {callback_error}")
    
    def _execute_event_handlers_sync(self, 
                                event_type: str, 
                                target_selector: str, 
                                html_content: Optional[str]) -> Dict[str, Any]:
        """Execute event handlers synchronously."""
        event_script = f"""
        // Simple event simulation
        var event = {{
            type: "{event_type}",
            target: {{
                value: "",
                checked: false,
                tagName: "DIV",
                getAttribute: function() {{ return ""; }},
                id: ""
            }},
            preventDefault: function() {{}},
            stopPropagation: function() {{}}
        }};
        
        // Log the event
        "Simulating " + event.type + " event on " + "{target_selector}";
        """
        
        # Execute the event simulation
        return self._execute_js_sync(event_script)
    
    def close(self):
        """Clean up resources used by the JavaScript engine."""
        logger.debug("Closing JavaScript engine")
        
        # Close the global interpreter
        if hasattr(self, 'global_interpreter'):
            del self.global_interpreter
        
        # Shut down the executor
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        
        logger.debug("JavaScript engine closed") 