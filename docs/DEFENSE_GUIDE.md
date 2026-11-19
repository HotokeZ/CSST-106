# Technical defense preparation

Use the final tagged code and your actual contribution statement. These are study prompts, not claims that any particular member authored a module.

| Area | Explain | Parameter-change exercise |
|---|---|---|
| `vision.load_rgb` | EXIF orientation, RGB ordering, supported image size | What happens if training uses RGB but inference uses BGR? |
| `vision.segment` | Otsu thresholding, pale-background three-class threshold, morphology and area/border rejection | Double opening iterations; compare missed small fragments and noise. |
| `vision._fill_small_holes` | Why a table enclosed by rice must not become a grain | Compare filling all holes with filling only pinholes. |
| `vision._separate_touching` | Distance map, prominence-suppressed seeds, watershed and near-convex preservation | Disable separation; explain merged regions. Lower prominence and examine over-splitting. |
| `model.shape_matrix` | Aspect ratio, solidity and ellipse-fill; invariance to uniform pixel scale | Multiply lengths by 2 and area by 4. Explain why the shape vector is unchanged. |
| `model.train_shape` | Validation model selection, class weighting, baseline, fixed splits | Increase tree depth; explain overfitting and compare validation rather than training accuracy. |
| `samples.SampleCatalog` | Why test IDs are accepted and arbitrary training paths are not | Change the split table; explain why the old gallery is rejected. |
| `checkpoints.evaluate_checkpoint` | Macro-F1 vs accuracy; confusion matrix; scope of runtime measurement | Explain 16 whole→broken vs 7 broken→whole errors. Why isn't classifier accuracy detector mAP? |
| Interface | Model loaded once; original upload vs annotated result; experimental leaf-vote score | Replace an image during an in-flight analysis and explain stale-response prevention. |

Be ready to say that the public dataset's capture groups are unknown, the exposed development-test set is not a fresh final set, and local-photo percentages remain unvalidated. If unsure of an effect, describe the experiment you would run instead of guessing.
