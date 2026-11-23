"""Local bright-object extraction for nonuniform photographic backgrounds."""
import numpy as np
from scipy import ndimage


def adaptive_foreground(rgb):
    # Grains remain small bright structures after local illumination removal.
    # Smoothing precedes subtraction so cloth weave does not dominate maxima.
    gray = rgb @ np.array([.299, .587, .114])
    smooth = ndimage.gaussian_filter(gray.astype(np.float32), 2.2)
    background = ndimage.gaussian_filter(smooth, 20.)
    signal = smooth - background
    noise = 1.4826 * np.median(np.abs(signal - np.median(signal)))
    threshold = max(6., 4.5 * noise)
    mask = signal > threshold
    # White/cream rice may be yellowish, but strongly red, green or blue
    # fabric is not rice. Broad ratios tolerate shadows and warm illumination;
    # they are deliberately not a hard 'pure white' threshold.
    color = ndimage.gaussian_filter(rgb.astype(np.float32), (2.2, 2.2, 0))
    red, green, blue = color[..., 0], color[..., 1], color[..., 2]
    median_color = np.median(color.reshape(-1, 3), axis=0)
    blue_surface = median_color[2] > 1.08*median_color[0] and median_color[2] > 1.03*median_color[1]
    red_blue_floor = .95 if blue_surface else .65
    neutral = ((red >= .65*green) & (red >= red_blue_floor*blue) &
               (green >= .55*red) & (green >= .6*blue) &
               (blue >= .3*np.maximum(red, green)))
    mask &= neutral
    if blue_surface:
        # Bright islands survive; broad phone-shadow transitions do not.
        island = ndimage.white_tophat(smooth, size=(41, 41))
        mask &= island > max(8., threshold)
    mask = ndimage.binary_opening(mask, np.ones((3, 3)))
    mask = ndimage.binary_closing(mask, np.ones((3, 3)))
    if blue_surface:
        labels, count = ndimage.label(mask, np.ones((3, 3)))
        if count:
            peaks = ndimage.maximum(island, labels, np.arange(count + 1))
            keep = peaks >= max(16., 1.5 * threshold)
            keep[0] = False
            mask = keep[labels]
    return mask
