# Local photo collection plan

Start with **30 development/validation photographs**. Ideally keep **10 additional photographs from new physical samples/capture sessions untouched** for final evaluation. Once a photograph has been used to adjust the algorithm, it is development data, not a fresh final test.

| Condition | Development photos | What to include |
|---|---:|---|
| Controlled | 10 | Plain contrasting surface, even light, grains separated |
| Lighting/background changes | 10 | Same kinds of samples with shadows, dim light or a pale surface |
| Touching/overlapping | 10 | Moderate clusters and crowding; keep the originals |
| New final captures, recommended | 10 extra | New physical grain samples/sessions, including the conditions above; keep them unused during tuning |

For each development condition, vary the mixture: whole only, mostly whole, mixed, mostly broken, and broken only. For controlled pictures, around 50 grains per photo is a practical starting point within the proposal's 50–150-grain target. Record the whole and broken counts before mixing/spreading the grains, then verify them after capture. Do not guess counts from the app output.

Keep the original resolution and do not add labels or boxes onto the image. Use simple filenames such as `controlled_01.jpg`. Supply:

```csv
image,group_id,actual_whole,actual_broken,condition
local/controlled_01.jpg,physical_sample_01,40,10,controlled
local/shadow_01.jpg,physical_sample_01,40,10,shadow
```

Rows above are format examples, not collected results. If the same physical grain sample is photographed again, retain its group ID across images. Capture/session groups must stay in a single partition. New names for copied images do not make them independent.

At least two people should review ambiguous whole/broken labels and resolve disagreements. Count-based evaluation needs the counts above. If the report claims detection precision/recall, add manually reviewed boxes on 30+ validation photographs; if claiming segmentation IoU/Dice, add at least 10 manually made masks. Algorithm-generated masks are not manual ground truth.

Collecting 30 photos is a prototype starting target, not a statistical guarantee of accuracy. The app's source-data accuracy cannot substitute for these local measurements.
