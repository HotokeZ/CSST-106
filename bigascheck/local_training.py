"""Local photo partitions and count-supervised integrity calibration.

Photo totals supervise a decision threshold, never individual crop labels. These
photos have already guided development; their test partition is not untouched.
"""
import csv
import hashlib
import json
import random
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .samples import SampleCatalog, SampleError, _thumbnail, digest

CAUTION = ("Development partition: these photographs were inspected previously. "
           "Capture/sample groups are unknown; image separation does not establish independence.")
FEATURE_NAMES = ("relative_major_axis", "relative_sqrt_area", "aspect_ratio")


def read_rows(manifest):
    with Path(manifest).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def partition(rows, seed=42):
    if len(rows) != 33 or len({r["photo_id"] for r in rows}) != 33:
        raise ValueError("This protocol requires the original 33 unique local photographs.")
    # User-corrected examples belong in training, never in a claimed blind test.
    reserved = {"local_005", "local_007", "local_021", "local_024"}
    assignments = {r["photo_id"]: "train" for r in rows}
    rng = random.Random(seed)
    for condition, n_test, n_sample in [
        ("Low Light, Shadow, Different BG", 3, 2), ("Overlap", 3, 1), ("Separated", 4, 2)
    ]:
        pool = sorted(r["photo_id"] for r in rows if r["condition"] == condition and r["photo_id"] not in reserved)
        if len(pool) < n_test + n_sample:
            raise ValueError("Insufficient photographs for the declared condition quotas.")
        rng.shuffle(pool)
        for photo_id in pool[:n_test]:
            assignments[photo_id] = "test"
        for photo_id in pool[n_test:n_test + n_sample]:
            assignments[photo_id] = "sample"
    if Counter(assignments.values()) != {"train": 18, "test": 10, "sample": 5}:
        raise ValueError("Unexpected partition size.")
    hashes = [r["sha256"] for r in rows]
    if len(set(hashes)) != len(rows):
        raise ValueError("Resolve exact duplicates before splitting.")
    groups = {}
    for row in rows:
        if row.get("group_id"):
            groups.setdefault(row["group_id"], set()).add(assignments[row["photo_id"]])
    if any(len(splits) > 1 for splits in groups.values()):
        raise ValueError("A known capture group crosses partitions. Revise the split protocol.")
    return assignments


def prepare(manifest="data/local_20261120/manifest.csv", output="data/local_20261120/split_v1"):
    manifest, output = Path(manifest).resolve(), Path(output).resolve()
    rows = read_rows(manifest)
    assignment = partition(rows)
    if (output / "protocol.json").exists():
        protocol = json.loads((output / "protocol.json").read_text())
        if protocol["source_manifest_sha256"] != digest(manifest):
            raise ValueError("The source manifest changed. Use a new output directory to preserve this split.")
        frozen = read_rows(output / "manifest.csv")
        if {r["photo_id"]: r["split"] for r in frozen} != assignment:
            raise ValueError("Frozen partition membership changed.")
        for row in frozen:
            if digest(output / row["image"]) != row["sha256"]:
                raise ValueError("A partition image changed.")
        return protocol
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use an empty output directory; partial splits are not overwritten.")
    # Validate every original before writing any split files.
    for row in rows:
        source = (manifest.parent / row["image"]).resolve()
        if not source.is_relative_to(manifest.parent) or digest(source) != row["sha256"]:
            raise ValueError("An original photograph is missing, outside the dataset, or changed.")
    output.mkdir(parents=True, exist_ok=True)
    samples, copied = [], []
    for row in rows:
        row = dict(row)
        split = assignment[row["photo_id"]]
        relative = Path(split) / (row["photo_id"] + ".jpg")
        target = output / relative
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(manifest.parent / row["image"], target)
        row.update(image=relative.as_posix(), split=split)
        copied.append(row)
        if split == "sample":
            if not row["actual_whole"] or not row["actual_broken"]:
                raise ValueError("Demo samples require known photo totals.")
            thumb = Path("thumbnails") / (row["photo_id"] + ".jpg")
            (output / thumb).parent.mkdir(exist_ok=True)
            _thumbnail(target, output / thumb)
            whole, broken = int(row["actual_whole"]), int(row["actual_broken"])
            samples.append({"id": row["photo_id"], "title": f"{whole} whole / {broken} broken · {row['condition']}",
                            "kind": "photograph", "label": "mixed" if whole and broken else "whole" if whole else "broken",
                            "split": "sample", "expected_whole": whole, "expected_broken": broken,
                            "image": relative.as_posix(), "thumbnail": thumb.as_posix(), "sha256": row["sha256"],
                            "note": "Local demo photo; totals supplied by the user. Excluded from training and test scoring."})
    for name in ["manifest", "train", "test", "sample"]:
        with (output / (name + ".csv")).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, list(copied[0]))
            writer.writeheader()
            writer.writerows(copied if name == "manifest" else [r for r in copied if r["split"] == name])
    protocol = {"format_version": 1, "seed": 42, "source_manifest_sha256": digest(manifest),
                "manifest_sha256": digest(output / "manifest.csv"), "counts": dict(Counter(assignment.values())),
                "test_condition_quotas": {"difficult_background": 3, "overlap": 3, "separated": 4},
                "sample_condition_quotas": {"difficult_background": 2, "overlap": 1, "separated": 2},
                "reserved_training_examples": ["local_005", "local_007", "local_021", "local_024"],
                "unlabelled_training_photos": [r["photo_id"] for r in copied if r["split"] == "train" and not r["actual_whole"]],
                "warning": CAUTION,
                "validation": "Leave-one-photo-out selection within labelled training photos only; no separate local validation folder.",
                "kaggle": "Original Kaggle train/validation/test assignments remain available and unchanged."}
    (output / "catalog.json").write_text(json.dumps({"format_version": 1, "manifest_sha256": protocol["manifest_sha256"],
                                                   "samples": samples, "split_counts": protocol["counts"]}, indent=2), encoding="utf-8")
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    return protocol


