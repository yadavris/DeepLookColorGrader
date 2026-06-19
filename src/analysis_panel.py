"""
Color analysis panel — a separate GUI window that displays detailed
color grading analysis for a selected region.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QProgressBar, QGroupBox, QGridLayout,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QFont, QPen, QBrush, QPixmap, QImage

import numpy as np
import cv2


class ColorBar(QWidget):
    """A horizontal bar showing a color with its percentage."""

    def __init__(self, name, percentage, bgr_color, parent=None):
        super().__init__(parent)
        self._name = name
        self._percentage = percentage
        self._bgr = bgr_color
        self.setMinimumHeight(36)
        self.setMaximumHeight(40)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(40, 40, 40))

        # Color fill
        fill_width = int(w * self._percentage / 100.0)
        r, g, b = self._bgr[2], self._bgr[1], self._bgr[0]  # BGR to RGB
        painter.fillRect(0, 0, fill_width, h, QColor(r, g, b))

        # Border
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        # Text
        text = f"  {self._name}  {self._percentage:.1f}%"
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(8, h - 10, text)

        painter.end()


class ColorWheelWidget(QWidget):
    """A simple color wheel visualization showing the hue distribution."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._analysis = None
        self.setMinimumSize(200, 200)
        self.setMaximumSize(250, 250)

    def set_analysis(self, analysis: dict):
        self._analysis = analysis
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        cx, cy = w // 2, h // 2
        radius = min(cx, cy) - 10

        # Background circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 30, 30))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        if not self._analysis or not self._analysis.get("colors"):
            painter.setPen(QColor(100, 100, 100))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(0, cy - 10, w, 20, Qt.AlignmentFlag.AlignCenter, "No color data")
            painter.end()
            return

        # Draw color arcs
        colors = self._analysis["colors"]
        total_pct = sum(c["percentage"] for c in colors)
        if total_pct == 0:
            total_pct = 1

        start_angle = 0
        for color_info in colors:
            sweep = int((color_info["percentage"] / total_pct) * 360)
            bgr = color_info["bgr"]
            qcolor = QColor(bgr[2], bgr[1], bgr[0])

            painter.setPen(QPen(qcolor, 12))
            painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2,
                            start_angle * 16, sweep * 16)
            start_angle += sweep

        # Center hole
        inner_r = radius // 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(25, 25, 25))
        painter.drawEllipse(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)

        # Center text
        dominant = self._analysis.get("dominant_color", "—")
        painter.setPen(QColor(220, 220, 220))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(cx - inner_r, cy - 10, inner_r * 2, 20,
                         Qt.AlignmentFlag.AlignCenter, dominant)

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(cx - inner_r, cy + 5, inner_r * 2, 20,
                         Qt.AlignmentFlag.AlignCenter, "Dominant")

        painter.end()


