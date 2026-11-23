"""Group-isolated validation, geometric baseline and Decision Tree comparison."""
from dataclasses import asdict
from pathlib import Path
import json
from time import perf_counter

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.tree import DecisionTreeClassifier

from .dataset import load_manifest
from .vision import FEATURES, Settings, backend, load_rgb, segment, resolve_background
from .local_training import calibrated_predictions, FEATURE_NAMES

SHAPE_FEATURES = ["aspect_ratio", "solidity", "ellipse_fill"]


def shape_matrix(raw):
    """Dimensionless silhouette features, independent of uniform pixel scale and RGB."""
    raw = np.asarray(raw, dtype=float)
    area = raw[:, FEATURES.index("area")]
    major = raw[:, FEATURES.index("major_axis")]
    minor = raw[:, FEATURES.index("minor_axis")]
    return np.column_stack([raw[:, FEATURES.index("aspect_ratio")],
                            raw[:, FEATURES.index("solidity")],
                            area / np.maximum(major * minor, 1e-9)])


def train_shape(feature_table, output):
    """Refit from the reproducible extracted-feature table; preserve existing splits."""
    source = Path(feature_table)
    frame = pd.read_csv(source, keep_default_na=False)
    if not set([*FEATURES, "label", "split"]).issubset(frame.columns):
        raise ValueError("Feature table is missing the raw features, label or split.")
    if not set(frame["label"]).issubset({"whole", "broken"}):
        raise ValueError("Unexpected integrity labels in feature table.")
    x = shape_matrix(frame[FEATURES].to_numpy(float))
    if not np.isfinite(x).all():
        raise ValueError("Non-finite shape features in table.")
    y = frame["label"].to_numpy()
    partitions = {name: np.flatnonzero(frame["split"].to_numpy() == name) for name in ["train", "validation", "test"]}
    if sum(map(len, partitions.values())) != len(frame) or any(set(y[ids]) != {"whole", "broken"} for ids in partitions.values()):
        raise ValueError("Require train/validation/test splits containing both classes.")
    tr, va, te = (partitions[name] for name in ["train", "validation", "test"])
    candidates = []
    for depth in [2, 3, 4, 5, 7]:
        for leaf in [3, 10, 20]:
            tree = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf,
                                          class_weight="balanced", random_state=42)
            tree.fit(x[tr], y[tr])
            candidates.append((f1_score(y[va], tree.predict(x[va]), pos_label="broken", zero_division=0), tree))
    validation_f1, tree = max(candidates, key=lambda item: item[0])
    thresholds = np.quantile(x[tr, 0], np.linspace(0.05, 0.95, 100))
    threshold = max(thresholds, key=lambda t: f1_score(y[va], np.where(x[va, 0] < t, "broken", "whole"),
                                                     pos_label="broken", zero_division=0))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    import shutil
    model_path = output / "model.joblib"
    previous = joblib.load(model_path) if model_path.is_file() else None
    if previous and previous.get("feature_mode") != "shape":
        shutil.copy2(model_path, output / "pixel_model.joblib")
        if (output / "evaluation.json").is_file():
            shutil.copy2(output / "evaluation.json", output / "pixel_evaluation.json")
    settings = previous["settings"] if previous else asdict(Settings(max_area_fraction=.6))
    old_report = previous.get("report", {}) if previous else {}
    report = {"training_mode": old_report.get("training_mode", "exploratory_source_labels"),
              "feature_mode": "shape", "classification_features": SHAPE_FEATURES,
              "dataset": {"images": len(frame), "classes": frame.label.value_counts().to_dict()},
              "split_unit": old_report.get("split_unit", "image"),
              "split": {name: {"instances": len(ids), "groups": sorted(set(frame.iloc[ids].group_id) - {""}) if "group_id" in frame else []}
                        for name, ids in partitions.items()},
              "settings": settings, "segmentation_backend": backend(),
              "validation_broken_f1": float(validation_f1),
              "decision_tree_parameters": {"max_depth": tree.max_depth, "min_samples_leaf": tree.min_samples_leaf},
              "baseline_feature": "aspect_ratio", "baseline_threshold": float(threshold),
              "test": {"decision_tree": scores(y[te], tree.predict(x[te])),
                       "baseline": scores(y[te], np.where(x[te, 0] < threshold, "broken", "whole"))},
              "feature_importance": dict(zip(SHAPE_FEATURES, tree.feature_importances_.tolist())),
              "limitations": ["Shape predictions are experimental on crowded or pale-background photos; silhouette errors change the features.",
                              "Naturally short whole grains can resemble broken grains. Camera-scale invariance does not resolve that ambiguity.",
                              "Source-image splits are retained; capture groups and independent local-photo accuracy remain unverified.",
                              "This development test set has been used in earlier prototype reports. Final evaluation requires fresh held-out captures."]}
    bundle = {"format_version": 1, "features": FEATURES, "feature_mode": "shape",
              "classification_features": SHAPE_FEATURES, "tree": tree, "baseline_threshold": float(threshold),
              "baseline_feature": "aspect_ratio", "settings": settings, "backend": backend(), "report": report}
    joblib.dump(bundle, model_path)
    (output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def grouped_split(labels, groups, seed=42):
    labels, groups = np.asarray(labels), np.asarray(groups)
    if len(set(groups)) < 7:
        raise ValueError("Supply at least 7 independent capture/sample groups for a 70/15/15 split.")
    # Split selection uses labels only to require both classes, never model scores.
    for attempt in range(100):
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=seed + attempt)
        development, test = next(splitter.split(labels, labels, groups))
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.15 / 0.85, random_state=seed + attempt)
        tr, va = next(splitter.split(labels[development], labels[development], groups[development]))
        train, val = development[tr], development[va]
        if all(set(labels[index]) == {"whole", "broken"} for index in [train, val, test]):
            return train, val, test
    raise ValueError("Could not create group-isolated splits containing both labels. Collect more independent groups.")