class LocalSampleCatalog:
    """Only the five explicit demo images are reachable through the gallery."""
    public = staticmethod(SampleCatalog.public)

    def __init__(self, root):
        self.root = Path(root).resolve()

    def refresh(self):
        try:
            catalog = json.loads((self.root / "catalog.json").read_text())
            if catalog.get("format_version") != 1 or catalog["manifest_sha256"] != digest(self.root / "manifest.csv"):
                raise SampleError("Local sample manifest changed; prepare a new split.")
            rows = read_rows(self.root / "manifest.csv")
            allowed = {r["photo_id"]: r for r in rows if r["split"] == "sample"}
            items = {}
            for item in catalog["samples"]:
                row = allowed.get(item["id"])
                if (row is None or item["split"] != "sample" or item["sha256"] != row["sha256"] or
                    item["image"] != row["image"] or item["id"] in items or
                    item["expected_whole"] != int(row["actual_whole"]) or item["expected_broken"] != int(row["actual_broken"])):
                    raise SampleError("Invalid local demo membership or reference counts.")
                if not (self.root / item["image"]).resolve().is_relative_to(self.root / "sample") or not (self.root / item["thumbnail"]).resolve().is_relative_to(self.root / "thumbnails"):
                    raise SampleError("Invalid local sample asset path.")
                items[item["id"]] = item
            if len(items) != 5 or set(items) != set(allowed):
                raise SampleError("The local gallery must contain exactly five demo photographs.")
            self._items, self.counts = items, catalog["split_counts"]
        except (KeyError, TypeError, ValueError) as exc:
            raise SampleError("Invalid local sample catalog.") from exc

    list = SampleCatalog.list
    get = SampleCatalog.get
    asset = SampleCatalog.asset


def calibration_values(grains, feature):
    if not grains:
        return np.array([], dtype=float)
    values = np.asarray([g["features"]["major_axis" if feature == "relative_major_axis" else
                         "area" if feature == "relative_sqrt_area" else "aspect_ratio"] for g in grains], dtype=float)
    if feature == "relative_sqrt_area":
        values = np.sqrt(np.maximum(values, 0))
    if feature != "aspect_ratio":
        values = values / max(float(np.quantile(values, .9)), 1e-9)
    return values


def count_loss(bag, broken):
    whole = len(bag["grains"]) - broken
    return (abs(whole - bag["whole"]) + abs(broken - bag["broken"])) / max(1, bag["whole"] + bag["broken"])


