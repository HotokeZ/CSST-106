import io
import json
import unittest
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw

from app import create_app
from bigascheck.cropping import crop_rgb
from bigascheck.vision import load_rgb


class CropTests(unittest.TestCase):
    def setUp(self):
        self.image=Image.new('RGB',(200,120),'black')
        draw=ImageDraw.Draw(self.image)
        for x in [40,100,160]:draw.ellipse((x-13,52,x+13,64),fill='white')
        self.png=io.BytesIO();self.image.save(self.png,format='PNG')
        self.client=create_app(model_path=Path('outputs/no_crop_test_model.joblib')).test_client()

    def request(self,crop=None):
        data={'image':(io.BytesIO(self.png.getvalue()),'rice.png'),'split_touching':'false'}
        if crop is not None:data['crop']=json.dumps(crop)
        return self.client.post('/api/analyze',data=data)

    def test_crop_changes_the_analyzed_area_and_records_original_coordinates(self):
        original=self.request();cropped=self.request({'x':.05,'y':.2,'width':.3,'height':.6})
        self.assertEqual(original.status_code,200)
        self.assertEqual(original.json['summary']['detected'],3)
        self.assertEqual(cropped.status_code,200)
        self.assertEqual(cropped.json['summary']['detected'],1)
        p=cropped.json['preprocessing']
        self.assertEqual(p['crop_box'],[10,24,60,72])
        self.assertEqual((p['original_width'],p['original_height']),(200,120))
        self.assertEqual((p['width'],p['height']),(60,72))
        self.assertEqual(p['coordinate_frame'],'processed_crop')
        self.assertIn('Only the selected crop',cropped.json['warnings'][0])

    def test_invalid_and_tiny_crops_are_rejected(self):
        for rect in [{'x':-.1,'y':0,'width':.5,'height':1}, {'x':.8,'y':0,'width':.5,'height':1},
                     {'x':0,'y':0,'width':0,'height':1}, {'x':False,'y':0,'width':1,'height':1},
                     {'x':0,'y':0,'width':.001,'height':1}, {'x':float('nan'),'y':0,'width':1,'height':1},
                     {'x':'0','y':0,'width':1,'height':1}, [0,0,1,1], {}]:
            with self.subTest(rect=rect):self.assertEqual(self.request(rect).status_code,400)
        self.assertEqual(self.client.post('/api/analyze',data={'sample_id':'local_003','crop':'{}'}).status_code,400)

    def test_crop_resizes_after_selecting_original_pixels_and_honors_exif_orientation(self):
        rgb=np.zeros((1200,2400,3),dtype=np.uint8);rgb[:,1200:]=255
        image,meta=crop_rgb(rgb,{'x':.5,'y':0,'width':.5,'height':1},max_edge=800)
        self.assertEqual(image.shape,(800,800,3));self.assertEqual(meta['crop_box'],[1200,0,1200,1200])
        self.assertTrue(np.all(image==255))
        im=Image.new('RGB',(80,40),'white');exif=im.getexif();exif[274]=6
        raw=io.BytesIO();im.save(raw,format='JPEG',exif=exif);raw.seek(0)
        oriented=load_rgb(raw)
        _,meta=crop_rgb(oriented,{'x':0,'y':0,'width':1,'height':.5})
        self.assertEqual((meta['original_width'],meta['original_height']),(40,80))
        self.assertEqual(meta['crop_box'],[0,0,40,40])


if __name__=='__main__':unittest.main()
