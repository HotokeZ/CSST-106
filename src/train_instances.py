"""Explicit optional instance-model training; never replaces the existing app model."""
import argparse
import json
from pathlib import Path


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',required=True,help='Prepared instance dataset directory')
    parser.add_argument('--weights',default='yolo11n-seg.pt')
    parser.add_argument('--epochs',type=int,default=100)
    parser.add_argument('--device',default='cpu')
    parser.add_argument('--batch',type=int,default=2)
    parser.add_argument('--output',required=True,help='New training output directory')
    args=parser.parse_args()
    data=Path(args.dataset).resolve()
    manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    if not manifest['partitions']['train'] or not manifest['partitions']['validation']:
        raise SystemExit('Collect reviewed training AND validation images from separate capture groups first.')
    if any(not manifest['class_counts'][s][c] for s in ['train','validation'] for c in manifest['classes']):
        raise SystemExit('Each configured class needs reviewed training and validation instances, including discoloration and impurities.')
    output=Path(args.output).resolve()
    if output.exists():
        raise SystemExit('Choose a new output directory; earlier runs are preserved.')
    if args.epochs<1 or args.batch<1:
        raise SystemExit('Epochs and batch size must be positive.')
    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit('Install Ultralytics in a separate training environment; see docs/INSTANCE_TRAINING.md.')
    model=YOLO(args.weights,task='segment')
    model.train(data=str(data/'dataset.yaml'),epochs=args.epochs,imgsz=1024,device=args.device,
                project=str(output.parent),name=output.name,exist_ok=False,seed=42,batch=args.batch,workers=0)
    print('Training complete. Evaluate instance masks, split/merge errors and speed before integrating these weights into the app.')
