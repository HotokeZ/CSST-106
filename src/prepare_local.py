"""Create the frozen 18 train / 10 test / 5 demo photo partition."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bigascheck.local_training import prepare

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="data/local_20261120/manifest.csv")
    parser.add_argument("--output", default="data/local_20261120/split_v1")
    args = parser.parse_args()
    print(json.dumps(prepare(args.manifest, args.output), indent=2))
