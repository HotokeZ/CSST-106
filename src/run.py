"""Checkpoint-compatible batch entry point; delegates to the application pipeline."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bigascheck.runner import run_path


def main():
    parser = argparse.ArgumentParser(description="Analyze one rice image or an image directory on CPU")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="outputs/batch")
    parser.add_argument("--weights", default="artifacts/model.joblib")
    parser.add_argument("--background", choices=["auto", "dark", "pale", "light"], default="auto")
    parser.add_argument("--connected-regions", action="store_true")
    parser.add_argument("--detector", choices=["adaptive", "legacy"], default="adaptive")
    args = parser.parse_args()
    rows = run_path(args.input, args.output, args.weights, args.background, not args.connected_regions, args.detector)
    print(json.dumps({"images": len(rows), "errors": sum(r["status"] == "error" for r in rows), "output": args.output}, indent=2))
    return int(any(row["status"] == "error" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
