"""Quality capability reporting: untrained defect classes are never clean results."""


def automatic_quality(summary):
    return {
        'classification': 'not_assessed',
        'basis': 'automatic_capability_status',
        'whole_broken': {'status': 'experimental_estimate' if summary.get('classified') else 'not_assessed',
                         'whole': summary.get('whole'), 'broken': summary.get('broken'),
                         'broken_percentage_by_count': summary.get('broken_percentage')},
        'discoloration': {'status': 'not_assessed', 'count': None},
        'impurities': {'status': 'not_assessed', 'count': None},
        'reason': 'The installed classifier predicts whole/broken only. Review and label discoloration and impurities before training these classes.',
        'scope': 'Visual inspection; not an official rice grade, mass percentage or food-safety assessment.',
    }
