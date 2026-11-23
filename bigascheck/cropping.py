"""Validate a user-selected region in the EXIF-oriented original photograph."""
import json
import math

import numpy as np
from PIL import Image


def crop_rgb(rgb, selection, max_edge=1600):
    if isinstance(selection,str):
        try:
            selection=json.loads(selection)
        except (ValueError,TypeError) as exc:
            raise ValueError('Invalid crop selection.') from exc
    fields={'x','y','width','height'}
    if not isinstance(selection,dict) or set(selection)!=fields:
        raise ValueError('Crop must specify x, y, width and height as image fractions.')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in selection.values()):
        raise ValueError('Crop coordinates must be finite numbers.')
    x,y,w,h=(selection[k] for k in ['x','y','width','height'])
    if x<0 or y<0 or w<=0 or h<=0 or x+w>1+1e-9 or y+h>1+1e-9:
        raise ValueError('Crop selection must stay inside the photograph.')
    height,width=rgb.shape[:2]
    left,top=math.floor(x*width),math.floor(y*height)
    right,bottom=min(width,math.ceil((x+w)*width)),min(height,math.ceil((y+h)*height))
    if right-left<8 or bottom-top<8:
        raise ValueError('Choose a crop at least 8 pixels wide and high; leave room around the grains.')
    image=Image.fromarray(rgb[top:bottom,left:right])
    image.thumbnail((max_edge,max_edge),Image.Resampling.LANCZOS)
    metadata={'original_width':width,'original_height':height,
              'crop':{'x':x,'y':y,'width':w,'height':h},
              'crop_box':[left,top,right-left,bottom-top],
              'coordinate_frame':'processed_crop'}
    return np.asarray(image).copy(),metadata
