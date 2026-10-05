# Changelog

All notable changes to the model artifacts in this repository.

Versions are tags. Deployments should pin a **Hugging Face commit SHA**, not a
tag and never `main` — see [README](README.md#usage).

## detector-2026.10.1

First release of the ONNX plate detection and text recognition artifacts.

### Detector — trained in this project

YOLOX-tiny, 640×640, single class, exported from `best_ckpt.pth` (epoch 93) with
torch 2.5.1+rocm6.2 at opset 11.

Trained on the Simanno annotated plate corpus (frame-grouped split with a
deliberate gap) plus 3,191 community-contributed images pseudo-labelled by an
8B Qwen3-VL teacher.

**Data corrections made before this release**, each because the label set was
measurably wrong rather than merely imperfect:

- A corrupt JPEG (`5e17d574-…`) that YOLOX's `cv2.imread` loader could not
  decode. This aborted validation at epoch 10 in three separate training runs.
  It had been previously reported as readable because PIL opens truncated JPEGs
  without error; `cv2.imread` returns `None` for both missing and corrupt.
- 247 training images dropped because they contained a plate the teacher never
  labelled. An unlabelled plate is false-negative supervision — the model is
  penalised for detecting something that is genuinely there.
- 4 images of up to 108 megapixels excluded (decoding one costs ~324 MB RGB).
- 86 images excluded where EXIF orientation put the annotations in the wrong
  coordinate frame for the training loader.
- Validation ground truth human-corrected: 43 plates the teacher omitted were
  added and 12 misplaced boxes replaced, after review of all candidates.
- 1 leaked image removed from validation (the same photograph existed in both
  the train and validation splits under different filenames).

### Measured performance

Split `v4` — 1,275 images, 1,143 plates, human-corrected ground truth,
detection IoU 0.3, confidence 0.3.

| | this release | previous model |
|---|---|---|
| recall | **0.926** | 0.906 |
| precision | **0.897** | 0.835 |
| false positives / image | **0.095** | 0.161 |
| recall, plates ≥100px | **0.958** | 0.899 |
| recall, plates <40px | 0.832 | 0.829 |
| latency mean / p95 | 20.8 / 38.6 ms | 21.7 / 39.6 ms |

Read against a measured seed-to-seed spread of **0.013 on recall, 0.013 on
precision, 0.021 on recall<40px**, the defensible claim is: **substantially
better precision and large-plate recall; recall overall and small-plate recall
unchanged.**

A previously reported 2-point *regression* on plates <40px was an artefact of
incomplete teacher labels and does not exist on corrected ground truth.

### Known limitations

- **Text accuracy is not measured.** The public corpus annotates plate boxes
  and carries no transcriptions. Confidence tracks correctness monotonically in
  a 20-plate pilot (CER 0.68 / 0.53 / 0.04 by confidence band), but 20
  non-randomly-ordered plates are not a basis for setting a threshold, so
  `PIPELINE_OCR_MIN_CONFIDENCE` remains 0.0.
- **Non-Latin recognition is unmeasured.** The recogniser runs with the
  `alphanumeric` charset profile, which strips non-Latin characters by design.
- **The recogniser's upstream release is unrecorded.** See
  [Provenance](README.md#provenance). Its dictionary is 18,383 characters, which
  does not match PaddleOCR's stock `ppocr_keys_v1.txt` (6,622). Do not
  regenerate it without first labelling non-Latin plates.
- Roughly 185 plates missed by **both** the teacher and the detector remain
  absent from validation, so true recall is a range rather than a point.

### Rollback

`PIPELINE_BACKEND=llm` selects the external API path and is configuration-only —
no rebuild, no migration. The previous detector weights remain available on
request as `plate_yolox_tiny_640.corpus_v1.onnx`; they are not published here,
because this repository publishes exactly one supported detector version.