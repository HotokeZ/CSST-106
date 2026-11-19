import csv
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from app import create_app
from bigascheck.demo import generate
from bigascheck.model import train
from bigascheck.samples import SampleCatalog, SampleError, build_samples

TEST_TEMP = Path(__file__).resolve().parents[1] / "outputs/test_temp"
TEST_TEMP.mkdir(parents=True, exist_ok=True)


class SampleLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=TEST_TEMP)
        cls.root = Path(cls.temp.name)
        manifest = generate(cls.root / "images")
        cls.models = cls.root / "models"
        train(manifest, cls.models)
        cls.features = cls.models / "features_and_splits.csv"
        cls.samples_root = cls.root / "splits"
        cls.summary = build_samples(cls.features, cls.samples_root)
        cls.catalog = SampleCatalog(cls.samples_root, cls.features)
        with cls.features.open(newline="", encoding="utf-8") as stream:
            cls.rows = list(csv.DictReader(stream))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def client(self):
        return create_app(self.models / "model.joblib", self.samples_root, self.features).test_client()

    def test_export_preserves_exact_split_membership(self):
        split_hashes = {name: {r["sha256"] for r in self.rows if r["split"] == name}
                        for name in ["train", "validation", "test"]}
        for name, hashes in split_hashes.items():
            files = list((Path(self.summary["directory"]) / name).rglob("*.png"))
            copied = {hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
            self.assertEqual(copied, hashes)
        self.assertFalse(split_hashes["train"] & split_hashes["test"])
        self.assertFalse(split_hashes["validation"] & split_hashes["test"])
        self.catalog.refresh()
        for item in self.catalog._items.values():
            self.assertEqual(item["split"], "test")
            self.assertTrue(set(item["source_sha256"]) <= split_hashes["test"])

    def test_pagination_filters_and_reference_counts(self):
        client = self.client()
        first = client.get("/api/samples?page_size=6").json
        self.assertEqual(len(first["items"]), 6)
        self.assertEqual(first["total"], self.summary["test_images"] + 3)
        second = client.get("/api/samples?page_size=6&page=2").json
        self.assertFalse({s["id"] for s in first["items"]} & {s["id"] for s in second["items"]})
        whole = client.get("/api/samples?label=whole").json
        self.assertTrue(all(s["label"] == "whole" for s in whole["items"]))
        mixed = client.get("/api/samples?label=mixed").json
        self.assertEqual(mixed["total"], 1)
        self.assertEqual(mixed["items"][0]["expected_whole"], 3)
        self.assertEqual(mixed["items"][0]["expected_broken"], 3)
        self.assertNotIn("image", mixed["items"][0])

    def test_sample_and_upload_follow_the_same_prediction_path(self):
        sample = next(s for s in self.catalog.list(page_size=24)["items"] if s["kind"] == "single")
        client = self.client()
        selected = client.post("/api/analyze", data={"sample_id": sample["id"]})
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected.json["sample"]["id"], sample["id"])
        path = self.catalog.asset(sample["id"])
        uploaded = client.post("/api/analyze", data={"image": (io.BytesIO(path.read_bytes()), "same.png")})
        self.assertEqual(uploaded.status_code, 200)
        self.assertEqual({k:v for k,v in selected.json["summary"].items() if k != "processing_ms"},
                         {k:v for k,v in uploaded.json["summary"].items() if k != "processing_ms"})
        self.assertEqual(selected.json["grains"], uploaded.json["grains"])
        composite = client.post("/api/analyze", data={"sample_id": "example-1"})
        self.assertEqual(composite.status_code, 200)
        self.assertEqual(composite.json["summary"]["detected"], 6)

    def test_training_images_invalid_choices_and_dual_inputs_are_rejected(self):
        client = self.client()
        training_hash = next(row["sha256"] for row in self.rows if row["split"] == "train")
        training_id = "test-" + training_hash[:16]
        self.assertEqual(client.get(f"/api/samples/{training_id}/image").status_code, 404)
        self.assertEqual(client.post("/api/analyze", data={"sample_id": training_id}).status_code, 404)
        self.assertEqual(client.get("/api/samples?page=0").status_code, 400)
        self.assertEqual(client.get("/api/samples?label=train").status_code, 400)
        self.assertEqual(client.get("/api/samples?page_size=100").status_code, 400)
        sample = self.catalog.list()["items"][0]
        response = client.post("/api/analyze", data={"sample_id": sample["id"],
                               "image": (io.BytesIO(b"ignored"), "image.png")})
        self.assertEqual(response.status_code, 400)

    def test_assets_and_missing_library(self):
        client = self.client()
        sample = self.catalog.list()["items"][0]
        for suffix in ["", "?thumbnail=1"]:
            response = client.get(f'/api/samples/{sample["id"]}/image{suffix}')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content_type.startswith("image/"))
            response.close()
        missing = create_app(self.models / "model.joblib", self.root / "missing", self.features).test_client()
        self.assertEqual(missing.get("/api/samples").status_code, 503)
        self.assertEqual(missing.get("/").status_code, 200)

    def test_changed_split_disables_the_old_gallery(self):
        changed_table = self.root / "changed.csv"
        changed_table.write_bytes(self.features.read_bytes() + b"\n")
        changed = SampleCatalog(self.samples_root, changed_table)
        with self.assertRaisesRegex(SampleError, "split has changed"):
            changed.list()


if __name__ == "__main__":
    unittest.main()
