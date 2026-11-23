"""Expose the real shared preprocessing stage for checkpoint review."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bigascheck.vision import Settings, load_rgb, segment

if __name__ == '__main__':
    import argparse
    from PIL import Image
    parser = argparse.ArgumentParser(description='Apply the same preprocessing used by BigasCheck')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--background', choices=['auto','dark','pale','light'], default='auto')
    args = parser.parse_args()
    grains, rejected, mask = segment(load_rgb(args.input), Settings(background=args.background))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask).save(target)
