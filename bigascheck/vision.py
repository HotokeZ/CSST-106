"""Segmentation and interpretable per-grain features; input arrays are RGB."""
from dataclasses import asdict, dataclass
import io
import heapq

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from scipy import ndimage
from scipy.spatial import ConvexHull, QhullError

try:
    import cv2
except ImportError:
    cv2 = None

FEATURES = ["area", "major_axis", "minor_axis", "aspect_ratio", "solidity",
            "extent", "mean_r", "mean_g", "mean_b", "std_r", "std_g", "std_b"]


@dataclass(frozen=True)
class Settings:
    background: str = "dark"
    min_area: int = 30
    max_area_fraction: float = 0.15
    morphology: int = 1
    exclude_border: bool = True
    split_touching: bool = False

    def __post_init__(self):
        if self.background not in {"auto", "dark", "light", "pale"}:
            raise ValueError("Background must be auto, dark, pale, or light.")
        if self.min_area < 1 or not 0 < self.max_area_fraction <= 1:
            raise ValueError("Invalid grain area limits.")
        if self.morphology not in range(4):
            raise ValueError("Morphology must be between 0 and 3.")


def load_rgb(source):
    with Image.open(source) as im:
        if im.width * im.height > 20_000_000:
            raise ValueError("Use an image with at most 20 megapixels.")
        # Apply smartphone EXIF rotation before measuring grains.
        return np.asarray(ImageOps.exif_transpose(im).convert("RGB")).copy()


def backend():
    return "opencv" if cv2 is not None else "scipy-fallback"


def _otsu(gray):
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    mass = hist.cumsum()
    weighted = (hist * np.arange(256)).cumsum()
    denom = mass * (mass[-1] - mass)
    score = np.divide((weighted[-1] * mass - weighted * mass[-1]) ** 2,
                      denom, out=np.zeros(256), where=denom > 0)
    return int(np.argmax(score))


def _bright_otsu(gray):
    """Three intensity classes separate shadows, pale table, and bright rice."""
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    mass = hist.cumsum()
    weighted = (hist * np.arange(256)).cumsum()
    best_score, threshold = -1.0, _otsu(gray)
    for low in range(1, 254):
        if mass[low] == 0:
            continue
        high = np.arange(low + 1, 255)
        middle_mass = mass[high] - mass[low]
        bright_mass = mass[-1] - mass[high]
        valid = (middle_mass > 0) & (bright_mass > 0)
        score = weighted[low] ** 2 / mass[low]
        score = score + np.divide((weighted[high] - weighted[low]) ** 2, middle_mass,
                                  out=np.zeros_like(middle_mass), where=valid)
        score = score + np.divide((weighted[-1] - weighted[high]) ** 2, bright_mass,
                                  out=np.zeros_like(bright_mass), where=valid)
        score[~valid] = -1
        index = int(np.argmax(score))
        if score[index] > best_score:
            best_score, threshold = float(score[index]), int(high[index])
    return threshold


def resolve_background(rgb, mode):
    if mode != "auto":
        return mode
    # Dark training images have a predominantly black surface; pale surfaces
    # require local contrast rather than simply reversing the threshold.
    gray = rgb @ np.array([0.299, 0.587, 0.114])
    return "dark" if np.percentile(gray, 25) < 80 else "pale"


def _fill_small_holes(mask, max_area):
    """Fill pinholes inside grains without filling table visible inside a rice ring."""
    holes, _ = ndimage.label(~mask, np.ones((3, 3)))
    sizes = np.bincount(holes.ravel())
    border = np.unique(np.concatenate([holes[0], holes[-1], holes[:, 0], holes[:, -1]]))
    fill = sizes <= max_area
    fill[border] = False
    fill[0] = False
    return mask | fill[holes]


def _watershed_distance(distance, seeds, mask):
    """FIFO priority flooding keeps equal-height plateaus shared between seeds."""
    labels = np.where(seeds > 0, seeds, 0).astype(np.int32)
    queue = []
    order = 0
    height, width = mask.shape
    for y, x in zip(*np.nonzero(labels)):
        heapq.heappush(queue, (-float(distance[y, x]), order, int(y), int(x)))
        order += 1
    neighbors = [(-1, 0), (0, -1), (0, 1), (1, 0)]
    while queue:
        level, _, y, x = heapq.heappop(queue)
        label = labels[y, x]
        for dy, dx in neighbors:
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and labels[ny, nx] == 0:
                labels[ny, nx] = label
                heapq.heappush(queue, (max(level, -float(distance[ny, nx])), order, ny, nx))
                order += 1
    return labels


