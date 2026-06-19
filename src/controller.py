"""
Wires together capture, detection, overlay, and analysis panel.
"""

import time
from PyQt6.QtCore import QTimer, QObject
from PyQt6.QtGui import QKeySequence, QShortcut

from src.capture import Grabber
from src.detect import find_regions, analyze
from src.overlay import Overlay
from src.panel import Panel


class AppController(QObject):
    def __init__(self):
        super().__init__()
        self._grabber = Grabber()
        scr = self._grabber.full

        self._overlay = Overlay(scr)
        self._overlay.selected.connect(self._on_select)
        self._overlay.mode_toggled.connect(self._toggle_mode)

        self._panel = Panel()

        self._running = False
        self._interactive = False
        self._last_frame = None
        self._last_regions = []

        self._scan_timer = QTimer()
        self._scan_timer.timeout.connect(self._scan)

        self._analysis_timer = QTimer()
        self._analysis_timer.timeout.connect(self._update_analysis)

    def start(self):
        self._overlay.show()
        self._panel.show()
        self._running = True
        self._scan_timer.start(500)
        self._analysis_timer.start(250)

    def stop(self):
        self._running = False
        self._scan_timer.stop()
        self._analysis_timer.stop()
        self._grabber.close()
        self._overlay.close()
        self._panel.close()

    def _scan(self):
        if not self._running:
            return
        frame = self._grabber.grab()
        if frame is None:
            return
        self._last_frame = frame
        regions = find_regions(frame, min_area=3000, max_regions=8, scale=0.4)
        self._last_regions = regions
        self._overlay.set_regions(regions)

    def _update_analysis(self):
        if not self._running:
            return
        sel = self._overlay.get_selected()
        if sel is None:
            return
        frame = self._last_frame
        if frame is None:
            return
        x, y, w, h = sel[0], sel[1], sel[2], sel[3]
        result = analyze(frame, x, y, w, h)
        if result is None:
            return
        crop = frame[y:y+h, x:x+w].copy()
        self._panel.update(result, region_img=crop, info={"x": x, "y": y, "w": w, "h": h})

    def _on_select(self, idx):
        pass

    def _toggle_mode(self):
        self._interactive = not self._interactive
        self._overlay.set_interactive(self._interactive)
