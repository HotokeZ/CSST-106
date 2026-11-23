import unittest
import numpy as np
from bigascheck.vision import _separate_touching


class IntensitySeparationTests(unittest.TestCase):
    def test_two_compact_lit_patches_do_not_split_one_silhouette(self):
        mask = np.zeros((70, 120), dtype=bool)
        mask[15:55, 15:95] = True
        intensity = np.zeros(mask.shape)
        intensity[mask] = 100
        intensity[15:55, 54:56] = 25
        self.assertEqual(_separate_touching(mask, 100, intensity=intensity).max(), 1)

    def test_dark_seam_separates_two_large_bright_interiors(self):
        mask = np.zeros((70, 150), dtype=bool)
        mask[15:55, 15:135] = True
        intensity = np.zeros(mask.shape)
        intensity[mask] = 100
        intensity[34:36, 15:135] = 25
        labels = _separate_touching(mask, 100, intensity=intensity)
        self.assertEqual(labels.max(), 2)
        self.assertNotEqual(labels[25, 70], labels[45, 70])

    def test_uniform_grain_and_small_highlight_do_not_split(self):
        mask = np.zeros((70, 150), dtype=bool)
        mask[20:45, 15:135] = True
        intensity = np.zeros(mask.shape)
        intensity[mask] = 100
        intensity[25:28, 70:75] = 200
        self.assertEqual(_separate_touching(mask, 100, intensity=intensity).max(), 1)
