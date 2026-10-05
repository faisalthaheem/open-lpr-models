#!/usr/bin/env python3
"""Regenerate manifest.json from the artifact files actually present.

Spec 13.23: the publish step must derive checksums from the files being
uploaded, not from a hand-maintained list. A hand-written manifest drifts from
its artifacts silently; there is no failure, only a deployment that verifies a
hash nobody published.

Run from the directory holding the artifacts, or pass --artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DETECTOR = "plate_yolox_tiny_640.onnx"
RECOGNISER = "plate_ocr_ppocrv5_mobile.onnx"
DICT = "plate_ocr_dict.json"
CHECKPOINT = "best_ckpt.pth"

# Provenance is stated per artifact. The detector is ours; the recogniser and
# dictionary are conversions of an upstream model whose exact release was never
# recorded, and that is stated rather than guessed -- an unciteable "latest
# version" is not provenance and would be the first thing a licence dispute
# turns on.
ENTRIES = {
    DETECTOR: {
        "role": "plate detector",
        "produced_by_us": True,
        "architecture": "YOLOX-tiny (depth 0.33, width 0.375)",
        "input_size": [640, 640],
        "num_classes": 1,
        "class_names": ["plate"],
        "upstream": "YOLOX (Megvii-BaseDetection/YOLOX)",
        "license": "Apache-2.0",
        "weights_license_basis": (
            "YOLOX code and its same-repository release weights are both Apache-2.0. Ultralytics YOLO "
            "weights are AGPL-3.0 and are deliberately NOT used; see the open-lpr repository for why."
        ),
        "pretrained_from": "COCO (yolox_tiny.pth)",
        "trained_on": (
            "Simanno annotated plate corpus (frame-grouped split with gap) plus community-contributed "
            "images pseudo-labelled by an 8B Qwen3-VL teacher per operator attestation. Human review found "
            "the teacher omitted roughly 7% of plates; 251 training images containing unlabelled plates "
            "were dropped as false-negative supervision, and val ground truth was human-corrected. "
            "Training imagery is NOT published -- see README."
        ),
        "checkpoint": CHECKPOINT,
        "exported_with": "torch 2.5.1+rocm6.2, opset 11",
    },
    RECOGNISER: {
        "role": "plate text recogniser (CTC)",
        "produced_by_us": False,
        "note": (
            "UPSTREAM MODEL, CONVERTED BY US. Not trained by this project. The upstream release was never "
            "recorded and cannot be recovered from the artifact: the ONNX graph carries no producer, "
            "producer_version or doc_string, and no PaddlePaddle installation, wheel, or shell history "
            "survives on the build host."
        ),
        "conversion": "Paddle 3.x (graph name 'PaddlePaddle Graph in PIR mode'), opset 13",
        "upstream": "PP-OCR recognition model (PaddleOCR)",
        "license": "Apache-2.0 (PaddleOCR)",
        "license_caveat": (
            "UNVERIFIED for this specific build. PaddleOCR is Apache-2.0, but the exact release is "
            "unknown, so the licence basis is asserted at project level, not pinned to a version."
        ),
        "must_match": DICT,
        "match_caveat": (
            "This recogniser and its dictionary are a MATCHED PAIR. Decoding assumes len(dict) + 2 output "
            "classes. Substituting either without the other produces silent garbage, not an error."
        ),
    },
    DICT: {
        "role": "character dictionary for the recogniser",
        "produced_by_us": False,
        "charset_size": 18383,
        "implied_num_classes": 18385,
        "upstream": "PP-OCR recognition model (PaddleOCR)",
        "license": "Apache-2.0 (PaddleOCR)",
        "license_caveat": "Same caveat as the recogniser: upstream release not recorded.",
        "open_question": (
            "UNRESOLVED. This dictionary is 18,383 characters. PaddleOCR's stock ppocr_keys_v1.txt is "
            "6,622 characters (verified against refs release/2.7, release/2.8, v2.7.0, v2.9.0). So this "
            "is NOT a stock PaddleOCR dictionary -- it is either a different recognition variant or a "
            "custom extension. Regenerating it from stock PP-OCR would change which characters the model "
            "can emit, and no labelled non-Latin data exists to detect a regression. Do not regenerate "
            "without first labelling non-Latin plates."
        ),
    },
    CHECKPOINT: {
        "role": "detector training checkpoint (torch state dict)",
        "produced_by_us": True,
        "produced_by": CHECKPOINT,
        "framework": "PyTorch",
        "load_requirements": (
            "Requires torch and YOLOX. ROCm is NOT required -- CPU torch reads a checkpoint fine; ROCm is "
            "only needed to train."
        ),
        "security_warning": (
            "A .pth is a pickle and executes constructors on load. Load only checkpoints you trust."
        ),
        "license": "Apache-2.0",
        "upstream": "YOLOX (Megvii-BaseDetection/YOLOX)",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts", required=True, help="directory holding the artifacts")
    ap.add_argument("--out", default="manifest.json")
    ap.add_argument("--base-url", default=None, help="release download base, recorded for convenience")
    args = ap.parse_args()

    root = Path(args.artifacts)
    manifest: dict[str, dict] = {}
    missing: list[str] = []
    for name, entry in ENTRIES.items():
        path = root / name
        if not path.is_file():
            missing.append(name)
            continue
        manifest[name] = {"artifact": name, "bytes": path.stat().st_size, "sha256": sha256(path), **entry}

    if missing:
        raise SystemExit(f"missing artifacts: {missing} -- refusing to write a partial manifest")

    out = {
        "schema": "open-lpr-models/manifest/1",
        "base_url": args.base_url,
        "note": (
            "Generated by generate_manifest.py from the artifact files themselves. Do not hand-edit: "
            "checksums must come from the bytes being published."
        ),
        "artifacts": manifest,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out} with {len(manifest)} artifacts")
    for name, entry in sorted(manifest.items()):
        print(f"  {name:34} {entry['sha256'][:16]}  {entry['bytes']:>10,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
