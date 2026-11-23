import unittest
import numpy as np
from PIL import Image, ImageDraw
from bigascheck.vision import Settings, segment


class AdaptiveForegroundTests(unittest.TestCase):
    def test_woven_surface_and_light_gradient_are_not_counted_as_grains(self):
        y, x = np.indices((480, 640))
        weave = 65 + 20*np.sin(x*2.)*np.sin(y*2.) + 30*x/640
        image = Image.fromarray(np.repeat(np.clip(weave,0,255).astype('uint8')[...,None],3,axis=2))
        draw = ImageDraw.Draw(image)
        for box in [(100,120,150,136),(260,250,310,267),(430,330,477,348)]:
            draw.ellipse(box,fill=(225,217,170))
        grains,_,_=segment(np.array(image),Settings(background='auto',detector='adaptive',split_touching=True))
        self.assertEqual(len(grains),3)

    def test_uniform_background_keeps_original_grain_regions(self):
        image=Image.new('RGB',(400,400),'black');draw=ImageDraw.Draw(image)
        draw.ellipse((100,150,220,185),fill='white')
        legacy=segment(np.array(image),Settings())[0]
        adaptive=segment(np.array(image),Settings(detector='adaptive'))[0]
        self.assertEqual([g['bbox'] for g in legacy],[g['bbox'] for g in adaptive])

    def test_unknown_detector_rejected(self):
        with self.assertRaises(ValueError):Settings(detector='unknown')

    def test_saturated_fabric_is_rejected_but_cream_grains_remain(self):
        y,x=np.indices((360,480))
        red=120+50*np.sin(x/12.)*np.sin(y/11.)
        rgb=np.stack([red,np.full(red.shape,25),np.full(red.shape,20)],axis=-1).astype('uint8')
        image=Image.fromarray(rgb);draw=ImageDraw.Draw(image)
        draw.ellipse((120,130,170,148),fill=(230,215,160))
        draw.ellipse((290,210,345,230),fill=(220,205,160))
        grains,_,_=segment(np.array(image),Settings(background='auto',detector='adaptive',split_touching=True))
        self.assertEqual(len(grains),2)


if __name__=='__main__':unittest.main()
