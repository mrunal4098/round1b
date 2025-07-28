#!/usr/bin/env bash
set -euo pipefail

IMAGE=round1b
INPUT_DIR="$(pwd)/sample_data/input"
OUTPUT_DIR="$(pwd)/sample_data/output"
RESULT_JSON="${OUTPUT_DIR}/result.json"

# 1️⃣ Build
docker build -t ${IMAGE} .

# 2️⃣ Prep output
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

# 3️⃣ Run
docker run --rm \
  -v "${INPUT_DIR}:/app/input" \
  -v "${OUTPUT_DIR}:/app/output" \
  ${IMAGE}

# 4️⃣ Smoke-check structure
jq -e 'has("metadata") and has("extracted_sections") and has("sub_section_analysis")' "${RESULT_JSON}" >/dev/null
jq -e '.extracted_sections | length > 0' "${RESULT_JSON}" >/dev/null

echo "✅ All tests passed!"
