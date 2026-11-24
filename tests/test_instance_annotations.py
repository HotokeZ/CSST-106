import base64
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from src.prepare_instances import prepare


class AnnotationTests(unittest.TestCase):
    def fixture(self, folder, name, color, group, split):
        raw=io.BytesIO();Image.new('RGB',(40,40),color).save(raw,format='PNG')
        data=dict(imageData=base64.b64encode(raw.getvalue()).decode(),imageWidth=40,imageHeight=40,
                  bigascheck=dict(capture_group=group,split=split,reviewed_complete=True),
                  shapes=[dict(label='whole',shape_type='polygon',points=[[2,2],[30,2],[30,10],[2,10]],flags=dict(manually_reviewed=True,discoloration_reviewed=True))])
        path=folder/name;path.write_text(json.dumps(data));return path,data

    def test_group_leakage_and_duplicate_images_are_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'annotations';source.mkdir()
            self.fixture(source,'a.json','gray','capture-A','train')
            path,data=self.fixture(source,'b.json','white','capture-A','validation')
            with self.assertRaisesRegex(ValueError,'groups'):prepare(source,root/'out')
            self.assertFalse((root/'out').exists())
            data['bigascheck']['capture_group']='capture-B'
            data['imageData']=json.loads((source/'a.json').read_text())['imageData'];path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'Duplicate'):prepare(source,root/'out')

    def test_only_reviewed_polygons_are_exported_and_paths_are_generated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'annotations';source.mkdir()
            path,data=self.fixture(source,'a.json','gray','capture-A','train')
            data['shapes'][0]['flags']['manually_reviewed']=False;path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'reviewed'):prepare(source,root/'out')
            data['shapes'][0]['flags']['manually_reviewed']=True;data['imagePath']='../../escape.png';path.write_text(json.dumps(data))
            report=prepare(source,root/'out')
            self.assertEqual(report['objects'],1);self.assertEqual(report['class_counts']['train']['whole'],1)
            self.assertEqual(len(list((root/'out/images/train').glob('*.png'))),1)
            label=next((root/'out/labels/train').glob('*.txt')).read_text()
            self.assertTrue(label.startswith('0 0.05000000 0.05000000'))
            self.assertFalse((root/'escape.png').exists())
            with self.assertRaisesRegex(ValueError,'empty'):prepare(source,root/'out')

    def test_bad_geometry_and_mismatched_image_dimensions_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'annotations';source.mkdir()
            path,data=self.fixture(source,'a.json','gray','capture-A','train')
            data['imageWidth']=41;path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'dimensions'):prepare(source,root/'out')
            data['imageWidth']=40;data['shapes'][0]['points'][1]=[float('nan'),5];path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'finite'):prepare(source,root/'out')
