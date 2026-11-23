import unittest
import numpy as np
from bigascheck.vision import _merge_unconstricted_basins


class BasinMergingTests(unittest.TestCase):
    def test_offset_fragments_do_not_qualify_as_side_by_side_grains(self):
        basins = np.zeros((24, 110), dtype=np.int32)
        basins[:12, :80] = 1
        basins[12:, 30:] = 2
        _, count = _merge_unconstricted_basins(
            basins, np.ones(basins.shape), basins > 0, 2)
        self.assertEqual(count, 1)

    def test_broad_contact_without_a_neck_is_not_evidence_of_two_grains(self):
        basins = np.ones((24, 80), dtype=np.int32)
        basins[12:] = 2
        result, count = _merge_unconstricted_basins(
            basins, np.ones(basins.shape), np.ones(basins.shape, dtype=bool), 2)
        self.assertEqual(count, 1)
        self.assertTrue(np.all(result[:12] == result[12:]))

    def test_lengthwise_fragments_of_one_grain_still_merge(self):
        basins = np.ones((16, 100), dtype=np.int32)
        basins[:, 50:] = 2
        _, count = _merge_unconstricted_basins(
            basins, np.ones(basins.shape), np.ones(basins.shape, dtype=bool), 2)
        self.assertEqual(count, 1)