def _hull_area(local):
    by, bx = np.nonzero(local & ~ndimage.binary_erosion(local))
    boundary = np.column_stack([bx, by]).astype(float)
    corners = np.concatenate([boundary + offset for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]])
    try:
        return ConvexHull(corners).volume
    except QhullError:
        return float(local.sum())


def _separate_touching(mask, min_area):
    """Distance-transform markers with prominence suppression and watershed.

    Reconstruction suppresses small peaks along a single long grain so those
    peaks do not each turn into a separate grain. Overlap remains ambiguous.
    """
    components, _ = ndimage.label(mask, np.ones((3, 3)))
    labels = np.zeros(mask.shape, dtype=np.int32)
    next_label = 1
    for component, box in enumerate(ndimage.find_objects(components), 1):
        if box is None:
            continue
        local = components[box] == component
        # A nearly convex isolated silhouette should remain one grain. This
        # prevents small intensity/edge irregularities from splitting source
        # grains that already have a clear outer boundary.
        if local.sum() < min_area * 2 or local.sum() / max(_hull_area(local), 1) >= 0.93:
            labels[box][local] = next_label
            next_label += 1
            continue
        padded = np.pad(local, 1)
        distance = ndimage.distance_transform_edt(padded)
        typical_radius = float(np.percentile(distance[padded], 90))
        prominence = max(1.0, 0.35 * typical_radius)
        reconstruction = np.maximum(distance - prominence, 0)
        for _ in range(max(padded.shape) * 2):
            expanded = np.minimum(distance, ndimage.grey_dilation(reconstruction, size=(3, 3)))
            if np.array_equal(expanded, reconstruction):
                break
            reconstruction = expanded
        peaks = (distance - reconstruction >= prominence - 1e-6) & padded
        seeds, seed_count = ndimage.label(peaks, np.ones((3, 3)))
        if seed_count <= 1:
            labels[box][local] = next_label
            next_label += 1
            continue
        basins = _watershed_distance(distance, seeds, padded)[1:-1, 1:-1]
        sizes = np.bincount(basins[local].clip(min=0), minlength=seed_count + 1)
        # Small basins around a rough grain edge are usually spurious peaks.
        # Compare to the largest basin, not the entire cluster, so a cluster
        # containing many similarly sized grains can retain all its markers.
        # A large basin may itself contain many grains. Cap the noise floor
        # using the typical local thickness, rather than that merged area.
        floor = max(min_area, min(0.08 * sizes[1:].max(), 0.8 * np.pi * typical_radius ** 2))
        keep = [seed for seed in range(1, seed_count + 1) if sizes[seed] >= floor]
        if len(keep) <= 1:
            labels[box][local] = next_label
            next_label += 1
            continue
        if len(keep) < seed_count:
            seeds[(seeds > 0) & ~np.isin(seeds, keep)] = 0
            basins = _watershed_distance(distance, seeds, padded)[1:-1, 1:-1]
        for seed in range(1, seed_count + 1):
            region = local & (basins == seed)
            if region.any():
                labels[box][region] = next_label
                next_label += 1
    return labels


