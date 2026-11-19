"""Recorded checkpoint demo cases; failures are retained, never converted to passes."""
import csv
import io
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
from .samples import SampleCatalog
from .vision import png_bytes, Settings, segment, load_rgb


def run_demo_cases(output="outputs/checkpoints/test_cases", samples_root="data/splits",
                   feature_table="artifacts/features_and_splits.csv", model="artifacts/model.joblib"):
    from app import create_app
    output = Path(output)
    inputs = output / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    catalog = SampleCatalog(samples_root, feature_table)
    whole = next(item for item in catalog.list("whole", page_size=24)["items"] if item["kind"] == "single")
    broken = next(item for item in catalog.list("broken", page_size=24)["items"] if item["kind"] == "single")
    with Image.open(catalog.asset(whole["id"])) as image:
        original = image.convert("RGB").copy()
    records = [
        {"id": "TC01", "condition": "Whole source image", "sample_id": whole["id"], "count": 1, "whole": 1, "broken": 0},
        {"id": "TC02", "condition": "Broken source image", "sample_id": broken["id"], "count": 1, "whole": 0, "broken": 1},
        {"id": "TC03", "condition": "Mixed six-grain composite", "sample_id": "example-1", "count": 6, "whole": 3, "broken": 3},
        {"id": "TC04", "condition": "All-whole six-grain composite", "sample_id": "example-2", "count": 6, "whole": 6, "broken": 0},
        {"id": "TC05", "condition": "All-broken six-grain composite", "sample_id": "example-3", "count": 6, "whole": 0, "broken": 6},
    ]
    fixtures = [
        ("TC06", "Blank dark image (edge case)", Image.new("RGB", (400, 400), "black"), 0, None, None),
        ("TC07", "Half-resolution whole image (scale hard case)", original.resize((original.width//2, original.height//2)), 1, 1, 0),
        ("TC08", "Dim whole image (lighting hard case)", ImageEnhance.Brightness(original).enhance(.4), 1, 1, 0),
    ]
    raw = np.array(original)
    grains, _, _ = segment(raw, Settings(max_area_fraction=.6))
    if not grains:
        raise ValueError("The source whole image could not be used for the crop fixture.")
    x, y, w, h = grains[0]["bbox"]
    fixtures.append(("TC09", "Grain cut by frame (edge case)", original.crop((x+w//2, 0, original.width, original.height)), 0, None, None))
    with Image.open(catalog.asset("example-2")) as image:
        composite = np.array(image.convert("RGB"))
    pale = np.full_like(composite, 195)
    foreground = composite.max(axis=2) > 80
    pale[foreground] = composite[foreground]
    fixtures.append(("TC11", "Pale-background composite (background hard case)", Image.fromarray(pale), 6, 6, 0))
    touching = Image.new("RGB", (320, 200), "black")
    draw = ImageDraw.Draw(touching)
    draw.ellipse((40, 75, 130, 105), fill="white")
    draw.ellipse((123, 75, 213, 105), fill="white")
    draw.ellipse((245, 50, 275, 150), fill="white")
    fixtures.append(("TC12", "Touching ellipses (synthetic separation hard case)", touching, 3, None, None))
    for case_id, condition, image, count, whole_count, broken_count in fixtures:
        path = inputs / (case_id + ".png")
        image.save(path)
        records.append({"id": case_id, "condition": condition, "image": str(path), "count": count,
                        "whole": whole_count, "broken": broken_count})
    records.append({"id": "TC10", "condition": "Invalid image upload (edge case)", "invalid": True, "status": 400})
    records.sort(key=lambda row: row["id"])
    # Preserve the expected outcomes separately before running the requests.
    (output / "case_plan.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    client = create_app(model, samples_root, feature_table).test_client()
    results = []
    for case in records:
        start = perf_counter()
        if case.get("invalid"):
            response = client.post("/api/analyze", data={"image": (io.BytesIO(b"not an image"), "bad.png")})
        elif "sample_id" in case:
            response = client.post("/api/analyze", data={"sample_id": case["sample_id"]})
        else:
            response = client.post("/api/analyze", data={"image": (io.BytesIO(Path(case["image"]).read_bytes()), "fixture.png")})
        summary = response.json.get("summary", {}) if response.is_json else {}
        passed = response.status_code == case.get("status", 200)
        if not case.get("invalid"):
            passed = passed and summary.get("detected") == case["count"]
            if case.get("whole") is not None:
                passed = passed and summary.get("whole") == case["whole"] and summary.get("broken") == case["broken"]
        results.append({**case, "actual_status": response.status_code, "actual_detected": summary.get("detected"),
                        "actual_whole": summary.get("whole"), "actual_broken": summary.get("broken"),
                        "request_ms": (perf_counter()-start)*1000, "pass": bool(passed)})
    (output / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = ["id", "condition", "count", "whole", "broken", "actual_status", "actual_detected", "actual_whole", "actual_broken", "request_ms", "pass"]
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    return {"cases": len(results), "passed": sum(r["pass"] for r in results),
            "failed": sum(not r["pass"] for r in results),
            "note": "Dataset labels and synthetic fixtures are references. This does not establish independent real-world accuracy.",
            "output": str(output)}