def fit_threshold(bags, feature, source_training=None, source_weight=0.0):
    values = np.unique(np.concatenate([calibration_values(b["grains"], feature) for b in bags]))
    if source_training is not None:
        if feature != "aspect_ratio":
            raise ValueError("Combined source/local supervision currently supports aspect ratio only.")
        values = np.unique(np.r_[values, source_training["values"]])
    if len(values) == 0:
        raise ValueError("No training detections for count calibration.")
    thresholds = np.r_[0, (values[:-1] + values[1:]) / 2, values[-1] + 1]
    losses = np.zeros(len(thresholds))
    for bag in bags:
        broken = np.searchsorted(np.sort(calibration_values(bag["grains"], feature)), thresholds, side="left")
        losses += (np.abs(broken-bag["broken"]) + np.abs(len(bag["grains"])-broken-bag["whole"])) / max(1, bag["whole"]+bag["broken"])
    losses /= len(bags)
    if source_training is not None:
        domains = source_training.get("domains", np.repeat("kaggle", len(source_training["labels"])))
        source_error = np.zeros(len(thresholds))
        for domain in np.unique(domains):
            selected = domains == domain
            whole = np.sort(source_training["values"][selected & (source_training["labels"] == "whole")])
            broken = np.sort(source_training["values"][selected & (source_training["labels"] == "broken")])
            if not len(whole) or not len(broken):
                raise ValueError("Each labelled training domain must contain both classes.")
            source_error += .5 * (np.searchsorted(whole, thresholds, side="left") / len(whole) +
                                 1 - np.searchsorted(broken, thresholds, side="left") / len(broken)) / len(np.unique(domains))
        losses += source_weight * source_error
    return float(thresholds[int(np.argmin(losses))])


def fit_calibration(training_bags, source_training=None):
    bags = [b for b in training_bags if b.get("whole") is not None and len(b["grains"]) >= 4]
    if len(bags) < 7 or not any(b["broken"] > 0 for b in bags) or not any(b["whole"] > 0 for b in bags):
        raise ValueError("Need at least seven labelled training photographs with four or more detections and both classes represented.")
    if any(b["split"] != "train" for b in bags):
        raise ValueError("Count calibration accepts training photographs only.")
    cv, candidates = {}, {}
    choices = [("aspect_ratio", weight) for weight in [.1, .25, .5, 1.0]] if source_training is not None else [(f, 0.0) for f in FEATURE_NAMES]
    for feature, weight in choices:
        losses = []
        for i, bag in enumerate(bags):
            threshold = fit_threshold(bags[:i] + bags[i+1:], feature, source_training, weight)
            losses.append(count_loss(bag, int(np.sum(calibration_values(bag["grains"], feature) < threshold))))
        key = f"{feature}:source_weight={weight}"
        cv[key] = float(np.mean(losses))
        candidates[key] = (feature, weight)
    selected = min(cv, key=cv.get)
    feature, weight = candidates[selected]
    prior_loss = float(np.mean([count_loss(b, b["source_broken"]) for b in bags]))
    return {"format_version": 1, "feature": feature, "threshold": fit_threshold(bags, feature, source_training, weight),
            "minimum_candidates": 4, "detector": "adaptive", "enabled": cv[selected] < prior_loss,
            "source_training_instances": len(source_training["labels"]) if source_training is not None else 0,
            "source_loss_weight": weight, "selected_candidate": selected,
            "objective": "Mean normalized local whole/broken count error + source weight * class-balanced labelled training error (equal domain weights when local single-grain labels are supplied).",
            "training_photo_ids": [b["photo_id"] for b in bags], "training_label_unit": "photo_counts",
            "selection_cv_normalized_count_error": cv, "source_tree_training_normalized_count_error": prior_loss,
            "selection_note": "Family selection uses leave-one-photo-out errors on training only. These selection scores are not unbiased final performance.",
            "limitation": "Count supervision cannot establish individual grain label accuracy or a confusion matrix."}


def calibrated_predictions(grains, calibration, detector, method):
    if (not calibration or not calibration.get("enabled") or method != "decision_tree" or
        detector != calibration["detector"] or len(grains) < calibration["minimum_candidates"]):
        return None
    values = calibration_values(grains, calibration["feature"])
    return np.where(values < calibration["threshold"], "broken", "whole")


def make_review_sheet(rgb, grains, folder):
    """Save review crops without fabricating whole/broken labels."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    image = Image.fromarray(rgb)
    canvas = Image.new("RGB", (800, 130 * max(1, (len(grains) + 7) // 8)), "white")
    draw = ImageDraw.Draw(canvas)
    records = []
    for i, grain in enumerate(grains):
        x, y, w, h = grain["bbox"]
        crop = image.crop((max(0, x-8), max(0, y-8), min(image.width, x+w+8), min(image.height, y+h+8)))
        name = f"grain_{i+1:03d}.jpg"
        crop.save(folder / name, quality=95)
        crop.thumbnail((90, 100))
        px, py = (i % 8) * 100, (i // 8) * 130
        canvas.paste(crop, (px, py))
        draw.text((px, py+103), str(i+1), fill="black")
        records.append({"image": name, "label": "", "verified": "false", "group_id": "", "grain_id": i+1})
    canvas.save(folder / "contact_sheet.jpg", quality=90)
    with (folder / "labels.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, ["image", "label", "verified", "group_id", "grain_id"])
        writer.writeheader()
        writer.writerows(records)
