import unittest
import numpy as np
from bigascheck.vision import _merge_unconstricted_basins


class BasinMergingTests(unittest.TestCase):
    def test_parallel_elongated_regions_survive_a_broad_contact(self):
        basins = np.ones((24, 80), dtype=np.int32)
        basins[12:] = 2
        result, count = _merge_unconstricted_basins(
            basins, np.ones(basins.shape), np.ones(basins.shape, dtype=bool), 2)
        self.assertEqual(count, 2)
        self.assertTrue(np.all(result[:12] != result[12:]))

    def test_lengthwise_fragments_of_one_grain_still_merge(self):
        basins = np.ones((16, 100), dtype=np.int32)
        basins[:, 50:] = 2
        _, count = _merge_unconstricted_basins(
            basins, np.ones(basins.shape), np.ones(basins.shape, dtype=bool), 2)
        self.assertEqual(count, 1)
