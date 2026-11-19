"""Evaluate multi-grain counting and count-based broken proportion independently."""
from pathlib import Path
import numpy as np
import pandas as pd
from .model import analyze
from .vision import load_rgb


def evaluate_samples(csv_path, bundle):
    path = Path(csv_path).resolve()
    frame = pd.read_csv(path, dtype={"group_id": str})
    if not {"image", "group_id", "actual_whole", "actual_broken"}.issubset(frame.columns):
        raise ValueError("Sample CSV requires image,group_id,actual_whole,actual_broken.")
    if frame.empty or frame.isna().any().any():
        raise ValueError("Sample CSV must contain complete rows.")
    used_groups = set(bundle["report"]["split"]["train"]["groups"]) | set(bundle["report"]["split"]["validation"]["groups"])
    if used_groups & set(frame.group_id):
        raise ValueError("Evaluation captures overlap training/validation groups.")
    rows = []
    for record in frame.to_dict("records"):
        whole, broken = float(record["actual_whole"]), float(record["actual_broken"])
        if not all(np.isfinite(n) and n >= 0 and n.is_integer() for n in [whole, broken]) or whole + broken == 0:
            raise ValueError("Manual grain counts must be nonnegative integers with a positive total.")
        result, _ = analyze(load_rgb(path.parent / record["image"]), bundle)
        summary = result["summary"]
        true_percentage = 100 * broken / (whole + broken)
        estimated = summary["broken_percentage"]
        rows.append({**record, "detected": summary["detected"],
                     "absolute_count_error": abs(summary["detected"] - whole - broken),
                     "actual_broken_percentage": true_percentage,
                     "predicted_broken_percentage": estimated,
                     "absolute_percentage_point_error": abs(estimated - true_percentage) if estimated is not None else None})
    errors = [r["absolute_percentage_point_error"] for r in rows if r["absolute_percentage_point_error"] is not None]
    return {"images": len(rows), "count_mae": float(np.mean([r["absolute_count_error"] for r in rows])),
            "percentage_point_mae": float(np.mean(errors)) if len(errors) == len(rows) else None,
            "percentage_evaluable_images": len(errors),
            "note": "Percentage MAE is withheld if any photograph has zero detected grains.", "samples": rows}
