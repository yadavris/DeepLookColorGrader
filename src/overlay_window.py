"""
Transparent overlay window that displays bounding boxes around detected colored regions.
Supports click-through mode and interactive selection mode.
"""

import sys
import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QPainterPath, QCursor
)
from src.color_analyzer import ColorRegion


class OverlayWindow(QWidget):
    """Always-on-top transparent overlay for drawing bounding boxes."""

    # Signals
    region_selected = pyqtSignal(int)  # Emits index of selected region
    regions_updated = pyqtSignal(list)  # Emits list of ColorRegion objects
    toggle_mode = pyqtSignal()  # Emits when user toggles click-through/interactive

    def __init__(self, screen_geometry, parent=None):
        super().__init__(parent)

        self._screen_geometry = screen_geometry
        self._regions: list[ColorRegion] = []
        self._selected_index: int = -1
        self._hover_index: int = -1
        self._interactive_mode: bool = False
        self._show_labels: bool = True

        # Drag state for moving/resizing
        self._dragging: bool = False
        self._drag_start: QPoint = QPoint()
        self._drag_region_start: QRect = QRect()
        self._resizing: bool = False
        self._resize_handle: int = -1  # 0=move, 1-8=resize handles

        # Animation
        self._pulse_phase: float = 0.0

        self._setup_window()
        self._setup_animation()

    def _setup_window(self):
        """Configure the overlay window flags and attributes."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |  # Don't show in taskbar
            Qt.WindowType.WindowTransparentForInput  # Click-through by default
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Cover the entire virtual screen
        self.setGeometry(
            self._screen_geometry["left"],
            self._screen_geometry["top"],
            self._screen_geometry["width"],
            self._screen_geometry["height"],
        )

    def _setup_animation(self):
        """Set up the pulse animation timer."""
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(50)  # 20 FPS animation

    def _animate(self):
        """Update animation phase and repaint."""
        self._pulse_phase = (self._pulse_phase + 0.08) % (2 * 3.14159)
        self.update()

    def set_regions(self, regions: list[ColorRegion]):
        """Update the detected regions and repaint."""
        self._regions = regions
        if self._selected_index >= len(regions):
            self._selected_index = -1
        self.regions_updated.emit(regions)
        self.update()

    def set_interactive(self, interactive: bool):
        """Toggle between click-through and interactive mode."""
        self._interactive_mode = interactive
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not interactive)
        if interactive:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def get_selected_region(self) -> ColorRegion | None:
        """Return the currently selected region, or None."""
        if 0 <= self._selected_index < len(self._regions):
            return self._regions[self._selected_index]
        return None

    def select_region_by_index(self, index: int):
        """Programmatically select a region by index."""
        if 0 <= index < len(self._regions):
            self._selected_index = index
            self.region_selected.emit(index)
            self.update()

    def cycle_selection(self):
        """Cycle to the next region."""
        if not self._regions:
            return
        self._selected_index = (self._selected_index + 1) % len(self._regions)
        self.region_selected.emit(self._selected_index)
        self.update()

    def paintEvent(self, event):
        """Draw bounding boxes for all detected regions."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i, region in enumerate(self._regions):
            is_selected = (i == self._selected_index)
            is_hovered = (i == self._hover_index)
            self._draw_region(painter, region, is_selected, is_hovered, i)

        painter.end()

    def _draw_region(self, painter: QPainter, region: ColorRegion,
                     is_selected: bool, is_hovered: bool, index: int):
        """Draw a single bounding box with labels."""
        x, y = region.x, region.y if hasattr(region, 'y') else region.top
        w, h = region.width, region.height

        # Pulsing glow for selected region
        if is_selected:
            glow_alpha = int(80 + 40 * abs(math.sin(self._pulse_phase)))
            glow_pen = QPen(QColor(0, 180, 255, glow_alpha), 8)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(x - 4, y - 4, w + 8, h + 8, 6, 6)

        # Main bounding box
        if is_selected:
            pen = QPen(QColor(0, 150, 255), 3)
        elif is_hovered:
            pen = QPen(QColor(100, 200, 255), 2, Qt.PenStyle.DashLine)
        else:
            pen = QPen(QColor(0, 120, 255), 2)

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(x, y, w, h, 4, 4)

        # Corner accents for selected
        if is_selected:
            self._draw_corner_accents(painter, x, y, w, h)

        # Resize handles for selected
        if is_selected and self._interactive_mode:
            self._draw_resize_handles(painter, x, y, w, h)

        # Label
        if self._show_labels:
            self._draw_label(painter, region, x, y, w, h, index, is_selected)

        # Semi-transparent fill for selected
        if is_selected:
            fill_color = QColor(0, 150, 255, 15)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill_color)
            painter.drawRoundedRect(x, y, w, h, 4, 4)

    def _draw_corner_accents(self, painter: QPainter, x: int, y: int, w: int, h: int):
        """Draw accent marks at corners of selected region."""
        accent_pen = QPen(QColor(0, 200, 255), 4)
        painter.setPen(accent_pen)
        length = 15

        # Top-left
        painter.drawLine(x, y, x + length, y)
        painter.drawLine(x, y, x, y + length)

        # Top-right
        painter.drawLine(x + w, y, x + w - length, y)
        painter.drawLine(x + w, y, x + w, y + length)

        # Bottom-left
        painter.drawLine(x, y + h, x + length, y + h)
        painter.drawLine(x, y + h, x, y + h - length)

        # Bottom-right
        painter.drawLine(x + w, y + h, x + w - length, y + h)
        painter.drawLine(x + w, y + h, x + w, y + h - length)

    def _draw_resize_handles(self, painter: QPainter, x: int, y: int, w: int, h: int):
        """Draw resize handles on the bounding box."""
        handle_size = 8
        painter.setPen(QPen(QColor(0, 150, 255), 1))
        painter.setBrush(QColor(0, 150, 255))

        positions = [
            (x - handle_size//2, y - handle_size//2),                    # Top-left
            (x + w//2 - handle_size//2, y - handle_size//2),            # Top-center
            (x + w - handle_size//2, y - handle_size//2),               # Top-right
            (x + w - handle_size//2, y + h//2 - handle_size//2),        # Right-center
            (x + w - handle_size//2, y + h - handle_size//2),           # Bottom-right
            (x + w//2 - handle_size//2, y + h - handle_size//2),        # Bottom-center
            (x - handle_size//2, y + h - handle_size//2),               # Bottom-left
            (x - handle_size//2, y + h//2 - handle_size//2),            # Left-center
        ]

        for px, py in positions:
            painter.drawRect(px, py, handle_size, handle_size)

    def _draw_label(self, painter: QPainter, region: ColorRegion,
                    x: int, y: int, w: int, h: int, index: int, is_selected: bool):
        """Draw a label above the bounding box."""
        label = f"Region {index + 1}"
        if region.color_distribution:
            dominant = region.color_distribution.get("dominant_color", "")
            if dominant:
                label += f" — {dominant}"

        font = QFont("Segoe UI", 9, QFont.Weight.Bold if is_selected else QFont.Weight.Normal)
        painter.setFont(font)

        # Measure text
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(label) + 16
        text_height = metrics.height() + 8

        # Position above the box, or below if too close to top
        label_x = x
        label_y = y - text_height - 4
        if label_y < 0:
            label_y = y + h + 4

        # Background
        bg_color = QColor(0, 120, 255, 200) if is_selected else QColor(0, 0, 0, 160)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(label_x, label_y, text_width, text_height, 4, 4)

        # Text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(label_x + 8, label_y + text_height - 6, label)

    def _get_handle_at_pos(self, pos: QPoint, region: ColorRegion) -> int:
        """Check if position is on a resize handle. Returns handle index or -1."""
        x, y = region.x, region.top
        w, h = region.width, region.height
        hs = 12  # Hit test size

        handles = [
            (x, y, 1), (x + w//2, y, 2), (x + w, y, 3),
            (x + w, y + h//2, 4), (x + w, y + h, 5),
            (x + w//2, y + h, 6), (x, y + h, 7), (x, y + h//2, 8),
        ]

        for hx, hy, idx in handles:
            if abs(pos.x() - hx) <= hs and abs(pos.y() - hy) <= hs:
                return idx

        # Check if inside region for move
        if x <= pos.x() <= x + w and y <= pos.y() <= y + h:
            return 0

        return -1

    def mousePressEvent(self, event):
        """Handle mouse press for region selection and manipulation."""
        if not self._interactive_mode:
            return

        pos = event.pos()

        # Check if clicking on a region
        for i, region in enumerate(self._regions):
            handle = self._get_handle_at_pos(pos, region)
            if handle >= 0:
                self._selected_index = i
                self._drag_start = pos
                self._drag_region_start = QRect(region.x, region.top, region.width, region.height)

                if handle == 0:
                    self._dragging = True
                    self._resizing = False
                else:
                    self._resizing = True
                    self._dragging = False
                    self._resize_handle = handle

                self.region_selected.emit(i)
                self.update()
                return

        # Click on empty space deselects
        self._selected_index = -1
        self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move for hover effects and dragging."""
        pos = event.pos()

        if self._dragging and self._selected_index >= 0:
            delta = pos - self._drag_start
            region = self._regions[self._selected_index]
            region.x = self._drag_region_start.x() + delta.x()
            region.top = self._drag_region_start.y() + delta.y()
            self.update()
            return

        if self._resizing and self._selected_index >= 0:
            delta = pos - self._drag_start
            region = self._regions[self._selected_index]
            rect = QRect(self._drag_region_start)

            # Apply resize based on handle
            if self._resize_handle in (1, 2, 3):
                rect.setTop(rect.top() + delta.y())
            if self._resize_handle in (3, 4, 5):
                rect.setRight(rect.right() + delta.x())
            if self._resize_handle in (5, 6, 7):
                rect.setBottom(rect.bottom() + delta.y())
            if self._resize_handle in (7, 8, 1):
                rect.setLeft(rect.left() + delta.x())

            region.x = rect.x()
            region.top = rect.y()
            region.width = max(20, rect.width())
            region.height = max(20, rect.height())
            self.update()
            return

        # Hover detection
        old_hover = self._hover_index
        self._hover_index = -1
        for i, region in enumerate(self._regions):
            if (region.x <= pos.x() <= region.x + region.width and
                    region.top <= pos.y() <= region.top + region.height):
                self._hover_index = i
                break

        if old_hover != self._hover_index:
            self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        self._dragging = False
        self._resizing = False
        self._resize_handle = -1

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        key = event.key()

        if key == Qt.Key.Key_Tab:
            self.cycle_selection()
        elif key == Qt.Key.Key_Escape:
            self._selected_index = -1
            self.update()
        elif key == Qt.Key.Key_I:
            self.toggle_mode.emit()
        elif key == Qt.Key.Key_V:
            self._show_labels = not self._show_labels
            self.update()
