"""
Color analysis module using OpenCV and HSV segmentation.
Detects colored regions and performs detailed color distribution analysis.
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class ColorRegion:
    """Represents a detected colored region on screen."""
    x: int
    top: int
    width: int
    height: int
    pixel_count: int = 0
    avg_color: Tuple[int, int, int] = (0, 0, 0)
    color_distribution: dict = field(default_factory=dict)

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.top + self.height

    @property
    def center(self):
        return (self.x + self.width // 2, self.top + self.height // 2)

    @property
    def area(self):
        return self.width * self.height

    def to_dict(self):
        return {
            "left": self.x,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class ColorSlice:
    """A named color range with its HSV bounds and statistics."""
    name: str
    lower: Tuple[int, int, int]
    upper: Tuple[int, int, int]
    bgr_display: Tuple[int, int, int]  # For UI rendering
    percentage: float = 0.0
    pixel_count: int = 0


# Define color ranges for analysis (HSV format)
# H: 0-180, S: 0-255, V: 0-255 in OpenCV
COLOR_SLICES = [
    ColorSlice("Red",       (0, 80, 80),   (10, 255, 255),   (0, 0, 255)),
    ColorSlice("Red",       (170, 80, 80), (180, 255, 255),  (0, 0, 255)),
    ColorSlice("Orange",    (10, 80, 80),  (25, 255, 255),   (0, 140, 255)),
    ColorSlice("Yellow",    (25, 80, 80),  (35, 255, 255),   (0, 255, 255)),
    ColorSlice("Lime",      (35, 80, 80),  (50, 255, 255),   (0, 255, 128)),
    ColorSlice("Green",     (50, 80, 80),  (75, 255, 255),   (0, 200, 0)),
    ColorSlice("Teal",      (75, 80, 80),  (95, 255, 255),   (200, 200, 0)),
    ColorSlice("Cyan",      (95, 80, 80),  (105, 255, 255),  (255, 255, 0)),
    ColorSlice("Blue",      (105, 80, 80), (125, 255, 255),  (255, 100, 0)),
    ColorSlice("Indigo",    (125, 80, 80), (140, 255, 255),  (200, 0, 100)),
    ColorSlice("Violet",    (140, 80, 80), (155, 255, 255),  (200, 0, 200)),
    ColorSlice("Magenta",   (155, 80, 80), (170, 255, 255),  (255, 0, 255)),
    ColorSlice("Pink",      (155, 40, 180),(170, 120, 255),  (200, 150, 255)),
    ColorSlice("Warm White",(0, 10, 200),  (30, 40, 255),    (240, 235, 230)),
    ColorSlice("Cool White",(90, 10, 200), (130, 40, 255),   (230, 235, 240)),
]


def _is_neutral(hsv_pixel):
    """Check if an HSV pixel is neutral (black, white, or gray)."""
    h, s, v = int(hsv_pixel[0]), int(hsv_pixel[1]), int(hsv_pixel[2])
    # Black: very low value
    if v < 30:
        return True
    # White: very low saturation, very high value
    if s < 20 and v > 220:
        return True
    # Gray: low saturation, mid-to-high value
    if s < 35 and 30 <= v <= 220:
        return True
    return False


def detect_colored_regions(
    bgr_image: np.ndarray,
    min_area: int = 5000,
    max_regions: int = 10,
    downscale: float = 0.5
) -> List[ColorRegion]:
    """
    Detect colored (non-neutral) regions in a BGR image.

    Uses HSV thresholding to isolate saturated regions, then finds contours.

    Args:
        bgr_image: Input BGR image.
        min_area: Minimum contour area in pixels (after scaling).
        max_regions: Maximum number of regions to return.
        downscale: Factor to downscale for faster processing.

    Returns:
        List of ColorRegion objects, sorted by area (largest first).
    """
    if bgr_image is None or bgr_image.size == 0:
        return []

    h, w = bgr_image.shape[:2]

    # Downscale for performance
    if downscale < 1.0:
        small = cv2.resize(bgr_image, None, fx=downscale, fy=downscale,
                           interpolation=cv2.INTER_AREA)
    else:
        small = bgr_image

    # Convert to HSV
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

    # Create mask of non-neutral pixels
    # Neutral = low saturation OR very low value OR very high value with low sat
    # We want: saturated enough AND not too dark AND not too bright-neutral
    sat_mask = hsv[:, :, 1] > 40  # Saturation threshold
    val_mask = (hsv[:, :, 2] > 35) & (hsv[:, :, 2] < 250)  # Value range
    color_mask = sat_mask & val_mask

    # Also include moderately saturated bright pixels (pastels)
    pastel_mask = (hsv[:, :, 1] > 20) & (hsv[:, :, 1] <= 40) & (hsv[:, :, 2] > 180)
    color_mask = color_mask | pastel_mask

    # Convert to uint8
    mask = color_mask.astype(np.uint8) * 255

    # Morphological operations to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Scale factor to map back to original coordinates
    scale = 1.0 / downscale

    regions = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        # Get bounding rect and scale back
        x, y, w_box, h_box = cv2.boundingRect(contour)
        x = int(x * scale)
        y = int(y * scale)
        w_box = int(w_box * scale)
        h_box = int(h_box * scale)

        # Clamp to image bounds
        x = max(0, x)
        y = max(0, y)
        w_box = min(w_box, w - x)
        h_box = min(h_box, h - y)

        if w_box <= 0 or h_box <= 0:
            continue

        # Calculate average color in the region
        roi = bgr_image[y:y+h_box, x:x+w_box]
        avg_bgr = cv2.mean(roi)[:3]

        # Count colored pixels in the region
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        roi_mask = np.zeros((h_box, w_box), dtype=np.uint8)
        roi_sat = roi_hsv[:, :, 1] > 40
        roi_val = (roi_hsv[:, :, 2] > 35) & (roi_hsv[:, :, 2] < 250)
        colored_count = int(np.count_nonzero(roi_sat & roi_val))

        region = ColorRegion(
            x=x,
            top=y,
            width=w_box,
            height=h_box,
            pixel_count=colored_count,
            avg_color=(int(avg_bgr[0]), int(avg_bgr[1]), int(avg_bgr[2])),
        )
        regions.append(region)

    # Sort by colored pixel count (most colorful first)
    regions.sort(key=lambda r: r.pixel_count, reverse=True)

    return regions[:max_regions]


def analyze_color_distribution(
    bgr_image: np.ndarray,
    region: Optional[ColorRegion] = None
) -> dict:
    """
    Perform detailed color distribution analysis on an image or region.

    Args:
        bgr_image: Full BGR image.
        region: Optional ColorRegion to analyze. If None, analyzes entire image.

    Returns:
        Dictionary with color distribution data:
        {
            "total_pixels": int,
            "colored_pixels": int,
            "neutral_pixels": int,
            "neutral_pct": float,
            "colors": [
                {"name": str, "percentage": float, "pixel_count": int, "bgr": (b,g,r)},
                ...
            ],
            "dominant_color": str,
            "avg_hsv": (h, s, v),
            "brightness": float,  # 0-100
            "saturation": float,  # 0-100
            "colorfulness": float,  # 0-100
        }
    """
    if bgr_image is None or bgr_image.size == 0:
        return _empty_analysis()

    # Crop to region if specified
    if region is not None:
        x, y, w, h = region.x, region.top, region.width, region.height
        img = bgr_image[y:y+h, x:x+w]
    else:
        img = bgr_image

    if img.size == 0:
        return _empty_analysis()

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    total_pixels = img.shape[0] * img.shape[1]

    # Count neutral pixels
    sat = hsv[:, :, 1].astype(np.int32)
    val = hsv[:, :, 2].astype(np.int32)

    neutral_mask = (
        (val < 30) |  # Black
        ((sat < 20) & (val > 220)) |  # White
        ((sat < 35) & (val >= 30) & (val <= 220))  # Gray
    )
    neutral_pixels = int(np.count_nonzero(neutral_mask))
    colored_pixels = total_pixels - neutral_pixels

    # Analyze each color slice
    color_results = []
    for cs in COLOR_SLICES:
        lower = np.array(cs.lower, dtype=np.uint8)
        upper = np.array(cs.upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        count = int(np.count_nonzero(mask))
        if count > 0:
            pct = (count / total_pixels) * 100
            color_results.append({
                "name": cs.name,
                "percentage": round(pct, 2),
                "pixel_count": count,
                "bgr": cs.bgr_display,
            })

    # Merge duplicate color names (e.g., Red has two ranges)
    merged = {}
    for cr in color_results:
        name = cr["name"]
        if name in merged:
            merged[name]["percentage"] += cr["percentage"]
            merged[name]["pixel_count"] += cr["pixel_count"]
        else:
            merged[name] = dict(cr)

    # Sort by percentage descending
    sorted_colors = sorted(merged.values(), key=lambda c: c["percentage"], reverse=True)

    # Round percentages after merge
    for c in sorted_colors:
        c["percentage"] = round(c["percentage"], 2)

    # Determine dominant color
    dominant = sorted_colors[0]["name"] if sorted_colors else "Neutral"

    # Average HSV of colored pixels only
    if colored_pixels > 0:
        colored_mask = ~neutral_mask
        avg_h = float(np.mean(hsv[:, :, 0][colored_mask]))
        avg_s = float(np.mean(hsv[:, :, 1][colored_mask]))
        avg_v = float(np.mean(hsv[:, :, 2][colored_mask]))
    else:
        avg_h = avg_s = avg_v = 0.0

    # Overall brightness (0-100)
    brightness = float(np.mean(val)) / 255.0 * 100.0

    # Overall saturation (0-100)
    saturation = float(np.mean(sat)) / 255.0 * 100.0

    # Colorfulness metric: std deviation of a* and b* channels in Lab space
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float64)
    a_channel = lab[:, :, 1] - 128  # Center around 0
    b_channel = lab[:, :, 2] - 128
    colorfulness = min(100.0, float(np.sqrt(np.std(a_channel)**2 + np.std(b_channel)**2)) * 2.0)

    neutral_pct = (neutral_pixels / total_pixels * 100) if total_pixels > 0 else 0

    return {
        "total_pixels": total_pixels,
        "colored_pixels": colored_pixels,
        "neutral_pixels": neutral_pixels,
        "neutral_pct": round(neutral_pct, 2),
        "colors": sorted_colors,
        "dominant_color": dominant,
        "avg_hsv": (round(avg_h, 1), round(avg_s, 1), round(avg_v, 1)),
        "brightness": round(brightness, 1),
        "saturation": round(saturation, 1),
        "colorfulness": round(colorfulness, 1),
    }


def _empty_analysis():
    """Return an empty analysis result."""
    return {
        "total_pixels": 0,
        "colored_pixels": 0,
        "neutral_pixels": 0,
        "neutral_pct": 100.0,
        "colors": [],
        "dominant_color": "None",
        "avg_hsv": (0, 0, 0),
        "brightness": 0.0,
        "saturation": 0.0,
        "colorfulness": 0.0,
    }
