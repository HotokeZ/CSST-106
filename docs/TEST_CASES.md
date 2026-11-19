# Recorded checkpoint demo cases

The reproducible case runner writes expected outcomes before requests in `case_plan.json`, then actual outcomes and pass/fail in JSON/CSV. Cases were authored for the upcoming checkpoint, not retrospectively claimed as cases written before earlier demonstrations.

Run `python src/test_cases.py`. No live test photo is needed: it uses dataset-reference singles, three held-out composites and labeled software fixtures. A composite/fixture is not independent real-world evidence.

| ID | Scenario | Expected |
|---|---|---|
| TC01 | Whole reference single | 1 whole, 0 broken |
| TC02 | Broken reference single | 0 whole, 1 broken |
| TC03 | Mixed composite | 6 regions; 3 whole, 3 broken |
| TC04 | All-whole composite | 6 regions; 6 whole |
| TC05 | All-broken composite | 6 regions; 6 broken |
| TC06 | Empty black image | 0 regions |
| TC07 | Half-resolution whole single — hard | 1 whole |
| TC08 | Dim whole single — hard | 1 whole |
| TC09 | Cropped grain touching frame — edge | 0 accepted complete grains under border-exclusion settings |
| TC10 | Invalid image bytes — edge | HTTP 400, useful error |
| TC11 | Pale-background composite — hard | 6 regions; 6 whole |
| TC12 | Two touching ellipses + one separate ellipse — hard | 3 separated regions; synthetic software fixture |

Failing cases remain FAIL. Use them for development and preserve previous runs when changing the implementation. Original source labels and synthetic shape counts are references; none establishes independent local-photo precision, IoU or percentage accuracy.
