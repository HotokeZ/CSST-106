"""Convert fully reviewed LabelMe exports to a grouped YOLO segmentation dataset."""
import argparse
import base64
import hashlib
import io
import json
import math
from pathlib import Path

from PIL import Image

CLASSES = ['whole', 'broken', 'discolored_whole', 'discolored_broken', 'impurity']


def prepare(annotations, output):
    source, target = Path(annotations).resolve(), Path(output).resolve()
    if target == source or source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError('Choose a separate output directory outside the annotation folder.')
    if target.exists() and any(target.iterdir()):
        raise ValueError('Choose a new empty output folder; existing datasets are preserved.')
    files = sorted(source.glob('*.json'))
    if not files:
        raise ValueError('No annotation JSON files found.')
    records, groups, images = [], {}, set()
    for path in files:
        data = json.loads(path.read_text(encoding='utf-8'))
        meta = data.get('bigascheck', {})
        group, split = meta.get('capture_group', '').strip(), meta.get('split')
        if meta.get('reviewed_complete') is not True or not group or split not in {'train', 'validation', 'test'}:
            raise ValueError(f'{path.name}: review confirmation, capture group and partition are required.')
        if group in groups and groups[group] != split:
            raise ValueError('Related capture groups cannot cross dataset partitions.')
        groups[group] = split
        raw = base64.b64decode(data['imageData'], validate=True)
        if len(raw) > 30 * 1024 * 1024:
            raise ValueError('Annotation image exceeds 30 MB.')
        with Image.open(io.BytesIO(raw)) as image:
            width, height = image.size
            if width * height > 20_000_000 or width < 8 or height < 8:
                raise ValueError('Image dimensions are outside the supported limits.')
            rgb = image.convert('RGB')
        if (width, height) != (data['imageWidth'], data['imageHeight']):
            raise ValueError('Annotation dimensions do not match the embedded image.')
        digest = hashlib.sha256(width.to_bytes(4, 'big') + height.to_bytes(4, 'big') + rgb.tobytes()).hexdigest()
        if digest in images:
            raise ValueError('Duplicate decoded image in annotations; keep one reviewed copy.')
        images.add(digest)
        labels = []
        for shape in data.get('shapes', []):
            if shape.get('shape_type') != 'polygon' or shape.get('flags', {}).get('manually_reviewed') is not True or shape.get('label') not in CLASSES:
                raise ValueError('Every object needs a manually reviewed polygon and supported rice/impurity label.')
            if shape['label'] != 'impurity' and shape.get('flags', {}).get('discoloration_reviewed') is not True:
                raise ValueError('Discoloration must be reviewed for every rice grain.')
            points = shape.get('points', [])
            if not 3 <= len(points) <= 1000:
                raise ValueError('Invalid polygon point count.')
            for point in points:
                if (len(point) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in point)
                        or not 0 <= point[0] < width or not 0 <= point[1] < height):
                    raise ValueError('Polygon points must be finite image coordinates.')
            area = abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points, points[1:]+points[:1]))) / 2
            if area < 4:
                raise ValueError('Polygon area is too small.')
            def cross(a,b,c):
                return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            def on(a,b,p):
                return cross(a,b,p)==0 and min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])
            for i,a in enumerate(points):
                b=points[(i+1)%len(points)]
                for j in range(i+1,len(points)):
                    if j==i+1 or (i==0 and j==len(points)-1):
                        continue
                    c,d=points[j],points[(j+1)%len(points)]
                    if (cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0) or on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b):
                        raise ValueError('Polygon edges cross or touch.')
            labels.append(str(CLASSES.index(shape['label'])) + ' ' + ' '.join(f'{v:.8f}' for x,y in points for v in [x/width,y/height]))
        if not labels:
            raise ValueError('Each export must contain at least one reviewed grain.')
        records.append((digest, split, group, rgb, labels, path.name))
    # Validate every input before writing anything.
    target.mkdir(parents=True, exist_ok=True)
    inventory = []
    for digest, split, group, rgb, labels, name in records:
        for folder in ['images', 'labels']:
            (target/folder/split).mkdir(parents=True, exist_ok=True)
        rgb.save(target/'images'/split/(digest+'.png'))
        (target/'labels'/split/(digest+'.txt')).write_text('\n'.join(labels)+'\n', encoding='utf-8')
        inventory.append(dict(image=digest+'.png', decoded_image_sha256=digest, split=split, capture_group=group, objects=len(labels), source_annotation=name))
    config = ['path: '+json.dumps(target.as_posix()), 'train: images/train', 'val: images/validation']
    if any(r['split']=='test' for r in inventory):
        config.append('test: images/test')
    config += ['names:'] + [f'  {i}: {label}' for i,label in enumerate(CLASSES)]
    (target/'dataset.yaml').write_text('\n'.join(config)+'\n', encoding='utf-8')
    class_counts={s:{name:sum(line.startswith(str(index)+' ') for _,sp,_,_,lines,_ in records if sp==s for line in lines) for index,name in enumerate(CLASSES)} for s in ['train','validation','test']}
    report = {'images':len(inventory),'objects':sum(r['objects'] for r in inventory),'classes':CLASSES,'class_counts':class_counts,'partitions':{s:sum(r['split']==s for r in inventory) for s in ['train','validation','test']},'inventory':inventory,
              'evaluation_note':'Group and duplicate checks do not prove independence. Test captures must never have been used for training or tuning.'}
    (target/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.annotations,args.output),indent=2))
