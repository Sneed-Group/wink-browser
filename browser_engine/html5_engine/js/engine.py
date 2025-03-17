"""
JavaScript Engine implementation.
This module provides JavaScript execution capabilities for the browser engine.
"""

import logging
import re
import threading
import json
import time
from typing import Dict, Any, List, Optional, Callable, Union

import dukpy

logger = logging.getLogger(__name__)

class JSEngine:
    """
    JavaScript engine using dukpy for script execution.
    
    This class provides a JavaScript execution environment that can interact
    with the DOM and browser environment.
    """
    
    def __init__(self, window=None):
        """
        Initialize the JavaScript engine.
        
        Args:
            window: Reference to the window/global object
        """
        self.window = window
        
        # Initialize dukpy interpreter
        self.interpreter = dukpy.JSInterpreter()
        
        # Setup standard objects and variables
        self._setup_global_objects()
        
        # JS console implementation
        self.console_output = []
        
        # Event queue
        self.event_queue = []
        
        # Execution state
        self.is_executing = False
        self.is_initialized = False
        
        # Create a separate thread for background evaluation
        self.eval_thread = None
        
        logger.info("JavaScript engine initialized")
    
    def _setup_global_objects(self) -> None:
        """Set up standard global objects in the JS environment."""
        # Define the console object
        console_js = """
        var console = {
            log: function() {
                var args = Array.prototype.slice.call(arguments);
                _console_log(JSON.stringify(args));
            },
            error: function() {
                var args = Array.prototype.slice.call(arguments);
                _console_error(JSON.stringify(args));
            },
            warn: function() {
                var args = Array.prototype.slice.call(arguments);
                _console_warn(JSON.stringify(args));
            },
            info: function() {
                var args = Array.prototype.slice.call(arguments);
                _console_info(JSON.stringify(args));
            }
        };
        """
        
        # Define basic timer functions
        timers_js = """
        var _timers = {};
        var _timerIdCounter = 1;
        
        function setTimeout(callback, delay) {
            var timerId = _timerIdCounter++;
            _timers[timerId] = {
                callback: callback,
                type: 'timeout',
                delay: delay,
                createdAt: Date.now()
            };
            _scheduleTimer(timerId, delay);
            return timerId;
        }
        
        function clearTimeout(timerId) {
            if (_timers[timerId]) {
                delete _timers[timerId];
                _clearTimer(timerId);
            }
        }
        
        function setInterval(callback, delay) {
            var timerId = _timerIdCounter++;
            _timers[timerId] = {
                callback: callback,
                type: 'interval',
                delay: delay,
                createdAt: Date.now()
            };
            _scheduleTimer(timerId, delay);
            return timerId;
        }
        
        function clearInterval(timerId) {
            if (_timers[timerId]) {
                delete _timers[timerId];
                _clearTimer(timerId);
            }
        }
        """
        
        # Define JSON methods
        json_js = """
        if (!window.JSON) {
            window.JSON = {
                parse: function(text) {
                    return eval('(' + text + ')');
                },
                stringify: function(obj) {
                    // Simple implementation
                    if (obj === null) return 'null';
                    if (obj === undefined) return undefined;
                    if (typeof obj === 'string') return '"' + obj.replace(/"/g, '\\"') + '"';
                    if (typeof obj === 'number') return obj.toString();
                    if (typeof obj === 'boolean') return obj.toString();
                    if (Array.isArray(obj)) {
                        return '[' + obj.map(function(item) { 
                            return JSON.stringify(item);
                        }).join(',') + ']';
                    }
                    if (typeof obj === 'object') {
                        var pairs = [];
                        for (var key in obj) {
                            if (obj.hasOwnProperty(key)) {
                                pairs.push('"' + key + '":' + JSON.stringify(obj[key]));
                            }
                        }
                        return '{' + pairs.join(',') + '}';
                    }
                    return '{}';
                }
            };
        }
        """
        
        # Create a basic window object
        window_js = """
        var window = this;
        var self = window;
        var location = {
            href: '',
            protocol: 'http:',
            host: '',
            hostname: '',
            port: '',
            pathname: '',
            search: '',
            hash: ''
        };
        var document = {
            title: '',
            readyState: 'loading'
        };
        window.document = document;
        """
        
        # Create a basic navigator object
        navigator_js = """
        var navigator = {
            userAgent: 'WinkBrowser/1.0 (JavaScript Engine)',
            platform: 'Python',
            language: 'en-US',
            languages: ['en-US', 'en'],
            onLine: true,
            cookieEnabled: true
        };
        window.navigator = navigator;
        """
        
        # Define XMLHttpRequest
        xhr_js = """
        function XMLHttpRequest() {
            this.readyState = 0;
            this.status = 0;
            this.statusText = '';
            this.responseText = '';
            this.responseXML = null;
            this.response = '';
            this.responseType = '';
            this.onreadystatechange = null;
            this.onload = null;
            this.onerror = null;
            this.upload = {};
            
            this.open = function(method, url, async) {
                this.method = method;
                this.url = url;
                this.async = async !== false;
                this.readyState = 1;
                if (this.onreadystatechange) this.onreadystatechange();
                _xhr_open(this._id, method, url, this.async);
            };
            
            this.setRequestHeader = function(header, value) {
                _xhr_setRequestHeader(this._id, header, value);
            };
            
            this.send = function(data) {
                this.readyState = 2;
                if (this.onreadystatechange) this.onreadystatechange();
                _xhr_send(this._id, data || '');
            };
            
            this.abort = function() {
                _xhr_abort(this._id);
            };
            
            this._id = _xhr_create();
        }
        window.XMLHttpRequest = XMLHttpRequest;
        """
        
        # Execute all the setup code
        self.interpreter.evaljs(window_js)
        self.interpreter.evaljs(navigator_js)
        self.interpreter.evaljs(console_js)
        self.interpreter.evaljs(timers_js)
        self.interpreter.evaljs(json_js)
        self.interpreter.evaljs(xhr_js)
        
        # Register Python callbacks for JS functions
        self.interpreter.export_function('_console_log', self._console_log)
        self.interpreter.export_function('_console_error', self._console_error)
        self.interpreter.export_function('_console_warn', self._console_warn)
        self.interpreter.export_function('_console_info', self._console_info)
        self.interpreter.export_function('_scheduleTimer', self._schedule_timer)
        self.interpreter.export_function('_clearTimer', self._clear_timer)
        self.interpreter.export_function('_xhr_create', self._xhr_create)
        self.interpreter.export_function('_xhr_open', self._xhr_open)
        self.interpreter.export_function('_xhr_setRequestHeader', self._xhr_set_request_header)
        self.interpreter.export_function('_xhr_send', self._xhr_send)
        self.interpreter.export_function('_xhr_abort', self._xhr_abort)
        
        # Mark as initialized
        self.is_initialized = True
    
    def _console_log(self, message: str) -> None:
        """
        Handle console.log calls from JavaScript.
        
        Args:
            message: The console message in JSON format
        """
        try:
            args = json.loads(message)
            log_message = ' '.join(str(arg) for arg in args)
            logger.info(f"JS console.log: {log_message}")
            self.console_output.append(('log', log_message))
        except Exception as e:
            logger.error(f"Error in console.log: {e}")
    
    def _console_error(self, message: str) -> None:
        """
        Handle console.error calls from JavaScript.
        
        Args:
            message: The console message in JSON format
        """
        try:
            args = json.loads(message)
            log_message = ' '.join(str(arg) for arg in args)
            logger.error(f"JS console.error: {log_message}")
            self.console_output.append(('error', log_message))
        except Exception as e:
            logger.error(f"Error in console.error: {e}")
    
    def _console_warn(self, message: str) -> None:
        """
        Handle console.warn calls from JavaScript.
        
        Args:
            message: The console message in JSON format
        """
        try:
            args = json.loads(message)
            log_message = ' '.join(str(arg) for arg in args)
            logger.warning(f"JS console.warn: {log_message}")
            self.console_output.append(('warn', log_message))
        except Exception as e:
            logger.error(f"Error in console.warn: {e}")
    
    def _console_info(self, message: str) -> None:
        """
        Handle console.info calls from JavaScript.
        
        Args:
            message: The console message in JSON format
        """
        try:
            args = json.loads(message)
            log_message = ' '.join(str(arg) for arg in args)
            logger.info(f"JS console.info: {log_message}")
            self.console_output.append(('info', log_message))
        except Exception as e:
            logger.error(f"Error in console.info: {e}")
    
    def _schedule_timer(self, timer_id: int, delay: int) -> None:
        """
        Schedule a timer for execution.
        
        Args:
            timer_id: The timer ID
            delay: Delay in milliseconds
        """
        # In a real implementation, would schedule the timer
        # For now, just log it
        logger.debug(f"Scheduled timer {timer_id} with delay {delay}ms")
    
    def _clear_timer(self, timer_id: int) -> None:
        """
        Clear a scheduled timer.
        
        Args:
            timer_id: The timer ID to clear
        """
        logger.debug(f"Cleared timer {timer_id}")
    
    def _xhr_create(self) -> int:
        """
        Create a new XMLHttpRequest instance.
        
        Returns:
            ID for the new XHR instance
        """
        # In a real implementation, would create an XHR instance
        return 1  # Dummy ID
    
    def _xhr_open(self, xhr_id: int, method: str, url: str, async_flag: bool) -> None:
        """
        Handle XMLHttpRequest.open.
        
        Args:
            xhr_id: The XHR instance ID
            method: HTTP method
            url: Request URL
            async_flag: Whether the request is asynchronous
        """
        logger.debug(f"XHR {xhr_id} open: {method} {url} (async: {async_flag})")
    
    def _xhr_set_request_header(self, xhr_id: int, header: str, value: str) -> None:
        """
        Handle XMLHttpRequest.setRequestHeader.
        
        Args:
            xhr_id: The XHR instance ID
            header: Header name
            value: Header value
        """
        logger.debug(f"XHR {xhr_id} setRequestHeader: {header}={value}")
    
    def _xhr_send(self, xhr_id: int, data: str) -> None:
        """
        Handle XMLHttpRequest.send.
        
        Args:
            xhr_id: The XHR instance ID
            data: Request data
        """
        logger.debug(f"XHR {xhr_id} send: {data}")
        
        # In a real implementation, would perform the actual HTTP request
        # For now, simulate a successful response after a short delay
        threading.Timer(0.5, self._simulate_xhr_response, args=[xhr_id]).start()
    
    def _simulate_xhr_response(self, xhr_id: int) -> None:
        """
        Simulate an XHR response.
        
        Args:
            xhr_id: The XHR instance ID
        """
        # Set readyState to 4 (DONE)
        self.interpreter.evaljs(f"""
        (function() {{
            var xhr = document.querySelector('[xhr-id="{xhr_id}"]')._xhr;
            if (xhr) {{
                xhr.readyState = 4;
                xhr.status = 200;
                xhr.statusText = 'OK';
                xhr.responseText = '{{"message": "This is a simulated response"}}';
                xhr.response = xhr.responseText;
                if (xhr.onreadystatechange) xhr.onreadystatechange();
                if (xhr.onload) xhr.onload();
            }}
        }})();
        """)
    
    def _xhr_abort(self, xhr_id: int) -> None:
        """
        Handle XMLHttpRequest.abort.
        
        Args:
            xhr_id: The XHR instance ID
        """
        logger.debug(f"XHR {xhr_id} abort")
    
    def evaluate(self, code: str, async_eval: bool = False) -> Any:
        """
        Evaluate JavaScript code.
        
        Args:
            code: JavaScript code to evaluate
            async_eval: Whether to evaluate asynchronously
            
        Returns:
            The result of the evaluation
        """
        if not self.is_initialized:
            logger.warning("JS engine not initialized, initializing now")
            self._setup_global_objects()
        
        if async_eval:
            # Run in a separate thread
            self.eval_thread = threading.Thread(
                target=self._evaluate_in_thread,
                args=(code,),
                daemon=True
            )
            self.eval_thread.start()
            return None
        else:
            # Run synchronously
            return self._evaluate_sync(code)
    
    def _evaluate_in_thread(self, code: str) -> None:
        """
        Evaluate JavaScript code in a separate thread.
        
        Args:
            code: JavaScript code to evaluate
        """
        try:
            self.is_executing = True
            result = self.interpreter.evaljs(code)
            logger.debug(f"Async JS evaluation result: {result}")
        except Exception as e:
            logger.error(f"Error in async JS evaluation: {e}")
        finally:
            self.is_executing = False
    
    def _evaluate_sync(self, code: str) -> Any:
        """
        Evaluate JavaScript code synchronously.
        
        Args:
            code: JavaScript code to evaluate
            
        Returns:
            The result of the evaluation
        """
        try:
            self.is_executing = True
            result = self.interpreter.evaljs(code)
            return result
        except Exception as e:
            logger.error(f"Error in JS evaluation: {e}")
            return None
        finally:
            self.is_executing = False
    
    def setup_document(self, document) -> None:
        """
        Set up the JavaScript document object to reflect the DOM.
        
        Args:
            document: The HTML document
        """
        if not document:
            logger.warning("Cannot setup document: document is None")
            return
        
        # Set document properties
        if hasattr(document, 'title'):
            self.interpreter.evaljs(f'document.title = "{document.title}";')
        
        # Set document readyState to 'interactive'
        self.interpreter.evaljs('document.readyState = "interactive";')
        
        # In a real implementation, would create the full DOM API and bind elements
        # For now, just set up a basic document object
        
        # Dispatch DOMContentLoaded event
        self.interpreter.evaljs("""
        if (typeof window.addEventListener === 'function') {
            var event = { type: 'DOMContentLoaded' };
            window.dispatchEvent(event);
        }
        document.readyState = "complete";
        """)
    
    def execute_scripts(self, document) -> None:
        """
        Execute all script tags in the document.
        
        Args:
            document: The HTML document
        """
        if not document:
            logger.warning("Cannot execute scripts: document is None")
            return
        
        # Find all script elements
        script_elements = self._find_script_elements(document)
        
        for script in script_elements:
            # Skip if script has a 'type' attribute that isn't JavaScript
            script_type = script.get_attribute('type') if hasattr(script, 'get_attribute') else None
            if script_type and script_type.lower() not in ('text/javascript', 'application/javascript', ''):
                continue
                
            # Check if it's an external script
            src = script.get_attribute('src') if hasattr(script, 'get_attribute') else None
            if src:
                # Would fetch and execute the external script
                logger.info(f"Would load external script from: {src}")
                # In a real implementation, would fetch the script content and execute it
                continue
                
            # Execute inline script
            if hasattr(script, 'text_content') and script.text_content:
                try:
                    logger.info("Executing inline script")
                    self.evaluate(script.text_content)
                except Exception as e:
                    logger.error(f"Error executing script: {e}")
    
    def _find_script_elements(self, node) -> List:
        """
        Find all script elements in the document.
        
        Args:
            node: The node to search from
            
        Returns:
            List of script elements
        """
        result = []
        
        # Check if this is a script element
        if hasattr(node, 'tag_name') and node.tag_name.lower() == 'script':
            result.append(node)
        
        # Check children
        if hasattr(node, 'children'):
            for child in node.children:
                result.extend(self._find_script_elements(child))
                
        return result
    
    def handle_event(self, event_type: str, target_id: str = None, event_data: Dict[str, Any] = None) -> None:
        """
        Handle a DOM event.
        
        Args:
            event_type: Type of event (e.g., 'click', 'load')
            target_id: ID of the target element
            event_data: Additional event data
        """
        if not event_data:
            event_data = {}
            
        event_json = json.dumps(event_data)
        
        # Create and dispatch the event
        if target_id:
            js_code = f"""
            (function() {{
                var target = document.getElementById('{target_id}');
                if (target) {{
                    var event = new Event('{event_type}');
                    Object.assign(event, {event_json});
                    target.dispatchEvent(event);
                }}
            }})();
            """
        else:
            # Global event
            js_code = f"""
            (function() {{
                var event = new Event('{event_type}');
                Object.assign(event, {event_json});
                window.dispatchEvent(event);
            }})();
            """
            
        self.evaluate(js_code)
    
    def cleanup(self) -> None:
        """Clean up resources used by the JavaScript engine."""
        # Clear timers
        self.interpreter.evaljs("""
        for (var id in _timers) {
            clearTimeout(id);
            clearInterval(id);
        }
        """)
        
        # Clear console output
        self.console_output = []
        
        # Stop any running evaluation
        if self.eval_thread and self.eval_thread.is_alive():
            # Can't really stop a thread in Python, but mark it
            self.is_executing = False 