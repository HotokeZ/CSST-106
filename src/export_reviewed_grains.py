"""Export exactly one manually reviewed target per labelled training photo."""
import argparse
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigascheck.local_training import read_rows
from bigascheck.samples import digest


def export(extraction,manifest,output,reviewer='manual_target_review'):
    extraction,manifest,output=Path(extraction),Path(manifest),Path(output)
    if output.exists():
        raise ValueError('Use a new reviewed feature output file.')
    protocol=json.loads((extraction/'protocol.json').read_text())
    if protocol['manifest_sha256']!=digest(manifest):
        raise ValueError('Extraction manifest changed.')
    originals={r['sha256']:r for r in read_rows(manifest)}
    candidates={(r['sha256'],r['grain_id']):r for r in read_rows(extraction/'candidates.csv')}
    reviews=read_rows(extraction/'review.csv');seen=set();rows=[]
    for review in reviews:
        key=(review['sha256'],review['reviewed_grain_id'])
        if review['reviewed']!='true' or key not in candidates or review['sha256'] in seen:
            raise ValueError('Every photo requires one explicitly reviewed candidate.')
        row=dict(candidates[key]);original=originals.get(row['sha256'])
        if original is None or row['label']!=original['label'] or row['split']!='train' or row['image']!=original['image']:
            raise ValueError('Invalid training label or target membership.')
        row.update(reviewed='true',reviewer=reviewer,
                   review_scope='correct visible grain and complete crop; integrity label supplied by user folder')
        rows.append(row);seen.add(row['sha256'])
    if seen!=set(originals):
        raise ValueError('Each original must have exactly one reviewed target.')
    with output.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,list(rows[0]));writer.writeheader();writer.writerows(rows)
    return len(rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extraction',default='artifacts/local_single_extraction_v1')
    parser.add_argument('--manifest',default='data/local_grains/batch_20261120_2/manifest.csv')
    parser.add_argument('--output',default='artifacts/local_single_extraction_v1/reviewed_features.csv')
    parser.add_argument('--reviewer',default='manual_target_review')
    args=parser.parse_args();print('Exported reviewed targets:',export(args.extraction,args.manifest,args.output,args.reviewer))
