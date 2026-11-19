"""Non-destructive archive audit and explicit, reviewed-label manifest loading."""
import csv
import hashlib
from collections import Counter
from pathlib import Path, PurePosixPath
import zipfile

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
MANIFEST_FIELDS = ["image", "label", "group_id", "verified"]


def audit(source):
    source = Path(source)
    if source.is_file() and zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            entries = [i for i in archive.infolist() if not i.is_dir()]
            names = [i.filename for i in entries]
            size = sum(i.file_size for i in entries)
    elif source.is_dir():
        entries = [p for p in source.rglob("*") if p.is_file()]
        names = [p.relative_to(source).as_posix() for p in entries]
        size = sum(p.stat().st_size for p in entries)
    else:
        raise ValueError(f"Dataset not found or not a ZIP/directory: {source}")
    image_names = [n for n in names if PurePosixPath(n).suffix.lower() in IMAGE_SUFFIXES]
    return {"source": str(source.resolve()), "files": len(names), "images": len(image_names),
            "uncompressed_bytes": size,
            "image_folders": dict(sorted(Counter(str(PurePosixPath(n).parent) for n in image_names).items())),
            "metadata_files": [n for n in names if PurePosixPath(n).suffix.lower() in
                               {".csv", ".json", ".txt", ".yaml", ".yml", ".xml", ".md"}][:100],
            "example_images": image_names[:20],
            "labels_verified": False,
            "note": "Folder names are inventory only, not confirmed integrity labels. Rice variety labels cannot train whole/broken classification."}


def extract_archive(source, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if sum(i.file_size for i in entries) > 4_000_000_000:
            raise ValueError("Archive exceeds the 4 GB uncompressed safety limit.")
        for info in entries:
            name = info.filename.replace("\\", "/")
            target = (destination / name).resolve()
            if not target.is_relative_to(destination) or ":" in name or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f"Unsafe archive member: {name}")
            if target.exists() and not info.is_dir():
                raise ValueError(f"Extraction would overwrite: {target}")
        # Validate the complete archive before writing any members.
        for info in entries:
            target = destination / info.filename.replace("\\", "/")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("xb") as dst:
                    import shutil
                    shutil.copyfileobj(src, dst)


def make_manifest(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    images = sorted(p for p in root.rglob("*") if p.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        raise ValueError("No images found.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, MANIFEST_FIELDS)
        writer.writeheader()
        for image in images:
            import os
            writer.writerow({"image": Path(os.path.relpath(image, output.parent)).as_posix(),
                             "label": "", "group_id": "", "verified": "false"})
    return len(images)


def load_manifest(path, source_labels=False):
    path = Path(path).resolve()
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not set(MANIFEST_FIELDS).issubset(reader.fieldnames or []):
            raise ValueError("Manifest requires: " + ", ".join(MANIFEST_FIELDS))
        records = list(reader)
    if not records:
        raise ValueError("Manifest is empty.")
    hashes = set()
    for line, row in enumerate(records, start=2):
        if row["label"] not in {"whole", "broken"}:
            raise ValueError(f"Row {line}: label must be whole or broken.")
        using_source = source_labels and row.get("label_source") == "dataset_folder"
        if not using_source and (row["verified"].strip().lower() != "true" or not row["group_id"].strip()):
            raise ValueError(f"Row {line}: manually verify the label and supply its original sample/capture group.")
        image = (path.parent / row["image"]).resolve()
        if not image.is_file():
            raise ValueError(f"Row {line}: missing image {image}")
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest in hashes:
            raise ValueError(f"Row {line}: duplicate image bytes; remove duplicates before training.")
        hashes.add(digest)
        row.update(image=str(image), sha256=digest, group_id=row["group_id"].strip())
    return records


def prepare_peruvian(root, output):
    """Import the documented entero/quebrado labels without inventing human review or capture IDs."""
    import json
    import os
    root, output = Path(root).resolve(), Path(output).resolve()
    rows, duplicates, conflicts, seen = [], [], [], {}
    conflict_hashes = set()
    for folder, label in [("entero", "whole"), ("quebrado", "broken")]:
        directory = root / "dataset" / folder
        images = sorted(p for p in directory.glob("*") if p.suffix.lower() in IMAGE_SUFFIXES)
        if not images:
            raise ValueError(f"Missing source category: {directory}")
        for image in images:
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            if digest in seen:
                previous, previous_label = seen[digest]
                if previous_label != label:
                    conflict_hashes.add(digest)
                    conflicts.append({"image": str(image), "conflicts_with": previous})
                    continue
                duplicates.append({"image": str(image), "duplicate_of": previous})
                continue
            seen[digest] = (str(image), label)
            rows.append({"image": Path(os.path.relpath(image, output.parent)).as_posix(),
                         "label": label, "group_id": "", "verified": "false", "label_source": "dataset_folder",
                         "_sha256": digest})
    rows = [row for row in rows if row["_sha256"] not in conflict_hashes]
    for row in rows:
        del row["_sha256"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, [*MANIFEST_FIELDS, "label_source"])
        writer.writeheader()
        writer.writerows(rows)
    report = {"manifest": str(output), "images": len(rows),
              "classes": dict(Counter(row["label"] for row in rows)),
              "duplicates_removed": duplicates, "source_capture_groups_known": False,
              "conflicting_label_pairs_excluded": conflicts,
              "independent_manual_label_review": False,
              "excluded_categories": ["mancha", "tiza", "visor"],
              "note": "Exploratory source-label training only. Original capture groups are unavailable; image-level test scores may overestimate generalization."}
    output.with_suffix(".import.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
