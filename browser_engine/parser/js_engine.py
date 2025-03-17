"""
JavaScript engine implementation.
This module is responsible for executing JavaScript code.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable
import re

# Pyppeteer is used as a wrapper around headless Chrome
import asyncio
import pyppeteer

logger = logging.getLogger(__name__)

class JSEngine:
    """JavaScript engine implementation using Pyppeteer (headless Chrome)."""
    
    def __init__(self, enabled: bool = True):
        """
        Initialize the JavaScript engine.
        
        Args:
            enabled: Whether JavaScript execution is enabled
        """
        self.enabled = enabled
        self.browser = None
        self.page = None
        self.context = {}  # Store JavaScript context (variables, functions, etc.)
        self.timers = {}  # Store timers (setTimeout, setInterval)
        self.timer_id_counter = 0
        self._lock = threading.Lock()  # Lock for thread safety
        
        # Initialize the browser if enabled
        if self.enabled:
            self._initialize_browser()
            
        logger.debug(f"JavaScript engine initialized (enabled: {enabled})")
    
    def _initialize_browser(self) -> None:
        """Initialize the headless browser."""
        # We run this on a background thread to not block the main thread
        threading.Thread(target=self._initialize_browser_thread, daemon=True).start()
    
    def _initialize_browser_thread(self) -> None:
        """Background thread for initializing the browser."""
        try:
            # Create a new asyncio event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Launch the browser
            self.browser = loop.run_until_complete(self._launch_browser())
            
            # Create a page
            self.page = loop.run_until_complete(self.browser.newPage())
            
            # Set up console log forwarding
            loop.run_until_complete(self._setup_console_forwarding())
            
            logger.info("Browser initialized successfully")
            
            # Keep the event loop running
            loop.run_forever()
        except Exception as e:
            logger.error(f"Error initializing browser: {e}")
            self.enabled = False
    
    async def _launch_browser(self) -> pyppeteer.browser.Browser:
        """
        Launch the headless browser.
        
        Returns:
            pyppeteer.browser.Browser: Browser instance
        """
        return await pyppeteer.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--disable-desktop-notifications',
            ]
        )
    
    async def _setup_console_forwarding(self) -> None:
        """Set up console log forwarding from browser to Python."""
        if self.page:
            await self.page.evaluate('''() => {
                console.originalLog = console.log;
                console.originalWarn = console.warn;
                console.originalError = console.error;
                console.originalInfo = console.info;
                
                console.log = (...args) => {
                    window.pythonConsoleLog('log', ...args);
                    console.originalLog(...args);
                };
                
                console.warn = (...args) => {
                    window.pythonConsoleLog('warn', ...args);
                    console.originalWarn(...args);
                };
                
                console.error = (...args) => {
                    window.pythonConsoleLog('error', ...args);
                    console.originalError(...args);
                };
                
                console.info = (...args) => {
                    window.pythonConsoleLog('info', ...args);
                    console.originalInfo(...args);
                };
            }''')
            
            # Expose a function to receive console logs
            await self.page.exposeFunction('pythonConsoleLog', self._handle_console_log)
    
    def _handle_console_log(self, log_type: str, *args) -> None:
        """
        Handle console logs from the browser.
        
        Args:
            log_type: Type of log (log, warn, error, info)
            *args: Log arguments
        """
        message = " ".join(str(arg) for arg in args)
        
        if log_type == 'error':
            logger.error(f"JavaScript console error: {message}")
        elif log_type == 'warn':
            logger.warning(f"JavaScript console warning: {message}")
        else:
            logger.info(f"JavaScript console {log_type}: {message}")
    
    def execute(self, js_code: str, 
                timeout: int = 5000, 
                context: Dict[str, Any] = None) -> Any:
        """
        Execute JavaScript code.
        
        Args:
            js_code: JavaScript code to execute
            timeout: Timeout in milliseconds
            context: Optional context dictionary to inject into JS
            
        Returns:
            Any: Result of the JavaScript execution
        """
        if not self.enabled:
            logger.warning("JavaScript execution is disabled")
            return None
        
        if not self.page:
            logger.warning("Browser not initialized, can't execute JavaScript")
            return None
        
        # Run in a background thread to not block the main thread
        with self._lock:
            result_thread = threading.Thread(
                target=self._execute_thread, 
                args=(js_code, timeout, context), 
                daemon=True
            )
            result_thread.start()
            result_thread.join(timeout=timeout/1000 + 1)  # Convert ms to seconds and add 1s buffer
            
            if result_thread.is_alive():
                logger.warning(f"JavaScript execution timed out after {timeout}ms")
                # In a real implementation, we would terminate the execution
                return None
            
            # Return the result from the context
            return self.context.get('_last_result', None)
    
    def _execute_thread(self, js_code: str, timeout: int, context: Dict[str, Any]) -> None:
        """
        Background thread for executing JavaScript.
        
        Args:
            js_code: JavaScript code to execute
            timeout: Timeout in milliseconds
            context: Optional context dictionary to inject into JS
        """
        try:
            # Create a new asyncio event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Execute JavaScript and get the result
            result = loop.run_until_complete(self._execute_async(js_code, timeout, context))
            
            # Store the result in the context
            self.context['_last_result'] = result
            
            loop.close()
        except Exception as e:
            logger.error(f"Error executing JavaScript: {e}")
            self.context['_last_result'] = None
    
    async def _execute_async(self, 
                             js_code: str, 
                             timeout: int, 
                             context: Dict[str, Any]) -> Any:
        """
        Execute JavaScript code asynchronously.
        
        Args:
            js_code: JavaScript code to execute
            timeout: Timeout in milliseconds
            context: Optional context dictionary to inject into JS
            
        Returns:
            Any: Result of the JavaScript execution
        """
        if not self.page:
            return None
        
        try:
            # Inject context if provided
            if context:
                for key, value in context.items():
                    await self.page.evaluate(f'window.{key} = {_js_value(value)};')
            
            # Execute the code with timeout
            result = await asyncio.wait_for(
                self.page.evaluate(js_code),
                timeout=timeout/1000  # Convert ms to seconds
            )
            
            return result
        except asyncio.TimeoutError:
            logger.warning(f"JavaScript execution timed out after {timeout}ms")
            return None
        except Exception as e:
            logger.error(f"Error executing JavaScript: {e}")
            return None
    
    def set_dom(self, html_content: str) -> bool:
        """
        Set the HTML content for the JavaScript context.
        
        Args:
            html_content: HTML content
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled or not self.page:
            return False
        
        try:
            # Run in a background thread to not block the main thread
            threading.Thread(
                target=self._set_dom_thread,
                args=(html_content,),
                daemon=True
            ).start()
            return True
        except Exception as e:
            logger.error(f"Error setting DOM: {e}")
            return False
    
    def _set_dom_thread(self, html_content: str) -> None:
        """
        Background thread for setting the DOM.
        
        Args:
            html_content: HTML content
        """
        try:
            # Create a new asyncio event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Set the HTML content
            loop.run_until_complete(self._set_dom_async(html_content))
            
            loop.close()
        except Exception as e:
            logger.error(f"Error setting DOM: {e}")
    
    async def _set_dom_async(self, html_content: str) -> None:
        """
        Set the HTML content asynchronously.
        
        Args:
            html_content: HTML content
        """
        if not self.page:
            return
        
        try:
            # Set the HTML content
            await self.page.setContent(html_content)
            
            # Run onload handlers
            await self.page.evaluate('''() => {
                if (window.onload) {
                    window.onload();
                }
            }''')
        except Exception as e:
            logger.error(f"Error setting DOM: {e}")
    
    def add_event_listener(self, 
                           selector: str, 
                           event_type: str, 
                           callback: Callable) -> bool:
        """
        Add a JavaScript event listener.
        
        Args:
            selector: CSS selector for the element
            event_type: Event type (click, input, etc.)
            callback: Python callback function
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled or not self.page:
            return False
        
        try:
            # Use a unique ID for this callback
            callback_id = f"callback_{id(callback)}"
            
            # Store the callback in the context
            self.context[callback_id] = callback
            
            # Run in a background thread to not block the main thread
            threading.Thread(
                target=self._add_event_listener_thread,
                args=(selector, event_type, callback_id),
                daemon=True
            ).start()
            
            return True
        except Exception as e:
            logger.error(f"Error adding event listener: {e}")
            return False
    
    def _add_event_listener_thread(self, 
                                  selector: str, 
                                  event_type: str, 
                                  callback_id: str) -> None:
        """
        Background thread for adding an event listener.
        
        Args:
            selector: CSS selector for the element
            event_type: Event type (click, input, etc.)
            callback_id: Callback ID in the context
        """
        try:
            # Create a new asyncio event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Add the event listener
            loop.run_until_complete(self._add_event_listener_async(selector, event_type, callback_id))
            
            loop.close()
        except Exception as e:
            logger.error(f"Error adding event listener: {e}")
    
    async def _add_event_listener_async(self, 
                                       selector: str, 
                                       event_type: str, 
                                       callback_id: str) -> None:
        """
        Add a JavaScript event listener asynchronously.
        
        Args:
            selector: CSS selector for the element
            event_type: Event type (click, input, etc.)
            callback_id: Callback ID in the context
        """
        if not self.page:
            return
        
        try:
            # Expose the callback function to JavaScript
            await self.page.exposeFunction(f"python_{callback_id}", self.context[callback_id])
            
            # Add the event listener
            await self.page.evaluate(f'''
                (() => {{
                    const elements = document.querySelectorAll('{selector}');
                    for (const element of elements) {{
                        element.addEventListener('{event_type}', (event) => {{
                            window.python_{callback_id}({{
                                type: event.type,
                                target: {{
                                    id: event.target.id,
                                    className: event.target.className,
                                    value: event.target.value
                                }}
                            }});
                        }});
                    }}
                }})();
            ''')
        except Exception as e:
            logger.error(f"Error adding event listener: {e}")
    
    def set_timeout(self, callback: Callable, timeout: int) -> int:
        """
        Set a timeout to call a function after a specified delay.
        
        Args:
            callback: Function to call
            timeout: Timeout in milliseconds
            
        Returns:
            int: Timer ID
        """
        if not self.enabled:
            return -1
        
        with self._lock:
            # Generate a unique timer ID
            timer_id = self.timer_id_counter
            self.timer_id_counter += 1
            
            # Create and start the timer
            timer = threading.Timer(timeout/1000, self._timer_callback, args=(callback, timer_id))
            timer.daemon = True
            timer.start()
            
            # Store the timer
            self.timers[timer_id] = timer
            
            return timer_id
    
    def clear_timeout(self, timer_id: int) -> bool:
        """
        Clear a timeout.
        
        Args:
            timer_id: Timer ID returned by set_timeout
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        with self._lock:
            if timer_id in self.timers:
                # Cancel the timer
                self.timers[timer_id].cancel()
                # Remove from the timers dictionary
                del self.timers[timer_id]
                return True
            
            return False
    
    def set_interval(self, callback: Callable, interval: int) -> int:
        """
        Set an interval to call a function repeatedly.
        
        Args:
            callback: Function to call
            interval: Interval in milliseconds
            
        Returns:
            int: Timer ID
        """
        if not self.enabled:
            return -1
        
        with self._lock:
            # Generate a unique timer ID
            timer_id = self.timer_id_counter
            self.timer_id_counter += 1
            
            # Create the repeating timer function
            def interval_callback():
                try:
                    callback()
                    
                    # Schedule the next call if the timer still exists
                    if timer_id in self.timers:
                        self.timers[timer_id] = threading.Timer(interval/1000, interval_callback)
                        self.timers[timer_id].daemon = True
                        self.timers[timer_id].start()
                except Exception as e:
                    logger.error(f"Error in interval callback: {e}")
            
            # Create and start the timer
            timer = threading.Timer(interval/1000, interval_callback)
            timer.daemon = True
            timer.start()
            
            # Store the timer
            self.timers[timer_id] = timer
            
            return timer_id
    
    def clear_interval(self, timer_id: int) -> bool:
        """
        Clear an interval.
        
        Args:
            timer_id: Timer ID returned by set_interval
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Same implementation as clear_timeout
        return self.clear_timeout(timer_id)
    
    def _timer_callback(self, callback: Callable, timer_id: int) -> None:
        """
        Callback for timeouts.
        
        Args:
            callback: Function to call
            timer_id: Timer ID
        """
        try:
            # Call the callback function
            callback()
            
            # Remove the timer from the timers dictionary
            with self._lock:
                if timer_id in self.timers:
                    del self.timers[timer_id]
        except Exception as e:
            logger.error(f"Error in timer callback: {e}")
    
    def clean_up(self) -> None:
        """Clean up resources used by the JavaScript engine."""
        if not self.enabled:
            return
        
        try:
            # Cancel all timers
            with self._lock:
                for timer in self.timers.values():
                    timer.cancel()
                self.timers.clear()
            
            # Close the browser in a background thread
            threading.Thread(target=self._clean_up_thread, daemon=True).start()
            
            logger.debug("JavaScript engine clean up initiated")
        except Exception as e:
            logger.error(f"Error cleaning up JavaScript engine: {e}")
    
    def _clean_up_thread(self) -> None:
        """Background thread for cleaning up resources."""
        try:
            # Create a new asyncio event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Close the browser
            if self.browser:
                loop.run_until_complete(self.browser.close())
                self.browser = None
                self.page = None
            
            loop.close()
            
            logger.debug("JavaScript engine clean up completed")
        except Exception as e:
            logger.error(f"Error cleaning up JavaScript engine: {e}")


def _js_value(value: Any) -> str:
    """
    Convert a Python value to a JavaScript literal.
    
    Args:
        value: Python value
        
    Returns:
        str: JavaScript literal representation
    """
    if value is None:
        return 'null'
    elif isinstance(value, bool):
        return 'true' if value else 'false'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Escape quotes and newlines
        escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'
    elif isinstance(value, (list, tuple)):
        items = [_js_value(item) for item in value]
        return f"[{', '.join(items)}]"
    elif isinstance(value, dict):
        items = [f"{_js_value(k)}: {_js_value(v)}" for k, v in value.items()]
        return f"{{{', '.join(items)}}}"
    else:
        # Convert to string for unsupported types
        return f'"{str(value)}"' 