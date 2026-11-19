import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bigascheck.demo_cases import run_demo_cases

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Record the checkpoint's 12 demo cases, including failures")
    parser.add_argument("--output", default="outputs/checkpoints/test_cases")
    args = parser.parse_args()
    print(json.dumps(run_demo_cases(args.output), indent=2))
