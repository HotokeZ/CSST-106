"""One raw image or directory -> annotated images, masks, JSON and CSV."""
import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from PIL import Image
from .dataset import IMAGE_SUFFIXES
from .model import analyze, load_model
from .vision import Settings, annotate, load_rgb


def run_path(source, output, model="artifacts/model.joblib", background="auto", split_touching=True, detector="adaptive"):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source.is_dir():
        if output.is_relative_to(source):
            raise ValueError("Put batch outputs outside the input directory.")
        inputs = sorted(p for p in source.rglob("*") if p.suffix.lower() in IMAGE_SUFFIXES)
    elif source.is_file():
        inputs = [source]
    else:
        raise ValueError("Input must be an existing image or image directory.")
    if not inputs:
        raise ValueError("No input images found.")
    bundle = load_model(model)
    settings = replace(Settings(**bundle["settings"]), background=background, split_touching=split_touching, detector=detector)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in inputs:
        key = path.stem + "_" + hashlib.sha256(str(path).encode()).hexdigest()[:8]
        target = output / key
        target.mkdir(exist_ok=True)
        try:
            rgb = load_rgb(path, max_edge=1600 if detector == "adaptive" else None)
            result, mask = analyze(rgb, bundle, settings)
            annotate(rgb, result["grains"]).save(target / "annotated.png")
            Image.fromarray(mask).save(target / "mask.png")
            (target / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            with (target / "grains.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, ["grain_id", "prediction", "model_score", *bundle["features"]])
                writer.writeheader()
                writer.writerows({"grain_id": g["grain_id"], "prediction": g.get("prediction", "unclassified"),
                                  "model_score": g.get("model_score"), **g["features"]} for g in result["grains"])
            rows.append({"image": str(path), "status": "ok", "output": str(target), **result["summary"]})
        except (OSError, ValueError) as exc:
            rows.append({"image": str(path), "status": "error", "error": str(exc), "output": str(target)})
    (output / "batch_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows
