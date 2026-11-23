import copy
import unittest

import numpy as np

from bigascheck.local_training import (partition, fit_calibration, calibrated_predictions,
                                      calibration_values)


def grain(aspect, scale=1):
    return {"features": {"aspect_ratio": aspect, "major_axis": aspect*10*scale,
                         "area": aspect*100*scale*scale}}


class LocalTrainingTests(unittest.TestCase):
    def test_partition_keeps_corrected_examples_in_training_and_groups_unknown(self):
        rows = [{"photo_id": f"local_{i:03d}", "sha256": f"{i:064x}", "group_id": "",
                 "condition": "Low Light, Shadow, Different BG" if i <= 10 else "Overlap" if i <= 21 else "Separated"}
                for i in range(1, 34)]
        before = copy.deepcopy(rows)
        result = partition(rows)
        self.assertEqual(rows, before)
        self.assertEqual({s: list(result.values()).count(s) for s in ["train", "test", "sample"]},
                         {"train":18,"test":10,"sample":5})
        for photo in ["local_005", "local_007", "local_021", "local_024"]:
            self.assertEqual(result[photo], "train")
        test = next(r for r in rows if result[r["photo_id"]] == "test")
        train = next(r for r in rows if result[r["photo_id"]] == "train")
        test["group_id"] = train["group_id"] = "confirmed-same-capture"
        with self.assertRaisesRegex(ValueError, "capture group"):
            partition(rows)

    def test_combined_training_uses_source_labels_without_inventing_crop_labels(self):
        bags = [{"photo_id": str(i), "split": "train", "whole": 2, "broken": 2,
                 "source_broken": 4, "grains": [grain(1),grain(1.2),grain(3),grain(4)]} for i in range(8)]
        source = {"values": np.array([1, 1.2, 3, 4.0]), "labels": np.array(["broken", "broken", "whole", "whole"])}
        before = copy.deepcopy(bags)
        fit = fit_calibration(bags, source)
        self.assertEqual(fit["source_training_instances"], 4)
        self.assertGreater(fit["source_loss_weight"], 0)
        self.assertTrue(fit["enabled"])
        self.assertEqual(bags, before)
        predicted = calibrated_predictions(bags[0]["grains"], fit, "adaptive", "decision_tree")
        self.assertEqual(list(predicted), ["broken", "broken", "whole", "whole"])
        self.assertIsNone(calibrated_predictions(bags[0]["grains"], fit, "adaptive", "baseline"))
        self.assertIsNone(calibrated_predictions(bags[0]["grains"], fit, "legacy", "decision_tree"))
        self.assertIsNone(calibrated_predictions(bags[0]["grains"][:1], fit, "adaptive", "decision_tree"))
        bags[0]["split"] = "test"
        with self.assertRaisesRegex(ValueError, "training photographs only"):
            fit_calibration(bags, source)

    def test_all_calibration_features_are_invariant_to_uniform_image_scale(self):
        grains = [grain(1), grain(2), grain(4)]
        scaled = [grain(1,3), grain(2,3), grain(4,3)]
        for feature in ["relative_major_axis", "relative_sqrt_area", "aspect_ratio"]:
            np.testing.assert_allclose(calibration_values(grains, feature), calibration_values(scaled, feature))


if __name__ == "__main__":
    unittest.main()
