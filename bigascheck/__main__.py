import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

from .dataset import audit, extract_archive, make_manifest, prepare_peruvian
from .model import analyze, load_model, train, train_shape
from .vision import Settings, annotate, load_rgb


def main():
    parser = argparse.ArgumentParser(description="BigasCheck rice inspection prototype")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("audit", help="Inventory a dataset ZIP/folder without assuming labels")
    p.add_argument("source")
    p.add_argument("--output")
    p = commands.add_parser("extract", help="Extract a ZIP without overwriting existing files")
    p.add_argument("source")
    p.add_argument("destination")
    p = commands.add_parser("manifest", help="Create a blank manifest for human review")
    p.add_argument("root")
    p.add_argument("output")
    p = commands.add_parser("prepare-peruvian", help="Import entero/quebrado source labels for exploratory training")
    p.add_argument("root")
    p.add_argument("output")
    p = commands.add_parser("train")
    p.add_argument("manifest")
    p.add_argument("--output", default="artifacts")
    p.add_argument("--background", choices=["dark", "light"], default="dark")
    p.add_argument("--min-area", type=int, default=30)
    p.add_argument("--max-area-fraction", type=float, default=0.15)
    p.add_argument("--morphology", type=int, choices=range(4), default=1)
    p.add_argument("--source-labels", action="store_true", help="Exploratory image split using dataset folder labels; capture groups not verified")
    p = commands.add_parser("analyze")
    p.add_argument("image")
    p.add_argument("--model")
    p.add_argument("--method", choices=["decision_tree", "baseline"], default="decision_tree")
    p.add_argument("--background", choices=["auto", "dark", "pale", "light"])
    p.add_argument("--split-touching", action="store_true")
    p.add_argument("--output", default="outputs/analysis")
    p = commands.add_parser("train-shape", help="Train a scale-invariant silhouette classifier from an extracted-feature table")
    p.add_argument("--features", default="artifacts/features_and_splits.csv")
    p.add_argument("--output", default="artifacts")
    p = commands.add_parser("prepare-samples", help="Create train/validation/test image folders and the held-out gallery")
    p.add_argument("--features", default="artifacts/features_and_splits.csv")
    p.add_argument("--output", default="data/splits")
    p = commands.add_parser("evaluate-samples")
    p.add_argument("csv")
    p.add_argument("--model", default="artifacts/model.joblib")
    p.add_argument("--output", default="outputs/sample_evaluation.json")
    p = commands.add_parser("demo", help="Generate artificial smoke-test images, not real rice")
    p.add_argument("--output", default="data/demo")
    args = parser.parse_args()
    try:
        if args.command == "audit":
            result = audit(args.source)
            if args.output:
                save_json(args.output, result)
        elif args.command == "extract":
            extract_archive(args.source, args.destination)
            result = {"extracted_to": args.destination}
        elif args.command == "manifest":
            result = {"rows": make_manifest(args.root, args.output), "manifest": args.output,
                      "next_step": "Review each image; fill label, original group_id, and verified=true."}
        elif args.command == "train":
            result = train(args.manifest, args.output, Settings(background=args.background, min_area=args.min_area,
                           max_area_fraction=args.max_area_fraction, morphology=args.morphology), source_labels=args.source_labels)
        elif args.command == "prepare-peruvian":
            result = prepare_peruvian(args.root, args.output)
        elif args.command == "train-shape":
            result = train_shape(args.features, args.output)
        elif args.command == "prepare-samples":
            from .samples import build_samples
            result = build_samples(args.features, args.output)
        elif args.command == "analyze":
            rgb = load_rgb(args.image)
            bundle = load_model(args.model) if args.model else None
            settings = Settings(**bundle["settings"]) if bundle else Settings()
            settings = replace(settings, background=args.background or settings.background,
                               split_touching=args.split_touching)
            result, mask = analyze(rgb, bundle, settings, args.method)
            output = Path(args.output)
            output.mkdir(parents=True, exist_ok=True)
            annotate(rgb, result["grains"]).save(output / "annotated.png")
            from PIL import Image
            Image.fromarray(mask).save(output / "mask.png")
            save_json(output / "results.json", result)
            import pandas as pd
            pd.DataFrame([{ "grain_id": g["grain_id"], "prediction": g.get("prediction", "unclassified"), "model_score": g.get("model_score"),
                            **g["features"]} for g in result["grains"]]).to_csv(output / "grains.csv", index=False)
            result = result["summary"]
        elif args.command == "evaluate-samples":
            from .evaluation import evaluate_samples
            result = evaluate_samples(args.csv, load_model(args.model))
            save_json(args.output, result)
        elif args.command == "demo":
            from .demo import generate
            result = {"synthetic_manifest": generate(args.output), "warning": "Software smoke tests only; not research evidence."}
        print(json.dumps(result, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"BigasCheck: {exc}\n")


def save_json(path, result):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
