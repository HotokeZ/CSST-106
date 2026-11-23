import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from src.import_single_grains import import_archive
from bigascheck.single_training import domain_weights, reviewed_rows
from bigascheck.vision import FEATURES, backend
from bigascheck.samples import digest

TEST_TEMP=Path(__file__).resolve().parents[1]/'outputs/test_temp'
TEST_TEMP.mkdir(parents=True,exist_ok=True)


def photo(color):
    data=io.BytesIO();Image.new('RGB',(20,30),color).save(data,format='PNG');return data.getvalue()


def table(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,list(rows[0]));writer.writeheader();writer.writerows(rows)


class SingleTrainingTests(unittest.TestCase):
    def test_archive_import_preserves_folder_labels_and_does_not_assign_groups(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as tmp:
            root=Path(tmp);archive=root/'new.zip';output=root/'imported'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('New/Whole Grains/one.png',photo('white'))
                z.writestr('New/Broken Grains/two.png',photo('gray'))
            audit=import_archive(archive,output)
            self.assertEqual(audit['counts'],{'broken':1,'whole':1})
            self.assertTrue(all(r['split']=='train' and r['group_id']=='' for r in audit['images']))
            self.assertEqual(import_archive(archive,output),audit)
            with zipfile.ZipFile(root/'bad.zip','w') as z:
                z.writestr('../Whole Grains/escape.png',photo('white'))
            with self.assertRaisesRegex(ValueError,'Unsafe'):
                import_archive(root/'bad.zip',root/'bad')
            self.assertFalse((root/'Whole Grains').exists())

    def test_conflicting_duplicate_labels_are_rejected_before_writing(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as tmp:
            root=Path(tmp);image=photo('white')
            with zipfile.ZipFile(root/'bad.zip','w') as z:
                z.writestr('whole/a.png',image);z.writestr('broken/b.png',image)
            with self.assertRaisesRegex(ValueError,'conflicting'):
                import_archive(root/'bad.zip',root/'output')
            self.assertFalse((root/'output').exists())

    def test_training_weights_balance_classes_within_each_domain(self):
        source=np.array(['whole']*8+['broken']*2);local=np.array(['whole']*3+['broken']*4)
        weights=domain_weights(source,local,.25)
        self.assertAlmostEqual(sum(weights[:10]),1)
        self.assertAlmostEqual(sum(weights[10:]),.25)
        self.assertAlmostEqual(sum(weights[:10][source=='whole']),.5)
        self.assertAlmostEqual(sum(weights[10:][local=='broken']),.125)

    def test_reviewed_features_reject_held_out_duplicates_and_unreviewed_targets(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as tmp:
            root=Path(tmp);rows=[];features=[]
            for label,color in [('whole','white'),('broken','gray')]:
                image=root/(label+'.png');image.write_bytes(photo(color))
                sha=digest(image)
                rows.append({'image':image.name,'label':label,'split':'train','sha256':sha})
                features.append({**rows[-1],'grain_id':'1','bbox':'[0,0,20,30]', 'reviewed':'true',**{f:'1.0' for f in FEATURES}})
            table(root/'manifest.csv',rows);table(root/'reviewed.csv',features);table(root/'candidates.csv',features)
            table(root/'source.csv',[{'sha256':'a'*64}]);table(root/'splits.csv',[{'sha256':'b'*64}])
            (root/'protocol.json').write_text(json.dumps({'manifest_sha256':digest(root/'manifest.csv'),'backend':backend()}))
            self.assertEqual(len(reviewed_rows(root/'reviewed.csv',root/'manifest.csv',root/'source.csv',root/'splits.csv')),2)
            features[0]['reviewed']='false';table(root/'reviewed.csv',features)
            with self.assertRaisesRegex(ValueError,'reviewed target'):
                reviewed_rows(root/'reviewed.csv',root/'manifest.csv',root/'source.csv',root/'splits.csv')
            features[0]['reviewed']='true';table(root/'reviewed.csv',features)
            table(root/'splits.csv',[{'sha256':features[0]['sha256']}])
            with self.assertRaisesRegex(ValueError,'already belongs'):
                reviewed_rows(root/'reviewed.csv',root/'manifest.csv',root/'source.csv',root/'splits.csv')


if __name__=='__main__':
    unittest.main()
