"""
Screen capture module using mss for high-performance screen grabbing.
"""

import numpy as np
import mss
import mss.windows


class ScreenCapture:
    """High-performance screen capture using mss."""

    def __init__(self):
        self._sct = mss.mss()
        self._monitor = self._sct.monitors[0]  # All monitors combined

    @property
    def monitor(self):
        return self._monitor

    def grab(self, region=None):
        """
        Capture a region of the screen.

        Args:
            region: Optional dict with 'left', 'top', 'width', 'height'.
                    If None, captures the entire virtual screen.

        Returns:
            numpy.ndarray: BGR image (OpenCV format), or None on failure.
        """
        try:
            if region is None:
                region = self._monitor
            screenshot = self._sct.grab(region)
            # mss returns BGRA, convert to BGR for OpenCV
            img = np.array(screenshot)
            # Drop alpha channel, keep BGR
            return img[:, :, :3].copy()
        except Exception:
            return None

    def grab_region(self, left, top, width, height):
        """Convenience method to grab a specific rectangular region."""
        return self.grab({"left": left, "top": top, "width": width, "height": height})

    def close(self):
        """Release resources."""
        self._sct.close()
