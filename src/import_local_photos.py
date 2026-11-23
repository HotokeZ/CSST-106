"""Import user photos/counts without inventing capture/sample group identities."""
import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path, PurePosixPath
from PIL import Image, ImageDraw, ImageOps

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',required=True)
    parser.add_argument('--output',default='data/local_20261120')
    args=parser.parse_args();out=Path(args.output);(out/'originals').mkdir(parents=True,exist_ok=True)
    rows=[];tiles=[];seen={}
    with zipfile.ZipFile(args.archive) as z:
        members=sorted((i for i in z.infolist() if not i.is_dir() and Path(i.filename).suffix.lower() in {'.jpg','.jpeg','.png','.webp'}),key=lambda x:x.filename)
        if sum(i.file_size for i in members)>1024**3:raise ValueError('Archive exceeds 1 GiB import limit')
        for index,item in enumerate(members,1):
            parts=PurePosixPath(item.filename).parts
            if '..' in parts or item.filename.startswith(('/', '\\')):raise ValueError('Unsafe archive path')
            raw=z.read(item);sha=hashlib.sha256(raw).hexdigest();name=Path(item.filename).name
            whole=re.search(r'(\d+)\s+whole\b',name,re.I);broken=re.search(r'(\d+)\s+brok(?:en|e)\b',name,re.I)
            w=int(whole[1]) if whole else '';b=int(broken[1]) if broken else (0 if whole else '')
            sid=f'local_{index:03d}';relative='originals/'+sid+Path(name).suffix.lower()
            (out/relative).write_bytes(raw)
            with Image.open(io.BytesIO(raw)) as photo:
                im=ImageOps.exif_transpose(photo).convert('RGB');width,height=im.size
                thumb=ImageOps.contain(im,(300,225))
            tile=Image.new('RGB',(320,285),'white');tile.paste(thumb,((320-thumb.width)//2,0));draw=ImageDraw.Draw(tile)
            draw.text((8,231),f'{sid} | whole {w} | broken {b}',fill='black')
            draw.text((8,248),name[:48],fill='black');draw.text((8,265),f'{width}x{height}',fill='black');tiles.append(tile)
            rows.append({'photo_id':sid,'image':relative,'condition':parts[-2],'original_filename':name,'actual_whole':w,'actual_broken':b,'sample_id':'','group_id':'','group_status':'unknown','count_source':'user filename','count_note':'missing broken count interpreted as zero' if whole and not broken else ('count missing' if w=='' else 'whole/broken explicit'),'sha256':sha,'duplicate_of':seen.get(sha,''),'width':width,'height':height,'split':'local_evaluation_only'})
            seen.setdefault(sha,sid)
    with (out/'manifest.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,rows[0].keys());writer.writeheader();writer.writerows(rows)
    sheet=Image.new('RGB',(320*5,285*((len(tiles)+4)//5)),'#dfe8df')
    for i,t in enumerate(tiles):sheet.paste(t,((i%5)*320,(i//5)*285))
    sheet.save(out/'photo_contact_sheet.jpg',quality=90)
    audit={'photos':len(rows),'labeled':sum(r['actual_whole']!='' for r in rows),'missing_counts':[r for r in rows if r['actual_whole']==''],'duplicate_photos':[r['photo_id'] for r in rows if r['duplicate_of']],'over_20_megapixels':sum(r['width']*r['height']>20_000_000 for r in rows),'whole_only_zero_broken_assumptions':[r['photo_id'] for r in rows if 'interpreted' in r['count_note']],'grouping':'Unknown. No per-photo unique capture groups invented. Do not split this cohort into training and final test without reliable physical sample/session grouping.','counts_status':'User filename counts, not independently reviewed','archive_sha256':hashlib.sha256(Path(args.archive).read_bytes()).hexdigest()}
    (out/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
