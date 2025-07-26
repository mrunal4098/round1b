# main.py  – Round-1B top-level runner
#!/usr/bin/env python3

import json
import time
import pathlib
import sys

from app.extract_outline_and_sections import extract
from app.ranker import rank_sections  # wraps build_query, score_sections, refine_section

INPUT_DIR = pathlib.Path("/app/input")
OUTPUT_DIR = pathlib.Path("/app/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_persona_job(path: pathlib.Path) -> tuple[dict, str]:
    """
    Reads persona definition JSON.
    Expected shape:
    {
      "persona": { ...arbitrary fields... },
      "job_to_be_done": "string"
    }
    Returns (persona_dict, job_string) where persona_dict is the inner object,
    not wrapped under another "persona" key.
    """
    data = json.load(open(path, "r", encoding="utf-8"))
    persona = data["persona"]
    job = data["job_to_be_done"]
    return persona, job

def main() -> None:
    # 1. Locate the persona-job JSON
    persona_files = list(INPUT_DIR.glob("*.json"))
    if not persona_files:
        print("✗ No persona JSON found in /app/input. Exiting.", file=sys.stderr)
        sys.exit(1)

    persona, job = load_persona_job(persona_files[0])

    # 2. Extract sections from each PDF
    sections = []
    for idx, pdf_path in enumerate(sorted(INPUT_DIR.glob("*.pdf")), start=1):
        sections.extend(extract(pdf_path, f"doc{idx}"))

    if not sections:
        print("✗ No PDFs or no sections extracted – nothing to do.", file=sys.stderr)
        sys.exit(1)

    # 3. Rank sections + perform sub-section analysis
    #    rank_sections returns (top_sections, sub_section_analysis)
    top_secs, sub_analysis = rank_sections(sections, persona, job)

    # 4. Build final JSON
    #    dedupe & sort input_documents by real filename
    docs = sorted({ sec["doc_name"] for sec in sections })

    out_json = {
        "metadata": {
            "input_documents"      : docs,
            "persona"              : persona,
            "job_to_be_done"       : job,
            "processing_timestamp" : time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        },
        "extracted_sections"  : top_secs,
        "sub_section_analysis": sub_analysis
    }

    # 5. Write result
    result_path = OUTPUT_DIR / "result.json"
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump(out_json, fh, ensure_ascii=False, indent=2)

    print(f"✓ Wrote {result_path}  ({len(top_secs)} sections)", file=sys.stderr)

if __name__ == "__main__":
    main()