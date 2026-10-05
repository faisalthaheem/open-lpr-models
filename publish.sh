#!/usr/bin/env bash
# Publish the model artifacts to GitHub Releases and Hugging Face.
#
# This runs LOCALLY, on the machine where training happened, because that is the
# only place the artifacts exist. They are never committed, so CI cannot publish
# them -- CI only verifies. See README.
#
# manifest.json is regenerated from the files actually being uploaded, so a
# checksum cannot drift from its artifact (spec 13.23).
set -euo pipefail

REPO_SLUG="${REPO_SLUG:-faisalthaheem/open-lpr-models}"
HF_REPO="${HF_REPO:-faisalthaheem/open-lpr-models}"
TAG="${TAG:?set TAG, e.g. detector-2026.10.1}"
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts}"
PYTHON="${PYTHON:-python3}"

ARTIFACTS=(
  plate_yolox_tiny_640.onnx
  plate_ocr_ppocrv5_mobile.onnx
  plate_ocr_dict.json
  best_ckpt.pth
)

for f in "${ARTIFACTS[@]}"; do
  [[ -f "$ARTIFACT_DIR/$f" ]] || { echo "missing artifact: $ARTIFACT_DIR/$f" >&2; exit 1; }
done

# HF_TOKEN is read from the environment, never from a file, so it cannot be
# committed by accident.
if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "HF_TOKEN is not set. Export it, or run 'huggingface-cli login' and unset the variable." >&2
  exit 1
fi

echo "==> regenerating manifest.json from $ARTIFACT_DIR"
"$PYTHON" generate_manifest.py --artifacts "$ARTIFACT_DIR" \
  --base-url "https://huggingface.co/$HF_REPO/resolve/main"

echo "==> committing manifest"
git add manifest.json
git commit -m "manifest: regenerate checksums for $TAG" || echo "(no manifest change)"
git tag -a "$TAG" -m "$TAG"
git push origin main --tags

echo "==> github release $TAG"
gh release create "$TAG" "${ARTIFACTS[@]/#/$ARTIFACT_DIR/}" \
  --repo "$REPO_SLUG" --title "$TAG" --generate-notes

echo "==> hugging face $HF_REPO"
hf repo create "$HF_REPO" --repo-type model --exist-ok
hf upload "$HF_REPO" manifest.json README.md NOTICE
hf upload "$HF_REPO" "${ARTIFACTS[@]/#/$ARTIFACT_DIR/}"

echo "==> resolve the HF commit SHA to pin (never pin 'main': it moves on retrain)"
hf repo-files "$HF_REPO" >/dev/null
echo "done. Pin deployments to a commit SHA, not to main."
