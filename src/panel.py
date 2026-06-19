"""
Analysis panel — separate window showing color breakdown for the selected region.
"""

import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPainterPath, QPixmap, QImage


class Bar(QWidget):
    """Single color bar with name + percentage."""
    def __init__(self, name, pct, bgr, parent=None):
        super().__init__(parent)
        self._name = name
        self._pct = pct
        self._bgr = bgr
        self.setMinimumHeight(36)
        self.setMaximumHeight(40)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(40, 40, 40))
        fill = int(w * self._pct / 100.0)
        b, g, r = self._bgr
        p.fillRect(0, 0, fill, h, QColor(r, g, b))
        p.setPen(QPen(QColor(80, 80, 80), 1))
        p.drawRect(0, 0, w - 1, h - 1)
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255))
        p.drawText(8, h - 10, f"  {self._name}  {self._pct:.1f}%")
        p.end()


class Wheel(QWidget):
    """Donut chart of hue distribution."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = None
        self.setMinimumSize(200, 200)
        self.setMaximumSize(250, 250)

    def set_data(self, data):
        self._data = data
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        r = min(cx, cy) - 10

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(30, 30, 30))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        if not self._data or not self._data.get("colors"):
            p.setPen(QColor(100, 100, 100))
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(0, cy - 10, w, 20, Qt.AlignmentFlag.AlignCenter, "no data")
            p.end()
            return

        colors = self._data["colors"]
        total = sum(c["pct"] for c in colors)
        if total == 0:
            total = 1

        angle = 0
        for c in colors:
            sweep = int((c["pct"] / total) * 360)
            bgr = c["bgr"]
            p.setPen(QPen(QColor(bgr[2], bgr[1], bgr[0]), 12))
            p.drawArc(cx - r, cy - r, r * 2, r * 2, angle * 16, sweep * 16)
            angle += sweep

        ir = r // 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(25, 25, 25))
        p.drawEllipse(cx - ir, cy - ir, ir * 2, ir * 2)

        dom = self._data.get("dominant", "—")
        p.setPen(QColor(220, 220, 220))
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p.drawText(cx - ir, cy - 10, ir * 2, 20, Qt.AlignmentFlag.AlignCenter, dom)
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(150, 150, 150))
        p.drawText(cx - ir, cy + 5, ir * 2, 20, Qt.AlignmentFlag.AlignCenter, "dominant")
        p.end()


class Histogram(QWidget):
    """RGB channel histogram."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._img = None
        self.setMinimumHeight(120)
        self.setMaximumHeight(160)

    def set_image(self, img):
        self._img = img
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(30, 30, 30))

        if self._img is None or self._img.size == 0:
            p.setPen(QColor(100, 100, 100))
            p.drawText(0, h // 2 - 10, w, 20, Qt.AlignmentFlag.AlignCenter, "no image")
            p.end()
            return

        margin = 5
        gh = h - 20
        gw = w - 2 * margin
        for idx, bgr in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
            hist = cv2.calcHist([self._img], [idx], None, [256], [0, 256])
            cv2.normalize(hist, hist, 0, gh, cv2.NORM_MINMAX)
            path = QPainterPath()
            path.moveTo(margin, h - 5)
            for i in range(256):
                px = margin + int(i / 256.0 * gw)
                py = h - 5 - int(hist[i])
                path.lineTo(px, py)
            path.lineTo(margin + gw, h - 5)
            path.closeSubpath()
            qb, qg, qr = bgr
            p.setPen(QPen(QColor(qr, qg, qb), 1.5))
            p.setBrush(QColor(qr, qg, qb, 80))
            p.drawPath(path)

        p.setPen(QPen(QColor(60, 60, 60), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(0, 0, w - 1, h - 1)
        p.end()


class Panel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        self.setWindowTitle("DeepLook — Color Analysis")
        self.setMinimumSize(480, 600)
        self.resize(520, 700)
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #e0e0e0;
                      font-family: 'Segoe UI', sans-serif; }
            QGroupBox { border: 1px solid #3a3a3a; border-radius: 6px;
                        margin-top: 12px; padding-top: 16px;
                        font-weight: bold; font-size: 12px; color: #88ccff; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QLabel { color: #c0c0c0; font-size: 11px; }
            QScrollArea { border: none; background-color: transparent; }
        """)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 16, 16, 16)

        hdr = QLabel("Color Grading Analysis")
        hdr.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        hdr.setStyleSheet("color: #fff; margin-bottom: 4px;")
        lay.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(12)
        cl.setContentsMargins(0, 0, 0, 0)

        # preview
        pg = QGroupBox("Selected Region")
        pl = QVBoxLayout(pg)
        self._preview = QLabel("no region selected")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(100)
        self._preview.setMaximumHeight(150)
        self._preview.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
        pl.addWidget(self._preview)
        cl.addWidget(pg)

        # wheel + stats side by side
        row = QHBoxLayout()

        wg = QGroupBox("Hue Distribution")
        wl = QVBoxLayout(wg)
        self._wheel = Wheel()
        wl.addWidget(self._wheel, alignment=Qt.AlignmentFlag.AlignCenter)
        row.addWidget(wg)

        sg = QGroupBox("Stats")
        sl = QGridLayout(sg)
        sl.setVerticalSpacing(6)
        self._stats = {}
        for row_i, (label, key) in enumerate([
            ("Dominant", "dominant"),
            ("Brightness", "brightness"),
            ("Saturation", "saturation"),
            ("Colorfulness", "colorfulness"),
            ("Neutral %", "neutral_pct"),
            ("Colored px", "colored"),
        ]):
            a = QLabel(f"{label}:")
            a.setStyleSheet("color: #888;")
            b = QLabel("—")
            b.setStyleSheet("color: #fff; font-weight: bold;")
            sl.addWidget(a, row_i, 0)
            sl.addWidget(b, row_i, 1)
            self._stats[key] = b
        row.addWidget(sg)
        cl.addLayout(row)

        # histogram
        hg = QGroupBox("RGB Histogram")
        hl = QVBoxLayout(hg)
        self._hist = Histogram()
        hl.addWidget(self._hist)
        cl.addWidget(hg)

        # breakdown bars
        bg = QGroupBox("Color Breakdown")
        self._bars = QVBoxLayout(bg)
        self._bars.setSpacing(4)
        cl.addWidget(bg)

        cl.addStretch()
        scroll.setWidget(content)
        lay.addWidget(scroll)

        self._status = QLabel("waiting for region...")
        self._status.setStyleSheet("color: #666; font-size: 10px; padding: 4px;")
        lay.addWidget(self._status)

    def update(self, analysis, region_img=None, info=None):
        if not analysis:
            return

        for key, lbl in self._stats.items():
            val = analysis.get(key, "—")
            if key in ("brightness", "saturation", "colorfulness", "neutral_pct"):
                lbl.setText(f"{val}%")
            elif key == "colored":
                lbl.setText(f"{val:,}")
            else:
                lbl.setText(str(val))

        self._wheel.set_data(analysis)

        if region_img is not None and region_img.size > 0:
            self._hist.set_image(region_img)
            self._set_preview(region_img)

        self._rebuild_bars(analysis.get("colors", []), analysis.get("neutral_pct", 0))

        if info:
            self._status.setText(
                f"({info['x']}, {info['y']}) {info['w']}x{info['h']} px | "
                f"total: {analysis.get('total', 0):,} px"
            )

    def _set_preview(self, img):
        mx, my = 200, 120
        h, w = img.shape[:2]
        s = min(mx / w, my / h, 1.0)
        rw, rh = int(w * s), int(h * s)
        resized = cv2.resize(img, (rw, rh), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        qi = QImage(rgb.data, rw, rh, rw * 3, QImage.Format.Format_RGB888)
        self._preview.setPixmap(QPixmap.fromImage(qi.copy()))
        self._preview.setText("")

    def _rebuild_bars(self, colors, neutral_pct):
        while self._bars.count():
            item = self._bars.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not colors:
            l = QLabel("no significant color")
            l.setStyleSheet("color: #666; padding: 8px;")
            self._bars.addWidget(l)
            return

        for c in colors:
            self._bars.addWidget(Bar(c["name"], c["pct"], c["bgr"]))

        if neutral_pct > 0:
            self._bars.addWidget(Bar("Neutral", neutral_pct, (128, 128, 128)))
