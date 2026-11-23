"""Portable Kaggle-first gallery with explicitly labelled local training demos."""
import csv
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

from .samples import SampleError, digest, read_split_table, _thumbnail
from .vision import load_rgb


def signature(rows, fields):
    data=sorted([[row.get(k, '') for k in fields] for row in rows])
    return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()


def build_gallery(feature_table='artifacts/features_and_splits.csv', output='data/gallery',
                  local_features='artifacts/local_single_extraction_v1/reviewed_features.csv',
                  local_root='data/local_grains/batch_20261120_2', per_class=12):
    feature_table,output=Path(feature_table).resolve(),Path(output).resolve()
    rows=read_split_table(feature_table)
    pools={label:sorted([r for r in rows if r['split']=='test' and r['label']==label],key=lambda r:r['sha256'])
           for label in ['whole','broken']}
    count=min(per_class,*(len(p) for p in pools.values()))
    if count<1:raise SampleError('Need both classes in the preserved Kaggle test partition.')
    for name in ['images','thumbnails']: (output/name).mkdir(parents=True,exist_ok=True)
    items=[]

    def item(sample_id,title,source,label,kind,image,refs,whole,broken,note,extra=None):
        thumb=Path('thumbnails')/(sample_id+'.jpg')
        _thumbnail(output/image,output/thumb)
        record={'id':sample_id,'title':title,'source':source,'label':label,'kind':kind,
                'split':'test' if source=='kaggle' else 'train',
                'evaluation_role':'development_test_demo' if source=='kaggle' else 'training_demo',
                'expected_whole':whole,'expected_broken':broken,'image':image.as_posix(),
                'thumbnail':thumb.as_posix(),'sha256':digest(output/image),
                'thumbnail_sha256':digest(output/thumb),'source_sha256':refs,'note':note}
        if extra:record.update(extra)
        items.append(record)
        return record

    selected={label:pools[label][:count] for label in pools}
    source_images={}
    for index in range(count):
        for label in ['whole','broken']:
            row=selected[label][index];path=(feature_table.parent/row['image']).resolve()
            if not path.is_file() or digest(path)!=row['sha256']:
                raise SampleError('A Kaggle source image is missing or changed; extract the original dataset first.')
            sample_id='kaggle-'+row['sha256'][:16]
            target=Path('images')/(sample_id+path.suffix.lower())
            shutil.copy2(path,output/target);source_images[row['sha256']]=target
            item(sample_id,f'Kaggle · {label} grain {index+1:02d}','kaggle',label,'single',target,
                 [row['sha256']],int(label=='whole'),int(label=='broken'),
                 'Original Kaggle reference label. This development-test image is available for demonstration; it is not new independent evaluation.')
    if count>=6:
        composites=[('mixed',selected['whole'][:3]+selected['broken'][:3]),
                    ('whole',selected['whole'][:6]),('broken',selected['broken'][:6])]
        for label,sources in composites:
            images=[]
            for row in sources:
                with Image.open(output/source_images[row['sha256']]) as im:images.append(im.convert('RGB').copy())
            cw,ch=max(im.width for im in images)+24,max(im.height for im in images)+24
            canvas=Image.new('RGB',(cw*3,ch*2),'black')
            for i,im in enumerate(images):canvas.paste(im,((i%3)*cw+(cw-im.width)//2,(i//3)*ch+(ch-im.height)//2))
            sample_id='kaggle-composite-'+label;target=Path('images')/(sample_id+'.png');canvas.save(output/target)
            item(sample_id,f'Kaggle · {label} six-grain demo','kaggle',label,'composite',target,
                 [r['sha256'] for r in sources],sum(r['label']=='whole' for r in sources),sum(r['label']=='broken' for r in sources),
                 'Composite assembled from six Kaggle development-test grains; not a captured multi-grain photograph.')
        items=items[-3:]+items[:-3]
    local_records=[]
    local_features,local_root=Path(local_features).resolve(),Path(local_root).resolve()
    if local_features.is_file() and local_root.is_dir():
        with local_features.open(encoding='utf-8-sig',newline='') as f:local_records=list(csv.DictReader(f))
        for label in ['whole','broken']:
            choices=sorted([r for r in local_records if r['label']==label and r['split']=='train' and r['reviewed']=='true'],key=lambda r:r['sha256'])[:2]
            for index,row in enumerate(choices,1):
                original=(local_root/row['image']).resolve()
                if not original.is_relative_to(local_root) or digest(original)!=row['sha256']:
                    raise SampleError('A Local Dataset 2 source image changed.')
                rgb=load_rgb(original,max_edge=1600);x,y,w,h=json.loads(row['bbox'])
                box=[max(0,x-24),max(0,y-24),min(rgb.shape[1],x+w+24),min(rgb.shape[0],y+h+24)]
                sample_id='local2-'+row['sha256'][:16];target=Path('images')/(sample_id+'.png')
                Image.fromarray(rgb).crop(box).save(output/target)
                item(sample_id,f'Local 2 · {label} training demo {index}','local2',label,'training_crop',target,
                     [row['sha256']],int(label=='whole'),int(label=='broken'),
                     'Reviewed crop from a user-labelled Local Dataset 2 TRAINING photo. Demonstration only; not an unseen test image.',
                     {'reviewed_grain_id':row['grain_id'],'crop_box':box})
    with (output/'local2_references.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['sha256','label','split','grain_id','bbox','reviewed'];writer=csv.DictWriter(f,fields,extrasaction='ignore');writer.writeheader();writer.writerows(local_records)
    catalog={'format_version':2,'kaggle_split_signature':signature(rows,['sha256','label','split']),
             'local_reference_signature':signature(local_records,['sha256','label','split','grain_id','bbox','reviewed']),
             'source_feature_table_sha256':digest(feature_table),'samples':items,
             'source_counts':{name:sum(i['source']==name for i in items) for name in ['kaggle','local2']},
             'note':'Kaggle-first demonstration gallery. Local Dataset 1 is excluded. Local 2 examples retain their training role.'}
    temporary=output/'catalog.json.tmp';temporary.write_text(json.dumps(catalog,indent=2),encoding='utf-8');temporary.replace(output/'catalog.json')
    license_source=Path(__file__).resolve().parents[1]/'docs/USER_PROVIDED_LICENSE.txt'
    if license_source.is_file():shutil.copy2(license_source,output/'KAGGLE_LICENSE.txt')
    (output/'README.md').write_text('# Demonstration gallery\n\nKaggle originals and composites use only the preserved source development-test partition. Local Dataset 2 examples are reviewed crops of training photographs supplied by the user, included as training demonstrations with no independent-test claim. Local photos do not inherit the Kaggle licence. Local Dataset 1 is excluded. Rebuild with `python src/prepare_gallery.py` when original datasets are available.\n',encoding='utf-8')
    return {'directory':str(output),'total':len(items),'source_counts':catalog['source_counts']}


class GalleryCatalog:
    def __init__(self,root,feature_table):
        self.root,self.feature_table=Path(root).resolve(),Path(feature_table).resolve()
        self._stamp=None;self._items={}

    def refresh(self):
        catalog_path=self.root/'catalog.json';local_path=self.root/'local2_references.csv'
        stamp=tuple((p.stat().st_mtime_ns,p.stat().st_size) for p in [catalog_path,self.feature_table,local_path])
        if stamp==self._stamp:return
        try:
            catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
            rows=read_split_table(self.feature_table)
            with local_path.open(encoding='utf-8-sig',newline='') as f:local_rows=list(csv.DictReader(f))
            if (catalog['format_version']!=2 or catalog['kaggle_split_signature']!=signature(rows,['sha256','label','split']) or
                catalog['local_reference_signature']!=signature(local_rows,['sha256','label','split','grain_id','bbox','reviewed'])):
                raise SampleError('Gallery source assignments changed. Rebuild the demonstration gallery.')
            test={r['sha256']:r['label'] for r in rows if r['split']=='test'}
            kaggle_hashes={r['sha256'] for r in rows}
            local={r['sha256']:r for r in local_rows if r['split']=='train' and r['reviewed']=='true'}
            if len(local)!=len(local_rows):
                raise SampleError('Local demo references must be unique reviewed training rows.')
            items={}
            for entry in catalog['samples']:
                if entry['id'] in items or entry['source'] not in {'kaggle','local2'} or not entry['source_sha256']:
                    raise SampleError('Invalid gallery source or identifier.')
                refs=entry['source_sha256']
                if entry['source']=='kaggle':
                    if entry['split']!='test' or entry['evaluation_role']!='development_test_demo' or any(h not in test for h in refs):
                        raise SampleError('A Kaggle gallery item crosses the preserved test assignment.')
                    if entry['kind'] not in {'single','composite'} or (entry['kind']=='single' and (len(refs)!=1 or entry['sha256']!=refs[0] or entry['label']!=test[refs[0]])):
                        raise SampleError('Invalid Kaggle original reference.')
                    whole=sum(test[h]=='whole' for h in refs);broken=len(refs)-whole
                else:
                    if (entry['split']!='train' or entry['evaluation_role']!='training_demo' or entry['kind']!='training_crop' or len(refs)!=1
                        or refs[0] not in local or refs[0] in kaggle_hashes or entry['reviewed_grain_id']!=local[refs[0]]['grain_id'] or entry['label']!=local[refs[0]]['label']):
                        raise SampleError('Local Dataset 2 examples must remain reviewed training demos.')
                    whole=int(entry['label']=='whole');broken=int(entry['label']=='broken')
                if entry['expected_whole']!=whole or entry['expected_broken']!=broken:
                    raise SampleError('Invalid gallery reference counts.')
                for field,folder in [('image','images'),('thumbnail','thumbnails')]:
                    if not (self.root/entry[field]).resolve().is_relative_to(self.root/folder):
                        raise SampleError('Invalid gallery asset path.')
                items[entry['id']]=entry
            counts={name:sum(i['source']==name for i in items.values()) for name in ['kaggle','local2']}
            if counts!=catalog['source_counts'] or counts['kaggle']<=counts['local2']:
                raise SampleError('Gallery source totals must match a Kaggle-majority catalog.')
            self._items,self._stamp,self.counts=items,stamp,counts
        except (KeyError,TypeError,ValueError) as exc:
            raise SampleError('Invalid gallery catalog: '+str(exc)) from exc

    @staticmethod
    def public(item):
        return {key:item[key] for key in ['id','title','kind','label','split','source','evaluation_role','expected_whole','expected_broken','note']}

    def list(self,label='all',page=1,page_size=6,source='all'):
        self.refresh()
        if label not in {'all','whole','broken','mixed'} or source not in {'all','kaggle','local2'} or page<1 or not 1<=page_size<=24:
            raise SampleError('Invalid gallery filter or page.')
        items=[v for v in self._items.values() if (label=='all' or v['label']==label) and (source=='all' or v['source']==source)]
        start=(page-1)*page_size
        return {'items':[self.public(v) for v in items[start:start+page_size]],'total':len(items),'page':page,
                'page_size':page_size,'source_counts':self.counts,'note':'Local 2 items are training demonstrations, not unseen tests.'}

    def get(self,sample_id):
        self.refresh()
        if sample_id not in self._items:raise KeyError(sample_id)
        return self._items[sample_id]

    def asset(self,sample_id,thumbnail=False):
        item=self.get(sample_id);field='thumbnail' if thumbnail else 'image';path=self.root/item[field]
        if not path.is_file() or digest(path)!=item['thumbnail_sha256' if thumbnail else 'sha256']:
            raise SampleError('This gallery image is missing or changed. Rebuild the gallery.')
        return path
