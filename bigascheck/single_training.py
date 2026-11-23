"""Combine reviewed local single-grain silhouettes with Kaggle training rows."""
import copy
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.tree import DecisionTreeClassifier

from .local_training import read_rows
from .model import load_model, scores, shape_matrix, SHAPE_FEATURES
from .samples import digest
from .vision import FEATURES, backend


def reviewed_rows(feature_table, manifest, source_table, local_split_manifest):
    feature_table, manifest = Path(feature_table).resolve(), Path(manifest).resolve()
    rows, originals = read_rows(feature_table), {r['sha256']:r for r in read_rows(manifest)}
    excluded = {r['sha256'] for r in read_rows(source_table)} | {r['sha256'] for r in read_rows(local_split_manifest)}
    seen = set()
    protocol = json.loads((feature_table.parent/'protocol.json').read_text())
    if protocol['manifest_sha256'] != digest(manifest) or protocol.get('backend',backend()) != backend():
        raise ValueError('Single-grain extraction does not match this manifest/backend.')
    candidates = {(r['sha256'],r['grain_id']):r for r in read_rows(feature_table.parent/'candidates.csv')}
    for row in rows:
        original = originals.get(row['sha256'])
        candidate = candidates.get((row['sha256'],row['grain_id']))
        if (row.get('reviewed') != 'true' or row['split'] != 'train' or original is None or candidate is None or
            original['split'] != 'train' or row['label'] != original['label'] or row['image'] != original['image'] or
            candidate['image'] != original['image'] or row['bbox'] != candidate['bbox'] or row['label'] not in {'whole','broken'}):
            raise ValueError('Require a reviewed target and user label from a training-only original.')
        if row['sha256'] in seen or row['sha256'] in excluded:
            raise ValueError('A single-grain image is duplicated or already belongs to the original dataset/partitions.')
        image = (manifest.parent/original['image']).resolve()
        if not image.is_relative_to(manifest.parent) or digest(image) != row['sha256']:
            raise ValueError('A local single-grain original changed.')
        values = np.asarray([float(row[f]) for f in FEATURES])
        if not np.isfinite(values).all() or any(row[f] != candidate[f] for f in FEATURES):
            raise ValueError('Reviewed feature values differ from the extracted candidate.')
        seen.add(row['sha256'])
    if not rows or set(r['label'] for r in rows) != {'whole','broken'}:
        raise ValueError('Reviewed local single grains must represent both classes.')
    return rows


def domain_weights(source_y, local_y, local_weight):
    weights=[]
    for labels,weight in [(source_y,1.0),(local_y,local_weight)]:
        if set(labels) != {'whole','broken'}:
            raise ValueError('Both classes are required in each training domain.')
        counts = {label:int(np.sum(labels==label)) for label in ['whole','broken']}
        weights.extend(weight/(2*counts[label]) for label in labels)
    return np.asarray(weights)


