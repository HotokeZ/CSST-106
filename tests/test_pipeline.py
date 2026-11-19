import csv
import io
import tempfile
import unittest
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image, ImageDraw

from app import create_app
from bigascheck.dataset import audit, extract_archive, load_manifest, prepare_peruvian
from bigascheck.demo import generate
from bigascheck.evaluation import evaluate_samples
from bigascheck.model import analyze, grouped_split, load_model, train, train_shape, shape_matrix
from bigascheck.vision import Settings, load_rgb, png_bytes, segment

TEST_TEMP = Path(__file__).resolve().parents[1] / "outputs" / "test_temp"
TEST_TEMP.mkdir(parents=True, exist_ok=True)


def grain_image(light=False):
    image = Image.new("RGB", (300, 200), "white" if light else "black")
    draw = ImageDraw.Draw(image)
    for x in [50, 150, 250]:
        draw.ellipse((x-25, 80, x+25, 95), fill="black" if light else "white")
    return image


class VisionTests(unittest.TestCase):
    def test_empty_surface_inside_a_grain_ring_is_not_filled(self):
        image = Image.new("RGB", (300, 300), (190, 190, 190))
        draw = ImageDraw.Draw(image)
        draw.rectangle((60, 60, 240, 240), outline=(245, 240, 230), width=12)
        _, _, mask = segment(np.array(image), Settings(background="pale"))
        self.assertEqual(mask[150, 150], 0)
        self.assertGreater(mask[65, 150], 0)

    def test_shape_features_ignore_uniform_scale_and_rgb(self):
        from bigascheck.vision import FEATURES
        raw = np.array([[200, 40, 10, 4, .95, .7, 220, 220, 200, 10, 10, 10]], float)
        changed = raw.copy()
        changed[:, FEATURES.index("area")] *= 16
        changed[:, FEATURES.index("major_axis")] *= 4
        changed[:, FEATURES.index("minor_axis")] *= 4
        changed[:, 6:] = 100
        np.testing.assert_allclose(shape_matrix(raw), shape_matrix(changed))

    def test_white_grains_on_pale_surface(self):
        rgb = np.zeros((300, 400, 3), np.uint8)
        # Slowly changing illumination and bright rice, including soft shadows.
        rgb[:] = np.linspace(175, 205, 400).astype(np.uint8)[None, :, None]
        image = Image.fromarray(rgb)
        draw = ImageDraw.Draw(image)
        for y in [65, 150, 235]:
            for x in [65, 155, 245, 335]:
                draw.ellipse((x-26, y-5, x+29, y+15), fill=(160, 158, 154))
                draw.ellipse((x-25, y-10, x+25, y+8), fill=(244, 239, 224))
        grains, _, _ = segment(np.array(image), Settings(background="auto", split_touching=True))
        self.assertEqual(len(grains), 12)

    def test_touching_grains_are_separated_without_splitting_a_single_grain(self):
        image = Image.new("RGB", (320, 200), "black")
        draw = ImageDraw.Draw(image)
        draw.ellipse((40, 75, 130, 105), fill="white")
        draw.ellipse((123, 75, 213, 105), fill="white")
        draw.ellipse((245, 50, 275, 150), fill="white")
        self.assertEqual(len(segment(np.array(image), Settings())[0]), 2)
        self.assertEqual(len(segment(np.array(image), Settings(split_touching=True))[0]), 3)

    def test_counts_and_polarity(self):
        for light in [False, True]:
            grains, rejected, _ = segment(np.array(grain_image(light)), Settings(background="light" if light else "dark"))
            self.assertEqual(len(grains), 3)
            self.assertFalse(rejected)
            for grain in grains:
                self.assertGreater(grain["features"]["aspect_ratio"], 2)
                self.assertLessEqual(grain["features"]["solidity"], 1)

    def test_blank_is_not_zero_percent_broken(self):
        result, _ = analyze(np.zeros((200, 200, 3), np.uint8))
        self.assertEqual(result["summary"]["detected"], 0)
        self.assertIsNone(result["summary"]["broken_percentage"])
        self.assertFalse(result["summary"]["classified"])

    def test_border_and_noise_rejected(self):
        image = Image.new("RGB", (200, 200), "black")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 80, 40, 100), fill="white")
        draw.rectangle((100, 100, 101, 101), fill="white")
        grains, rejected, _ = segment(np.array(image), Settings(morphology=0))
        self.assertEqual(grains, [])
        self.assertEqual({r["reason"] for r in rejected}, {"touches_border", "below_min_area"})

    def test_group_disjointness(self):
        groups = np.repeat([f"session_{n}" for n in range(14)], 4)
        labels = np.tile(["whole", "broken", "whole", "broken"], 14)
        tr, va, te = grouped_split(labels, groups)
        for a, b in [(tr, va), (tr, te), (va, te)]:
            self.assertFalse(set(groups[a]) & set(groups[b]))
        self.assertEqual(len(set(tr) | set(va) | set(te)), len(groups))


