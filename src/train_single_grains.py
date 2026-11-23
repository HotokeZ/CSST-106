"""Train a shape tree from Kaggle and reviewed local single-grain labels."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigascheck.single_training import train_single_combined

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-features',default='artifacts/features_and_splits.csv')
    parser.add_argument('--local-features',default='artifacts/local_single_extraction_v1/reviewed_features.csv')
    parser.add_argument('--local-manifest',default='data/local_grains/batch_20261120_2/manifest.csv')
    parser.add_argument('--local-split-manifest',default='data/local_20261120/split_v1/manifest.csv')
    parser.add_argument('--weights',default='artifacts/model.joblib')
    parser.add_argument('--output',default='artifacts/combined_single_v1')
    args=parser.parse_args()
    report=train_single_combined(args.source_features,args.local_features,args.local_manifest,
                                args.local_split_manifest,args.weights,args.output)
    print(json.dumps({k:v for k,v in report.items() if k!='selection_candidates'},indent=2))
