"""Frozen development regression comparison, not a new independent test."""
import argparse,csv,json,platform,shutil
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image
import bigascheck.vision as vision
from bigascheck.model import load_model,analyze
from bigascheck.samples import digest

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',required=True)
parser.add_argument('--before-vision',default='milestone submission/shared/updates_20261123/vision_before.py')
args=parser.parse_args()
before_path=Path(args.before_vision);out=Path(args.output)
out.parent.mkdir(parents=True,exist_ok=True)
out.mkdir(exist_ok=False)
before=dict(vision.__dict__);exec((before_path).read_text(encoding='utf-8'),before)
for name in ['vision.py','foreground.py','model.py','gallery.py']:
    shutil.copy2(root/'bigascheck'/name,out/('current_'+name))
def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
source=root/'data/local_20261120/manifest.csv';split=root/'data/local_20261120/split_v1/manifest.csv'
assignments={r['photo_id']:r['split'] for r in rows(split)}
samples=[]
for row in rows(source):
    samples.append({'photo_id':row['photo_id'],'dataset':'local1','condition':row['condition'],'sha256':row['sha256'],
                    'split':assignments[row['photo_id']],'path':source.parent/row['image'],
                    'whole':int(row['actual_whole']) if row['actual_whole'] else None,
                    'broken':int(row['actual_broken']) if row['actual_broken'] else None})
singles=root/'data/local_grains/batch_20261120_2/manifest.csv'
for row in rows(singles):
    samples.append({'photo_id':'single_'+Path(row['image']).stem,'dataset':'local2','condition':'single_grain_training','sha256':row['sha256'],
                    'split':'train','path':singles.parent/row['image'],
                    'whole':int(row['label']=='whole'),'broken':int(row['label']=='broken')})
weights=root/'artifacts/model.joblib';bundle=load_model(weights)
settings=replace(vision.Settings(**bundle['settings']),background='auto',detector='adaptive',min_area=30,split_touching=True)
warmup=vision.load_rgb(next((root/'data/gallery/images').glob('kaggle-*.png')),max_edge=1600)
for _ in range(3):analyze(warmup,bundle,settings)
records=[]
protocol={'warning':'All photos are development/training material already inspected. No independent final evaluation is claimed.',
          'model_sha256':digest(weights),'local1_manifest_sha256':digest(source),'local2_manifest_sha256':digest(singles),
          'settings':settings.__dict__,'max_edge':1600,'warmups':3,
          'platform':platform.platform(),'processor':platform.processor(),
          'before_vision_sha256':digest(before_path),'after_vision_sha256':digest(root/'bigascheck/vision.py'),
          'speed_scope':'One loaded model, core analysis including segmentation/features/classification; excludes image loading/output rendering and HTTP.'}
(out/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
for index,sample in enumerate(samples,1):
    if digest(sample['path'])!=sample['sha256']:raise ValueError('Source image hash changed')
    rgb=vision.load_rgb(sample['path'],max_edge=1600)
    for variant,segment_fn in [('before',before['segment']),('after',vision.segment)]:
        with patch('bigascheck.model.segment',segment_fn):result,mask=analyze(rgb,bundle,settings)
        for method in ['main','baseline']:
            n=result['summary']['detected']
            broken=result['summary']['broken'] if method=='main' else sum(g['features']['aspect_ratio']<bundle['baseline_threshold'] for g in result['grains'])
            target=sample['whole']+sample['broken'] if sample['whole'] is not None else None
            row={k:sample[k] for k in ['photo_id','dataset','condition','split']}
            row.update(variant=variant,method=method,reference_whole=sample['whole'],reference_broken=sample['broken'],
                       detected=n,whole=n-broken,broken=broken,processing_ms=result['summary']['processing_ms'],
                       count_error=abs(n-target) if target is not None else None,
                       whole_error=abs(n-broken-sample['whole']) if target is not None else None,
                       broken_error=abs(broken-sample['broken']) if target is not None else None,
                       percentage_error_pp=abs(100*broken/n-100*sample['broken']/target) if n and target else None,
                       texture_recovery_used=result['preprocessing'].get('texture_recovery_used',False))
            records.append(row)
        if sample['photo_id']=='local_010':
            vision.annotate(rgb,result['grains']).save(out/f'pattern_{variant}.jpg',quality=92)
            Image.fromarray(mask).save(out/f'pattern_{variant}_mask.png')
            (out/f'pattern_{variant}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f"{index}/{len(samples)} {sample['photo_id']}: {records[-4]['detected']} -> {records[-2]['detected']}",flush=True)
with (out/'per_photo.csv').open('w',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,list(records[0]));writer.writeheader();writer.writerows(records)
def summarize(items):
    scored=[r for r in items if r['count_error'] is not None]
    percentage=[r['percentage_error_pp'] for r in scored if r['percentage_error_pp'] is not None]
    return {'images':len(items),'count_scored_images':len(scored),
            'count_mae':float(np.mean([r['count_error'] for r in scored])) if scored else None,
            'whole_mae':float(np.mean([r['whole_error'] for r in scored])) if scored else None,
            'broken_mae':float(np.mean([r['broken_error'] for r in scored])) if scored else None,
            'percentage_mae_pp':float(np.mean(percentage)) if percentage else None,
            'percentage_scored_images':len(percentage),'zero_detection_images':sum(r['detected']==0 for r in items),
            'mean_processing_ms':float(np.mean([r['processing_ms'] for r in items]))}
metrics={}
for name,predicate in [('local1_all',lambda r:r['dataset']=='local1'),
                       ('local1_fixed_development_test',lambda r:r['dataset']=='local1' and r['split']=='test'),
                       ('local2_training_photos',lambda r:r['dataset']=='local2')]:
    metrics[name]={}
    for variant in ['before','after']:
        metrics[name][variant]={method:summarize([r for r in records if predicate(r) and r['variant']==variant and r['method']==method]) for method in ['main','baseline']}
(out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
print(json.dumps(metrics,indent=2),flush=True)
