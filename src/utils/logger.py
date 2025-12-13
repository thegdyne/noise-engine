"""
Logger - Central logging system for Noise Engine

Usage:
    from src.utils.logger import logger
    
    logger.debug("Detailed debug info")
    logger.info("Normal operation")
    logger.warning("Something unexpected")
    logger.error("Something failed")
    
    # With context
    logger.info("Gen 1 started", component="OSC")
    logger.error("Connection failed", component="OSC", details=str(e))

The logger emits Qt signals for thread-safe GUI console updates.
"""

import logging
import sys
from datetime import datetime
from enum import IntEnum
from typing import Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal


class LogLevel(IntEnum):
    """Log levels matching Python logging."""
    DEBUG = logging.DEBUG      # 10
    INFO = logging.INFO        # 20
    WARNING = logging.WARNING  # 30
    ERROR = logging.ERROR      # 40


class LogSignalEmitter(QObject):
    """Qt signal emitter for thread-safe log updates."""
    log_message = pyqtSignal(str, int, str)  # message, level, timestamp


class QtSignalHandler(logging.Handler):
    """
    Custom logging handler that emits Qt signals.
    Thread-safe: can be called from any thread, signal delivered to main thread.
    """
    
    def __init__(self, emitter: LogSignalEmitter):
        super().__init__()
        self.emitter = emitter
        
    def emit(self, record: logging.LogRecord):
        try:
            # Format: include component if present
            msg = self.format(record)
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.emitter.log_message.emit(msg, record.levelno, timestamp)
        except Exception:
            self.handleError(record)


class NoiseEngineLogger:
    """
    Central logger for Noise Engine.
    
    Features:
    - Qt signal emission for GUI console
    - Component tagging for filtering
    - Console (terminal) output
    - Optional file output
    """
    
    def __init__(self):
        self._logger = logging.getLogger("noise_engine")
        self._logger.setLevel(logging.DEBUG)  # Capture all, filter on handlers
        self._logger.propagate = False  # Don't pass to root logger
        
        # Qt signal emitter (for GUI console)
        self.signal_emitter = LogSignalEmitter()
        
        # Console handler (terminal output)
        self._console_handler = logging.StreamHandler(sys.stdout)
        self._console_handler.setLevel(logging.INFO)  # Default: INFO and above
        self._console_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        ))
        self._logger.addHandler(self._console_handler)
        
        # Qt signal handler (GUI console)
        self._qt_handler = QtSignalHandler(self.signal_emitter)
        self._qt_handler.setLevel(logging.DEBUG)  # GUI shows all levels
        self._qt_handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(self._qt_handler)
        
        # File handler (optional, for bug reports)
        self._file_handler: Optional[logging.FileHandler] = None
        
    def set_level(self, level: LogLevel):
        """Set minimum log level for console output."""
        self._console_handler.setLevel(level)
        
    def set_gui_level(self, level: LogLevel):
        """Set minimum log level for GUI console."""
        self._qt_handler.setLevel(level)
        
    def enable_file_logging(self, filepath: str):
        """Enable logging to file."""
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)
            
        self._file_handler = logging.FileHandler(filepath)
        self._file_handler.setLevel(logging.DEBUG)
        self._file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        self._logger.addHandler(self._file_handler)
        
    def disable_file_logging(self):
        """Disable file logging."""
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None
    
    def _format_message(self, msg: str, component: Optional[str] = None, 
                        details: Optional[str] = None) -> str:
        """Format message with optional component tag and details."""
        parts = []
        if component:
            parts.append(f"[{component}]")
        parts.append(msg)
        if details:
            parts.append(f"- {details}")
        return " ".join(parts)
    
    def debug(self, msg: str, component: Optional[str] = None, 
              details: Optional[str] = None):
        """Log debug message (detailed info for troubleshooting)."""
        self._logger.debug(self._format_message(msg, component, details))
        
    def info(self, msg: str, component: Optional[str] = None,
             details: Optional[str] = None):
        """Log info message (normal operation)."""
        self._logger.info(self._format_message(msg, component, details))
        
    def warning(self, msg: str, component: Optional[str] = None,
                details: Optional[str] = None):
        """Log warning message (unexpected but recoverable)."""
        self._logger.warning(self._format_message(msg, component, details))
        
    def error(self, msg: str, component: Optional[str] = None,
              details: Optional[str] = None):
        """Log error message (something failed)."""
        self._logger.error(self._format_message(msg, component, details))
        
    def osc(self, msg: str, details: Optional[str] = None):
        """Convenience: log OSC-related message."""
        self.debug(msg, component="OSC", details=details)
        
    def midi(self, msg: str, details: Optional[str] = None):
        """Convenience: log MIDI-related message."""
        self.debug(msg, component="MIDI", details=details)
        
    def gen(self, slot_id: int, msg: str, details: Optional[str] = None):
        """Convenience: log generator-related message."""
        self.debug(f"Gen {slot_id}: {msg}", component="GEN", details=details)


# Global logger instance
logger = NoiseEngineLogger()


def set_log_level(level: LogLevel):
    """Set the console log level."""
    logger.set_level(level)