def segment(rgb, settings=Settings()):
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("Expected an RGB uint8 image.")
    mode = resolve_background(rgb, settings.background)
    if mode == "pale":
        # White rice on a light surface is brighter than its immediate
        # surroundings. White top-hat removes slow illumination changes and
        # avoids classifying the entire pale background as a single object.
        gray = np.round(rgb @ np.array([0.299, 0.587, 0.114])).astype(np.uint8)
        smooth = ndimage.gaussian_filter(gray.astype(float), 0.7)
        window = max(15, min(gray.shape) // 8) | 1
        signal = np.clip(smooth - ndimage.grey_opening(smooth, size=(window, window)), 0, 255).astype(np.uint8)
        # The brightness condition rejects pale gaps next to dark shadows,
        # which can otherwise create top-hat responses resembling fragments.
        mask = (signal > max(4, _otsu(signal))) & (gray > _bright_otsu(gray))
        if settings.morphology:
            mask = ndimage.binary_opening(mask, np.ones((3, 3)), iterations=settings.morphology)
        mask = _fill_small_holes(mask, max(9, settings.min_area))
        labels, _ = ndimage.label(mask, np.ones((3, 3)))
    elif cv2 is not None:
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        kind = cv2.THRESH_BINARY if mode == "dark" else cv2.THRESH_BINARY_INV
        _, mask = cv2.threshold(gray, 0, 255, kind | cv2.THRESH_OTSU)
        if settings.morphology:
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel,
                                    iterations=settings.morphology)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel,
                                    iterations=settings.morphology)
        _, labels = cv2.connectedComponents(mask, connectivity=8)
    else:
        gray = np.round(rgb @ np.array([0.299, 0.587, 0.114])).astype(np.uint8)
        threshold = _otsu(gray)
        mask = gray > threshold if mode == "dark" else gray <= threshold
        if settings.morphology:
            mask = ndimage.binary_opening(mask, np.ones((3, 3)), iterations=settings.morphology)
            mask = ndimage.binary_closing(mask, np.ones((3, 3)), iterations=settings.morphology)
        labels, _ = ndimage.label(mask, np.ones((3, 3)))
    if settings.split_touching:
        labels = _separate_touching(labels > 0, settings.min_area)
    grains, rejected = [], []
    height, width = gray.shape
    for component, box in enumerate(ndimage.find_objects(labels), start=1):
        if box is None:
            continue
        ys, xs = box
        local = labels[box] == component
        area = int(local.sum())
        reason = None
        if area < settings.min_area:
            reason = "below_min_area"
        elif area > settings.max_area_fraction * height * width:
            reason = "above_max_area"
        elif settings.exclude_border and (ys.start <= settings.morphology or xs.start <= settings.morphology
                                          or ys.stop >= height-settings.morphology or xs.stop >= width-settings.morphology):
            reason = "touches_border"
        if reason:
            rejected.append({"area": area, "reason": reason})
            continue
        y, x = np.nonzero(local)
        points = np.column_stack([x, y]).astype(float)
        eigen = np.maximum(np.linalg.eigvalsh(np.cov(points, rowvar=False, bias=True)), 0) if len(points) > 1 else np.zeros(2)
        # Equivalent-ellipse diameters from second central moments, in pixels.
        minor, major = np.maximum(4 * np.sqrt(eigen), 1)
        hull_area = _hull_area(local)
        colors = rgb[box][local].astype(float)
        values = [area, major, minor, major / minor, min(area / hull_area, 1),
                  area / local.size, *colors.mean(axis=0), *colors.std(axis=0)]
        grains.append({"grain_id": len(grains) + 1,
                       "bbox": [xs.start, ys.start, xs.stop - xs.start, ys.stop - ys.start],
                       "centroid": [float(x.mean() + xs.start), float(y.mean() + ys.start)],
                       "features": dict(zip(FEATURES, map(float, values)))})
    # Keep watershed seams visible in the preview mask.
    visible = labels > 0
    if settings.split_touching:
        seam = (labels[:, 1:] != labels[:, :-1]) & (labels[:, 1:] > 0) & (labels[:, :-1] > 0)
        visible[:, 1:][seam] = False
        seam = (labels[1:, :] != labels[:-1, :]) & (labels[1:, :] > 0) & (labels[:-1, :] > 0)
        visible[1:, :][seam] = False
    return grains, rejected, visible.astype(np.uint8) * 255


def annotate(rgb, grains):
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    for grain in grains:
        x, y, w, h = grain["bbox"]
        label = grain.get("prediction", "unclassified")
        color = {"whole": "#34d399", "broken": "#fb7185"}.get(label, "#fbbf24")
        draw.rectangle((x, y, x + w, y + h), outline=color, width=2)
        draw.text((x, max(0, y - 13)), f'{grain["grain_id"]} {label}', fill=color)
    return image


def png_bytes(image):
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()
