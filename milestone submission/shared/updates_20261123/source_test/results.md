# Reproducible development evaluation

Split: test; images: 582.

| Method | Accuracy | Macro-F1 | Broken F1 |
|---|---:|---:|---:|
| baseline | 0.9588 | 0.9362 | 0.8983 |
| decision_tree | 0.9622 | 0.9430 | 0.9098 |

CPU pipeline mean: 42.14 ms/image after 3 warm-ups; 10 images.
Model size: 9304 bytes.

Development evidence. Source capture groups unknown and the test gallery has been exposed.

Classification numbers use the saved per-grain feature table. Runtime measurements execute the image pipeline. Neither supplies mask IoU, detection mAP, or independent multi-grain count accuracy.
