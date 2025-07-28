IMAGE=round1b
INPUT_DIR=sample_data/input
OUTPUT_DIR=sample_data/output
RESULT_JSON=$(OUTPUT_DIR)/result.json

.PHONY: all build run test clean

all: test

build:
	docker build -t $(IMAGE) .

run: build
	mkdir -p $(OUTPUT_DIR)
	docker run --rm \
	  -v "$(PWD)/$(INPUT_DIR):/app/input" \
	  -v "$(PWD)/$(OUTPUT_DIR):/app/output" \
	  $(IMAGE)

test: run
	@echo "🔍 Validating JSON schema…"
	@jq -e 'has("metadata") and has("extracted_sections") and has("sub_section_analysis")' $(RESULT_JSON) \
	  && echo "  ✔ Top-level OK"
	@jq -e '.extracted_sections | length > 0' $(RESULT_JSON) \
	  && echo "  ✔ extracted_sections non-empty"
	@echo "✅ All checks passed"

clean:
	rm -rf $(OUTPUT_DIR)