class ArchiveTests(unittest.TestCase):
    def test_source_import_preserves_review_status_and_removes_duplicates(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
            root = Path(folder)
            for name in ["entero", "quebrado", "tiza"]:
                (root / "dataset" / name).mkdir(parents=True)
            grain_image().save(root / "dataset/entero/a.png")
            grain_image().save(root / "dataset/entero/duplicate.png")
            grain_image(light=True).save(root / "dataset/quebrado/b.png")
            grain_image().save(root / "dataset/tiza/excluded.png")
            manifest = root / "manifest.csv"
            report = prepare_peruvian(root, manifest)
            self.assertEqual(report["images"], 2)
            self.assertEqual(len(report["duplicates_removed"]), 1)
            with self.assertRaisesRegex(ValueError, "verify"):
                load_manifest(manifest)
            records = load_manifest(manifest, source_labels=True)
            self.assertTrue(all(r["verified"] == "false" and not r["group_id"] for r in records))

    def test_cross_label_duplicates_are_excluded_from_both_classes(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
            root = Path(folder)
            for name in ["entero", "quebrado"]:
                (root / "dataset" / name).mkdir(parents=True)
                grain_image().save(root / "dataset" / name / "conflict.png")
            grain_image(light=True).save(root / "dataset/entero/unique.png")
            report = prepare_peruvian(root, root / "source.csv")
            self.assertEqual(report["images"], 1)
            self.assertEqual(len(report["conflicting_label_pairs_excluded"]), 1)

    def test_unsafe_archive_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
            root = Path(folder)
            archive = root / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as stream:
                stream.writestr("safe.txt", "ok")
                stream.writestr("../outside.txt", "bad")
            with self.assertRaises(ValueError):
                extract_archive(archive, root / "out")
            self.assertFalse((root / "out" / "safe.txt").exists())

    def test_audit_does_not_invent_labels(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
            archive = Path(folder) / "data.zip"
            with zipfile.ZipFile(archive, "w") as stream:
                stream.writestr("variety_a/grain.png", b"image")
            result = audit(archive)
            self.assertEqual(result["images"], 1)
            self.assertFalse(result["labels_verified"])


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=TEST_TEMP)
        cls.root = Path(cls.temp.name)
        cls.manifest = generate(cls.root / "demo")
        cls.output = cls.root / "model"
        cls.report = train(cls.manifest, cls.output)
        cls.bundle = load_model(cls.output / "model.joblib")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_full_training_and_sample_evaluation(self):
        evaluation = evaluate_samples(self.root / "demo/samples.csv", self.bundle)
        self.assertEqual(evaluation["samples"][0]["detected"], 12)
        self.assertEqual(evaluation["count_mae"], 0)
        self.assertEqual(evaluation["percentage_evaluable_images"], 1)
        self.assertTrue((self.output / "features_and_splits.csv").exists())

    def test_manifest_duplicate_and_unverified_rejected(self):
        with Path(self.manifest).open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        path = self.root / "demo/bad.csv"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, rows[0].keys())
            writer.writeheader()
            writer.writerows([rows[0], rows[0]])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_manifest(path)
        rows[0]["verified"] = "false"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, rows[0].keys())
            writer.writeheader()
            writer.writerow(rows[0])
        with self.assertRaisesRegex(ValueError, "verify"):
            load_manifest(path)

    def test_api_without_model_and_invalid_upload(self):
        client = create_app(self.root / "absent.joblib").test_client()
        self.assertEqual(client.get("/").status_code, 200)
        self.assertEqual(client.post("/api/analyze").status_code, 400)
        response = client.post("/api/analyze", data={"image": (io.BytesIO(b"not an image"), "bad.png")})
        self.assertEqual(response.status_code, 400)
        response = client.post("/api/analyze", data={"image": (io.BytesIO(png_bytes(grain_image())), "grains.png")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["summary"]["detected"], 3)
        self.assertIsNone(response.json["summary"]["broken_percentage"])

    def test_api_with_trained_model(self):
        client = create_app(self.output / "model.joblib").test_client()
        self.assertTrue(client.get("/api/status").json["trained"])
        image = (self.root / "demo/sample.png").read_bytes()
        response = client.post("/api/analyze", data={"image": (io.BytesIO(image), "sample.png")})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["summary"]["classified"])
        self.assertEqual(response.json["summary"]["detected"], 12)
        self.assertIn("annotated_png", response.json)
        self.assertGreaterEqual(response.json["summary"]["processing_ms"], 0)
        self.assertTrue(all(0 <= g["model_score"] <= 1 for g in response.json["grains"]))

    def test_batch_runner_and_reproducible_evaluation(self):
        from bigascheck.runner import run_path
        from bigascheck.checkpoints import evaluate_checkpoint
        batch = run_path(self.root / "demo/sample.png", self.root / "batch", self.output / "model.joblib")
        self.assertEqual(batch[0]["status"], "ok")
        self.assertEqual(batch[0]["detected"], 12)
        report = evaluate_checkpoint(self.output / "model.joblib", self.output / "features_and_splits.csv",
                                     "validation", self.root / "evaluation", speed_images=2)
        self.assertEqual(report["instances"], self.report["split"]["validation"]["instances"])
        self.assertEqual(report["speed"]["images"], 2)
        self.assertEqual(report["speed"]["warmup_runs"], 3)
        self.assertTrue((self.root / "evaluation/decision_tree_confusion_matrix.png").is_file())

    def test_background_override_is_honored_with_loaded_model(self):
        client = create_app(self.output / "model.joblib").test_client()
        image = Image.new("RGB", (400, 250), (195, 195, 195))
        draw = ImageDraw.Draw(image)
        for x in [70, 190, 310]:
            draw.ellipse((x-30, 90, x+30, 110), fill=(245, 240, 230))
        response = client.post("/api/analyze", data={"image": (io.BytesIO(png_bytes(image)), "pale.png"),
                                                  "background": "pale"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["summary"]["detected"], 3)
        self.assertFalse(response.json["summary"]["classified"])
        self.assertIsNone(response.json["summary"]["broken_percentage"])
        self.assertEqual(response.json["summary"]["background_used"], "pale")

    def test_scale_mismatch_does_not_label_every_small_grain_broken(self):
        image = Image.new("RGB", (400, 250), "black")
        draw = ImageDraw.Draw(image)
        for x in [70, 190, 310]:
            draw.ellipse((x-6, 90, x+6, 97), fill="white")
        result, _ = analyze(np.array(image), self.bundle)
        self.assertGreater(result["summary"]["detected"], 0)
        self.assertFalse(result["summary"]["classified"])
        self.assertIsNone(result["summary"]["broken_percentage"])

    def test_shape_classifier_returns_predictions_on_pale_background(self):
        output = self.root / "shape_model"
        report = train_shape(self.output / "features_and_splits.csv", output)
        self.assertEqual(report["feature_mode"], "shape")
        client = create_app(output / "model.joblib").test_client()
        image = Image.new("RGB", (400, 250), (195, 195, 195))
        draw = ImageDraw.Draw(image)
        for x in [70, 190, 310]:
            draw.ellipse((x-30, 90, x+30, 110), fill=(245, 240, 230))
        response = client.post("/api/analyze", data={"image": (io.BytesIO(png_bytes(image)), "pale.png")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["summary"]["detected"], 3)
        self.assertTrue(response.json["summary"]["classified"])
        self.assertEqual(response.json["summary"]["classification_basis"], "shape_only")
        self.assertTrue(all(g["prediction"] in {"whole", "broken"} for g in response.json["grains"]))

    @unittest.skipUnless((Path(__file__).resolve().parents[1] / "inputs/rice_test_2.jpg").is_file(), "Local regression photo is not available")
    def test_local_crowded_photo_no_longer_returns_only_thirteen_regions(self):
        project = Path(__file__).resolve().parents[1]
        if not (project / "artifacts/model.joblib").is_file():
            self.skipTest("Local trained model is not available")
        bundle = load_model(project / "artifacts/model.joblib")
        if bundle.get("feature_mode") != "shape":
            self.skipTest("Local shape model is not available")
        result, _ = analyze(load_rgb(project / "inputs/rice_test_2.jpg"), bundle,
                            Settings(background="auto", max_area_fraction=.6, split_touching=True))
        self.assertGreater(result["summary"]["detected"], 50)
        self.assertTrue(result["summary"]["classified"])
        self.assertTrue(result["summary"]["classification_experimental"])
        self.assertEqual(result["summary"]["whole"] + result["summary"]["broken"], result["summary"]["detected"])

    @unittest.skipUnless((Path(__file__).resolve().parents[1] / "outputs/dataset_composite_check.png").is_file(), "Six-grain source fixture is not available")
    def test_real_isolated_grains_are_not_split_into_extra_fragments(self):
        project = Path(__file__).resolve().parents[1]
        grains, _, _ = segment(load_rgb(project / "outputs/dataset_composite_check.png"),
                               Settings(background="auto", max_area_fraction=.6, split_touching=True))
        self.assertEqual(len(grains), 6)

    def test_training_capture_overlap_rejected(self):
        path = self.root / "demo/leak.csv"
        group = self.report["split"]["train"]["groups"][0]
        path.write_text(f"image,group_id,actual_whole,actual_broken\nsample.png,{group},8,4\n")
        with self.assertRaisesRegex(ValueError, "overlap"):
            evaluate_samples(path, self.bundle)

    def test_source_training_is_explicitly_exploratory(self):
        with Path(self.manifest).open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        path = self.root / "demo/source.csv"
        for row in rows:
            row.update(group_id="", verified="false", label_source="dataset_folder")
        (self.root / "demo/empty.png").write_bytes(b"")
        rows.append({"image": "empty.png", "label": "broken", "group_id": "", "verified": "false",
                     "label_source": "dataset_folder"})
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        report = train(path, self.root / "source_model", source_labels=True)
        self.assertEqual(report["training_mode"], "exploratory_source_labels")
        self.assertEqual(report["split_unit"], "image")
        self.assertIsNone(report["dataset"]["groups"])
        self.assertEqual(report["dataset"]["segmentation_exclusions"], 1)
        self.assertTrue(all(not part["groups"] for part in report["split"].values()))


if __name__ == "__main__":
    unittest.main()
