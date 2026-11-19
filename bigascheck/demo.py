"""Generate artificial ellipses ONLY for smoke testing, never research evidence."""
import csv
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


def generate(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    rows = []
    for group in range(14):
        for label in ["whole", "broken"]:
            for number in range(3):
                image = Image.new("RGB", (256, 256), (15, 22, 29))
                draw = ImageDraw.Draw(image)
                length = int(rng.integers(64, 86) if label == "whole" else rng.integers(23, 43))
                width = int(rng.integers(14, 21))
                cx, cy = map(int, rng.integers(100, 155, size=2))
                color = tuple(map(int, rng.integers(190, 241, size=3)))
                draw.ellipse((cx-length//2, cy-width//2, cx+length//2, cy+width//2), fill=color)
                name = f"synthetic_{group}_{label}_{number}.png"
                image.save(root / name)
                rows.append({"image": name, "label": label, "group_id": f"synthetic_{group}", "verified": "true"})
    with (root / "manifest.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, ["image", "label", "group_id", "verified"])
        writer.writeheader()
        writer.writerows(rows)
    sample = Image.new("RGB", (600, 400), (15, 22, 29))
    draw = ImageDraw.Draw(sample)
    for n in range(12):
        x, y = 65 + (n % 4) * 145, 65 + (n // 4) * 130
        half_length = 16 if n % 3 == 0 else 38
        draw.ellipse((x-half_length, y-9, x+half_length, y+9), fill=(220, 215, 200))
    sample.save(root / "sample.png")
    with (root / "samples.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["image", "group_id", "actual_whole", "actual_broken"])
        writer.writerow(["sample.png", "synthetic_external", 8, 4])
    (root / "SYNTHETIC_ONLY.txt").write_text("Artificial ellipse images for software tests. NOT real rice data or research results.\n", encoding="utf-8")
    return str(root / "manifest.csv")
