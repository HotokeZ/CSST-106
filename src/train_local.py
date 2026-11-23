"""Fit local count supervision, evaluate fixed partitions, optionally install.

No per-grain labels are inferred from mixed-photo totals. The original Kaggle
tree is retained for single-grain inputs, legacy segmentation and the baseline.
"""
import argparse
import copy
import csv
import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import numpy as np
from bigascheck.local_training import (CAUTION, read_rows, fit_calibration,
                                      calibrated_predictions, make_review_sheet)
from bigascheck.model import analyze, load_model
from bigascheck.samples import digest
from bigascheck.vision import Settings, FEATURES, load_rgb, annotate


def metrics(bags, method, calibration):
    rows = []
    for bag in bags:
        if bag["whole"] is None:
            continue
        predictions = calibrated_predictions(bag["grains"], calibration, "adaptive", "decision_tree")
        n = len(bag["grains"])
        broken = int(np.sum(predictions == "broken")) if method == "local_count_calibration" and predictions is not None else bag["source_broken"]
        if method == "baseline":
            broken = bag["baseline_broken"]
        total = bag["whole"] + bag["broken"]
        rows.append({"photo_id": bag["photo_id"], "detected": n, "reference_whole": bag["whole"],
                     "reference_broken": bag["broken"], "whole": n-broken, "broken": broken,
                     "count_error": abs(n-total), "whole_error": abs(n-broken-bag["whole"]),
                     "broken_error": abs(broken-bag["broken"]),
                     "broken_percentage_error_pp": abs(100*broken/n - 100*bag["broken"]/total) if n and total else None})
    def mean(key):
        values = [r[key] for r in rows if r[key] is not None]
        return float(np.mean(values)) if values else None
    return {"scored_photos": len(rows), "count_mae": mean("count_error"), "whole_mae": mean("whole_error"),
            "broken_mae": mean("broken_error"), "broken_percentage_mae_pp": mean("broken_percentage_error_pp"),
            "percentage_scored_photos": sum(r["broken_percentage_error_pp"] is not None for r in rows), "per_photo": rows}


