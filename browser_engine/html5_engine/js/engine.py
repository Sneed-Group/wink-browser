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
        
        # Setup polyfills for modern JavaScript features
        self._setup_polyfills()
        
        # JS console implementation
        self.console_output = []
        
        # Event queue
        self.event_queue = []
        
        # Execution state
        self.is_executing = False
        self.is_initialized = True
        
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
        
        # Define the Event class
        event_js = """
        function Event(type, eventInitDict) {
            this.type = type;
            this.target = null;
            this.currentTarget = null;
            this.eventPhase = 0;
            this.bubbles = eventInitDict ? !!eventInitDict.bubbles : false;
            this.cancelable = eventInitDict ? !!eventInitDict.cancelable : false;
            this.defaultPrevented = false;
            this.isTrusted = false;
            this.timeStamp = Date.now();
            
            this.stopPropagation = function() {
                // Not implemented yet
            };
            
            this.stopImmediatePropagation = function() {
                // Not implemented yet
            };
            
            this.preventDefault = function() {
                if (this.cancelable) {
                    this.defaultPrevented = true;
                }
            };
        }
        """
        
        # Register the Python callbacks for console methods
        self.interpreter.export_function("_console_log", self._console_log)
        self.interpreter.export_function("_console_error", self._console_error)
        self.interpreter.export_function("_console_warn", self._console_warn)
        self.interpreter.export_function("_console_info", self._console_info)
        
        # Initialize the console object
        self.interpreter.evaljs(console_js)
        
        # Initialize the Event class
        self.interpreter.evaljs(event_js)
        
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
            readyState: 'loading',
            getElementById: function(id) {
                return null;
            },
            getElementsByTagName: function(tagName) {
                return [];
            },
            getElementsByClassName: function(className) {
                return [];
            },
            querySelector: function(selector) {
                return null;
            },
            querySelectorAll: function(selector) {
                return [];
            },
            createElement: function(tagName) {
                var element = {
                    tagName: tagName.toUpperCase(),
                    style: {},
                    attributes: {},
                    children: [],
                    addEventListener: function(type, listener, options) {
                        // Store event listeners
                        if (!this._eventListeners) this._eventListeners = {};
                        if (!this._eventListeners[type]) this._eventListeners[type] = [];
                        this._eventListeners[type].push(listener);
                    },
                    removeEventListener: function(type, listener) {
                        // Remove event listeners
                        if (!this._eventListeners || !this._eventListeners[type]) return;
                        var index = this._eventListeners[type].indexOf(listener);
                        if (index !== -1) this._eventListeners[type].splice(index, 1);
                    },
                    setAttribute: function(name, value) {
                        this.attributes[name] = value;
                    },
                    getAttribute: function(name) {
                        return this.attributes[name] || null;
                    },
                    appendChild: function(child) {
                        this.children.push(child);
                        return child;
                    }
                };
                return element;
            }
        };
        window.document = document;
        
        // Event listeners storage
        window._eventListeners = {};
        document._eventListeners = {};
        
        // Add addEventListener method to window
        window.addEventListener = function(type, listener, options) {
            if (!window._eventListeners) window._eventListeners = {};
            if (!window._eventListeners[type]) window._eventListeners[type] = [];
            window._eventListeners[type].push(listener);
        };
        
        // Add removeEventListener method to window
        window.removeEventListener = function(type, listener) {
            if (!window._eventListeners || !window._eventListeners[type]) return;
            var index = window._eventListeners[type].indexOf(listener);
            if (index !== -1) window._eventListeners[type].splice(index, 1);
        };
        
        // Add addEventListener method to document
        document.addEventListener = function(type, listener, options) {
            if (!document._eventListeners) document._eventListeners = {};
            if (!document._eventListeners[type]) document._eventListeners[type] = [];
            document._eventListeners[type].push(listener);
        };
        
        // Add removeEventListener method to document
        document.removeEventListener = function(type, listener) {
            if (!document._eventListeners || !document._eventListeners[type]) return;
            var index = document._eventListeners[type].indexOf(listener);
            if (index !== -1) document._eventListeners[type].splice(index, 1);
        };
        
        // Add dispatchEvent method to window
        window.dispatchEvent = function(event) {
            if (event && event.type) {
                // Call the on* handler if it exists
                var handler = window['on' + event.type];
                if (typeof handler === 'function') {
                    handler.call(window, event);
                }
                
                // Call all registered event listeners
                var listeners = window._eventListeners && window._eventListeners[event.type];
                if (listeners) {
                    for (var i = 0; i < listeners.length; i++) {
                        listeners[i].call(window, event);
                    }
                }
                
                return !event.defaultPrevented;
            }
            return true;
        };
        
        // Add dispatchEvent method to document
        document.dispatchEvent = function(event) {
            if (event && event.type) {
                // Call the on* handler if it exists
                var handler = document['on' + event.type];
                if (typeof handler === 'function') {
                    handler.call(document, event);
                }
                
                // Call all registered event listeners
                var listeners = document._eventListeners && document._eventListeners[event.type];
                if (listeners) {
                    for (var i = 0; i < listeners.length; i++) {
                        listeners[i].call(document, event);
                    }
                }
                
                return !event.defaultPrevented;
            }
            return true;
        };
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
        self.interpreter.evaljs(timers_js)
        self.interpreter.evaljs(json_js)
        self.interpreter.evaljs(xhr_js)
        
        # Register Python callbacks for JS functions
        self.interpreter.export_function('_scheduleTimer', self._schedule_timer)
        self.interpreter.export_function('_clearTimer', self._clear_timer)
        self.interpreter.export_function('_xhr_create', self._xhr_create)
        self.interpreter.export_function('_xhr_open', self._xhr_open)
        self.interpreter.export_function('_xhr_setRequestHeader', self._xhr_set_request_header)
        self.interpreter.export_function('_xhr_send', self._xhr_send)
        self.interpreter.export_function('_xhr_abort', self._xhr_abort)
        
        # Mark as initialized
        self.is_initialized = True
    
    def _setup_polyfills(self) -> None:
        """Set up polyfills for modern JavaScript features not supported by dukpy."""
        # Polyfills for ES6+ features
        polyfills_js = """
        // Array polyfills
        if (!Array.prototype.find) {
            Array.prototype.find = function(predicate) {
                if (this == null) {
                    throw new TypeError('Array.prototype.find called on null or undefined');
                }
                if (typeof predicate !== 'function') {
                    throw new TypeError('predicate must be a function');
                }
                var list = Object(this);
                var length = list.length >>> 0;
                var thisArg = arguments[1];
                
                for (var i = 0; i < length; i++) {
                    var value = list[i];
                    if (predicate.call(thisArg, value, i, list)) {
                        return value;
                    }
                }
                return undefined;
            };
        }

        if (!Array.prototype.findIndex) {
            Array.prototype.findIndex = function(predicate) {
                if (this == null) {
                    throw new TypeError('Array.prototype.findIndex called on null or undefined');
                }
                if (typeof predicate !== 'function') {
                    throw new TypeError('predicate must be a function');
                }
                var list = Object(this);
                var length = list.length >>> 0;
                var thisArg = arguments[1];
                
                for (var i = 0; i < length; i++) {
                    if (predicate.call(thisArg, list[i], i, list)) {
                        return i;
                    }
                }
                return -1;
            };
        }

        if (!Array.prototype.includes) {
            Array.prototype.includes = function(searchElement, fromIndex) {
                if (this == null) {
                    throw new TypeError('Array.prototype.includes called on null or undefined');
                }
                
                var O = Object(this);
                var len = parseInt(O.length) || 0;
                if (len === 0) {
                    return false;
                }
                
                var n = parseInt(fromIndex) || 0;
                var k;
                
                if (n >= 0) {
                    k = n;
                } else {
                    k = len + n;
                    if (k < 0) {
                        k = 0;
                    }
                }
                
                while (k < len) {
                    var currentElement = O[k];
                    if (searchElement === currentElement || 
                        (searchElement !== searchElement && currentElement !== currentElement)) {
                        return true;
                    }
                    k++;
                }
                
                return false;
            };
        }

        // String polyfills
        if (!String.prototype.startsWith) {
            String.prototype.startsWith = function(searchString, position) {
                position = position || 0;
                return this.substr(position, searchString.length) === searchString;
            };
        }

        if (!String.prototype.endsWith) {
            String.prototype.endsWith = function(searchString, position) {
                var subjectString = this.toString();
                if (typeof position !== 'number' || !isFinite(position) || 
                    Math.floor(position) !== position || position > subjectString.length) {
                    position = subjectString.length;
                }
                position -= searchString.length;
                var lastIndex = subjectString.indexOf(searchString, position);
                return lastIndex !== -1 && lastIndex === position;
            };
        }

        if (!String.prototype.includes) {
            String.prototype.includes = function(search, start) {
                if (typeof start !== 'number') {
                    start = 0;
                }
                if (start + search.length > this.length) {
                    return false;
                } else {
                    return this.indexOf(search, start) !== -1;
                }
            };
        }

        if (!String.prototype.repeat) {
            String.prototype.repeat = function(count) {
                if (this == null) {
                    throw new TypeError('String.prototype.repeat called on null or undefined');
                }
                
                var string = String(this);
                count = +count;
                
                if (count !== count) {
                    count = 0;
                }
                
                if (count < 0 || count === Infinity) {
                    throw new RangeError('Invalid count value');
                }
                
                count = Math.floor(count);
                if (string.length === 0 || count === 0) {
                    return '';
                }
                
                var result = '';
                while (count) {
                    if (count & 1) {
                        result += string;
                    }
                    if (count >>= 1) {
                        string += string;
                    }
                }
                return result;
            };
        }

        // Object polyfills
        if (!Object.assign) {
            Object.assign = function(target) {
                if (target == null) {
                    throw new TypeError('Cannot convert undefined or null to object');
                }
                
                var to = Object(target);
                
                for (var index = 1; index < arguments.length; index++) {
                    var nextSource = arguments[index];
                    
                    if (nextSource != null) {
                        for (var nextKey in nextSource) {
                            if (Object.prototype.hasOwnProperty.call(nextSource, nextKey)) {
                                to[nextKey] = nextSource[nextKey];
                            }
                        }
                    }
                }
                
                return to;
            };
        }

        // Promise polyfill for basic promise support
        if (typeof Promise === 'undefined') {
            window.Promise = function(executor) {
                var self = this;
                self.status = 'pending';
                self.value = undefined;
                self.reason = undefined;
                self.onFulfilledCallbacks = [];
                self.onRejectedCallbacks = [];
                
                function resolve(value) {
                    if (self.status === 'pending') {
                        self.status = 'fulfilled';
                        self.value = value;
                        for (var i = 0; i < self.onFulfilledCallbacks.length; i++) {
                            self.onFulfilledCallbacks[i](value);
                        }
                    }
                }
                
                function reject(reason) {
                    if (self.status === 'pending') {
                        self.status = 'rejected';
                        self.reason = reason;
                        for (var i = 0; i < self.onRejectedCallbacks.length; i++) {
                            self.onRejectedCallbacks[i](reason);
                        }
                    }
                }
                
                try {
                    executor(resolve, reject);
                } catch(e) {
                    reject(e);
                }
            };
            
            Promise.prototype.then = function(onFulfilled, onRejected) {
                var self = this;
                var promise2 = new Promise(function(resolve, reject) {
                    function handleFulfilled(value) {
                        if (typeof onFulfilled === 'function') {
                            try {
                                var x = onFulfilled(value);
                                resolve(x);
                            } catch(e) {
                                reject(e);
                            }
                        } else {
                            resolve(value);
                        }
                    }
                    
                    function handleRejected(reason) {
                        if (typeof onRejected === 'function') {
                            try {
                                var x = onRejected(reason);
                                resolve(x);
                            } catch(e) {
                                reject(e);
                            }
                        } else {
                            reject(reason);
                        }
                    }
                    
                    if (self.status === 'fulfilled') {
                        setTimeout(function() {
                            handleFulfilled(self.value);
                        }, 0);
                    } else if (self.status === 'rejected') {
                        setTimeout(function() {
                            handleRejected(self.reason);
                        }, 0);
                    } else if (self.status === 'pending') {
                        self.onFulfilledCallbacks.push(function(value) {
                            setTimeout(function() {
                                handleFulfilled(value);
                            }, 0);
                        });
                        self.onRejectedCallbacks.push(function(reason) {
                            setTimeout(function() {
                                handleRejected(reason);
                            }, 0);
                        });
                    }
                });
                
                return promise2;
            };
            
            Promise.prototype.catch = function(onRejected) {
                return this.then(null, onRejected);
            };
            
            Promise.resolve = function(value) {
                return new Promise(function(resolve) {
                    resolve(value);
                });
            };
            
            Promise.reject = function(reason) {
                return new Promise(function(resolve, reject) {
                    reject(reason);
                });
            };
            
            Promise.all = function(promises) {
                return new Promise(function(resolve, reject) {
                    if (!Array.isArray(promises)) {
                        return reject(new TypeError('Promise.all accepts an array'));
                    }
                    
                    var results = [];
                    var remaining = promises.length;
                    
                    if (remaining === 0) {
                        return resolve(results);
                    }
                    
                    function resolvePromise(i, value) {
                        results[i] = value;
                        remaining--;
                        if (remaining === 0) {
                            resolve(results);
                        }
                    }
                    
                    for (var i = 0; i < promises.length; i++) {
                        (function(i) {
                            var promise = promises[i];
                            if (promise && typeof promise.then === 'function') {
                                promise.then(
                                    function(value) {
                                        resolvePromise(i, value);
                                    },
                                    function(reason) {
                                        reject(reason);
                                    }
                                );
                            } else {
                                resolvePromise(i, promise);
                            }
                        })(i);
                    }
                });
            };
        }
        """
        
        try:
            # Add the polyfills to the JS environment
            self.interpreter.evaljs(polyfills_js)
            logger.debug("JavaScript polyfills initialized")
        except Exception as e:
            logger.error(f"Error setting up JavaScript polyfills: {e}")
    
    def _apply_polyfill_middleware(self, js_code: str) -> str:
        """
        Apply polyfill middleware to JavaScript code.
        This function checks the code for unsupported features and wraps
        them with compatible alternatives.
        
        Args:
            js_code: The JavaScript code to process
            
        Returns:
            Processed JavaScript code with polyfills applied as needed
        """
        if not js_code:
            return js_code
        
        # Wrap the code in a try-catch block to capture and log errors
        wrapped_code = """
        try {
            %s
        } catch (e) {
            console.error('JavaScript error: ' + e.message);
        }
        """ % js_code
        
        # Check for modern array methods and ensure they're polyfilled
        array_methods = ['find', 'findIndex', 'includes', 'from', 'of']
        for method in array_methods:
            if f"Array.prototype.{method}" in js_code or f".{method}(" in js_code:
                logger.debug(f"Detected possible use of Array.{method} - polyfill will be applied")
        
        # Check for modern string methods
        string_methods = ['startsWith', 'endsWith', 'includes', 'repeat', 'padStart', 'padEnd']
        for method in string_methods:
            if f"String.prototype.{method}" in js_code or f".{method}(" in js_code:
                logger.debug(f"Detected possible use of String.{method} - polyfill will be applied")
        
        # Check for Promise usage
        if "new Promise" in js_code or "Promise." in js_code:
            logger.debug("Detected possible use of Promises - polyfill will be applied")
        
        # Check for Object.assign
        if "Object.assign" in js_code:
            logger.debug("Detected possible use of Object.assign - polyfill will be applied")
        
        return wrapped_code
    
    def evaluate(self, js_code: str, async_eval: bool = False) -> Any:
        """
        Evaluate JavaScript code.
        
        Args:
            js_code: JavaScript code to evaluate
            async_eval: Whether to evaluate asynchronously
            
        Returns:
            The result of the evaluation, or None if async_eval is True
        """
        if not self.is_initialized:
            logger.warning("JS engine not initialized, initializing now")
            self._setup_global_objects()
            self._setup_polyfills()
            self.is_initialized = True
        
        # Apply polyfill middleware to the code
        processed_code = self._apply_polyfill_middleware(js_code)
        
        if async_eval:
            if self.eval_thread and self.eval_thread.is_alive():
                logger.warning("Another JavaScript evaluation is already running")
                return None
            
            self.eval_thread = threading.Thread(
                target=self._evaluate_in_thread, 
                args=(processed_code,)
            )
            self.eval_thread.daemon = True
            self.eval_thread.start()
            return None
        else:
            return self._evaluate_sync(processed_code)
    
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
            # Catch syntax errors before evaluation
            try:
                result = self.interpreter.evaljs(code)
                return result
            except dukpy.JSRuntimeError as js_error:
                # More informative error handling for JavaScript runtime errors
                error_msg = str(js_error)
                logger.error(f"Error in JS evaluation: {error_msg}")
                
                # Attempt to extract line number from error message
                line_match = re.search(r'line (\d+)', error_msg)
                if line_match:
                    line_num = int(line_match.group(1))
                    code_lines = code.split('\n')
                    
                    # Show context around the error
                    start_line = max(0, line_num - 3)
                    end_line = min(len(code_lines), line_num + 2)
                    
                    context = "\n".join(f"{i+1}: {line}" for i, line in enumerate(code_lines[start_line:end_line]))
                    logger.error(f"Error context:\n{context}")
                
                return None
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
                logger.info(f"Would load external script from: {src}")
                
                # Check if we have a window and can request the script
                if self.window and hasattr(self.window, 'document') and hasattr(self.window.document, 'network_manager'):
                    try:
                        # Only attempt to load scripts from the same origin or if CORS allows
                        base_url = self.window.document.url if hasattr(self.window.document, 'url') else None
                        
                        if base_url:
                            # Resolve relative URLs
                            if not src.startswith(('http://', 'https://')):
                                from urllib.parse import urljoin
                                full_src_url = urljoin(base_url, src)
                            else:
                                full_src_url = src
                                
                            logger.debug(f"Attempting to load script from: {full_src_url}")
                            
                            # Use the network manager to fetch the script
                            # This is simplified - in a real implementation you'd check CORS,
                            # handle errors, etc.
                            script_content = self.window.document.network_manager.fetch(full_src_url)
                            
                            if script_content:
                                logger.info(f"Successfully loaded script from {src}")
                                sanitized_content = self._sanitize_script_content(script_content)
                                try:
                                    self.evaluate(sanitized_content)
                                except Exception as e:
                                    logger.error(f"Error in JS evaluation: {e}")
                            else:
                                logger.warning(f"Failed to load script from {src}")
                    except Exception as e:
                        logger.error(f"Error loading external script {src}: {e}")
                
                continue
                
            # Execute inline script - first check for script_content property, then fallback to text_content
            if hasattr(script, 'script_content') and script.script_content:
                try:
                    logger.info("Executing inline script")
                    # Clean up the script content to avoid unterminated statement errors
                    script_content = self._sanitize_script_content(script.script_content)
                    self.evaluate(script_content)
                except Exception as e:
                    logger.error(f"Error in JS evaluation: {e}")
            elif hasattr(script, 'text_content') and script.text_content:
                try:
                    logger.info("Executing inline script from text_content")
                    # Clean up the script content to avoid unterminated statement errors
                    script_content = self._sanitize_script_content(script.text_content)
                    self.evaluate(script_content)
                except Exception as e:
                    logger.error(f"Error in JS evaluation: {e}")
    
    def _sanitize_script_content(self, content: str) -> str:
        """
        Sanitize script content to avoid common errors.
        
        Args:
            content: The script content to sanitize
            
        Returns:
            Sanitized script content
        """
        if not content:
            return ""
            
        # Remove HTML comments that might be in the script
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # Special fix for DuckDuckGo scripts that have unterminated if statements
        if "duckduckgo.com" in content or "duck.com" in content:
            # If we find an if statement without closing braces, add them
            if re.search(r'if\s*\([^{]*\)\s*{[^}]*$', content) or \
               re.search(r'if\s*\(typeof console !== \'undefined\'\s*&&\s*console\.error\)', content):
                content += "\nconsole.error(e); }"
        
        # Ensure balanced braces and parentheses
        braces_count = content.count('{') - content.count('}')
        if braces_count > 0:
            content += '}' * braces_count
        
        parens_count = content.count('(') - content.count(')')
        if parens_count > 0:
            content += ')' * parens_count
            
        # Ensure the script ends with a semicolon to avoid unterminated statement errors
        content = content.strip()
        if content and not content.endswith(';'):
            content += ';'
            
        # Wrap in try-catch with proper error handling
        wrapped_content = """
        try {
            %s
        } catch (e) {
            if (typeof console !== 'undefined' && console.error) {
                console.error('JS Error: ' + e.message);
            }
        }
        """ % content
        
        return wrapped_content
    
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