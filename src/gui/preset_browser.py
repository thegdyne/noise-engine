"""
Preset Browser Panel - R1.1

Dockable browser for preset management with:
- Recent presets list
- All presets list with search
- Rating (0-5 stars)
- Operations: Load, Save As, Duplicate, Rename, Delete
"""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Callable, List
import os
import unicodedata

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QFrame, QMessageBox,
    QInputDialog, QFileDialog, QSplitter, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from .theme import COLORS, FONT_FAMILY, FONT_SIZES, button_style
from src.presets.preset_schema import PresetState
from src.presets.preset_manager import PresetManager, PresetError
from src.presets.preset_utils import (
    TimestampProvider, canonical_path,
    RecentsManager, get_recents_manager, RecentPresetEntry
)


# =============================================================================
# OPERATION TYPES AND CONTEXT
# =============================================================================

class OperationType(Enum):
    LOADING = auto()
    SAVING_AS = auto()
    DUPLICATING = auto()
    RENAMING = auto()
    DELETING = auto()
    RATING_WRITE = auto()


@dataclass
class OperationContext:
    """Context for an in-progress operation."""
    operation_timestamp: str
    target_path: Optional[str]  # Canonical path or None
    selection_invalidated: bool


# =============================================================================
# STAR RATING WIDGET
# =============================================================================

class StarRating(QWidget):
    """Clickable star rating widget (0-5 stars)."""

    rating_changed = pyqtSignal(int)  # Emits new rating

    def __init__(self, rating: int = 0, parent=None):
        super().__init__(parent)
        self._rating = max(0, min(5, rating))
        self._enabled = True
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._star_buttons = []
        for i in range(5):
            btn = QPushButton()
            btn.setFixedSize(16, 16)
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i+1: self._on_star_clicked(idx))
            self._star_buttons.append(btn)
            layout.addWidget(btn)

        self._update_stars()

    def _update_stars(self):
        """Update star button appearances."""
        for i, btn in enumerate(self._star_buttons):
            star_num = i + 1
            if star_num <= self._rating:
                btn.setText("★")
                btn.setStyleSheet(f"color: #ffd700; font-size: 14px; border: none;")
            else:
                btn.setText("☆")
                btn.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 14px; border: none;")
            btn.setEnabled(self._enabled)

    def _on_star_clicked(self, star_num: int):
        """Handle star click per R1.1 spec."""
        if not self._enabled:
            return

        # Click semantics per spec
        if self._rating == 0:
            # Current 0, click M → rating = M
            new_rating = star_num
        elif self._rating == star_num:
            # Current N, click N → rating = 0
            new_rating = 0
        else:
            # Current N, click M (M≠N) → rating = M
            new_rating = star_num

        self._rating = new_rating
        self._update_stars()
        self.rating_changed.emit(new_rating)

    def set_rating(self, rating: int):
        """Set rating programmatically."""
        self._rating = max(0, min(5, rating))
        self._update_stars()

    def rating(self) -> int:
        return self._rating

    def set_enabled(self, enabled: bool):
        """Enable/disable the widget."""
        self._enabled = enabled
        self._update_stars()


# =============================================================================
# PRESET LIST ITEM
# =============================================================================

class PresetListItem(QListWidgetItem):
    """List item for a preset with metadata."""

    def __init__(self, path: str, name: str, rating: int = 0, updated: str = ""):
        super().__init__()
        self.preset_path = path  # Canonical path
        self.preset_name = name
        self.preset_rating = rating
        self.preset_updated = updated
        self.setText(name)


# =============================================================================
# PRESET BROWSER PANEL
# =============================================================================