def run(args):
    root, output, weights = Path(args.split_root).resolve(), Path(args.output).resolve(), Path(args.weights).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a new output directory to preserve previous training/evaluation evidence.")
    rows = read_rows(root / "manifest.csv")
    protocol = json.loads((root / "protocol.json").read_text())
    if digest(root / "manifest.csv") != protocol["manifest_sha256"]:
        raise ValueError("The frozen split manifest changed.")
    if {name: sum(r["split"] == name for r in rows) for name in ("train", "test", "sample")} != {"train":18,"test":10,"sample":5}:
        raise ValueError("Expected the frozen 18/10/5 partition.")
    source = load_model(weights)
    source.pop("local_count_calibration", None)
    settings = replace(Settings(**source["settings"]), detector="adaptive", background="auto", min_area=30, split_touching=True)
    output.mkdir(parents=True)
    bags, feature_rows = [], []

    def extract(row):
        path = (root / row["image"]).resolve()
        if not path.is_relative_to(root / row["split"]) or digest(path) != row["sha256"]:
            raise ValueError("Changed photo or invalid split path.")
        rgb = load_rgb(path, max_edge=1600)
        result, _ = analyze(rgb, source, settings)
        baseline = sum(g["features"]["aspect_ratio"] < source["baseline_threshold"] for g in result["grains"])
        bag = {"photo_id": row["photo_id"], "split": row["split"],
               "whole": int(row["actual_whole"]) if row["actual_whole"] else None,
               "broken": int(row["actual_broken"]) if row["actual_broken"] else None,
               "source_broken": result["summary"]["broken"], "baseline_broken": baseline,
               "grains": result["grains"], "processing_ms": result["summary"]["processing_ms"]}
        if row["split"] == "train":
            make_review_sheet(rgb, result["grains"], output / "crop_review" / row["photo_id"])
            for grain in result["grains"]:
                feature_rows.append({"photo_id": row["photo_id"], "grain_id": grain["grain_id"], "split": "train", "label": "", "verified": "false", **grain["features"]})
        folder = output / "predictions" / row["photo_id"]
        folder.mkdir(parents=True)
        (folder / "source.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return bag, rgb

    print("Extracting the 18 training photos; test and demo photos are not used for fitting.", flush=True)
    for row in [r for r in rows if r["split"] == "train"]:
        bag, _ = extract(row)
        bags.append(bag)
        print(f"Training features: {row['photo_id']} ({len(bag['grains'])} candidates)", flush=True)
    source_rows = read_rows(args.kaggle_features)
    source_train = [r for r in source_rows if r["split"] == "train"]
    source_training = {"values": np.asarray([float(r["aspect_ratio"]) for r in source_train]),
                       "labels": np.asarray([r["label"] for r in source_train])}
    single_rows = []
    if args.local_single_features:
        from bigascheck.single_training import reviewed_rows
        single_rows = reviewed_rows(args.local_single_features, args.local_single_manifest,
                                    args.kaggle_features, root / "manifest.csv")
        source_training["domains"] = np.asarray(["kaggle"]*len(source_train) + ["local_single"]*len(single_rows))
        source_training["values"] = np.r_[source_training["values"], [float(r["aspect_ratio"]) for r in single_rows]]
        source_training["labels"] = np.r_[source_training["labels"], [r["label"] for r in single_rows]]
    if not np.isfinite(source_training["values"]).all() or set(source_training["labels"]) != {"whole", "broken"}:
        raise ValueError("Invalid Kaggle training features.")
    calibration = fit_calibration(bags, source_training)
    calibration["kaggle_feature_table_sha256"] = digest(args.kaggle_features)
    if single_rows:
        calibration["local_single_features_sha256"] = digest(args.local_single_features)
        calibration["labelled_training_domains"] = {"kaggle":len(source_train), "local_single":len(single_rows)}
    fitted = copy.deepcopy(source)
    fitted["local_count_calibration"] = calibration
    fitted["report"]["local_count_calibration"] = {**calibration, "split_manifest_sha256": digest(root / "manifest.csv"), "warning": CAUTION}
    # Freeze model bytes before looking at the test partition or sample totals.
    joblib.dump(fitted, output / "model.joblib")
    frozen_model_hash = digest(output / "model.joblib")
    (output / "calibration.json").write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    print(f"Frozen fitted threshold: {calibration['feature']} < {calibration['threshold']:.6f}; enabled={calibration['enabled']}", flush=True)
    for row in [r for r in rows if r["split"] != "train"]:
        bag, _ = extract(row)
        bags.append(bag)
        print(f"Scoring {row['split']}: {row['photo_id']}", flush=True)
    for bag in bags:
        predictions = calibrated_predictions(bag["grains"], calibration, "adaptive", "decision_tree")
        grains = copy.deepcopy(bag["grains"])
        if predictions is not None:
            for grain, label in zip(grains, predictions):
                grain["prediction"] = str(label)
                grain.pop("model_score", None)
        row = next(r for r in rows if r["photo_id"] == bag["photo_id"])
        rgb = load_rgb(root / row["image"], max_edge=1600)
        folder = output / "predictions" / bag["photo_id"]
        annotate(rgb, grains).save(folder / "calibrated.jpg", quality=90)
        (folder / "calibrated_grains.json").write_text(json.dumps(grains, indent=2), encoding="utf-8")
    source_results = {}
    from bigascheck.model import scores
    for split in ["train", "validation", "test"]:
        selected_rows = [r for r in source_rows if r["split"] == split]
        labels = [r["label"] for r in selected_rows]
        predicted = ["broken" if float(r["aspect_ratio"]) < calibration["threshold"] else "whole" for r in selected_rows]
        source_results[split] = scores(labels, predicted)
    report = {"format_version": 1, "warning": CAUTION, "split_counts": protocol["counts"],
              "kaggle_training_instances": len(source_train), "kaggle_threshold_results": source_results,
              "local_single_training_instances": len(single_rows),
              "local_single_class_counts": {label:sum(r["label"]==label for r in single_rows) for label in ["whole","broken"]},
              "labelled_training_photos": len(calibration["training_photo_ids"]),
              "unlabelled_training_photos": protocol["unlabelled_training_photos"],
              "source_model_sha256": digest(weights), "fitted_model_sha256": frozen_model_hash,
              "manifest_sha256": digest(root / "manifest.csv"), "calibration": calibration,
              "preprocessing": {"max_edge": 1600, "min_area": 30, "background": "auto", "detector": "adaptive", "split_touching": True},
              "results": {name: {method: metrics([b for b in bags if b["split"] == name], method, calibration)
                                 for method in ["source_tree", "baseline", "local_count_calibration"]}
                          for name in ["train", "test", "sample"]},
              "mean_extraction_ms": float(np.mean([b["processing_ms"] for b in bags])),
              "limitations": ["Photo totals do not verify individual grain predictions; per-grain F1/confusion matrix cannot be computed.",
                              "The unlabeled training photo is excluded from threshold fitting; its crops are ready for review.",
                              "Unknown capture groups can cause related-photo leakage. All local partitions are development data.",
                              "No guarantee of improvement on unseen rice varieties or pale crowded stock photographs."]}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with (output / "training_candidates.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, ["photo_id", "grain_id", "split", "label", "verified", *FEATURES])
        writer.writeheader()
        writer.writerows(feature_rows)
    if args.install:
        if not calibration["enabled"]:
            raise ValueError("Candidate did not improve training cross-validation selection score; model not installed.")
        backup = weights.with_name("model_before_local_" + digest(weights)[:16] + ".joblib")
        if not backup.exists():
            shutil.copy2(weights, backup)
        shutil.copy2(output / "model.joblib", weights)
        print(f"Installed local count calibration. Previous model: {backup}", flush=True)
    compact = {k: v for k, v in report.items() if k not in {"results", "calibration"}}
    compact["test"] = {m: {k:v for k,v in r.items() if k != "per_photo"} for m,r in report["results"]["test"].items()}
    print(json.dumps(compact, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-root", default="data/local_20261120/split_v1")
    parser.add_argument("--weights", default="artifacts/model.joblib")
    parser.add_argument("--kaggle-features", default="artifacts/features_and_splits.csv")
    parser.add_argument("--local-single-features", help="Reviewed, training-only single-grain feature CSV.")
    parser.add_argument("--local-single-manifest", default="data/local_grains/batch_20261120_2/manifest.csv")
    parser.add_argument("--output", default="artifacts/combined_count_v1")
    parser.add_argument("--install", action="store_true", help="Back up and replace the active model if training-only selection improves.")
    run(parser.parse_args())
