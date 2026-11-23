"""Real upload regression checks; optional when private local photos are absent."""
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
from bigascheck.vision import Settings,load_rgb,segment

ROOT=Path(__file__).resolve().parents[1]


class LocalRegressionTests(unittest.TestCase):
    @unittest.skipUnless((ROOT/'data/local_20261120/originals/local_010.jpg').exists(),'Private local photo is not included')
    def test_shadowed_patterned_cloth_finds_each_reviewed_grain_once(self):
        rgb=load_rgb(ROOT/'data/local_20261120/originals/local_010.jpg',max_edge=1600)
        settings=Settings(background='auto',detector='adaptive',split_touching=True,max_area_fraction=.6)
        grains,_,_=segment(rgb,settings)
        # Spatially reviewed targets; a matching total alone could conceal
        # missed grains compensated by false fabric detections.
        boxes=[(497,540,539,580),(391,580,476,631),(465,599,529,668),
               (534,663,626,716),(218,756,296,826),(112,894,145,928),
               (383,906,477,979),(519,945,582,1020),(604,950,694,1029),
               (451,998,490,1040),(395,1050,495,1103),(737,1052,790,1110)]
        matched=[]
        for grain in grains:
            x,y=grain['centroid']
            found=[i for i,(x0,y0,x1,y1) in enumerate(boxes) if x0<=x<=x1 and y0<=y<=y1]
            self.assertEqual(len(found),1,'Recovery must find rice, not fabric edges')
            matched.extend(found)
            self.assertEqual(grain.get('detection_method'),'texture_recovery')
        self.assertEqual(sorted(matched),list(range(12)))

    @unittest.skipUnless((ROOT/'data/local_20261120/originals/local_007.jpg').exists(),'Private local photo is not included')
    def test_blue_cloth_matches_ten_reviewed_grain_positions_without_false_boxes(self):
        rgb=load_rgb(ROOT/'data/local_20261120/originals/local_007.jpg',max_edge=1600)
        settings=Settings(background='auto',detector='adaptive',split_touching=True,max_area_fraction=.6)
        grains,_,_=segment(rgb,settings)
        # Reviewed positions at the app's 1200x1600 working resolution. The
        # bent fragment at (585,760) is one physical grain, not two basins.
        boxes=[(642,508,688,576),(447,526,508,563),(392,613,437,647),
               (591,614,642,670),(437,680,476,721),(398,691,431,716),
               (607,721,640,760),(581,756,619,800),(721,807,792,841),
               (495,980,533,1063)]
        assigned=[]
        for g in grains:
            x,y=g['centroid']
            matches=[i for i,(x0,y0,x1,y1) in enumerate(boxes) if x0<=x<=x1 and y0<=y<=y1]
            self.assertEqual(len(matches),1,'Candidate must correspond to one reviewed grain, not background')
            assigned.extend(matches)
        self.assertEqual(sorted(assigned),list(range(10)),'Each real grain must be found exactly once')

    def test_pale_failure_recovers_without_inventing_grains_on_blank_surface(self):
        gray=np.tile(np.linspace(210,232,400).astype('uint8'),(350,1))
        image=Image.fromarray(np.repeat(gray[...,None],3,axis=2));draw=ImageDraw.Draw(image)
        for x,y in [(60,70),(180,70),(300,70),(60,220),(180,220),(300,220)]:
            draw.ellipse((x,y,x+45,y+17),fill=(255,254,247))
        with patch('bigascheck.foreground.adaptive_foreground',side_effect=lambda rgb:np.ones(rgb.shape[:2],dtype=bool)):
            grains,_,_=segment(np.array(image),Settings(background='auto',detector='adaptive',split_touching=True))
        self.assertEqual(len(grains),6)
        blank=np.full((250,350,3),225,dtype='uint8')
        self.assertEqual(segment(blank,Settings(background='auto',detector='adaptive'))[0],[])


if __name__=='__main__':unittest.main()
