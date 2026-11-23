# Reproducible development evaluation

Split: test; images: 582.

| Method | Accuracy | Macro-F1 | Broken F1 |
|---|---:|---:|---:|
| baseline | 0.9588 | 0.9362 | 0.8983 |
| decision_tree | 0.9605 | 0.9409 | 0.9069 |

CPU pipeline mean: 46.05 ms/image after 3 warm-ups; 20 images.
Model size: 7176 bytes.

Development evidence. Source capture groups unknown and the test gallery has been exposed.

Classification numbers use the saved per-grain feature table. Runtime measurements execute the image pipeline. Neither supplies mask IoU, detection mAP, or independent multi-grain count accuracy.
