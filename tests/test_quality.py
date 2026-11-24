import base64
import io
from pathlib import Path
import re
import unittest
from PIL import Image
from app import create_app
from bigascheck.quality import automatic_quality


class QualityTests(unittest.TestCase):
    def test_whole_grains_do_not_imply_absent_discoloration_or_impurities(self):
        quality=automatic_quality(dict(classified=True,whole=10,broken=0,broken_percentage=0))
        self.assertEqual(quality['classification'],'not_assessed')
        self.assertIsNone(quality['discoloration']['count'])
        self.assertIsNone(quality['impurities']['count'])
        self.assertEqual(quality['whole_broken']['whole'],10)

    def test_api_supplies_processed_original_for_review_and_no_defect_claim(self):
        raw=io.BytesIO();Image.new('RGB',(100,80),'gray').save(raw,format='PNG');raw.seek(0)
        client=create_app().test_client()
        response=client.post('/api/analyze',data={'image':(raw,'sample.png'),'crop':'{"x":0.1,"y":0.1,"width":0.5,"height":0.5}'})
        self.assertEqual(response.status_code,200)
        result=response.json
        with Image.open(io.BytesIO(base64.b64decode(result['original_png']))) as image:
            self.assertEqual(image.size,(50,40))
        self.assertEqual(result['quality']['impurities']['status'],'not_assessed')

    def test_review_and_quality_controls_are_present_once(self):
        root=Path(__file__).resolve().parents[1]
        text=create_app().test_client().get('/').text
        ids=re.findall(r'id="([^"]+)"',text)
        self.assertEqual(len(ids),len(set(ids)))
        for source in ['review.js']:
            for identifier in re.findall(r"querySelector\('#([^']+)'\)",(root/'static'/source).read_text(encoding='utf-8')):
                self.assertIn(identifier,ids)
