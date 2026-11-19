"""Reproducible classification evidence, failure gallery, preprocessing and CPU speed."""
import csv
import hashlib
import json
import os
import platform
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageOps
from .model import analyze, load_model, scores, shape_matrix
from .vision import FEATURES, Settings, annotate, load_rgb, segment


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _plot_confusion(matrix, title, path):
    os.environ.setdefault("MPLCONFIGDIR", str(Path(path).resolve().parent / "matplotlib_cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.imshow(matrix, cmap="Greens")
    ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Whole", "Broken"], yticklabels=["Whole", "Broken"],
           xlabel="Predicted", ylabel="Dataset reference", title=title)
    for y in range(2):
        for x in range(2):
            ax.text(x, y, str(matrix[y][x]), ha="center", va="center", fontsize=15,
                    color="white" if matrix[y][x] > np.max(matrix) / 2 else "black")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def evaluate_checkpoint(model, feature_table, split, output, speed_images=20):
    if split not in {"validation", "test"}:
        raise ValueError("Checkpoint evaluation uses validation or development test, not training.")
    output, feature_table = Path(output), Path(feature_table).resolve()
    output.mkdir(parents=True, exist_ok=True)
    bundle = load_model(model)
    frame = pd.read_csv(feature_table, keep_default_na=False)
    selected = frame[frame["split"] == split].copy()
    # Published feature tables use paths relative to the table, while older
    # local tables may contain absolute paths. Support both layouts.
    selected["image"] = selected["image"].map(lambda name: str((feature_table.parent / str(name)).resolve()))
    if selected.empty or set(selected.label) != {"whole", "broken"}:
        raise ValueError("Selected split must contain both classes.")
    if selected.sha256.duplicated().any():
        raise ValueError("Duplicate images in evaluation split.")
    for other in ["train", "validation", "test"]:
        if other != split and set(selected.sha256) & set(frame[frame["split"] == other].sha256):
            raise ValueError("Image hashes overlap dataset splits.")
    raw = selected[FEATURES].to_numpy(float)
    is_shape = bundle.get("feature_mode") == "shape"
    x = shape_matrix(raw) if is_shape else raw
    actual = selected.label.to_numpy()
    tree_predictions = bundle["tree"].predict(x)
    baseline_values = x[:, 0] if is_shape else raw[:, FEATURES.index("major_axis")]
    baseline_predictions = np.where(baseline_values < bundle["baseline_threshold"], "broken", "whole")
    metrics = {"split": split, "instances": len(selected), "model_sha256": sha256(model),
               "feature_table_sha256": sha256(feature_table), "model_size_bytes": Path(model).stat().st_size,
               "method": bundle.get("feature_mode", "pixel"),
               "classification_scope": "Per-grain classification from saved extracted features; not detection or segmentation accuracy.",
               "evaluation_status": "Development evidence. Source capture groups unknown and the test gallery has been exposed.",
               "baseline": scores(actual, baseline_predictions), "decision_tree": scores(actual, tree_predictions),
               "hardware": {"os": platform.platform(), "machine": platform.machine(),
                            "processor": platform.processor(), "logical_cpus": os.cpu_count(),
                            "python": platform.python_version()},
               "dependencies": {name: version(name) for name in ["numpy", "scipy", "pandas", "scikit-learn", "Pillow", "Flask", "joblib"]}}
    for name in ["baseline", "decision_tree"]:
        metrics[name]["macro_f1"] = metrics[name]["classification_report"]["macro avg"]["f1-score"]
        _plot_confusion(metrics[name]["confusion_matrix"], name.replace("_", " ").title()+" — "+split,
                        output / (name + "_confusion_matrix.png"))
    selected["predicted"] = tree_predictions
    selected["baseline_predicted"] = baseline_predictions
    selected.to_csv(output / "predictions.csv", index=False)
    settings = Settings(**bundle["settings"])
    bench = selected.iloc[:max(1, min(int(speed_images), len(selected)))].copy()
    timings, runtime = [], []
    warm = load_rgb(bench.iloc[0].image)
    for _ in range(3):
        analyze(warm, bundle, settings)
    for row in bench.to_dict("records"):
        if sha256(row["image"]) != row["sha256"]:
            raise ValueError("A benchmark image differs from the extracted feature table.")
        started = perf_counter()
        result, _ = analyze(load_rgb(row["image"]), bundle, settings)
        elapsed = (perf_counter() - started) * 1000
        timings.append(elapsed)
        runtime.append({"image": row["image"], "ms": elapsed, "detected": result["summary"]["detected"]})
    metrics["speed"] = {"warmup_runs": 3, "images": len(timings), "mean_ms": float(np.mean(timings)),
                        "median_ms": float(np.median(timings)), "fps_equivalent": float(1000 / np.mean(timings)),
                        "scope": "Load image + segment + extract features + classify on CPU; excludes model loading, rendering, web and disk output.",
                        "settings": asdict(settings), "runs": runtime}
    failures = selected[selected.predicted != selected.label].copy()
    (output / "failures").mkdir(exist_ok=True)
    gallery, cause_counts = [], {}
    for index, row in enumerate(failures.to_dict("records"), 1):
        cause = ("Whole reference with a short/low-elongation silhouette" if row["label"] == "whole"
                 else "Broken reference with an elongated/look-alike silhouette")
        cause_counts[cause] = cause_counts.get(cause, 0) + 1
        path = output / "failures" / f"failure_{index:02d}.jpg"
        with Image.open(row["image"]) as image:
            tile = Image.new("RGB", (360, 280), "white")
            image = ImageOps.contain(image.convert("RGB"), (360, 225))
            tile.paste(image, ((360-image.width)//2, 0))
            draw = ImageDraw.Draw(tile)
            draw.text((8, 231), f'Reference: {row["label"]}; predicted: {row["predicted"]}', fill="black")
            draw.text((8, 252), f'Aspect ratio: {row["aspect_ratio"]:.3f}; solidity: {row["solidity"]:.3f}', fill="black")
            tile.save(path, quality=90)
        gallery.append({"id": f"F{index:02d}", "image": row["image"], "reference": row["label"],
                        "prediction": row["predicted"], "aspect_ratio": row["aspect_ratio"],
                        "hypothesized_cause": cause, "cause_review": "Needs manual label and contour review",
                        "evidence": str(path)})
    metrics["failure_analysis"] = {"failures": len(gallery), "hypothesized_cause_counts": cause_counts,
                                   "note": "Error directions are observed. Root causes and original label correctness are not independently verified."}
    (output / "failure_log.json").write_text(json.dumps(gallery, indent=2), encoding="utf-8")
    if gallery:
        sheet = Image.new("RGB", (360 * 4, 280 * int(np.ceil(min(12, len(gallery))/4))), "#eeeeee")
        chosen = [g for g in gallery if g["reference"] == "whole"][:6] + [g for g in gallery if g["reference"] == "broken"][:6]
        chosen += [g for g in gallery if g not in chosen][:max(0, 12-len(chosen))]
        for index, item in enumerate(chosen):
            with Image.open(item["evidence"]) as image:
                sheet.paste(image, ((index % 4)*360, (index // 4)*280))
        sheet.save(output / "failure_contact_sheet.png")
    # A reproducible visual before/after strip on the same preprocessing code.
    strip = Image.new("RGB", (900, 260), "white")
    rgb = load_rgb(bench.iloc[0].image)
    grains, _, mask = segment(rgb, settings)
    for index, image in enumerate([Image.fromarray(rgb), Image.fromarray(mask).convert("RGB"), annotate(rgb, grains)]):
        tile = ImageOps.contain(image, (300, 230))
        strip.paste(tile, (index*300+(300-tile.width)//2, 0))
    draw = ImageDraw.Draw(strip)
    for index, label in enumerate(["Original RGB", "Foreground mask", "Grain regions"]):
        draw.text((index*300+15, 238), label, fill="black")
    strip.save(output / "preprocessing_strip.png")
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    lines = ["# Reproducible development evaluation", "", f"Split: {split}; images: {len(selected)}.", "",
             "| Method | Accuracy | Macro-F1 | Broken F1 |", "|---|---:|---:|---:|"]
    for name in ["baseline", "decision_tree"]:
        value = metrics[name]
        lines.append(f'| {name} | {value["accuracy"]:.4f} | {value["macro_f1"]:.4f} | {value["broken_f1"]:.4f} |')
    lines.extend(["", f'CPU pipeline mean: {metrics["speed"]["mean_ms"]:.2f} ms/image after 3 warm-ups; {len(timings)} images.',
                  f'Model size: {metrics["model_size_bytes"]} bytes.', "", metrics["evaluation_status"], "",
                  "Classification numbers use the saved per-grain feature table. Runtime measurements execute the image pipeline. Neither supplies mask IoU, detection mAP, or independent multi-grain count accuracy."])
    (output / "results.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return metrics
