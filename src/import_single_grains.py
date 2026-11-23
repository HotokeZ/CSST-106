"""Safely import user-labelled individual-grain photos into training only."""
import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageOps


def import_archive(archive, output):
    archive, output = Path(archive).resolve(), Path(output).resolve()
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    if (output / "audit.json").is_file():
        audit = json.loads((output / "audit.json").read_text())
        if audit["archive_sha256"] != archive_hash:
            raise ValueError("Use a new output directory for a different collection.")
        for row in audit["images"]:
            if hashlib.sha256((output / row["image"]).read_bytes()).hexdigest() != row["sha256"]:
                raise ValueError("An imported original changed.")
        return audit
    if output.exists() and any(output.iterdir()):
        raise ValueError("Import output must be empty.")
    candidates, seen, duplicates = [], {}, []
    with zipfile.ZipFile(archive) as source:
        entries = [info for info in source.infolist() if not info.is_dir()]
        if len(entries) > 1000 or sum(info.file_size for info in entries) > 2_000_000_000:
            raise ValueError("Archive exceeds import size limits.")
        for info in sorted(entries, key=lambda item: item.filename):
            path = PurePosixPath(info.filename.replace('\\', '/'))
            if path.is_absolute() or '..' in path.parts or any(':' in p for p in path.parts) or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Unsafe archive entry.")
            if path.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}:
                continue
            labels = {label for label, names in [('whole', {'whole','whole grains'}), ('broken', {'broken','broken grains'})]
                      if any(part.casefold() in names for part in path.parts[:-1])}
            if len(labels) != 1 or info.file_size > 15*1024*1024:
                raise ValueError("Each photo must have exactly one whole/broken parent folder and be under 15 MB.")
            data = source.read(info)
            sha = hashlib.sha256(data).hexdigest()
            label = labels.pop()
            if sha in seen:
                if seen[sha] != label:
                    raise ValueError("The same photograph has conflicting folder labels.")
                duplicates.append(info.filename)
                continue
            seen[sha] = label
            with Image.open(io.BytesIO(data)) as image:
                if image.width * image.height > 20_000_000:
                    raise ValueError("A photo exceeds the 20 MP input limit.")
                oriented = ImageOps.exif_transpose(image).convert('RGB')
                thumbnail = oriented.copy()
                thumbnail.thumbnail((230, 265))
                width, height = oriented.size
            relative = Path(label) / (path.stem + path.suffix.lower())
            if any(item[0]['image'] == relative.as_posix() for item in candidates):
                relative = Path(label) / (path.stem+'_'+sha[:8]+path.suffix.lower())
            row = {'image':relative.as_posix(), 'label':label, 'split':'train', 'sha256':sha,
                   'original_filename':info.filename, 'group_id':'', 'group_status':'unknown',
                   'label_source':'user-confirmed whole/broken folder', 'width':width, 'height':height,
                   'import_batch':archive_hash[:16]}
            candidates.append((row, data, thumbnail))
    if not candidates or set(row['label'] for row,_,_ in candidates) != {'whole','broken'}:
        raise ValueError("The collection must contain both whole and broken photos.")
    output.mkdir(parents=True)
    canvas = Image.new('RGB', (1200, 310*((len(candidates)+4)//5)), '#eeeeee')
    draw = ImageDraw.Draw(canvas)
    for i, (row, data, thumb) in enumerate(candidates):
        target = output / row['image']
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(data)
        x, y = (i%5)*240, (i//5)*310
        canvas.paste(thumb, (x+(240-thumb.width)//2, y))
        draw.text((x+4,y+268), f"{i+1:02d} {row['label']}", fill='black')
        draw.text((x+4,y+285), Path(row['image']).stem, fill='black')
    canvas.save(output / 'contact_sheet.jpg', quality=92)
    rows = [row for row,_,_ in candidates]
    with (output/'manifest.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,list(rows[0])); writer.writeheader(); writer.writerows(rows)
    audit={'archive_sha256':archive_hash,'counts':dict(Counter(r['label'] for r in rows)),
           'split':'train','duplicates_skipped':duplicates,'images':rows,
           'notes':['Folder labels were explicitly supplied by the user.',
                    'All photos are training-only; no new validation/test claims are made.',
                    'Capture and rice-sample groups are unknown and remain blank.',
                    'Segmentation must be reviewed before using a photo as one labelled grain.']}
    (output/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    return audit


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    parser.add_argument('--output',default='data/local_grains/batch_20261120_2')
    args=parser.parse_args()
    audit=import_archive(args.archive,args.output)
    print(json.dumps({k:v for k,v in audit.items() if k!='images'},indent=2))
