"""Prepare a portable, bounded repository upload; excludes raw/user images."""
import argparse
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path


def prepare(destination):
    root = Path(__file__).resolve().parents[1]
    target = Path(destination).resolve()
    if target == root or root.is_relative_to(target):
        raise ValueError("Choose a dedicated export directory, not the project or its parent.")
    target.mkdir(parents=True, exist_ok=True)
    published = []
    top = ["app.py", "README.md", "requirements.txt", "requirements-opencv.txt", "setup.ps1", "start.ps1",
           "train.ps1", ".gitignore", "THIRD_PARTY_NOTICES.md"]
    files = [root / name for name in top]
    files += [path for folder in ["bigascheck", "src", "static", "templates", "tests", "docs"]
              for path in (root / folder).rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    for source in files:
        relative = source.relative_to(root)
        text = source.read_text(encoding="utf-8")
        text = re.sub(r"\[([^\]]+)\]\(https://chatgpt\.com/library[^)]*\)",
                      r"\1 (course-provided guide; not redistributed)", text)
        text = text.replace(str(root), "<project-root>")
        text = re.sub(r"C:\\Users\\[^\\\r\n]+\\Downloads\\archive\.zip", "inputs/archive.zip", text)
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        published.append(relative.as_posix())
    for name in ["model.joblib", "pixel_model.joblib", "evaluation.json", "pixel_evaluation.json"]:
        source = root / "artifacts" / name
        if source.is_file():
            dest = target / "artifacts" / name
            dest.parent.mkdir(exist_ok=True)
            shutil.copy2(source, dest)
            published.append("artifacts/" + name)
    table = root / "artifacts/features_and_splits.csv"
    with table.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        names = reader.fieldnames
        rows = list(reader)
    for row in rows:
        image = (table.parent / row["image"]).resolve()
        relative = image.relative_to(root / "data/raw")
        row["image"] = (Path("..") / "data/raw" / relative).as_posix()
    portable_table = target / "artifacts/features_and_splits.csv"
    with portable_table.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, names)
        writer.writeheader()
        writer.writerows(rows)
    published.append("artifacts/features_and_splits.csv")
    for split in ["validation", "development_test"]:
        source = root / "outputs/checkpoints" / split / "metrics.json"
        if not source.is_file():
            continue
        metric = json.loads(source.read_text(encoding="utf-8"))
        metric["original_feature_table_sha256"] = metric["feature_table_sha256"]
        metric["feature_table_sha256"] = hashlib.sha256(portable_table.read_bytes()).hexdigest()
        metric["publication_note"] = "Source image paths were made relative; numeric features and split assignments are unchanged. Timings are the original local measurement."
        for row in metric.get("speed", {}).get("runs", []):
            row["image"] = Path(row["image"]).name
        relative = Path("docs/evidence") / (split + "_metrics.json")
        (target / relative).parent.mkdir(parents=True, exist_ok=True)
        (target / relative).write_text(json.dumps(metric, indent=2), encoding="utf-8")
        published.append(relative.as_posix())
    inventory = [{"path": name, "size": (target / name).stat().st_size,
                  "sha256": hashlib.sha256((target / name).read_bytes()).hexdigest()} for name in sorted(published)]
    (target / "upload_manifest.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    return {"directory": str(target), "files": len(inventory), "bytes": sum(item["size"] for item in inventory)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    print(json.dumps(prepare(parser.parse_args().output), indent=2))
