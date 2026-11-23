"""Extract individual-grain candidates for visual review before training."""
import argparse
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw
from bigascheck.local_training import read_rows
from bigascheck.samples import digest
from bigascheck.vision import FEATURES, Settings, annotate, load_rgb, segment


def extract(manifest, output):
    manifest, output = Path(manifest).resolve(), Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a new extraction output directory.")
    rows = read_rows(manifest)
    if any(r['split'] != 'train' or r['label'] not in {'whole','broken'} for r in rows):
        raise ValueError("Only labelled training images may be extracted.")
    output.mkdir(parents=True)
    candidates, index, thumbnails = [], [], []
    for row in rows:
        source = (manifest.parent / row['image']).resolve()
        if not source.is_relative_to(manifest.parent) or digest(source) != row['sha256']:
            raise ValueError("Changed or invalid training image.")
        rgb = load_rgb(source, max_edge=1600)
        settings = Settings(background='auto', min_area=30, max_area_fraction=.6, split_touching=True, detector='adaptive')
        grains, rejected, mask = segment(rgb, settings)
        name = row['sha256'][:16]
        folder = output / name
        folder.mkdir()
        annotate(rgb, grains).save(folder / 'candidates.jpg', quality=92)
        Image.fromarray(mask).save(folder / 'mask.png')
        for grain in grains:
            x,y,w,h = grain['bbox']
            crop = Image.fromarray(rgb).crop((max(0,x-12),max(0,y-12),min(rgb.shape[1],x+w+12),min(rgb.shape[0],y+h+12)))
            crop.save(folder / f"grain_{grain['grain_id']:03d}.jpg", quality=95)
            thumb = crop.copy(); thumb.thumbnail((180,160))
            thumbnails.append((row['label'],Path(row['image']).stem,grain['grain_id'],thumb))
            candidates.append({**row, 'image':str(source.relative_to(manifest.parent)).replace('\\','/'),
                               'grain_id':grain['grain_id'], 'bbox':json.dumps(grain['bbox']),
                               **grain['features']})
        index.append({'image':row['image'],'sha256':row['sha256'],'label':row['label'],
                      'candidates':len(grains),'reviewed_grain_id':'','reviewed':'false'})
        print(f"{row['label']} {Path(row['image']).name}: {len(grains)} candidates",flush=True)
    canvas=Image.new('RGB',(1000,210*max(1,(len(thumbnails)+4)//5)),'#eeeeee'); draw=ImageDraw.Draw(canvas)
    for i,(label,name,grain_id,thumb) in enumerate(thumbnails):
        x,y=(i%5)*200,(i//5)*210
        canvas.paste(thumb,(x,y)); draw.text((x+2,y+163),f'{i+1:02d} {label} · grain {grain_id}',fill='black'); draw.text((x+2,y+181),name,fill='black')
    canvas.save(output/'candidate_contact_sheet.jpg',quality=95)
    for name, records in [('candidates.csv',candidates),('review.csv',index)]:
        with (output/name).open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,list(records[0])); writer.writeheader(); writer.writerows(records)
    protocol={'manifest_sha256':digest(manifest),'settings':settings.__dict__,
              'preprocessing_max_edge':1600,'extraction_code_sha256':digest(__file__),
              'vision_code_sha256':digest(Path(__file__).resolve().parents[1]/'bigascheck/vision.py'),
              'foreground_code_sha256':digest(Path(__file__).resolve().parents[1]/'bigascheck/foreground.py')}
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    return index


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',default='data/local_grains/batch_20261120_2/manifest.csv')
    parser.add_argument('--output',default='artifacts/local_single_extraction_v1')
    args=parser.parse_args(); extract(args.manifest,args.output)
