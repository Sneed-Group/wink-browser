"""
Logging utility module for the browser.
"""

import logging
import os
import sys
import time
from typing import Optional
from datetime import datetime
import traceback

# Define logging levels dictionary for easy reference
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

class LogFormatter(logging.Formatter):
    """Custom log formatter with colored output for console."""
    
    # ANSI color codes
    COLORS = {
        'RESET': '\033[0m',
        'BLACK': '\033[30m',
        'RED': '\033[31m',
        'GREEN': '\033[32m',
        'YELLOW': '\033[33m',
        'BLUE': '\033[34m',
        'MAGENTA': '\033[35m',
        'CYAN': '\033[36m',
        'WHITE': '\033[37m',
        'BOLD': '\033[1m'
    }
    
    # Level-specific colors
    LEVEL_COLORS = {
        'DEBUG': COLORS['BLUE'],
        'INFO': COLORS['GREEN'],
        'WARNING': COLORS['YELLOW'],
        'ERROR': COLORS['RED'],
        'CRITICAL': COLORS['RED'] + COLORS['BOLD']
    }
    
    def __init__(self, colored: bool = True, *args, **kwargs):
        """
        Initialize formatter.
        
        Args:
            colored: Whether to use colored output
            *args: Additional formatter args
            **kwargs: Additional formatter kwargs
        """
        self.colored = colored and sys.platform != 'win32'  # Disable colors on Windows
        super().__init__(*args, **kwargs)
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record.
        
        Args:
            record: Log record to format
        
        Returns:
            str: Formatted log message
        """
        # Get the original formatted message
        formatted_msg = super().format(record)
        
        if self.colored:
            # Apply color based on level
            level_name = record.levelname
            if level_name in self.LEVEL_COLORS:
                colored_level = f"{self.LEVEL_COLORS[level_name]}{level_name}{self.COLORS['RESET']}"
                # Replace level name with colored level
                formatted_msg = formatted_msg.replace(level_name, colored_level)
        
        return formatted_msg


def setup_logging(log_file: Optional[str] = None, 
                  console_level: str = "INFO", 
                  file_level: str = "DEBUG",
                  component: Optional[str] = None) -> logging.Logger:
    """
    Set up logging for the browser.
    
    Args:
        log_file: Path to log file (None for no file logging)
        console_level: Console logging level
        file_level: File logging level
        component: Optional component name for the logger
        
    Returns:
        logging.Logger: Configured logger
    """
    # Get or create logger
    logger_name = "wink_browser"
    if component:
        logger_name = f"{logger_name}.{component}"
    
    logger = logging.getLogger(logger_name)
    
    # If handlers already exist, assume logger is already configured
    if logger.handlers:
        return logger
    
    # Set root logger level to lowest of console and file to ensure messages are passed
    logger.setLevel(min(LOG_LEVELS.get(console_level, logging.INFO),
                        LOG_LEVELS.get(file_level, logging.DEBUG)))
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVELS.get(console_level, logging.INFO))
    
    # Create console formatter
    console_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    console_formatter = LogFormatter(colored=True, fmt=console_format, datefmt='%H:%M:%S')
    console_handler.setFormatter(console_formatter)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        # Ensure the directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(LOG_LEVELS.get(file_level, logging.DEBUG))
        
        # Create file formatter (more detailed than console)
        file_format = ("%(asctime)s [%(levelname)s] %(name)s "
                       "(%(filename)s:%(lineno)d): %(message)s")
        file_formatter = logging.Formatter(file_format, datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        
        # Add file handler to logger
        logger.addHandler(file_handler)
    
    return logger


def get_default_log_file() -> str:
    """
    Get the default log file path.
    
    Returns:
        str: Default log file path
    """
    # Default to ~/.wink_browser/logs/wink_browser_YYYY-MM-DD.log
    home_dir = os.path.expanduser("~")
    log_dir = os.path.join(home_dir, ".wink_browser", "logs")
    
    # Create directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file with current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"wink_browser_{date_str}.log")
    
    return log_file


def log_exception(logger: logging.Logger, exception: Exception, 
                  message: str = "An exception occurred") -> None:
    """
    Log an exception.
    
    Args:
        logger: Logger to use
        exception: Exception to log
        message: Message to log with the exception
    """
    exc_info = (type(exception), exception, exception.__traceback__)
    logger.error(f"{message}: {exception}", exc_info=exc_info)


class PerformanceLogger:
    """Utility class for logging performance metrics."""
    
    def __init__(self, logger: logging.Logger, component: str):
        """
        Initialize performance logger.
        
        Args:
            logger: Logger to use
            component: Component name
        """
        self.logger = logger
        self.component = component
        self.start_times = {}
    
    def start(self, name: str) -> None:
        """
        Start timing an operation.
        
        Args:
            name: Operation name
        """
        self.start_times[name] = time.time()
    
    def end(self, name: str, level: str = "DEBUG") -> float:
        """
        End timing an operation and log the duration.
        
        Args:
            name: Operation name
            level: Log level
            
        Returns:
            float: Duration in seconds
        """
        if name not in self.start_times:
            self.logger.warning(f"No start time found for {name}")
            return 0
        
        duration = time.time() - self.start_times[name]
        log_func = getattr(self.logger, level.lower())
        log_func(f"{self.component} {name} took {duration:.4f} seconds")
        
        return duration
    
    def log(self, name: str, duration: float, level: str = "DEBUG") -> None:
        """
        Log a duration.
        
        Args:
            name: Operation name
            duration: Duration in seconds
            level: Log level
        """
        log_func = getattr(self.logger, level.lower())
        log_func(f"{self.component} {name} took {duration:.4f} seconds")
    
    def clear(self) -> None:
        """Clear all start times."""
        self.start_times.clear() 