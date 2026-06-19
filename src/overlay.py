"""
Transparent overlay that draws blue boxes around detected colored regions.
Toggle between click-through and interactive with the I key or Ctrl+Shift+I.
"""

import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QFont


class Overlay(QWidget):
    selected = pyqtSignal(int)     # region index
    mode_toggled = pyqtSignal()

    def __init__(self, screen_rect, parent=None):
        super().__init__(parent)
        self._scr = screen_rect
        self._regions = []         # list of (x, y, w, h, cnt)
        self._sel = -1
        self._hover = -1
        self._interactive = False
        self._labels = True

        # drag / resize state
        self._dragging = False
        self._resizing = False
        self._drag_start = QPoint()
        self._drag_orig = QRect()
        self._handle = -1

        self._pulse = 0.0
        self._configure()
        self._start_anim()

    def _configure(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setGeometry(
            self._scr["left"], self._scr["top"],
            self._scr["width"], self._scr["height"],
        )

    def _start_anim(self):
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(50)
        self._timer = t

    def _tick(self):
        self._pulse = (self._pulse + 0.08) % (2 * math.pi)
        self.update()

    def set_regions(self, regions):
        self._regions = regions
        if self._sel >= len(regions):
            self._sel = -1
        self.update()

    def set_interactive(self, on):
        self._interactive = on
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not on)
        self.setCursor(Qt.CursorShape.CrossCursor if on else Qt.CursorShape.ArrowCursor)
        self.update()

    def get_selected(self):
        if 0 <= self._sel < len(self._regions):
            return self._regions[self._sel]
        return None

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, r in enumerate(self._regions):
            self._draw_box(p, r, i == self._sel, i == self._hover, i)
        p.end()

    def _draw_box(self, p, r, sel, hover, idx):
        x, y, w, h = r[0], r[1], r[2], r[3]

        if sel:
            ga = int(80 + 40 * abs(math.sin(self._pulse)))
            p.setPen(QPen(QColor(0, 180, 255, ga), 8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(x - 4, y - 4, w + 8, h + 8, 6, 6)

        if sel:
            pen = QPen(QColor(0, 150, 255), 3)
        elif hover:
            pen = QPen(QColor(100, 200, 255), 2, Qt.PenStyle.DashLine)
        else:
            pen = QPen(QColor(0, 120, 255), 2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(x, y, w, h, 4, 4)

        if sel:
            # corner ticks
            p.setPen(QPen(QColor(0, 200, 255), 4))
            L = 15
            p.drawLine(x, y, x + L, y)
            p.drawLine(x, y, x, y + L)
            p.drawLine(x + w, y, x + w - L, y)
            p.drawLine(x + w, y, x + w, y + L)
            p.drawLine(x, y + h, x + L, y + h)
            p.drawLine(x, y + h, x, y + h - L)
            p.drawLine(x + w, y + h, x + w - L, y + h)
            p.drawLine(x + w, y + h, x + w, y + h - L)

            if self._interactive:
                p.setPen(QPen(QColor(0, 150, 255), 1))
                p.setBrush(QColor(0, 150, 255))
                hs = 8
                for px, py in [
                    (x - hs//2, y - hs//2),
                    (x + w//2 - hs//2, y - hs//2),
                    (x + w - hs//2, y - hs//2),
                    (x + w - hs//2, y + h//2 - hs//2),
                    (x + w - hs//2, y + h - hs//2),
                    (x + w//2 - hs//2, y + h - hs//2),
                    (x - hs//2, y + h - hs//2),
                    (x - hs//2, y + h//2 - hs//2),
                ]:
                    p.drawRect(px, py, hs, hs)

        if sel:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 150, 255, 15))
            p.drawRoundedRect(x, y, w, h, 4, 4)

        # label
        if self._labels:
            lbl = f"R{idx + 1}"
            font = QFont("Segoe UI", 9, QFont.Weight.Bold if sel else QFont.Weight.Normal)
            p.setFont(font)
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(lbl) + 16
            th = fm.height() + 8
            lx = x
            ly = y - th - 4
            if ly < 0:
                ly = y + h + 4
            bg = QColor(0, 120, 255, 200) if sel else QColor(0, 0, 0, 160)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(lx, ly, tw, th, 4, 4)
            p.setPen(QColor(255, 255, 255))
            p.drawText(lx + 8, ly + th - 6, lbl)

    def _hit_test(self, pos, r):
        x, y, w, h = r[0], r[1], r[2], r[3]
        margin = 12
        handles = [
            (x, y, 1), (x + w//2, y, 2), (x + w, y, 3),
            (x + w, y + h//2, 4), (x + w, y + h, 5),
            (x + w//2, y + h, 6), (x, y + h, 7), (x, y + h//2, 8),
        ]
        for hx, hy, hid in handles:
            if abs(pos.x() - hx) <= margin and abs(pos.y() - hy) <= margin:
                return hid
        if x <= pos.x() <= x + w and y <= pos.y() <= y + h:
            return 0
        return -1

    def mousePressEvent(self, ev):
        if not self._interactive:
            return
        pos = ev.pos()
        for i, r in enumerate(self._regions):
            h = self._hit_test(pos, r)
            if h >= 0:
                self._sel = i
                self._drag_start = pos
                self._drag_orig = QRect(r[0], r[1], r[2], r[3])
                if h == 0:
                    self._dragging = True
                else:
                    self._resizing = True
                    self._handle = h
                self.selected.emit(i)
                self.update()
                return
        self._sel = -1
        self.update()

    def mouseMoveEvent(self, ev):
        pos = ev.pos()
        if self._dragging and self._sel >= 0:
            d = pos - self._drag_start
            r = self._regions[self._sel]
            r = (self._drag_orig.x() + d.x(), self._drag_orig.y() + d.y(), r[2], r[3], r[4])
            self._regions[self._sel] = r
            self.update()
            return
        if self._resizing and self._sel >= 0:
            d = pos - self._drag_start
            r = self._regions[self._sel]
            rect = QRect(self._drag_orig)
            if self._handle in (1, 2, 3):
                rect.setTop(rect.top() + d.y())
            if self._handle in (3, 4, 5):
                rect.setRight(rect.right() + d.x())
            if self._handle in (5, 6, 7):
                rect.setBottom(rect.bottom() + d.y())
            if self._handle in (7, 8, 1):
                rect.setLeft(rect.left() + d.x())
            self._regions[self._sel] = (rect.x(), rect.y(), max(20, rect.width()), max(20, rect.height()), r[4])
            self.update()
            return

        old = self._hover
        self._hover = -1
        for i, r in enumerate(self._regions):
            if r[0] <= pos.x() <= r[0] + r[2] and r[1] <= pos.y() <= r[1] + r[3]:
                self._hover = i
                break
        if old != self._hover:
            self.update()

    def mouseReleaseEvent(self, ev):
        self._dragging = False
        self._resizing = False
        self._handle = -1

    def keyPressEvent(self, ev):
        k = ev.key()
        if k == Qt.Key.Key_Tab:
            if self._regions:
                self._sel = (self._sel + 1) % len(self._regions)
                self.selected.emit(self._sel)
                self.update()
        elif k == Qt.Key.Key_Escape:
            self._sel = -1
            self.update()
        elif k == Qt.Key.Key_I:
            self.mode_toggled.emit()
        elif k == Qt.Key.Key_V:
            self._labels = not self._labels
            self.update()
