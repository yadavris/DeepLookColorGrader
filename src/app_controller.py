"""
Main application controller — orchestrates screen capture, region detection,
overlay rendering, and analysis panel updates.
"""

import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt6.QtGui import QKeySequence, QShortcut

from src.screen_capture import ScreenCapture
from src.color_analyzer import detect_colored_regions, analyze_color_distribution
from src.overlay_window import OverlayWindow
from src.analysis_panel import AnalysisPanel


class AppController(QObject):
    """Central controller for the DeepLook Color Grader application."""

    def __init__(self):
        super().__init__()

        # Initialize screen capture
        self._capture = ScreenCapture()
        screen = self._capture.monitor

        # Create overlay
        self._overlay = OverlayWindow(screen)
        self._overlay.region_selected.connect(self._on_region_selected)
        self._overlay.toggle_mode.connect(self._toggle_interactive_mode)

        # Create analysis panel
        self._analysis_panel = AnalysisPanel()

        # Processing state
        self._running = False
        self._scan_interval_ms = 500  # Screen scan interval
        self._analysis_interval_ms = 250  # Analysis update interval
        self._last_regions = []
        self._selected_region = None
        self._interactive_mode = False

        # Performance tracking
        self._frame_times = []

        # Timers
        self._scan_timer = QTimer()
        self._scan_timer.timeout.connect(self._scan_screen)

        self._analysis_timer = QTimer()
        self._analysis_timer.timeout.connect(self._update_analysis)

    def start(self):
        """Start the application."""
        self._overlay.show()
        self._analysis_panel.show()
        self._running = True

        # Start timers
        self._scan_timer.start(self._scan_interval_ms)
        self._analysis_timer.start(self._analysis_interval_ms)

    def stop(self):
        """Stop the application and release resources."""
        self._running = False
        self._scan_timer.stop()
        self._analysis_timer.stop()
        self._capture.close()
        self._overlay.close()
        self._analysis_panel.close()

    def _scan_screen(self):
        """Capture screen and detect colored regions."""
        if not self._running:
            return

        start = time.perf_counter()

        # Grab screen
        frame = self._capture.grab()
        if frame is None:
            return

        # Detect colored regions
        regions = detect_colored_regions(
            frame,
            min_area=3000,
            max_regions=8,
            downscale=0.4  # Downscale for speed
        )

        # Store frame for analysis
        self._last_frame = frame
        self._last_regions = regions

        # Update overlay
        self._overlay.set_regions(regions)

        # Track performance
        elapsed = (time.perf_counter() - start) * 1000
        self._frame_times.append(elapsed)
        if len(self._frame_times) > 30:
            self._frame_times.pop(0)

    def _update_analysis(self):
        """Update the analysis panel for the selected region."""
        if not self._running:
            return

        region = self._overlay.get_selected_region()
        if region is None:
            return

        # Use cached frame
        frame = getattr(self, '_last_frame', None)
        if frame is None:
            return

        # Analyze the selected region
        analysis = analyze_color_distribution(frame, region)

        # Extract region image
        x, y, w, h = region.x, region.top, region.width, region.height
        region_img = frame[y:y+h, x:x+w].copy() if frame is not None else None

        # Update panel
        self._analysis_panel.update_analysis(
            analysis,
            region_image=region_img,
            region_info={"x": x, "top": y, "width": w, "height": h}
        )

    def _on_region_selected(self, index: int):
        """Handle region selection from overlay."""
        if 0 <= index < len(self._last_regions):
            self._selected_region = self._last_regions[index]

    def _toggle_interactive_mode(self):
        """Toggle overlay between click-through and interactive."""
        self._interactive_mode = not self._interactive_mode
        self._overlay.set_interactive(self._interactive_mode)


def main():
    """Application entry point."""
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("DeepLook Color Grader")
    app.setOrganizationName("DeepLook")

    # Global dark palette
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    app.setPalette(palette)

    controller = AppController()

    # Keyboard shortcuts
    shortcut_toggle = QShortcut(QKeySequence("Ctrl+Shift+I"), app)
    shortcut_toggle.activated.connect(controller._toggle_interactive_mode)

    shortcut_quit = QShortcut(QKeySequence("Ctrl+Shift+Q"), app)
    shortcut_quit.activated.connect(controller.stop)
    shortcut_quit.activated.connect(app.quit)

    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
