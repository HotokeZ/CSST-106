"""Quality capability reporting: untrained defect classes are never clean results."""
import math

BROKEN_BANDS = [('Premium',5),('Grade no. 1',10),('Grade no. 2',15),('Grade no. 3',25),('Grade no. 4',35),('Grade no. 5',45)]


def broken_band(percent, basis='count'):
    if basis not in {'count','weight'}:
        raise ValueError('Unknown measurement basis.')
    if percent is None:
        return None
    if isinstance(percent,bool) or not isinstance(percent,(int,float)) or not math.isfinite(percent) or not 0<=percent<=100:
        raise ValueError('Broken percentage must be between 0 and 100.')
    band=next((name for name,limit in BROKEN_BANDS if percent<=limit),'Above listed Grade no. 5 broken limit')
    return {'band':band,'broken_percentage':percent,'basis':basis,'standard':'PNS/BAFS 290:2025, Table 2 broken-kernel limits',
            'pns_grade':None,'scope':'Broken-factor comparison only. PNS uses weight; other factors and the brewers exception are not evaluated.'}


def measured_broken_band(total, broken):
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in [total,broken]) or total<=0 or not 0<=broken<=total:
        raise ValueError('Enter positive total weight and broken weight between zero and total.')
    result=broken_band(100*broken/total,'weight')
    return {**result,'total_weight_g':total,'broken_weight_g':broken,'measurement_source':'user_entered'}


def automatic_quality(summary):
    return {
        'classification': 'not_assessed',
        'broken_factor_comparison': broken_band(summary.get('broken_percentage')),
        'basis': 'automatic_capability_status',
        'whole_broken': {'status': 'experimental_estimate' if summary.get('classified') else 'not_assessed',
                         'whole': summary.get('whole'), 'broken': summary.get('broken'),
                         'broken_percentage_by_count': summary.get('broken_percentage')},
        'discoloration': {'status': 'not_assessed', 'count': None},
        'impurities': {'status': 'not_assessed', 'count': None},
        'reason': 'The installed classifier predicts whole/broken only. Review and label discoloration and impurities before training these classes.',
        'scope': 'Visual inspection; not an official rice grade, mass percentage or food-safety assessment.',
    }