def train_single_combined(source_table, local_features, local_manifest, split_manifest, weights, output):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new supervised training output directory.')
    local = reviewed_rows(local_features, local_manifest, source_table, split_manifest)
    frame = pd.read_csv(source_table,keep_default_na=False)
    training=frame[frame.split=='train']; validation=frame[frame.split=='validation']; test=frame[frame.split=='test']
    if any(set(part.label) != {'whole','broken'} for part in [training,validation,test]):
        raise ValueError('Retain the original Kaggle train/validation/test splits with both classes.')
    sx=shape_matrix(training[FEATURES].to_numpy(float)); sy=training.label.to_numpy()
    lx=shape_matrix(np.asarray([[float(r[f]) for f in FEATURES] for r in local])); ly=np.asarray([r['label'] for r in local])
    vx=shape_matrix(validation[FEATURES].to_numpy(float)); vy=validation.label.to_numpy()
    active=load_model(weights)
    x,y=np.r_[sx,lx],np.r_[sy,ly]
    selection=[]; best=None
    for depth in [3,4,5]:
        for leaf in [3,10]:
            for local_weight in [.1,.25,.5]:
                tree=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=leaf,random_state=42)
                tree.fit(x,y,sample_weight=domain_weights(sy,ly,local_weight))
                local_predictions=[]
                for i in range(len(local)):
                    keep=np.arange(len(local))!=i
                    fold=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=leaf,random_state=42)
                    fold.fit(np.r_[sx,lx[keep]],np.r_[sy,ly[keep]],sample_weight=domain_weights(sy,ly[keep],local_weight))
                    local_predictions.append(fold.predict(lx[i:i+1])[0])
                source_f1=float(f1_score(vy,tree.predict(vx),average='macro',zero_division=0))
                local_f1=float(f1_score(ly,local_predictions,average='macro',zero_division=0))
                score=.75*source_f1+.25*local_f1
                record={'max_depth':depth,'min_samples_leaf':leaf,'local_domain_weight':local_weight,
                        'source_validation_macro_f1':source_f1,'local_leave_one_photo_out_macro_f1':local_f1,
                        'selection_score':score}
                selection.append(record)
                if best is None or score>best[0]:
                    best=(score,tree,record,local_predictions)
    _,tree,chosen,loo=best
    bundle=copy.deepcopy(active)
    bundle.pop('local_count_calibration',None)
    bundle['tree']=tree
    bundle['feature_mode']='shape'; bundle['classification_features']=SHAPE_FEATURES
    report={'training_mode':'kaggle_plus_user_labelled_single_grains',
            'kaggle_training_instances':len(training),'local_training_instances':len(local),
            'local_class_counts':{label:int(sum(ly==label)) for label in ['whole','broken']},
            'feature_schema':SHAPE_FEATURES,'selection':chosen,'selection_candidates':selection,
            'selection_rule':'0.75 * Kaggle validation macro F1 + 0.25 * local training leave-one-photo-out macro F1',
            'local_selection_limit':'Capture/sample groups are unknown; leave-one-photo-out results are selection scores, not independent final performance.',
            'local_label_provenance':'User-confirmed folder labels; assistant visually reviewed target identity and crop completeness, not physical grain integrity.',
            'local_resubstitution':scores(ly,tree.predict(lx)),
            'previous_tree_local_resubstitution':scores(ly,active['tree'].predict(lx)),
            'source_validation':scores(vy,tree.predict(vx)),
            'source_feature_table_sha256':digest(source_table),'local_features_sha256':digest(local_features),
            'local_manifest_sha256':digest(local_manifest),'source_model_sha256':digest(weights),
            'source_partition_note':'Kaggle split assignments unchanged; every new local single-grain photograph is training-only.',
            'segmentation_backend':backend()}
    # Replace inherited tree metrics so an updated model never claims the old
    # tree's parameters, importances, dataset size or test results.
    bundle['report']={
        'training_mode':report['training_mode'],'feature_mode':'shape','classification_features':SHAPE_FEATURES,
        'dataset':{'images':len(frame)+len(local),'classes':{
            label:int(sum(frame.label==label)+sum(ly==label)) for label in ['whole','broken']}},
        'split_unit':'image; capture groups unknown',
        'split':{name:{'instances':len(part)+(len(local) if name=='train' else 0),'groups':[]}
                 for name,part in [('train',training),('validation',validation),('test',test)]},
        'settings':bundle['settings'],'segmentation_backend':backend(),
        'decision_tree_parameters':{'max_depth':tree.max_depth,'min_samples_leaf':tree.min_samples_leaf},
        'validation_broken_f1':report['source_validation']['broken_f1'],
        'feature_importance':dict(zip(SHAPE_FEATURES,tree.feature_importances_.tolist())),
        'baseline_feature':bundle['baseline_feature'],'baseline_threshold':bundle['baseline_threshold'],
        'single_grain_training':report,
        'evaluation_report':f'{output.name}/report.json',
        'limitations':['Local single-grain selection scores use related training photos; capture/sample identities are unknown.',
                       'User folder labels are retained; crop review verifies the target, not a physical measurement of breakage.',
                       'Shape classification cannot fix extra detections or missing/merged grains.']}
    output.mkdir(parents=True)
    # Save model before evaluating the existing source development-test labels.
    joblib.dump(bundle,output/'model.joblib')
    report['model_sha256']=digest(output/'model.joblib')
    tx=shape_matrix(test[FEATURES].to_numpy(float))
    report['source_development_test']=scores(test.label.to_numpy(),tree.predict(tx))
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    combined=frame.copy()
    local_frame=pd.DataFrame(local)
    local_frame['image']=[str((Path(local_manifest).resolve().parent/r['image']).resolve()) for r in local]
    local_frame['label_source']='user_folder_reviewed_target'; local_frame['verified']='user_label'
    combined=pd.concat([combined,local_frame],ignore_index=True)
    combined.to_csv(output/'features_and_splits.csv',index=False)
    return report
