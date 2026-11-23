# Reproducible development evaluation

Split: validation; images: 582.

| Method | Accuracy | Macro-F1 | Broken F1 |
|---|---:|---:|---:|
| baseline | 0.9725 | 0.9580 | 0.9333 |
| decision_tree | 0.9588 | 0.9389 | 0.9040 |

CPU pipeline mean: 46.03 ms/image after 3 warm-ups; 20 images.
Model size: 7176 bytes.

Development evidence. Source capture groups unknown and the test gallery has been exposed.

Classification numbers use the saved per-grain feature table. Runtime measurements execute the image pipeline. Neither supplies mask IoU, detection mAP, or independent multi-grain count accuracy.
