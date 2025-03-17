"""
JavaScript engine implementation with full support for modern JavaScript features.
This module is responsible for executing JavaScript code in the browser.
"""

import logging
import asyncio
import os
import json
import re
import threading
import tempfile
from typing import Dict, List, Optional, Any, Callable, Union, Set
import traceback
import subprocess
import shutil
import sys
from pathlib import Path
import time
import signal

# Check if pyppeteer is available
try:
    import pyppeteer
    from pyppeteer import launch
    from pyppeteer.errors import NetworkError, PageError, TimeoutError
    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False
    logging.warning("pyppeteer not available. JavaScript execution will be limited.")

logger = logging.getLogger(__name__)

# Set of modern JavaScript features supported
MODERN_JS_FEATURES = {
    # ES6+
    'arrow_functions', 'classes', 'const_let', 'destructuring', 'generators',
    'iterators', 'modules', 'promises', 'rest_spread', 'template_literals',
    'default_parameters', 'async_await',
    
    # ES2016+
    'exponentiation', 'array_includes',
    
    # ES2017+
    'async_functions', 'shared_memory', 'atomics', 'string_padding',
    'object_entries_values', 'trailing_commas',
    
    # ES2018+
    'async_iteration', 'promise_finally', 'regexp_features', 'rest_properties',
    'spread_properties',
    
    # ES2019+
    'optional_catch', 'array_flat', 'object_fromentries', 'string_trimstart',
    'symbol_description',
    
    # ES2020+
    'bigint', 'dynamic_import', 'nullish_coalescing', 'optional_chaining',
    'promise_allsettled',
    
    # ES2021+
    'logical_assignment', 'numeric_separators', 'promise_any', 'replace_all',
    
    # ES2022+
    'class_fields', 'class_static_blocks', 'top_level_await', 'error_cause',
    
    # ES2023+
    'array_findlast', 'hashbang_grammar', 'symbols_as_weakmap_keys'
}

