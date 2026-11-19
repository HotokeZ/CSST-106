import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bigascheck.checkpoints import evaluate_checkpoint

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reproduce classification metrics and CPU speed without retraining")
    parser.add_argument("--split", choices=["validation", "test"], default="validation")
    parser.add_argument("--weights", default="artifacts/model.joblib")
    parser.add_argument("--features", default="artifacts/features_and_splits.csv")
    parser.add_argument("--output", default="outputs/checkpoints/evaluation")
    parser.add_argument("--speed-images", type=int, default=20)
    args = parser.parse_args()
    metrics = evaluate_checkpoint(args.weights, args.features, args.split, args.output, args.speed_images)
    print(json.dumps({"split": metrics["split"], "instances": metrics["instances"],
                      "baseline_accuracy": metrics["baseline"]["accuracy"],
                      "tree_accuracy": metrics["decision_tree"]["accuracy"],
                      "tree_macro_f1": metrics["decision_tree"]["macro_f1"],
                      "mean_ms": metrics["speed"]["mean_ms"], "failures": metrics["failure_analysis"]["failures"],
                      "output": args.output}, indent=2))
