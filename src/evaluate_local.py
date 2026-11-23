"""Frozen-model descriptive evaluation of user-counted, ungrouped local photos."""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
from time import perf_counter
import numpy as np
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bigascheck.model import analyze,load_model
from bigascheck.vision import Settings,annotate,load_rgb,backend

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',default='data/local_20261120/manifest.csv')
    parser.add_argument('--output',default='outputs/local_20261120_frozen')
    parser.add_argument('--weights',default='artifacts/model.joblib')
    parser.add_argument('--detector',choices=['legacy','adaptive'],default='legacy')
    args=parser.parse_args();manifest=Path(args.manifest).resolve();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    # Preserve the first evaluation. New runs must choose another output folder.
    if (out/'protocol.json').exists():raise ValueError('Choose a new output folder; the prior protocol/results are preserved.')
    bundle=load_model(args.weights);settings=replace(Settings(**bundle['settings']),background='auto',split_touching=True,detector=args.detector)
    rows=list(csv.DictReader(manifest.open(encoding='utf-8')))
    protocol={'prepared':'2026-11-20','model_sha256':sha(args.weights),'manifest_sha256':sha(manifest),'backend':backend(),'settings':asdict(settings),'max_image_edge':1600,'resize':'EXIF transpose; RGB; proportional thumbnail to max 1600 using LANCZOS; save JPEG quality 95; no crops','selection':'All supplied photos. Score only complete filename counts; no selection based on predictions. Whole-only filenames imply zero broken, pending user confirmation.','grouping':'Physical sample/capture groups unknown; descriptive pooled and condition-level scores only. No capture-level independence or group confidence intervals claimed.','training':'No training or parameter tuning on these photos. Frozen saved model. Once evaluated, these images are exposed evaluation data.','count_reference':'User filename whole/broken counts; not independently reviewed. Photo IDs identify files, not physical rice samples.','timing':'Decode working JPEG + segmentation + features + tree; first image recorded separately, mean excludes first warm-up; excludes original resizing, rendering and disk output.'}
    protocol['evaluation_status']='Development comparison: these photo results guided adaptive detector changes; not an untouched final test.' if args.detector=='adaptive' else 'Frozen original detector evaluation.'
    protocol['code_sha256']={name:sha(ROOT/name) for name in ['src/evaluate_local.py','bigascheck/vision.py','bigascheck/foreground.py','bigascheck/model.py']}
    for name in protocol['code_sha256']:
        target=out/'code_snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    prepared=manifest.parent/'working_1600';prepared.mkdir(exist_ok=True)
    all_results=[];log=[]
    for row in rows:
        pid=row['photo_id'];target=out/pid;target.mkdir(exist_ok=True)
        try:
            source=manifest.parent/row['image']
            if sha(source)!=row['sha256']:raise ValueError('Original source hash mismatch')
            working=prepared/(pid+'.jpg')
            with Image.open(source) as image:
                image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((1600,1600),Image.Resampling.LANCZOS);image.save(working,quality=95)
            started=perf_counter();rgb=load_rgb(working);result,mask=analyze(rgb,bundle,settings);ms=1000*(perf_counter()-started)
            annotate(rgb,result['grains']).save(target/'annotated.jpg',quality=90)
            Image.fromarray(mask).save(target/'mask.png')
            baseline_broken=sum(g['features']['aspect_ratio']<bundle['baseline_threshold'] for g in result['grains'])
            baseline={'detected':len(result['grains']),'broken':int(baseline_broken),'whole':len(result['grains'])-int(baseline_broken),'broken_percentage':100*baseline_broken/len(result['grains']) if result['grains'] else None}
            (target/'results.json').write_text(json.dumps({'reference':row,'working_sha256':sha(working),'working_size':[rgb.shape[1],rgb.shape[0]],'decision_tree':result,'baseline_summary':baseline,'pipeline_ms':ms},indent=2),encoding='utf-8')
            scored=row['actual_whole']!='' and row['actual_broken']!=''
            for method,s in [('decision_tree',result['summary']),('baseline',baseline)]:
                r={'photo_id':pid,'original_filename':row['original_filename'],'condition':row['condition'],'method':method,'status':'scored' if scored else 'unscored_missing_counts','actual_whole':row['actual_whole'],'actual_broken':row['actual_broken'],'detected':s['detected'],'predicted_whole':s['whole'],'predicted_broken':s['broken'],'predicted_broken_percentage':s['broken_percentage'],'pipeline_ms':ms if method=='decision_tree' else ''}
                if scored:
                    actual=int(row['actual_whole'])+int(row['actual_broken']);truepct=100*int(row['actual_broken'])/actual
                    r.update(actual_count=actual,actual_broken_percentage=truepct,count_absolute_error=abs(s['detected']-actual),whole_absolute_error=abs(s['whole']-int(row['actual_whole'])),broken_absolute_error=abs(s['broken']-int(row['actual_broken'])),percentage_point_error=abs(s['broken_percentage']-truepct) if s['broken_percentage'] is not None else '')
                all_results.append(r)
            log.append({'photo_id':pid,'status':'ok','pipeline_ms':ms})
            print(f'{pid}: detected {result["summary"]["detected"]}; labeled={scored}; {ms:.0f} ms',flush=True)
        except (ValueError,OSError) as exc:
            log.append({'photo_id':pid,'status':'error','error':str(exc)})
            print(f'{pid}: ERROR {exc}',flush=True)
        (out/'progress.json').write_text(json.dumps(log,indent=2),encoding='utf-8')
    fields=list(dict.fromkeys(k for r in all_results for k in r))
    with (out/'per_photo_results.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(all_results)
    def summary(records):
        records=[r for r in records if r['status']=='scored'];percent=[r['percentage_point_error'] for r in records if r['percentage_point_error']!='']
        return {'photos':len(records),'count_mae':float(np.mean([r['count_absolute_error'] for r in records])) if records else None,'whole_count_mae':float(np.mean([r['whole_absolute_error'] for r in records])) if records else None,'broken_count_mae':float(np.mean([r['broken_absolute_error'] for r in records])) if records else None,'percentage_point_mae':float(np.mean(percent)) if len(percent)==len(records) and records else None,'conditional_percentage_point_mae':float(np.mean(percent)) if percent else None,'percentage_evaluable_photos':len(percent),'zero_detection_photos':sum(r['detected']==0 for r in records),'within_5_grains':sum(r['count_absolute_error']<=5 for r in records),'within_5_percentage_points':sum(r['percentage_point_error']!='' and r['percentage_point_error']<=5 for r in records)}
    metrics={'protocol':protocol,'imported_photos':len(rows),'execution_errors':[r for r in log if r['status']=='error'],'missing_count_photos':[r['photo_id'] for r in rows if r['actual_whole']==''],'conditions':dict(Counter(r['condition'] for r in rows)),'methods':{m:summary([r for r in all_results if r['method']==m]) for m in ['baseline','decision_tree']},'by_condition':{c:{m:summary([r for r in all_results if r['method']==m and r['condition']==c]) for m in ['baseline','decision_tree']} for c in sorted({r['condition'] for r in rows})},'pipeline_mean_ms_excluding_first':float(np.mean([r['pipeline_ms'] for r in log[1:] if r['status']=='ok'])),'limitations':['Counts alone do not identify per-grain predictions: no classification F1, confusion matrix, detection precision/recall, mAP or IoU is derived.','Percentage MAE is withheld when any scored photo has no detections; conditional percentage MAE has a smaller denominator.','No model improvement or independence claim is based on unknown capture/sample groups.']}
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    if sha(args.weights)!=protocol['model_sha256']:raise RuntimeError('Model changed during evaluation')
    print(json.dumps(metrics['methods'],indent=2))

if __name__=='__main__':main()