class JSEngine:
    """JavaScript engine using Pyppeteer (headless Chrome) for full JavaScript support."""
    
    def __init__(self, 
                 sandbox: bool = True, 
                 timeout: int = 5000, 
                 enable_modern_js: bool = True,
                 cache_dir: Optional[str] = None):
        """
        Initialize the JavaScript engine.
        
        Args:
            sandbox: Whether to run JavaScript in a sandbox
            timeout: Default timeout for JavaScript execution (in milliseconds)
            enable_modern_js: Whether to enable modern JavaScript features
            cache_dir: Directory to use for caching browser and JavaScript files
        """
        self.sandbox = sandbox
        self.timeout = timeout
        self.enable_modern_js = enable_modern_js
        
        # Create cache directory if not provided
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), 'wink_browser', 'js_cache')
        
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_dir = cache_dir
        
        # Browser instance and page
        self.browser = None
        self.page = None
        self.browser_ready = False
        
        # Function to call when results are available
        self.result_callback = None
        
        # Flag for event loop issues
        self.event_loop_issues = False
        
        # Check if pyppeteer is available
        self.pyppeteer_available = PYPPETEER_AVAILABLE
        
        # Start browser in a separate thread to avoid blocking main thread
        if self.pyppeteer_available:
            self.browser_thread = threading.Thread(target=self._start_browser, daemon=True)
            self.browser_thread.start()
        else:
            logger.warning("JavaScript execution disabled (pyppeteer not available)")
        
        logger.debug(f"JavaScript engine initialized (sandbox={sandbox}, timeout={timeout}ms)")
    
    async def _launch_browser(self):
        """Launch the browser asynchronously."""
        try:
            # Configure browser launch options
            launch_options = {
                'headless': True,
                'args': [
                    '--no-sandbox' if not self.sandbox else '',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--disable-infobars',
                    '--no-zygote',
                    '--disable-web-security',  # Allow cross-origin requests
                    '--allow-file-access-from-files',  # Allow loading local files
                    '--disable-features=site-per-process',  # Disable site isolation
                    '--disable-extensions',
                    '--mute-audio',
                    '--hide-scrollbars',
                    '--disable-breakpad',
                    '--disable-translate',
                    '--disable-hangout-services',
                    '--disable-notifications',
                    f'--user-data-dir={self.cache_dir}'
                ],
                'userDataDir': self.cache_dir,
                'ignoreHTTPSErrors': True,
                'handleSIGINT': False,  # Let Python handle interrupts
                'handleSIGTERM': False,  # Let Python handle termination
                'handleSIGHUP': False   # Let Python handle HUP signals
            }
            
            # Launch browser
            self.browser = await launch(**launch_options)
            
            # Create a new page
            self.page = await self.browser.newPage()
            
            # Configure page
            await self.page.setJavaScriptEnabled(True)
            await self.page.setViewport({'width': 1280, 'height': 800})
            
            # Set content to a basic HTML page with modern JS polyfills if needed
            if self.enable_modern_js:
                init_content = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <script>
                        // Basic polyfills for older browsers
                        if (!Object.entries) {
                            Object.entries = function(obj) {
                                return Object.keys(obj).map(key => [key, obj[key]]);
                            };
                        }
                        
                        // Create a global context for JavaScript execution
                        window.executeJS = function(code) {
                            try {
                                return { result: eval(code), error: null };
                            } catch (error) {
                                return { result: null, error: error.toString() };
                            }
                        };
                    </script>
                </head>
                <body>
                    <div id="content"></div>
                </body>
                </html>
                """
            else:
                init_content = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <script>
                        // Create a global context for JavaScript execution
                        window.executeJS = function(code) {
                            try {
                                return { result: eval(code), error: null };
                            } catch (error) {
                                return { result: null, error: error.toString() };
                            }
                        };
                    </script>
                </head>
                <body>
                    <div id="content"></div>
                </body>
                </html>
                """
            
            await self.page.setContent(init_content)
            
            # Add event listeners
            await self.page.exposeFunction('jsCallback', self._handle_js_callback)
            
            self.browser_ready = True
            logger.debug("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            self.browser_ready = False
    
    def _start_browser(self):
        """Start the browser in a background thread."""
        if not self.pyppeteer_available:
            return
        
        try:
            # Create an event loop for the thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Deal with signal handling to avoid "signal only works in main thread" error
            # This is a workaround for pyppeteer's signal handling in background threads
            
            # Avoid trying to set signal handlers in background threads
            # Just launch the browser without attempting to set signal handlers
            
            # Launch the browser
            try:
                loop.run_until_complete(self._launch_browser())
            except Exception as e:
                logger.error(f"Error launching browser: {e}")
                self.browser_ready = False
            
            # Keep the loop running
            try:
                loop.run_forever()
            except Exception as e:
                logger.error(f"Error in browser thread event loop: {e}")
        except Exception as e:
            logger.error(f"Error in browser thread: {e}")
            self.browser_ready = False
    
    async def _execute_js_async(self, js_code: str) -> Dict[str, Any]:
        """
        Execute JavaScript code asynchronously.
        
        Args:
            js_code: JavaScript code to execute
            
        Returns:
            Dict[str, Any]: Dictionary with result or error
        """
        if not self.pyppeteer_available or not self.browser_ready:
            logger.warning("JavaScript execution not available")
            return {"error": "JavaScript execution not available", "result": None}
        
        try:
            # Add a timeout to prevent hanging
            result = await asyncio.wait_for(
                self.page.evaluate(f'executeJS(`{js_code.replace("`", "\\`")}`)'),
                timeout=self.timeout / 1000  # Convert from milliseconds to seconds
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"JavaScript execution timed out after {self.timeout}ms")
            return {"error": f"JavaScript execution timed out after {self.timeout}ms", "result": None}
        except Exception as e:
            logger.error(f"Error executing JavaScript: {e}")
            return {"error": str(e), "result": None}
    
    def execute_js(self, js_code: str, callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute JavaScript code.
        
        Args:
            js_code: JavaScript code to execute
            callback: Optional callback function to call with the result
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary with result or error if no callback is provided
        """
        # If we've had event loop issues, disable JavaScript execution
        if self.event_loop_issues:
            error_result = {"error": "JavaScript execution disabled due to event loop issues", "result": None}
            if callback:
                callback(error_result)
                return None
            return error_result
            
        if not self.pyppeteer_available:
            error_result = {"error": "JavaScript execution not available (pyppeteer not installed)", "result": None}
            if callback:
                callback(error_result)
                return None
            return error_result
        
        if not self.browser_ready:
            # Wait for the browser to be ready (up to 5 seconds)
            wait_start = time.time()
            while not self.browser_ready and time.time() - wait_start < 5:
                time.sleep(0.1)
            
            if not self.browser_ready:
                error_result = {"error": "Browser not ready", "result": None}
                if callback:
                    callback(error_result)
                    return None
                return error_result
        
        # If a callback is provided, execute asynchronously
        if callback:
            self.result_callback = callback
            # Execute in a new thread to avoid blocking
            thread = threading.Thread(target=self._execute_js_thread, args=(js_code,), daemon=True)
            thread.start()
            return None
        
        # Otherwise, execute synchronously and return the result
        return self._execute_js_sync(js_code)
    
    def _execute_js_thread(self, js_code: str) -> None:
        """
        Execute JavaScript code in a separate thread.
        
        Args:
            js_code: JavaScript code to execute
        """
        result = self._execute_js_sync(js_code)
        if self.result_callback:
            self.result_callback(result)
    
    def _execute_js_sync(self, js_code: str) -> Dict[str, Any]:
        """
        Execute JavaScript code synchronously.
        
        Args:
            js_code: JavaScript code to execute
            
        Returns:
            Dict[str, Any]: Dictionary with result or error
        """
        if not self.pyppeteer_available or not self.browser_ready:
            return {"error": "JavaScript execution not available", "result": None}
        
        try:
            # Create a new event loop for this thread if it doesn't exist
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If the current loop is running, create a new one
                    loop = asyncio.new_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
            
            # Set the event loop for this thread
            asyncio.set_event_loop(loop)
            
            # Define the async function that will be executed
            async def execute_js_async_wrapper():
                try:
                    return await self._execute_js_async(js_code)
                except Exception as e:
                    error_message = f"Error in execute_js_async_wrapper: {e}"
                    logger.error(error_message)
                    return {"error": error_message, "result": None}
            
            # Execute the async function in the loop
            result = loop.run_until_complete(execute_js_async_wrapper())
            return result
        except RuntimeError as e:
            if "attached to a different loop" in str(e):
                # Mark that we're having event loop issues - disable JS after this
                self.event_loop_issues = True
                error_message = f"Event loop error executing JavaScript: {e}. JavaScript will be disabled."
                logger.error(error_message)
                return {"error": error_message, "result": None}
            else:
                error_message = f"Error executing JavaScript: {e}"
                logger.error(error_message)
                return {"error": error_message, "result": None}
        except Exception as e:
            error_message = f"Error executing JavaScript: {e}"
            logger.error(error_message)
            return {"error": error_message, "result": None}
    
    async def _handle_js_callback(self, data: str) -> None:
        """
        Handle callbacks from JavaScript.
        
        Args:
            data: JSON string with callback data
        """
        try:
            # Parse the JSON data
            callback_data = json.loads(data)
            
            # Call the callback if set
            if self.result_callback:
                self.result_callback(callback_data)
        except Exception as e:
            logger.error(f"Error handling JavaScript callback: {e}")
    
    def execute_js_with_dom(self, 
                           js_code: str, 
                           html_content: str, 
                           callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute JavaScript code with a specific HTML DOM.
        
        Args:
            js_code: JavaScript code to execute
            html_content: HTML content to set as the DOM
            callback: Optional callback function to call with the result
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary with result or error if no callback is provided
        """
        # If we've had event loop issues, disable JavaScript execution
        if self.event_loop_issues:
            error_result = {"error": "JavaScript execution disabled due to event loop issues", "result": None}
            if callback:
                callback(error_result)
                return None
            return error_result
            
        if not self.pyppeteer_available:
            error_result = {"error": "JavaScript execution not available (pyppeteer not installed)", "result": None}
            if callback:
                callback(error_result)
                return None
            return error_result
        
        if not self.browser_ready:
            # Wait for the browser to be ready (up to 5 seconds)
            wait_start = time.time()
            while not self.browser_ready and time.time() - wait_start < 5:
                time.sleep(0.1)
            
            if not self.browser_ready:
                error_result = {"error": "Browser not ready", "result": None}
                if callback:
                    callback(error_result)
                    return None
                return error_result
        
        # If a callback is provided, execute asynchronously
        if callback:
            self.result_callback = callback
            # Execute in a new thread to avoid blocking
            thread = threading.Thread(target=self._execute_js_with_dom_thread, 
                                      args=(js_code, html_content), 
                                      daemon=True)
            thread.start()
            return None
        
        # Otherwise, execute synchronously and return the result
        return self._execute_js_with_dom_sync(js_code, html_content)
    
    def _execute_js_with_dom_thread(self, js_code: str, html_content: str) -> None:
        """
        Execute JavaScript code with a specific HTML DOM in a separate thread.
        
        Args:
            js_code: JavaScript code to execute
            html_content: HTML content to set as the DOM
        """
        result = self._execute_js_with_dom_sync(js_code, html_content)
        if self.result_callback:
            self.result_callback(result)
    
    def _execute_js_with_dom_sync(self, js_code: str, html_content: str) -> Dict[str, Any]:
        """
        Execute JavaScript code with a specific HTML DOM synchronously.
        
        Args:
            js_code: JavaScript code to execute
            html_content: HTML content to set as the DOM
            
        Returns:
            Dict[str, Any]: Dictionary with result or error
        """
        if not self.pyppeteer_available or not self.browser_ready:
            return {"error": "JavaScript execution not available", "result": None}
        
        try:
            # Create a new event loop for this thread if it doesn't exist
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If the current loop is running, create a new one
                    loop = asyncio.new_event_loop()
                    
            except RuntimeError:
                loop = asyncio.new_event_loop()
            
            # Set the event loop for this thread
            asyncio.set_event_loop(loop)
                
            # Define the async function that will be executed
            async def execute_js_with_dom_async():
                try:
                    # Set the HTML content
                    await self.page.setContent(html_content)
                    
                    # Execute the JavaScript code
                    return await self._execute_js_async(js_code)
                except Exception as e:
                    error_message = f"Error in execute_js_with_dom_async: {e}"
                    logger.error(error_message)
                    return {"error": error_message, "result": None}
            
            # Execute the async function in the loop
            result = loop.run_until_complete(execute_js_with_dom_async())
            return result
        except RuntimeError as e:
            if "attached to a different loop" in str(e):
                # Mark that we're having event loop issues - disable JS after this
                self.event_loop_issues = True
                error_message = f"Event loop error executing JavaScript with DOM: {e}. JavaScript will be disabled."
                logger.error(error_message)
                return {"error": error_message, "result": None}
            else:
                error_message = f"Error executing JavaScript with DOM: {e}"
                logger.error(error_message)
                return {"error": error_message, "result": None}
        except Exception as e:
            error_message = f"Error executing JavaScript with DOM: {e}"
            logger.error(error_message)
            return {"error": error_message, "result": None}
    
    def execute_event_handlers(self, 
                              event_type: str, 
                              target_selector: str, 
                              html_content: Optional[str] = None,
                              callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute event handlers for a specific event type on a target element.
        
        Args:
            event_type: Type of event to trigger (e.g., 'click', 'submit')
            target_selector: CSS selector for the target element
            html_content: Optional HTML content to set as the DOM
            callback: Optional callback function to call with the result
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary with result or error if no callback is provided
        """
        # If we've had event loop issues, disable JavaScript execution
        if self.event_loop_issues:
            error_result = {"error": "JavaScript execution disabled due to event loop issues", "result": None}
            if callback:
                callback(error_result)
                return None
            return error_result
            
        if not self.pyppeteer_available:
            error_result = {"error": "JavaScript execution not available (pyppeteer not installed)", "result": None}
            if callback:
                callback(error_result)
                return None
            return error_result
        
        if not self.browser_ready:
            # Wait for the browser to be ready (up to 5 seconds)
            wait_start = time.time()
            while not self.browser_ready and time.time() - wait_start < 5:
                time.sleep(0.1)
            
            if not self.browser_ready:
                error_result = {"error": "Browser not ready", "result": None}
                if callback:
                    callback(error_result)
                    return None
                return error_result
        
        # If a callback is provided, execute asynchronously
        if callback:
            self.result_callback = callback
            # Execute in a new thread to avoid blocking
            thread = threading.Thread(target=self._execute_event_handlers_thread, 
                                      args=(event_type, target_selector, html_content), 
                                      daemon=True)
            thread.start()
            return None
        
        # Otherwise, execute synchronously and return the result
        return self._execute_event_handlers_sync(event_type, target_selector, html_content)
    
    def _execute_event_handlers_thread(self, 
                                      event_type: str, 
                                      target_selector: str, 
                                      html_content: Optional[str]) -> None:
        """
        Execute event handlers in a separate thread.
        
        Args:
            event_type: Type of event to trigger
            target_selector: CSS selector for the target element
            html_content: Optional HTML content to set as the DOM
        """
        result = self._execute_event_handlers_sync(event_type, target_selector, html_content)
        if self.result_callback:
            self.result_callback(result)
    
    def _execute_event_handlers_sync(self, 
                                    event_type: str, 
                                    target_selector: str, 
                                    html_content: Optional[str]) -> Dict[str, Any]:
        """
        Execute event handlers synchronously.
        
        Args:
            event_type: Type of event to trigger
            target_selector: CSS selector for the target element
            html_content: Optional HTML content to set as the DOM
            
        Returns:
            Dict[str, Any]: Dictionary with result or error
        """
        if not self.pyppeteer_available or not self.browser_ready:
            return {"error": "JavaScript execution not available", "result": None}
        
        try:
            # Create a new event loop for this thread if it doesn't exist
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If the current loop is running, create a new one
                    loop = asyncio.new_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
            
            # Set the event loop for this thread
            asyncio.set_event_loop(loop)
            
            # Define the async function that will be executed
            async def execute_event_handlers_async():
                try:
                    # Set the HTML content if provided
                    if html_content:
                        await self.page.setContent(html_content)
                    
                    # Execute the event
                    await self._trigger_event_async(event_type, target_selector)
                    
                    # Get the updated DOM
                    updated_dom = await self.page.content()
                    
                    return {"result": updated_dom, "error": None}
                except Exception as e:
                    error_message = f"Error in execute_event_handlers_async: {e}"
                    logger.error(error_message)
                    return {"error": error_message, "result": None}
            
            # Execute the async function in the loop
            result = loop.run_until_complete(execute_event_handlers_async())
            return result
        except RuntimeError as e:
            if "attached to a different loop" in str(e):
                # Mark that we're having event loop issues - disable JS after this
                self.event_loop_issues = True
                error_message = f"Event loop error executing event handlers: {e}. JavaScript will be disabled."
                logger.error(error_message)
                return {"error": error_message, "result": None}
            else:
                error_message = f"Error executing event handlers: {e}"
                logger.error(error_message)
                return {"error": error_message, "result": None}
        except Exception as e:
            error_message = f"Error executing event handlers: {e}"
            logger.error(error_message)
            return {"error": error_message, "result": None}
    
    async def _trigger_event_async(self, event_type: str, target_selector: str) -> None:
        """
        Trigger an event on a target element asynchronously.
        
        Args:
            event_type: Type of event to trigger
            target_selector: CSS selector for the target element
        """
        try:
            # Wait for the element to be available
            await self.page.waitForSelector(target_selector, {'timeout': self.timeout})
            
            # Map event type to appropriate page method
            if event_type.lower() == 'click':
                await self.page.click(target_selector)
            elif event_type.lower() == 'focus':
                await self.page.focus(target_selector)
            elif event_type.lower() == 'hover':
                await self.page.hover(target_selector)
            elif event_type.lower() == 'submit' and await self.page.querySelector(target_selector + ' form'):
                # If the target contains a form, submit it
                await self.page.evaluate(f'document.querySelector("{target_selector} form").submit()')
            else:
                # For other events, use evaluate to dispatch the event
                await self.page.evaluate(f'''
                    (() => {{
                        const element = document.querySelector("{target_selector}");
                        if (element) {{
                            const event = new Event('{event_type}', {{
                                bubbles: true,
                                cancelable: true
                            }});
                            element.dispatchEvent(event);
                        }}
                    }})()
                ''')
        except Exception as e:
            logger.error(f"Error triggering event: {e}")
            raise
    
    def close(self):
        """Close the browser and clean up resources."""
        if self.pyppeteer_available and self.browser:
            try:
                # Schedule browser closure without using an event loop
                # to avoid "This event loop is already running" error
                async def close_browser_async():
                    try:
                        if self.browser:
                            await self.browser.close()
                            logger.debug("Browser closed successfully")
                    except Exception as e:
                        logger.error(f"Error closing browser: {e}")
                
                # Create a separate thread just to close the browser
                def close_browser_thread():
                    try:
                        # Create a new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        # Run the close coroutine
                        loop.run_until_complete(close_browser_async())
                        loop.close()
                    except Exception as e:
                        logger.error(f"Error in browser close thread: {e}")
                
                # Start the thread and don't wait for it (daemon)
                thread = threading.Thread(target=close_browser_thread, daemon=True)
                thread.start()
                
                # Give the thread a moment to do its work
                time.sleep(0.5)
                
                logger.debug("Browser close scheduled")
            except Exception as e:
                logger.error(f"Error scheduling browser close: {e}")
        
        # Set flags to indicate the browser is closed
        self.browser = None
        self.page = None
        self.browser_ready = False 