def scores(actual, predicted):
    return {"accuracy": float(accuracy_score(actual, predicted)),
            "broken_f1": float(f1_score(actual, predicted, pos_label="broken", zero_division=0)),
            "confusion_matrix_labels": ["whole", "broken"],
            "confusion_matrix": confusion_matrix(actual, predicted, labels=["whole", "broken"]).tolist(),
            "classification_report": classification_report(actual, predicted, labels=["whole", "broken"],
                                                           output_dict=True, zero_division=0)}


def train(manifest, output, settings=Settings(), source_labels=False):
    source_records = load_manifest(manifest, source_labels=source_labels)
    features, records, skipped = [], [], []
    for index, record in enumerate(source_records):
        if index % 250 == 0:
            print(f"Reading grain images: {index}/{len(source_records)}", flush=True)
        try:
            grains, _, _ = segment(load_rgb(record["image"]), settings)
        except (OSError, ValueError) as exc:
            if not source_labels:
                raise
            skipped.append({"image": record["image"], "label": record["label"],
                            "detected_regions": None, "reason": f"unreadable_image: {exc}"})
            continue
        if len(grains) != 1:
            if source_labels:
                skipped.append({"image": record["image"], "label": record["label"],
                                "detected_regions": len(grains), "reason": "expected_one_isolated_grain"})
                continue
            raise ValueError(f'{record["image"]}: expected exactly one isolated labeled grain; detected {len(grains)}. Review segmentation or crop/label individual grains.')
        records.append(record)
        features.append([grains[0]["features"][name] for name in FEATURES])
        if (index + 1) % 250 == 0:
            print(f"Extracted features: {index + 1}/{len(source_records)}", flush=True)
    if len(records) < 20 or set(r["label"] for r in records) != {"whole", "broken"}:
        raise ValueError("Need at least 20 accepted grain images containing both classes.")
    x = np.asarray(features)
    y = np.array([r["label"] for r in records])
    groups = np.array([r["group_id"] for r in records])
    if source_labels:
        development, te = train_test_split(np.arange(len(y)), test_size=0.15, stratify=y, random_state=42)
        tr, va = train_test_split(development, test_size=0.15 / 0.85, stratify=y[development], random_state=42)
    else:
        tr, va, te = grouped_split(y, groups)
    # All threshold candidates come from training whole grains; validation selects one.
    lengths = x[:, FEATURES.index("major_axis")]
    whole_length = float(np.median(lengths[tr][y[tr] == "whole"]))
    thresholds = whole_length * np.linspace(0.4, 0.95, 23)
    threshold = max(thresholds, key=lambda t: f1_score(y[va], np.where(lengths[va] < t, "broken", "whole"),
                                                     pos_label="broken", zero_division=0))
    candidates = []
    for depth in [2, 3, 5, 8, None]:
        for leaf in [1, 3, 5]:
            tree = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf,
                                          class_weight="balanced", random_state=42)
            tree.fit(x[tr], y[tr])
            score = f1_score(y[va], tree.predict(x[va]), pos_label="broken", zero_division=0)
            candidates.append((score, tree))
    validation_f1, tree = max(candidates, key=lambda pair: pair[0])
    # Keep the fitted training-only model; test data is used once for final reporting.
    report = {"dataset": {"images": len(records), "groups": None if source_labels else len(set(groups)),
                          "source_images": len(source_records), "segmentation_exclusions": len(skipped),
                          "classes": {label: int(sum(y == label)) for label in ["whole", "broken"]}},
              "training_mode": "exploratory_source_labels" if source_labels else "reviewed_grouped",
              "split_unit": "image" if source_labels else "capture_group",
              "segmentation_backend": backend(), "settings": asdict(settings),
              "split": {name: {"instances": len(idx), "groups": [] if source_labels else sorted(set(groups[idx]))}
                        for name, idx in [("train", tr), ("validation", va), ("test", te)]},
              "baseline_threshold_pixels": float(threshold),
              "decision_tree_parameters": {"max_depth": tree.max_depth, "min_samples_leaf": tree.min_samples_leaf},
              "validation_broken_f1": float(validation_f1),
              "test": {"baseline": scores(y[te], np.where(lengths[te] < threshold, "broken", "whole")),
                       "decision_tree": scores(y[te], tree.predict(x[te]))},
              "feature_importance": dict(zip(FEATURES, tree.feature_importances_.tolist())),
              "limitations": ["Pixel features require consistent capture scale and background.",
                              "Instance classification metrics do not measure multi-grain counting or percentage error."] +
                              (["Uses dataset folder labels without independent per-image manual verification.",
                                "Original capture groups are unknown. Image-level test scores may include related captures and are exploratory, not session-independent evaluation."] if source_labels else [])}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    bundle = {"format_version": 1, "features": FEATURES, "tree": tree,
              "baseline_threshold": float(threshold), "settings": asdict(settings),
              "backend": backend(), "report": report}
    joblib.dump(bundle, output / "model.joblib")
    (output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    split_for = {int(i): name for name, ids in [("train", tr), ("validation", va), ("test", te)] for i in ids}
    frame = pd.DataFrame([{**r, **dict(zip(FEATURES, f)), "split": split_for[i]}
                          for i, (r, f) in enumerate(zip(records, features))])
    frame.to_csv(output / "features_and_splits.csv", index=False)
    pd.DataFrame(skipped, columns=["image", "label", "detected_regions", "reason"]).to_csv(output / "excluded_images.csv", index=False)
    return report


def load_model(path):
    # Only load locally produced/trusted files: pickle/joblib can execute code.
    bundle = joblib.load(path)
    if bundle.get("format_version") != 1 or bundle.get("features") != FEATURES:
        raise ValueError("Unsupported model format or feature schema.")
    if bundle["backend"] != backend():
        raise ValueError("Segmentation backend differs from training. Retrain with the current backend before prediction.")
    calibration = bundle.get("local_count_calibration")
    if calibration and (calibration.get("format_version") != 1 or calibration.get("feature") not in FEATURE_NAMES or
                        not np.isfinite(calibration.get("threshold", float("nan"))) or
                        calibration.get("minimum_candidates", 0) < 4 or calibration.get("detector") != "adaptive"):
        raise ValueError("Invalid local count calibration.")
    return bundle


def analyze(rgb, bundle=None, settings=None, method="decision_tree"):
    started = perf_counter()
    if method not in {"decision_tree", "baseline"}:
        raise ValueError("Unknown classification method.")
    if bundle is not None:
        trained_settings = Settings(**bundle["settings"])
        settings = settings or trained_settings
    settings = settings or Settings()
    grains, rejected, mask = segment(rgb, settings)
    mode = resolve_background(rgb, settings.background)
    classification_reason = None
    shape_model = bundle is not None and bundle.get("feature_mode") == "shape"
    if bundle is not None and not shape_model and mode != trained_settings.background:
        classification_reason = "Grains were counted, but this background differs from the classifier's training images. Whole/broken predictions are withheld."
    if bundle is not None and not shape_model and grains and classification_reason is None:
        median_length = float(np.median([g["features"]["major_axis"] for g in grains]))
        # Detect a gross scale mismatch. This cannot replace camera calibration.
        typical_whole = bundle["baseline_threshold"] / 0.75
        if median_length < typical_whole * 0.3 or median_length > typical_whole * 2.5:
            classification_reason = "Grains are at a substantially different pixel scale from training. Whole/broken predictions are withheld; use a matching camera scale."
    classification_enabled = bundle is not None and classification_reason is None
    local_predictions = None
    if classification_enabled and grains:
        x = np.array([[g["features"][f] for f in FEATURES] for g in grains])
        model_x = shape_matrix(x) if shape_model else x
        if method == "baseline":
            baseline_values = model_x[:, 0] if shape_model else x[:, FEATURES.index("major_axis")]
            predictions = np.where(baseline_values < bundle["baseline_threshold"], "broken", "whole")
        else:
            predictions = bundle["tree"].predict(model_x)
            model_scores = bundle["tree"].predict_proba(model_x).max(axis=1)
            local_predictions = calibrated_predictions(grains, bundle.get("local_count_calibration"), settings.detector, method)
            if local_predictions is not None:
                predictions = local_predictions
        for grain, prediction in zip(grains, predictions):
            grain["prediction"] = str(prediction)
        if method == "decision_tree" and local_predictions is None:
            for grain, score in zip(grains, model_scores):
                grain["model_score"] = float(score)
    broken = sum(g.get("prediction") == "broken" for g in grains) if classification_enabled else None
    return {"grains": grains, "summary": {"detected": len(grains), "broken": broken,
             "whole": len(grains) - broken if broken is not None else None,
             "broken_percentage": 100 * broken / len(grains) if broken is not None and grains else None,
             "classified": classification_enabled, "method": method if classification_enabled else None,
             "background_used": mode, "split_touching": settings.split_touching,
             "classification_basis": "local_count_supervised" if local_predictions is not None else "shape_only" if shape_model else "pixel_features",
             "classifier_used": "local_count_calibration" if local_predictions is not None else method if classification_enabled else None,
             "count_is_estimate": True, "classification_experimental": shape_model,
             "processing_ms": round((perf_counter() - started) * 1000, 3),
             "backend": backend(), "rejected_regions": len(rejected)},
            "preprocessing": {"detector": settings.detector, "width": int(rgb.shape[1]), "height": int(rgb.shape[0])},
            "warnings": ["Touching grains can merge into one region; spread grains apart.",
                         "Count-based visual estimate; not a mass percentage or official grade."] +
                        (["Model scores are decision-tree leaf votes, not calibrated probabilities of correctness."]
                         if classification_enabled and method == "decision_tree" and local_predictions is None else []) +
                        (["Whole/broken labels use a local threshold trained from photo totals. Individual grain labels remain unverified; predictions are experimental."]
                         if local_predictions is not None else []) +
                        ([classification_reason] if classification_reason else []) +
                        (["Whole/broken labels use a shape-only classifier. Predictions and percentages on this photo are experimental and need manual verification.",
                          "Pale-background and crowded-photo percentages have not been validated as rice quality measurements; overlapping grains and short rice varieties can be misclassified."] if shape_model and local_predictions is None else []) +
                        ([f'{sum(r["reason"] == "touches_border" for r in rejected)} regions touching the image edge were excluded; counts cover accepted visible grain regions.']
                         if any(r["reason"] == "touches_border" for r in rejected) else []) +
                        (["Exploratory classifier trained on public dataset labels; validate on local rice photographs."]
                         if bundle and bundle.get("report", {}).get("training_mode") == "exploratory_source_labels" else []) +
                        (["No trained model loaded; grains are detected but unclassified."] if bundle is None else [])}, mask