class PresetBrowser(QWidget):
    """
    Dockable preset browser panel.

    Signals:
        preset_load_requested: Emitted when user wants to load a preset
        preset_save_requested: Emitted when user wants to save current state
    """

    preset_load_requested = pyqtSignal(str)  # Canonical path
    preset_save_requested = pyqtSignal(str, str)  # dest_path, name

    def __init__(self, preset_manager: PresetManager, parent=None):
        super().__init__(parent)
        self.preset_manager = preset_manager
        self.recents_manager = get_recents_manager()

        # State
        self._operation_in_progress: Optional[OperationType] = None
        self._operation_ctx: Optional[OperationContext] = None
        self._selected_preset_path: Optional[str] = None
        self._all_presets: List[tuple] = []  # [(canon_path, name, rating, updated)]

        self._setup_ui()
        self._refresh_lists()

    def _setup_ui(self):
        """Build the browser UI."""
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header = QLabel("PRESET BROWSER")
        header.setFont(QFont(FONT_FAMILY, FONT_SIZES['section'], QFont.Bold))
        header.setStyleSheet(f"color: {COLORS['text_bright']};")
        layout.addWidget(header)

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_dim']};
                border: none;
                font-size: 18px;
            }}
            QPushButton:hover {{
                color: {COLORS['text_bright']};
            }}
        """)
        close_btn.clicked.connect(self.hide)

        header_layout = QHBoxLayout()
        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)

        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        layout.insertWidget(0, header_widget)

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Filter presets...")
        self._search_box.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['background_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                padding: 4px;
            }}
        """)
        self._search_box.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self._search_box)
        layout.addLayout(search_layout)

        # Recents section
        recents_label = QLabel("RECENT")
        recents_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
        recents_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        layout.addWidget(recents_label)

        self._recents_list = QListWidget()
        self._recents_list.setMaximumHeight(120)
        self._recents_list.setStyleSheet(self._list_style())
        self._recents_list.itemDoubleClicked.connect(self._on_recent_double_clicked)
        self._recents_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._recents_list)

        # All presets section
        all_label = QLabel("ALL PRESETS")
        all_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
        all_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        layout.addWidget(all_label)

        self._all_list = QListWidget()
        self._all_list.setStyleSheet(self._list_style())
        self._all_list.itemDoubleClicked.connect(self._on_preset_double_clicked)
        self._all_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._all_list, 1)

        # Rating display/edit
        rating_layout = QHBoxLayout()
        rating_label = QLabel("Rating:")
        rating_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        self._rating_widget = StarRating(0)
        self._rating_widget.rating_changed.connect(self._on_rating_changed)
        rating_layout.addWidget(rating_label)
        rating_layout.addWidget(self._rating_widget)
        rating_layout.addStretch()
        layout.addLayout(rating_layout)

        # Action buttons
        btn_layout = QHBoxLayout()

        self._load_btn = QPushButton("Load")
        self._load_btn.clicked.connect(self._on_load_clicked)
        self._load_btn.setStyleSheet(button_style('enabled'))

        self._save_as_btn = QPushButton("Save As")
        self._save_as_btn.clicked.connect(self._on_save_as_clicked)
        self._save_as_btn.setStyleSheet(button_style('enabled'))

        btn_layout.addWidget(self._load_btn)
        btn_layout.addWidget(self._save_as_btn)
        layout.addLayout(btn_layout)

        btn_layout2 = QHBoxLayout()

        self._duplicate_btn = QPushButton("Duplicate")
        self._duplicate_btn.clicked.connect(self._on_duplicate_clicked)
        self._duplicate_btn.setStyleSheet(button_style('disabled'))

        self._rename_btn = QPushButton("Rename")
        self._rename_btn.clicked.connect(self._on_rename_clicked)
        self._rename_btn.setStyleSheet(button_style('disabled'))

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        self._delete_btn.setStyleSheet(button_style('warning'))

        btn_layout2.addWidget(self._duplicate_btn)
        btn_layout2.addWidget(self._rename_btn)
        btn_layout2.addWidget(self._delete_btn)
        layout.addLayout(btn_layout2)

        self._update_button_states()

    def _list_style(self) -> str:
        """Common list widget style."""
        return f"""
            QListWidget {{
                background: {COLORS['background_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
            }}
            QListWidget::item {{
                padding: 4px;
            }}
            QListWidget::item:selected {{
                background: {COLORS['selected']};
                color: {COLORS['selected_text']};
            }}
            QListWidget::item:hover {{
                background: {COLORS['background_highlight']};
            }}
        """

    def _update_button_states(self):
        """Update button enabled states based on selection."""
        has_selection = self._selected_preset_path is not None
        in_operation = self._operation_in_progress is not None

        self._load_btn.setEnabled(has_selection and not in_operation)
        self._save_as_btn.setEnabled(not in_operation)
        self._duplicate_btn.setEnabled(has_selection and not in_operation)
        self._rename_btn.setEnabled(has_selection and not in_operation)
        self._delete_btn.setEnabled(has_selection and not in_operation)
        self._rating_widget.set_enabled(has_selection and not in_operation)

        # Update visual styles
        self._duplicate_btn.setStyleSheet(
            button_style('enabled' if has_selection and not in_operation else 'disabled')
        )
        self._rename_btn.setStyleSheet(
            button_style('enabled' if has_selection and not in_operation else 'disabled')
        )

    def _refresh_lists(self):
        """Refresh both recents and all presets lists."""
        self._refresh_recents()
        self._refresh_all_presets()
        self._apply_search_filter()

    def _refresh_recents(self):
        """Refresh the recents list."""
        self._recents_list.clear()
        recents = self.recents_manager.load()

        for entry in recents:
            item = PresetListItem(
                path=entry.path,
                name=entry.name,
                rating=0,
                updated=entry.last_used
            )
            self._recents_list.addItem(item)

    def _refresh_all_presets(self):
        """Refresh the all presets list from disk."""
        self._all_presets = []

        # Scan preset directory
        preset_dir = self.preset_manager.presets_dir
        if not preset_dir.exists():
            return

        for file_path in preset_dir.glob("*.json"):
            try:
                # Check for orphan placeholder (0-byte file)
                if file_path.stat().st_size == 0:
                    # Per spec: attempt best-effort deletion once per session
                    canon = canonical_path(str(file_path))
                    if not self.recents_manager.has_placeholder_deletion_failed(canon):
                        try:
                            file_path.unlink()
                        except OSError:
                            self.recents_manager.mark_placeholder_deletion_failed(canon)
                    continue

                # Load preset metadata
                state = self.preset_manager.load(file_path)
                canon = canonical_path(str(file_path))
                self._all_presets.append((
                    canon,
                    state.name,
                    state.rating,
                    state.updated
                ))
            except (PresetError, OSError):
                # Skip unreadable presets
                continue

        # Sort by updated date descending (default DATE_DESC)
        self._all_presets.sort(key=lambda x: x[3] or "", reverse=True)

    def _apply_search_filter(self):
        """Apply search filter to all presets list."""
        self._all_list.clear()

        # Normalize search query
        query = self._search_box.text()
        q = unicodedata.normalize("NFC", query).casefold().strip()

        for canon, name, rating, updated in self._all_presets:
            # Match rule: empty query or substring match
            name_norm = unicodedata.normalize("NFC", name).casefold()
            if not q or q in name_norm:
                item = PresetListItem(
                    path=canon,
                    name=name,
                    rating=rating,
                    updated=updated
                )
                self._all_list.addItem(item)

        # Restore selection if target exists
        if self._selected_preset_path:
            for i in range(self._all_list.count()):
                item = self._all_list.item(i)
                if isinstance(item, PresetListItem) and item.preset_path == self._selected_preset_path:
                    self._all_list.setCurrentItem(item)
                    break

    def _on_search_changed(self, text: str):
        """Handle search text change."""
        self._apply_search_filter()

    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle item selection."""
        if self._operation_in_progress:
            return

        if isinstance(item, PresetListItem):
            self._selected_preset_path = item.preset_path
            self._rating_widget.set_rating(item.preset_rating)

            # Sync selection between lists
            sender = self.sender()
            if sender == self._recents_list:
                self._all_list.clearSelection()
            else:
                self._recents_list.clearSelection()

            self._update_button_states()

    def _on_recent_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on recent preset."""
        if isinstance(item, PresetListItem):
            self._load_preset(item.preset_path)

    def _on_preset_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on preset."""
        if isinstance(item, PresetListItem):
            self._load_preset(item.preset_path)

    def _on_load_clicked(self):
        """Handle Load button click."""
        if self._selected_preset_path:
            self._load_preset(self._selected_preset_path)

    def _load_preset(self, file_path: str):
        """Load a preset file."""
        if self._operation_in_progress:
            return

        # Create operation context
        op_timestamp = TimestampProvider.now()
        self._operation_ctx = OperationContext(
            operation_timestamp=op_timestamp,
            target_path=canonical_path(file_path),
            selection_invalidated=False
        )
        self._operation_in_progress = OperationType.LOADING
        self._update_button_states()

        try:
            # Emit signal for main frame to handle actual load
            self.preset_load_requested.emit(file_path)

            # Record in recents (best-effort)
            try:
                state = self.preset_manager.load(Path(file_path))
                self.recents_manager.record_use(
                    file_path,
                    state.name,
                    op_timestamp
                )
            except (PresetError, OSError):
                pass  # Non-fatal recents failure

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load preset:\n{e}")

        finally:
            self._operation_in_progress = None
            self._operation_ctx = None
            self._refresh_lists()
            self._update_button_states()

    def _on_save_as_clicked(self):
        """Handle Save As button click."""
        if self._operation_in_progress:
            return

        # Show file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Preset As",
            str(self.preset_manager.presets_dir),
            "JSON Files (*.json)"
        )

        if not file_path:
            return

        # Ensure .json extension
        if not file_path.endswith('.json'):
            file_path += '.json'

        # Create operation context
        op_timestamp = TimestampProvider.now()
        self._operation_ctx = OperationContext(
            operation_timestamp=op_timestamp,
            target_path=canonical_path(file_path),
            selection_invalidated=False
        )
        self._operation_in_progress = OperationType.SAVING_AS
        self._update_button_states()

        try:
            # Get preset name from filename
            name = Path(file_path).stem

            # Emit signal for main frame to handle save
            self.preset_save_requested.emit(file_path, name)

        finally:
            self._operation_in_progress = None
            self._selected_preset_path = self._operation_ctx.target_path
            self._operation_ctx = None
            self._refresh_lists()
            self._update_button_states()

    def _on_duplicate_clicked(self):
        """Handle Duplicate button click."""
        if self._operation_in_progress or not self._selected_preset_path:
            return

        source_path = Path(self._selected_preset_path)
        if not source_path.exists():
            QMessageBox.warning(self, "Error", "Selected preset no longer exists.")
            self._refresh_lists()
            return

        # Determine non-colliding duplicate name
        base_name = source_path.stem
        dest_path = source_path.parent / f"{base_name} Copy.json"
        counter = 2
        while dest_path.exists():
            dest_path = source_path.parent / f"{base_name} Copy {counter}.json"
            counter += 1

        # Create operation context
        op_timestamp = TimestampProvider.now()
        self._operation_ctx = OperationContext(
            operation_timestamp=op_timestamp,
            target_path=canonical_path(str(dest_path)),
            selection_invalidated=False
        )
        self._operation_in_progress = OperationType.DUPLICATING
        self._update_button_states()

        try:
            # Load source preset
            state = self.preset_manager.load(source_path)

            # Apply timestamp rules
            self.preset_manager.apply_timestamps(state, op_timestamp)

            # Update name
            state.name = dest_path.stem

            # Write duplicate (allow_overwrite=False per spec)
            self.preset_manager.write_preset_file(
                dest_path, state, allow_overwrite=False
            )

            # Record in recents (best-effort)
            self.recents_manager.record_use(
                str(dest_path),
                state.name,
                op_timestamp
            )

            self._selected_preset_path = self._operation_ctx.target_path

        except PresetError as e:
            QMessageBox.critical(self, "Duplicate Error", f"Failed to duplicate preset:\n{e}")

        finally:
            self._operation_in_progress = None
            self._operation_ctx = None
            self._refresh_lists()
            self._update_button_states()

    def _on_rename_clicked(self):
        """Handle Rename button click."""
        if self._operation_in_progress or not self._selected_preset_path:
            return

        old_path = Path(self._selected_preset_path)
        if not old_path.exists():
            QMessageBox.warning(self, "Error", "Selected preset no longer exists.")
            self._refresh_lists()
            return

        # Get new name from user
        current_name = old_path.stem
        new_name, ok = QInputDialog.getText(
            self, "Rename Preset",
            "Enter new name:",
            QLineEdit.Normal,
            current_name
        )

        if not ok or not new_name or new_name == current_name:
            return

        # Sanitize and compute new path
        new_name = self.preset_manager._sanitize_filename(new_name)
        new_path = old_path.parent / f"{new_name}.json"

        # Create operation context
        op_timestamp = TimestampProvider.now()
        self._operation_ctx = OperationContext(
            operation_timestamp=op_timestamp,
            target_path=canonical_path(str(new_path)),
            selection_invalidated=True
        )
        self._operation_in_progress = OperationType.RENAMING
        self._update_button_states()

        try:
            # Check if destination exists (no clobber)
            if new_path.exists():
                QMessageBox.warning(
                    self, "Rename Error",
                    f"A preset named '{new_name}' already exists."
                )
                return

            # Create exclusive placeholder per spec
            try:
                fd = os.open(str(new_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                os.close(fd)
            except FileExistsError:
                QMessageBox.warning(
                    self, "Rename Error",
                    "Destination already exists."
                )
                return
            except OSError as e:
                QMessageBox.critical(
                    self, "Rename Error",
                    f"Failed to reserve destination:\n{e}"
                )
                return

            try:
                # Load preset
                state = self.preset_manager.load(old_path)
                old_display_name = state.name

                # Update state
                state.name = new_name
                self.preset_manager.apply_timestamps(state, op_timestamp)

                # Write to new path (overwrite placeholder)
                self.preset_manager.write_preset_file(
                    new_path, state, allow_overwrite=True
                )

                # Delete old file
                delete_outcome = "DELETED"
                try:
                    old_path.unlink()
                except FileNotFoundError:
                    delete_outcome = "ALREADY_MISSING"
                except OSError:
                    delete_outcome = "FAILED"

                # Handle deletion failure with user resolution
                if delete_outcome == "FAILED":
                    result = QMessageBox.warning(
                        self,
                        "Rename Incomplete",
                        "The new preset was created, but the original could not be removed.\n\n"
                        "Choose how to proceed:",
                        QMessageBox.Retry | QMessageBox.Ignore | QMessageBox.Abort,
                        QMessageBox.Retry
                    )

                    if result == QMessageBox.Retry:
                        try:
                            old_path.unlink()
                            delete_outcome = "DELETED"
                        except OSError:
                            delete_outcome = "FAILED"
                    elif result == QMessageBox.Abort:
                        # Rollback: delete new file
                        try:
                            new_path.unlink()
                            self._refresh_lists()
                            return
                        except OSError:
                            QMessageBox.critical(
                                self, "Rollback Failed",
                                "Could not remove the new file. Both files may exist."
                            )

                # Update recents
                old_canon = canonical_path(str(old_path))
                new_canon = canonical_path(str(new_path))

                if delete_outcome in ("DELETED", "ALREADY_MISSING"):
                    self.recents_manager.remove(old_canon)
                    self.recents_manager.record_use(new_canon, new_name, op_timestamp)
                else:
                    # Keep both per spec
                    self.recents_manager.record_use(new_canon, new_name, op_timestamp)

                self._selected_preset_path = new_canon

            except PresetError as e:
                # Clean up placeholder
                try:
                    new_path.unlink()
                except OSError:
                    pass
                raise e

        except PresetError as e:
            QMessageBox.critical(self, "Rename Error", f"Failed to rename preset:\n{e}")
            self._selected_preset_path = None

        finally:
            self._operation_in_progress = None
            self._operation_ctx = None
            self._refresh_lists()
            self._update_button_states()

    def _on_delete_clicked(self):
        """Handle Delete button click."""
        if self._operation_in_progress or not self._selected_preset_path:
            return

        file_path = Path(self._selected_preset_path)

        # Confirmation dialog
        result = QMessageBox.question(
            self,
            "Delete Preset",
            f"Are you sure you want to delete '{file_path.stem}'?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result != QMessageBox.Yes:
            return

        # Create operation context
        op_timestamp = TimestampProvider.now()
        self._operation_ctx = OperationContext(
            operation_timestamp=op_timestamp,
            target_path=None,  # Per spec: Delete sets target_path to null
            selection_invalidated=True
        )
        self._operation_in_progress = OperationType.DELETING
        self._update_button_states()

        try:
            # Delete file
            if file_path.exists():
                file_path.unlink()

            # Remove from recents
            self.recents_manager.remove(self._selected_preset_path)

            self._selected_preset_path = None

        except OSError as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to delete preset:\n{e}")

        finally:
            self._operation_in_progress = None
            self._operation_ctx = None
            self._refresh_lists()
            self._update_button_states()

    def _on_rating_changed(self, new_rating: int):
        """Handle rating change from star widget."""
        if self._operation_in_progress or not self._selected_preset_path:
            return

        file_path = Path(self._selected_preset_path)
        if not file_path.exists():
            QMessageBox.warning(self, "Error", "Preset moved or deleted.")
            self._refresh_lists()
            return

        # Create operation context
        op_timestamp = TimestampProvider.now()
        self._operation_ctx = OperationContext(
            operation_timestamp=op_timestamp,
            target_path=self._selected_preset_path,
            selection_invalidated=False
        )
        self._operation_in_progress = OperationType.RATING_WRITE
        self._update_button_states()

        try:
            # Load preset
            state = self.preset_manager.load(file_path)

            # Update rating and timestamps
            state.rating = new_rating
            self.preset_manager.apply_timestamps(state, op_timestamp)

            # Write back (overwrite allowed for rating)
            self.preset_manager.write_preset_file(
                file_path, state, allow_overwrite=True
            )

        except PresetError as e:
            QMessageBox.critical(self, "Rating Error", f"Failed to save rating:\n{e}")

        finally:
            self._operation_in_progress = None
            self._operation_ctx = None
            self._refresh_lists()
            self._update_button_states()
