"""
Color region detection and analysis.
Finds non-neutral patches on screen and breaks down their hue distribution.
"""

import cv2
import numpy as np


# HSV ranges for named colors — H is 0-180 in opencv, S and V are 0-255
_RANGES = [
    ("Red",       (0, 80, 80),   (10, 255, 255),   (0, 0, 255)),
    ("Red",       (170, 80, 80), (180, 255, 255),  (0, 0, 255)),
    ("Orange",    (10, 80, 80),  (25, 255, 255),   (0, 140, 255)),
    ("Yellow",    (25, 80, 80),  (35, 255, 255),   (0, 255, 255)),
    ("Lime",      (35, 80, 80),  (50, 255, 255),   (0, 255, 128)),
    ("Green",     (50, 80, 80),  (75, 255, 255),   (0, 200, 0)),
    ("Teal",      (75, 80, 80),  (95, 255, 255),   (200, 200, 0)),
    ("Cyan",      (95, 80, 80),  (105, 255, 255),  (255, 255, 0)),
    ("Blue",      (105, 80, 80), (125, 255, 255),  (255, 100, 0)),
    ("Indigo",    (125, 80, 80), (140, 255, 255),  (200, 0, 100)),
    ("Violet",    (140, 80, 80), (155, 255, 255),  (200, 0, 200)),
    ("Magenta",   (155, 80, 80), (170, 255, 255),  (255, 0, 255)),
    ("Pink",      (155, 40, 180),(170, 120, 255),  (200, 150, 255)),
    ("Warm White",(0, 10, 200),  (30, 40, 255),    (240, 235, 230)),
    ("Cool White",(90, 10, 200), (130, 40, 255),   (230, 235, 240)),
]


def find_regions(bgr, min_area=3000, max_regions=8, scale=0.4):
    """Return list of (x, y, w, h, colored_pixel_count) for colorful areas."""
    if bgr is None or bgr.size == 0:
        return []

    h, w = bgr.shape[:2]

    # work smaller for speed
    if scale < 1.0:
        small = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    else:
        small = bgr

    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

    # mask out neutrals: low sat, or very dark, or very bright with low sat
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    colorful = (s > 40) & (v > 35) & (v < 250)
    pastel = (s > 20) & (s <= 40) & (v > 180)
    mask = (colorful | pastel).astype(np.uint8) * 255

    # clean up noise
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    fac = 1.0 / scale
    results = []
    for c in contours:
        if cv2.contourArea(c) < min_area:
            continue
        bx, by, bw, bh = cv2.boundingRect(c)
        bx, by = int(bx * fac), int(by * fac)
        bw, bh = int(bw * fac), int(bh * fac)
        bx = max(0, bx)
        by = max(0, by)
        bw = min(bw, w - bx)
        bh = min(bh, h - by)
        if bw <= 0 or bh <= 0:
            continue

        # count colored pixels inside this box
        roi = bgr[by:by+bh, bx:bx+bw]
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        rs, rv = roi_hsv[:, :, 1], roi_hsv[:, :, 2]
        cnt = int(np.count_nonzero((rs > 40) & (rv > 35) & (rv < 250)))

        results.append((bx, by, bw, bh, cnt))

    results.sort(key=lambda r: r[4], reverse=True)
    return results[:max_regions]


def analyze(bgr, x, y, w, h):
    """
    Detailed color breakdown of a sub-rectangle.
    Returns a dict with percentages, stats, etc.
    """
    if bgr is None or bgr.size == 0:
        return None

    crop = bgr[y:y+h, x:x+w]
    if crop.size == 0:
        return None

    total = crop.shape[0] * crop.shape[1]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1].astype(np.int32)
    v = hsv[:, :, 2].astype(np.int32)

    # neutral = black, white, or gray
    is_neutral = (v < 30) | ((s < 20) & (v > 220)) | ((s < 35) & (v >= 30) & (v <= 220))
    n_neutral = int(np.count_nonzero(is_neutral))
    n_colored = total - n_neutral

    # tally each named color
    hits = {}
    for name, lo, hi, bgr_col in _RANGES:
        lo_np, hi_np = np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8)
        m = cv2.inRange(hsv, lo_np, hi_np)
        cnt = int(np.count_nonzero(m))
        if cnt > 0:
            pct = cnt / total * 100
            if name in hits:
                hits[name]["pct"] += pct
                hits[name]["px"] += cnt
            else:
                hits[name] = {"pct": round(pct, 2), "px": cnt, "bgr": bgr_col}

    colors = sorted(hits.values(), key=lambda c: c["pct"], reverse=True)
    for c in colors:
        c["pct"] = round(c["pct"], 2)

    dominant = colors[0].get("name", "?") if colors else "Neutral"
    # fix: we didn't store name in hits dict, rebuild
    # actually let me just redo this properly
    color_list = []
    for name, lo, hi, bgr_col in _RANGES:
        lo_np, hi_np = np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8)
        m = cv2.inRange(hsv, lo_np, hi_np)
        cnt = int(np.count_nonzero(m))
        if cnt > 0:
            color_list.append((name, cnt, bgr_col))

    # merge same names
    merged = {}
    for name, cnt, bgr_col in color_list:
        if name in merged:
            merged[name] = (merged[name][0] + cnt, bgr_col)
        else:
            merged[name] = (cnt, bgr_col)

    final = []
    for name, (cnt, bgr_col) in merged.items():
        final.append({
            "name": name,
            "pct": round(cnt / total * 100, 2),
            "px": cnt,
            "bgr": bgr_col,
        })
    final.sort(key=lambda c: c["pct"], reverse=True)
    dominant = final[0]["name"] if final else "Neutral"

    # avg HSV of colored pixels only
    if n_colored > 0:
        cmask = ~is_neutral
        avg_h = float(np.mean(hsv[:, :, 0][cmask]))
        avg_s = float(np.mean(hsv[:, :, 1][cmask]))
        avg_v = float(np.mean(hsv[:, :, 2][cmask]))
    else:
        avg_h = avg_s = avg_v = 0.0

    brightness = float(np.mean(v)) / 255.0 * 100.0
    saturation = float(np.mean(s)) / 255.0 * 100.0

    # colorfulness from Lab space
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).astype(np.float64)
    a_ch = lab[:, :, 1] - 128
    b_ch = lab[:, :, 2] - 128
    colorfulness = min(100.0, float(np.sqrt(np.std(a_ch)**2 + np.std(b_ch)**2)) * 2.0)

    return {
        "total": total,
        "colored": n_colored,
        "neutral": n_neutral,
        "neutral_pct": round(n_neutral / total * 100, 2) if total else 0,
        "colors": final,
        "dominant": dominant,
        "avg_hsv": (round(avg_h, 1), round(avg_s, 1), round(avg_v, 1)),
        "brightness": round(brightness, 1),
        "saturation": round(saturation, 1),
        "colorfulness": round(colorfulness, 1),
    }
