"""Materialize the existing model split and expose only test images for demos."""
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps


class SampleError(ValueError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_split_table(path):
    path = Path(path).resolve()
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"image", "label", "split", "sha256"}.issubset(reader.fieldnames or []):
            raise SampleError("The feature table must include image, label, split and sha256.")
        rows = list(reader)
    if not rows:
        raise SampleError("The split table is empty.")
    seen = set()
    group_splits = {}
    for row in rows:
        if row["split"] not in {"train", "validation", "test"} or row["label"] not in {"whole", "broken"}:
            raise SampleError("Unexpected split or label in feature table.")
        value = row["sha256"]
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value) or value in seen:
            raise SampleError("Image hashes must be valid and unique across all splits.")
        seen.add(value)
        if row.get("group_id"):
            group_splits.setdefault(row["group_id"], set()).add(row["split"])
    if any(len(splits) > 1 for splits in group_splits.values()):
        raise SampleError("A known capture group appears in more than one split.")
    if {r["split"] for r in rows} != {"train", "validation", "test"}:
        raise SampleError("The existing train, validation and test assignments are required.")
    return rows


def _thumbnail(source, target):
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((224, 144))
        canvas = Image.new("RGB", (240, 160), (18, 24, 19))
        canvas.paste(image, ((240 - image.width) // 2, (160 - image.height) // 2))
        canvas.save(target, format="JPEG", quality=85)


def build_samples(feature_table="artifacts/features_and_splits.csv", output="data/splits"):
    """Keep the model's assignments; never reshuffle trained-on images into test."""
    feature_table, output = Path(feature_table).resolve(), Path(output).resolve()
    rows = read_split_table(feature_table)
    fingerprint = digest(feature_table)
    version = fingerprint[:16]
    dataset_root = output / version
    dataset_root.mkdir(parents=True, exist_ok=True)
    samples = []
    test_sources = []
    counts = {name: Counter() for name in ["train", "validation", "test"]}
    for index, row in enumerate(rows):
        source = (feature_table.parent / row["image"]).resolve()
        if not source.is_file() or digest(source) != row["sha256"]:
            raise SampleError(f"Source image missing or changed: {source.name}")
        relative = Path(version) / row["split"] / row["label"] / (row["sha256"][:16] + source.suffix.lower())
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if digest(target) != row["sha256"]:
                raise SampleError(f"An existing split image has changed: {target.name}")
        else:
            shutil.copy2(source, target)
        counts[row["split"]][row["label"]] += 1
        if row["split"] == "test":
            sample_id = "test-" + row["sha256"][:16]
            thumbnail = Path(version) / "thumbnails" / (sample_id + ".jpg")
            (output / thumbnail).parent.mkdir(parents=True, exist_ok=True)
            if not (output / thumbnail).is_file():
                _thumbnail(target, output / thumbnail)
            number = counts["test"][row["label"]]
            item = {"id": sample_id, "title": f'{row["label"].title()} grain {number:03d}',
                    "kind": "single", "label": row["label"], "split": "test",
                    "image": relative.as_posix(), "thumbnail": thumbnail.as_posix(),
                    "sha256": row["sha256"], "source_sha256": [row["sha256"]],
                    "expected_whole": int(row["label"] == "whole"),
                    "expected_broken": int(row["label"] == "broken"),
                    "note": "Reference label supplied by the dataset."}
            samples.append(item)
            test_sources.append(item)
        if (index + 1) % 500 == 0:
            print(f"Prepared split images: {index + 1}/{len(rows)}", flush=True)

    examples = []
    whole = [s for s in test_sources if s["label"] == "whole"]
    broken = [s for s in test_sources if s["label"] == "broken"]
    if len(whole) >= 6 and len(broken) >= 6:
        selections = [("mixed", "Mixed sample", [*whole[:3], *broken[:3]]),
                      ("whole", "Whole-grain sample", whole[:6]),
                      ("broken", "Broken-grain sample", broken[:6])]
        for index, (label, title, selected) in enumerate(selections, 1):
            # No resize: preserve each source grain's pixel dimensions.
            images = []
            for item in selected:
                with Image.open(output / item["image"]) as image:
                    images.append(image.convert("RGB").copy())
            cell_w, cell_h = max(im.width for im in images) + 24, max(im.height for im in images) + 24
            canvas = Image.new("RGB", (cell_w * 3, cell_h * 2), "black")
            for pos, image in enumerate(images):
                canvas.paste(image, ((pos % 3) * cell_w + (cell_w-image.width)//2,
                                     (pos // 3) * cell_h + (cell_h-image.height)//2))
            relative = Path(version) / "examples" / f"sample-{index}.png"
            (output / relative).parent.mkdir(parents=True, exist_ok=True)
            canvas.save(output / relative)
            thumbnail = Path(version) / "thumbnails" / f"sample-{index}.jpg"
            _thumbnail(output / relative, output / thumbnail)
            examples.append({"id": f"example-{index}", "title": title, "kind": "composite",
                             "label": label, "split": "test", "image": relative.as_posix(),
                             "thumbnail": thumbnail.as_posix(), "sha256": digest(output / relative),
                             "source_sha256": [s["sha256"] for s in selected],
                             "expected_whole": sum(s["expected_whole"] for s in selected),
                             "expected_broken": sum(s["expected_broken"] for s in selected),
                             "note": "Assembled from six held-out test grains. This is a composite, not a captured multi-grain photograph."})
    catalog = {"format_version": 1, "dataset_version": version, "source_fingerprint": fingerprint,
               "split_counts": {name: dict(value) for name, value in counts.items()},
               "samples": examples + samples,
               "note": "Existing model split preserved. Only test images are exposed to the sample gallery."}
    temporary = output / "catalog.json.tmp"
    temporary.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    temporary.replace(output / "catalog.json")
    for name in ["train", "validation", "test"]:
        with (dataset_root / (name + ".csv")).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, ["image", "label", "split", "sha256"])
            writer.writeheader()
            for row in rows:
                if row["split"] == name:
                    source = Path(row["image"])
                    writer.writerow({"image": f'{name}/{row["label"]}/{row["sha256"][:16]}{source.suffix.lower()}',
                                     "label": row["label"], "split": name, "sha256": row["sha256"]})
    return {"directory": str(dataset_root), "split_counts": catalog["split_counts"],
            "test_images": len(test_sources), "composite_examples": len(examples),
            "gallery_samples": len(catalog["samples"])}


class SampleCatalog:
    def __init__(self, root, feature_table):
        self.root = Path(root).resolve()
        self.feature_table = Path(feature_table).resolve()
        self._stamp = None
        self._items = {}
        self.counts = {}

    def refresh(self):
        catalog_path = self.root / "catalog.json"
        if not catalog_path.is_file() or not self.feature_table.is_file():
            raise SampleError("Test samples are not ready. Run python -m bigascheck prepare-samples.")
        stamp = (catalog_path.stat().st_mtime_ns, self.feature_table.stat().st_mtime_ns,
                 catalog_path.stat().st_size, self.feature_table.stat().st_size)
        if stamp == self._stamp:
            return
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            if catalog.get("format_version") != 1 or catalog.get("source_fingerprint") != digest(self.feature_table):
                raise SampleError("The dataset split has changed. Rebuild the test samples with prepare-samples.")
            rows = read_split_table(self.feature_table)
            test_rows = {r["sha256"]: r["label"] for r in rows if r["split"] == "test"}
            version = catalog["dataset_version"]
            if version != catalog["source_fingerprint"][:16]:
                raise SampleError("Invalid sample catalog version.")
            items = {}
            for item in catalog["samples"]:
                if item["split"] != "test" or not item["source_sha256"] or any(s not in test_rows for s in item["source_sha256"]):
                    raise SampleError("A gallery sample is not from the held-out test split.")
                if item["kind"] == "single" and (item["sha256"] not in test_rows or item["label"] != test_rows[item["sha256"]]):
                    raise SampleError("Invalid test sample reference label.")
                allowed = "test" if item["kind"] == "single" else "examples"
                image = (self.root / item["image"]).resolve()
                thumbnail = (self.root / item["thumbnail"]).resolve()
                if not image.is_relative_to(self.root / version / allowed) or not thumbnail.is_relative_to(self.root / version / "thumbnails"):
                    raise SampleError("Invalid sample asset path.")
                if item["id"] in items:
                    raise SampleError("Duplicate sample identifier.")
                items[item["id"]] = item
            self._items, self.counts, self._stamp = items, catalog["split_counts"], stamp
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise SampleError("The test sample catalog is invalid. Rebuild it with prepare-samples.") from exc

    @staticmethod
    def public(item):
        return {k: item[k] for k in ["id", "title", "kind", "label", "split", "expected_whole", "expected_broken", "note"]}

    def list(self, label="all", page=1, page_size=6):
        self.refresh()
        if label not in {"all", "whole", "broken", "mixed"} or page < 1 or not 1 <= page_size <= 24:
            raise SampleError("Invalid sample filter or page.")
        items = [item for item in self._items.values() if label == "all" or item["label"] == label]
        start = (page - 1) * page_size
        return {"items": [self.public(item) for item in items[start:start+page_size]],
                "total": len(items), "page": page, "page_size": page_size, "split_counts": self.counts}

    def get(self, sample_id):
        self.refresh()
        if sample_id not in self._items:
            raise KeyError(sample_id)
        return self._items[sample_id]

    def asset(self, sample_id, thumbnail=False):
        item = self.get(sample_id)
        path = self.root / item["thumbnail" if thumbnail else "image"]
        if not path.is_file():
            raise SampleError("This sample file is missing. Rebuild the sample library.")
        if not thumbnail and digest(path) != item["sha256"]:
            raise SampleError("This sample image has changed. Rebuild the sample library.")
        return path
