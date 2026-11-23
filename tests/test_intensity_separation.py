import unittest
import numpy as np
from bigascheck.vision import _separate_touching
from pathlib import Path


class IntensitySeparationTests(unittest.TestCase):
    @unittest.skipUnless((Path(__file__).resolve().parents[1] / 'inputs/separation_case/IMG_20261121_005008.jpg').is_file(), 'Private regression photo is not distributed')
    def test_reported_crop_has_three_middle_grains_without_extra_fragment(self):
        from bigascheck.vision import load_rgb, Settings, segment
        from bigascheck.cropping import crop_rgb
        image = load_rgb(Path(__file__).resolve().parents[1] / 'inputs/separation_case/IMG_20261121_005008.jpg')
        rgb, _ = crop_rgb(image, {'height': .6230958380921761, 'width': .42066420664206644,
                                 'x': .30885613360528136, 'y': .2627764052782363})
        grains, _, _ = segment(rgb, Settings(background='auto', detector='adaptive', split_touching=True, max_area_fraction=.6))
        self.assertEqual(len(grains), 21)
        middle = [g for g in grains if 300 < g['centroid'][0] < 380 and 280 < g['centroid'][1] < 365]
        self.assertEqual(len(middle), 3)
        for point in [(326, 300), (337, 321), (349, 340)]:
            self.assertEqual(sum(np.linalg.norm(np.array(g['centroid']) - point) < 12 for g in middle), 1)

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
