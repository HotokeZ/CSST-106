import csv
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image,ImageDraw

from app import create_app
from bigascheck.gallery import GalleryCatalog,build_gallery
from bigascheck.samples import SampleError,digest

ROOT=Path(__file__).resolve().parents[1]
TEMP=ROOT/'outputs/test_temp';TEMP.mkdir(parents=True,exist_ok=True)


class GalleryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=TEMP);cls.root=Path(cls.temp.name)
        cls.features=cls.root/'features.csv';rows=[]
        for split in ['train','validation','test']:
            for label in ['whole','broken']:
                for i in range(6):
                    im=Image.new('RGB',(120,100),'black');draw=ImageDraw.Draw(im)
                    draw.ellipse((20,30,85 if label=='whole' else 45,48),fill=(240-i,235,220))
                    # Distinct file bytes for every split without changing the grain.
                    draw.point((0,0),fill=(i+1,len(rows)+1,1))
                    path=cls.root/f'{split}_{label}_{i}.png';im.save(path)
                    rows.append({'image':path.name,'label':label,'split':split,'sha256':digest(path)})
        with cls.features.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,list(rows[0]));writer.writeheader();writer.writerows(rows)
        local=cls.root/'local';local.mkdir();local_rows=[]
        for label in ['whole','broken']:
            for i in range(2):
                path=local/f'{label}_{i}.png';Image.new('RGB',(200,160),(70+i if label=='whole' else 100+i,70,70)).save(path)
                local_rows.append({'image':path.name,'label':label,'split':'train','sha256':digest(path),
                                   'grain_id':'1','bbox':'[50,50,60,30]','reviewed':'true'})
        cls.local_features=cls.root/'reviewed.csv'
        with cls.local_features.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,list(local_rows[0]));writer.writeheader();writer.writerows(local_rows)
        cls.gallery=cls.root/'gallery';cls.result=build_gallery(cls.features,cls.gallery,cls.local_features,local,per_class=6)
        cls.catalog=GalleryCatalog(cls.gallery,cls.features)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_gallery_prefers_kaggle_and_retains_training_demo_roles(self):
        data=self.catalog.list(page_size=24)
        self.assertGreater(data['source_counts']['kaggle'],data['source_counts']['local2'])
        self.assertTrue(all(s['source']=='kaggle' for s in data['items'][:6]))
        local=self.catalog.list(source='local2')['items'];self.assertEqual(len(local),4)
        self.assertTrue(all(s['split']=='train' and s['evaluation_role']=='training_demo' for s in local))
        self.assertFalse(any(s['id'].startswith('local_') for s in data['items']))
        self.assertTrue(all(s['label']=='whole' for s in self.catalog.list(label='whole',source='local2')['items']))

    def test_image_selection_and_upload_use_identical_processing(self):
        client=create_app(model_path=self.root/'missing.joblib',gallery_root=self.gallery,feature_table=self.features).test_client()
        data=client.get('/api/samples?source=kaggle').json;sample=data['items'][0]
        selected=client.post('/api/analyze',data={'sample_id':sample['id']})
        path=self.catalog.asset(sample['id'])
        uploaded=client.post('/api/analyze',data={'image':(io.BytesIO(path.read_bytes()),'same.png')})
        self.assertEqual(selected.status_code,200);self.assertEqual(uploaded.status_code,200)
        self.assertEqual(selected.json['grains'],uploaded.json['grains'])
        self.assertEqual(selected.json['summary']['classified'],False)
        self.assertEqual(client.get('/api/samples/local_010/image').status_code,404)
        self.assertEqual(client.get('/api/samples?source=local1').status_code,400)
        self.assertEqual(client.get('/api/samples?source=local2').json['total'],4)

    def test_portable_table_paths_do_not_invalidate_split_identity(self):
        changed=self.root/'portable.csv';rows=list(csv.DictReader(self.features.open()))
        for row in rows:row['image']='new/location/'+Path(row['image']).name
        with changed.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,list(rows[0]));writer.writeheader();writer.writerows(rows)
        portable=GalleryCatalog(self.gallery,changed)
        self.assertEqual(portable.list()['total'],self.result['total'])
        rows[0]['split']='test'
        with changed.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,list(rows[0]));writer.writeheader();writer.writerows(rows)
        with self.assertRaises(SampleError):portable.list()

    def test_catalog_cannot_relabel_local_training_images_as_test(self):
        bad=self.root/'bad';bad.mkdir()
        catalog=json.loads((self.gallery/'catalog.json').read_text())
        next(s for s in catalog['samples'] if s['source']=='local2')['split']='test'
        (bad/'catalog.json').write_text(json.dumps(catalog))
        (bad/'local2_references.csv').write_bytes((self.gallery/'local2_references.csv').read_bytes())
        with self.assertRaises(SampleError):GalleryCatalog(bad,self.features).list()


if __name__=='__main__':unittest.main()
