---
license: apache-2.0
library_name: onnxruntime
tags:
  - license:apache-2.0
  - onnx
  - object-detection
  - license-plate-recognition
  - alpr
---

# open-lpr models

Model artifacts for [open-lpr](https://github.com/faisalthaheem/open-lpr), a
free and open-source licence plate recognition system. The application code is
in the `open-lpr` repository; this repository holds only the weights.

The detector is **trained by this project**. The recogniser and dictionary are
**conversions of an upstream model** — see [Provenance](#provenance) before
assuming otherwise.

## What is here

| artifact | role | ours? |
|---|---|---|
| `plate_yolox_tiny_640.onnx` | plate detector, YOLOX-tiny, 640×640 | **trained here** |
| `plate_ocr_ppocrv5_mobile.onnx` | plate text recogniser, CTC | upstream, converted |
| `plate_ocr_dict.json` | character dictionary (18,383 chars) | upstream, converted |
| `best_ckpt.pth` | detector training checkpoint | **trained here** |

All three runtime artifacts are required. The application refuses to start
without them; see [Usage](#usage).

Verify any artifact against the `sha256` in [`manifest.json`](manifest.json)
before loading it. That file is generated from the artifact bytes themselves,
not written by hand.

## Measured accuracy

Scored on split `v4` — 1,275 images, 1,143 plates, human-corrected ground truth.
**Detection IoU 0.3, confidence 0.3.**

| | detector (this repo) | superseded model |
|---|---|---|
| recall | **0.926** | 0.906 |
| precision | **0.897** | 0.835 |
| false positives / image | **0.095** | 0.161 |
| recall, plates ≥100px tall | **0.958** | 0.899 |
| recall, plates <40px tall | 0.832 | 0.829 |
| latency, mean / p95 | 20.8 ms / 38.6 ms | 21.7 ms / 39.6 ms |

**Sample sizes matter here, because several plausible-looking differences are not
real.** A seed-repeat of the identical configuration on 1,275 images gave:

| axis | run-to-run spread |
|---|---|
| recall | 0.013 |
| precision | 0.013 |
| recall <40px | 0.021 |

Read against that noise floor:

- **Real:** precision +0.063 and recall ≥100px +0.059 — roughly 5× the spread.
- **Marginal:** recall +0.019 — about 1.5× the spread.
- **Noise:** recall <40px +0.003 — no measurable effect.

So the defensible claim is that this model is **substantially better at precision
and large plates, with recall and small-plate performance unchanged.** A previous
measurement showing a 2-point *regression* on small plates was an artefact of
incomplete teacher labels and does not exist on corrected ground truth.

The noise floor above comes from one seed pair (n=2). It indicates scale, not a
confidence interval.

**Text accuracy is not measured.** The public corpus annotates plate *boxes* and
carries no transcriptions. The recogniser's accuracy on non-Latin scripts is
therefore unknown — see [Provenance](#provenance).

## Usage

The application loads these from `PIPELINE_MODEL_DIR`, default `model/plate/`,
and expects these filenames:

```
PIPELINE_MODEL_DIR=model/plate/
PIPELINE_DETECTOR_MODEL=plate_yolox_tiny_640.onnx
PIPELINE_OCR_MODEL=plate_ocr_ppocrv5_mobile.onnx
PIPELINE_OCR_DICT=plate_ocr_dict.json
```

Inference needs `onnxruntime` only. **ROCm is not required** to load the
checkpoint — only to train. CPU torch reads a `.pth` fine.

The three runtime artifacts are a **set**: the recogniser and dictionary must
come from the same export. Decoding assumes `len(dict) + 2` output classes, so
substituting one without the other yields silently wrong text rather than an
error.

> **`best_ckpt.pth` is a pickle.** Loading it executes constructors. Only load
> checkpoints you trust.

## Provenance

### Detector — trained here

YOLOX-tiny, Apache-2.0 for both the code and the same-repository release
weights. Pretrained from COCO `yolox_tiny.pth`, then trained on the Simanno
annotated plate corpus (frame-grouped split with a deliberate gap) plus
community-contributed images pseudo-labelled by a teacher model.

Ultralytics YOLO weights are **AGPL-3.0 and are not used** anywhere in this
project. The detector is YOLOX.

The community images were pseudo-labelled by an 8B Qwen3-VL teacher. Human
review found that teacher **omitted roughly 7% of plates** and misplaced a
further batch. Val ground truth here is human-corrected; 251 training images
containing unlabelled plates were dropped, because an unlabelled plate is
false-negative supervision — the model is penalised for detecting something that
is really there. Teacher identity is operator-attested, not verifiable from
artifacts.

### Recogniser and dictionary — upstream, converted by us

**These were not trained by this project**, and their exact upstream release was
never recorded. It cannot be recovered: the ONNX graph carries no producer,
version or doc string, and no PaddlePaddle installation, wheel or shell history
survives on the build host.

What can be stated:

- Converted from a PP-OCR recognition model using **Paddle 3.x**
  (graph name `PaddlePaddle Graph in PIR mode`, opset 13).
- PaddleOCR is **Apache-2.0**. That licence is asserted at project level; the
  specific release is unverified.

**One unresolved question, flagged rather than hidden.** The dictionary is
18,383 characters. PaddleOCR's stock `ppocr_keys_v1.txt` is 6,622 — verified
against refs `release/2.7`, `release/2.8`, `v2.7.0` and `v2.9.0`. So this is
**not** a stock PaddleOCR dictionary: it is either a different recognition
variant or a custom extension. Regenerating it from stock PP-OCR would change
which characters the model can emit, and there is no labelled non-Latin data to
detect a regression. **Do not regenerate it without first labelling non-Latin
plates.**

## Training imagery is not published

The photographs this model was trained on are community-contributed images
containing **real licence plates, faces and vehicles**, uploaded without consent
obtained. Publishing them would create a searchable index of real registration
numbers, which is a privacy harm the licence terms cannot excuse.

The reusable contribution is the tooling — dataset conversion, evaluation and
export in `lpr_app/ml/` in the `open-lpr` repository — and it is already public
and needs none of that imagery to be useful.

## Licence

Apache-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

The repository as a whole is Apache-2.0, but **that does not mean every artifact
here is ours.** The recogniser and dictionary are conversions of an upstream
Apache-2.0 project and are attributed as such in `manifest.json`.