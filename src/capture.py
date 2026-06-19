"""
Screen grabber — wraps mss to grab the virtual screen.
"""

import numpy as np
import mss


class Grabber:
    def __init__(self):
        self._sct = mss.mss()
        self.full = self._sct.monitors[0]

    def grab(self, rect=None):
        """Return a BGR numpy array, or None on failure."""
        try:
            region = rect if rect else self.full
            raw = self._sct.grab(region)
            img = np.array(raw)
            return img[:, :, :3].copy()  # drop alpha
        except Exception:
            return None

    def close(self):
        self._sct.close()
