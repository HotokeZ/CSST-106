# Reproducible development evaluation

Split: validation; images: 582.

| Method | Accuracy | Macro-F1 | Broken F1 |
|---|---:|---:|---:|
| baseline | 0.9725 | 0.9580 | 0.9333 |
| decision_tree | 0.9570 | 0.9369 | 0.9012 |

CPU pipeline mean: 44.87 ms/image after 3 warm-ups; 10 images.
Model size: 9304 bytes.

Development evidence. Source capture groups unknown and the test gallery has been exposed.

Classification numbers use the saved per-grain feature table. Runtime measurements execute the image pipeline. Neither supplies mask IoU, detection mAP, or independent multi-grain count accuracy.
