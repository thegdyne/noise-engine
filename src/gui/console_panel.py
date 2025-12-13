"""
Console Panel - Slide-out logging console

Features:
- Slide-out from right side (overlay style)
- Color-coded log levels
- Auto-scroll with pause option
- Max 500 lines (memory limit)
- Clear and copy buttons
- Level filter dropdown
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QComboBox, QLabel, QFrame
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QTextCursor

from src.gui.theme import COLORS, MONO_FONT, FONT_SIZES
from src.utils.logger import logger, LogLevel

import logging


# Log level colors
LOG_COLORS = {
    logging.DEBUG: "#666666",     # Grey
    logging.INFO: "#88ff88",      # Green  
    logging.WARNING: "#ffaa44",   # Orange
    logging.ERROR: "#ff6666",     # Red
}

LOG_LEVEL_NAMES = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARN",
    logging.ERROR: "ERROR",
}


class ConsolePanel(QFrame):
    """
    Slide-out console panel for viewing logs.
    
    Overlay style - slides over mixer panel from right edge.
    Toggle with button or Cmd+` keyboard shortcut.
    """
    
    MAX_LINES = 500
    PANEL_WIDTH = 300
    ANIMATION_DURATION = 200  # ms
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._visible_width = 0  # For animation
        self._is_open = False
        self._auto_scroll = True
        self._filter_level = logging.DEBUG  # Show all by default
        
        self.setup_ui()
        self.connect_logger()
        
        # Start hidden (zero width)
        self.setFixedWidth(0)
        
    def setup_ui(self):
        """Create console UI."""
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background_dark']};
                border-left: 2px solid {COLORS['border_light']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        
        # Header row
        header = QHBoxLayout()
        header.setSpacing(5)
        
        title = QLabel("CONSOLE")
        title.setFont(QFont(MONO_FONT, FONT_SIZES['label']))
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        header.addWidget(title)
        
        header.addStretch()
        
        # Level filter
        self.level_filter = QComboBox()
        self.level_filter.addItems(["DEBUG", "INFO", "WARN", "ERROR"])
        self.level_filter.setFixedWidth(70)
        self.level_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: {FONT_SIZES['tiny']}px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['border_light']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 16px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {COLORS['text']};
                margin-right: 4px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border_light']};
                selection-background-color: {COLORS['enabled']};
                selection-color: {COLORS['enabled_text']};
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 4px 8px;
                min-height: 20px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {COLORS['background_highlight']};
            }}
        """)
        self.level_filter.currentTextChanged.connect(self.on_filter_changed)
        header.addWidget(self.level_filter)
        
        layout.addLayout(header)
        
        # Log text area
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        self.log_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_text.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['selected']};
            }}
            QScrollBar:vertical {{
                background: {COLORS['background']};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border_light']};
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        layout.addWidget(self.log_text)
        
        # Button row
        buttons = QHBoxLayout()
        buttons.setSpacing(5)
        
        self.auto_scroll_btn = QPushButton("Auto ↓")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.setFixedWidth(55)
        self.auto_scroll_btn.clicked.connect(self.toggle_auto_scroll)
        self.style_button(self.auto_scroll_btn, checked=True)
        buttons.addWidget(self.auto_scroll_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(45)
        clear_btn.clicked.connect(self.clear_log)
        self.style_button(clear_btn)
        buttons.addWidget(clear_btn)
        
        copy_btn = QPushButton("Copy")
        copy_btn.setFixedWidth(45)
        copy_btn.clicked.connect(self.copy_log)
        self.style_button(copy_btn)
        buttons.addWidget(copy_btn)
        
        buttons.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedWidth(25)
        close_btn.clicked.connect(self.hide_panel)
        self.style_button(close_btn)
        buttons.addWidget(close_btn)
        
        layout.addLayout(buttons)
        
    def style_button(self, btn, checked=False):
        """Apply consistent button styling."""
        if checked:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: none;
                    border-radius: 3px;
                    padding: 3px 5px;
                    font-size: {FONT_SIZES['tiny']}px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['enabled_hover']};
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 3px;
                    padding: 3px 5px;
                    font-size: {FONT_SIZES['tiny']}px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['background_highlight']};
                }}
            """)
        
    def connect_logger(self):
        """Connect to the global logger's signal."""
        logger.signal_emitter.log_message.connect(self.on_log_message)
        
    def on_log_message(self, message: str, level: int, timestamp: str):
        """Handle incoming log message."""
        # Check filter
        if level < self._filter_level:
            return
            
        # Format with timestamp and level
        level_name = LOG_LEVEL_NAMES.get(level, "???")
        color = LOG_COLORS.get(level, COLORS['text'])
        
        # Build formatted line
        formatted = f"<span style='color: {COLORS['text_dim']}'>{timestamp}</span> "
        formatted += f"<span style='color: {color}'>[{level_name}]</span> "
        formatted += f"<span style='color: {COLORS['text']}'>{message}</span>"
        
        # Append to log
        self.log_text.appendHtml(formatted)
        
        # Enforce line limit
        doc = self.log_text.document()
        if doc.blockCount() > self.MAX_LINES:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 
                              doc.blockCount() - self.MAX_LINES)
            cursor.removeSelectedText()
            
        # Auto-scroll if enabled
        if self._auto_scroll:
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
            
    def on_filter_changed(self, text: str):
        """Handle filter level change."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARN": logging.WARNING,
            "ERROR": logging.ERROR,
        }
        self._filter_level = level_map.get(text, logging.DEBUG)
        
    def toggle_auto_scroll(self):
        """Toggle auto-scroll behavior."""
        self._auto_scroll = self.auto_scroll_btn.isChecked()
        self.style_button(self.auto_scroll_btn, checked=self._auto_scroll)
        
    def clear_log(self):
        """Clear the log text."""
        self.log_text.clear()
        logger.info("Console cleared", component="UI")
        
    def copy_log(self):
        """Copy log to clipboard."""
        from PyQt5.QtWidgets import QApplication
        text = self.log_text.toPlainText()
        QApplication.clipboard().setText(text)
        logger.info("Log copied to clipboard", component="UI")
        
    # Animation property for width
    def get_visible_width(self):
        return self._visible_width
        
    def set_visible_width(self, width):
        self._visible_width = width
        self.setFixedWidth(int(width))
        
    visible_width = pyqtProperty(float, get_visible_width, set_visible_width)
    
    def show_panel(self):
        """Animate panel open."""
        if self._is_open:
            return
            
        self._is_open = True
        self.show()
        
        self.animation = QPropertyAnimation(self, b"visible_width")
        self.animation.setDuration(self.ANIMATION_DURATION)
        self.animation.setStartValue(0)
        self.animation.setEndValue(self.PANEL_WIDTH)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()
        
        logger.debug("Console opened", component="UI")
        
    def hide_panel(self):
        """Animate panel closed."""
        if not self._is_open:
            return
            
        self._is_open = False
        
        self.animation = QPropertyAnimation(self, b"visible_width")
        self.animation.setDuration(self.ANIMATION_DURATION)
        self.animation.setStartValue(self.PANEL_WIDTH)
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.InCubic)
        self.animation.finished.connect(lambda: self.hide() if not self._is_open else None)
        self.animation.start()
        
        logger.debug("Console closed", component="UI")
        
    def toggle_panel(self):
        """Toggle panel visibility."""
        if self._is_open:
            self.hide_panel()
        else:
            self.show_panel()
            
    @property
    def is_open(self):
        return self._is_open
