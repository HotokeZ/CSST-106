"""Prepare portable Kaggle-first demonstration images; Local Dataset 1 is excluded."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigascheck.gallery import build_gallery

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--feature-table',default='artifacts/features_and_splits.csv')
    parser.add_argument('--output',default='data/gallery')
    parser.add_argument('--local-features',default='artifacts/local_single_extraction_v1/reviewed_features.csv')
    parser.add_argument('--local-root',default='data/local_grains/batch_20261120_2')
    parser.add_argument('--per-class',type=int,default=12)
    args=parser.parse_args();print(json.dumps(build_gallery(args.feature_table,args.output,args.local_features,args.local_root,args.per_class),indent=2))