class HistogramWidget(QWidget):
    """RGB histogram visualization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = None
        self.setMinimumHeight(120)
        self.setMaximumHeight(160)

    def set_image(self, bgr_image: np.ndarray):
        self._image = bgr_image
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(30, 30, 30))

        if self._image is None or self._image.size == 0:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(0, h // 2 - 10, w, 20, Qt.AlignmentFlag.AlignCenter, "No image")
            painter.end()
            return

        # Calculate histograms
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # BGR
        labels = ["B", "G", "R"]
        margin = 5
        graph_h = h - 20
        graph_w = w - 2 * margin

        for idx, (bgr, label) in enumerate(zip(colors, labels)):
            hist = cv2.calcHist([self._image], [idx], None, [256], [0, 256])
            cv2.normalize(hist, hist, 0, graph_h, cv2.NORM_MINMAX)

            # Draw filled path
            path = QPainterPath()
            path.moveTo(margin, h - 5)

            for i in range(256):
                x = margin + int(i / 256.0 * graph_w)
                y = h - 5 - int(hist[i])
                path.lineTo(x, y)

            path.lineTo(margin + graph_w, h - 5)
            path.closeSubpath()

            qcolor = QColor(bgr[2], bgr[1], bgr[0], 80)
            painter.setPen(QPen(QColor(bgr[2], bgr[1], bgr[0]), 1.5))
            painter.setBrush(qcolor)
            painter.drawPath(path)

        # Border
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, w - 1, h - 1)

        painter.end()


class AnalysisPanel(QWidget):
    """Main analysis panel window."""

    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._analysis = None
        self._region_image = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the analysis panel UI."""
        self.setWindowTitle("DeepLook Color Analysis")
        self.setMinimumSize(480, 600)
        self.resize(520, 700)

        # Dark theme
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
                font-weight: bold;
                font-size: 12px;
                color: #88ccff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QLabel {
                color: #c0c0c0;
                font-size: 11px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header = QLabel("🎨 Color Grading Analysis")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #ffffff; margin-bottom: 4px;")
        main_layout.addWidget(header)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Region preview
        preview_group = QGroupBox("Selected Region")
        preview_layout = QVBoxLayout(preview_group)
        self._preview_label = QLabel("No region selected")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumHeight(100)
        self._preview_label.setMaximumHeight(150)
        self._preview_label.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
        preview_layout.addWidget(self._preview_label)
        content_layout.addWidget(preview_group)

        # Color wheel + stats row
        wheel_row = QHBoxLayout()

        wheel_group = QGroupBox("Hue Distribution")
        wheel_layout = QVBoxLayout(wheel_group)
        self._color_wheel = ColorWheelWidget()
        wheel_layout.addWidget(self._color_wheel, alignment=Qt.AlignmentFlag.AlignCenter)
        wheel_row.addWidget(wheel_group)

        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout(stats_group)
        stats_layout.setVerticalSpacing(6)

        self._stat_labels = {}
        stat_names = [
            ("Dominant", "dominant_color"),
            ("Brightness", "brightness"),
            ("Saturation", "saturation"),
            ("Colorfulness", "colorfulness"),
            ("Neutral %", "neutral_pct"),
            ("Colored Pixels", "colored_pixels"),
        ]

        for row, (label, key) in enumerate(stat_names):
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet("color: #888;")
            val = QLabel("—")
            val.setStyleSheet("color: #fff; font-weight: bold;")
            stats_layout.addWidget(lbl, row, 0)
            stats_layout.addWidget(val, row, 1)
            self._stat_labels[key] = val

        wheel_row.addWidget(stats_group)
        content_layout.addLayout(wheel_row)

        # Histogram
        hist_group = QGroupBox("RGB Histogram")
        hist_layout = QVBoxLayout(hist_group)
        self._histogram = HistogramWidget()
        hist_layout.addWidget(self._histogram)
        content_layout.addWidget(hist_group)

        # Color breakdown
        breakdown_group = QGroupBox("Color Breakdown")
        self._breakdown_layout = QVBoxLayout(breakdown_group)
        self._breakdown_layout.setSpacing(4)
        content_layout.addWidget(breakdown_group)

        # Stretch at bottom
        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Status bar
        self._status = QLabel("Waiting for region selection...")
        self._status.setStyleSheet("color: #666; font-size: 10px; padding: 4px;")
        main_layout.addWidget(self._status)

    def update_analysis(self, analysis: dict, region_image: np.ndarray = None,
                        region_info: dict = None):
        """Update the panel with new analysis data."""
        self._analysis = analysis
        self._region_image = region_image

        if not analysis:
            return

        # Update statistics
        for key, label in self._stat_labels.items():
            value = analysis.get(key, "—")
            if key in ("brightness", "saturation", "colorfulness", "neutral_pct"):
                label.setText(f"{value}%")
            elif key == "colored_pixels":
                total = analysis.get("total_pixels", 0)
                label.setText(f"{value:,} / {total:,}")
            else:
                label.setText(str(value))

        # Update color wheel
        self._color_wheel.set_analysis(analysis)

        # Update histogram
        if region_image is not None and region_image.size > 0:
            self._histogram.set_image(region_image)

        # Update preview
        if region_image is not None and region_image.size > 0:
            self._update_preview(region_image)

        # Update color breakdown bars
        self._update_breakdown(analysis.get("colors", []))

        # Update status
        if region_info:
            x = region_info.get("x", 0)
            y = region_info.get("top", 0)
            w = region_info.get("width", 0)
            h = region_info.get("height", 0)
            self._status.setText(
                f"Region: ({x}, {y}) {w}×{h} px | "
                f"Total: {analysis.get('total_pixels', 0):,} px | "
                f"Mode: {analysis.get('dominant_color', '—')}"
            )

    def _update_preview(self, bgr_image: np.ndarray):
        """Update the region preview thumbnail."""
        # Scale down for preview
        max_w, max_h = 200, 120
        h, w = bgr_image.shape[:2]
        scale = min(max_w / w, max_h / h, 1.0)
        new_w, new_h = int(w * scale), int(h * scale)

        resized = cv2.resize(bgr_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        qimg = QImage(rgb.data, new_w, new_h, new_w * 3, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg.copy())  # Copy to ensure data persistence
        self._preview_label.setPixmap(pixmap)
        self._preview_label.setText("")

    def _update_breakdown(self, colors: list):
        """Update the color breakdown bars."""
        # Clear existing bars
        while self._breakdown_layout.count():
            item = self._breakdown_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not colors:
            label = QLabel("No significant color detected")
            label.setStyleSheet("color: #666; padding: 8px;")
            self._breakdown_layout.addWidget(label)
            return

        for color_info in colors:
            bar = ColorBar(
                name=color_info["name"],
                percentage=color_info["percentage"],
                bgr_color=color_info["bgr"],
            )
            self._breakdown_layout.addWidget(bar)

        # Add neutral bar
        neutral_pct = self._analysis.get("neutral_pct", 0) if self._analysis else 0
        if neutral_pct > 0:
            neutral_bar = ColorBar(
                name="Neutral (B/W/Gray)",
                percentage=neutral_pct,
                bgr_color=(128, 128, 128),
            )
            self._breakdown_layout.addWidget(neutral_bar)
