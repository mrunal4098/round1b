# main.py  – Round-1B top-level runner
#!/usr/bin/env python3
import json, time, pathlib, sys

from app.extract_outline_and_sections import extract
from app.ranker              import rank_sections, build_query
from app.paragraph_summarize import refine_section   # <- NEW

INPUT_DIR  = pathlib.Path("/app/input")
OUTPUT_DIR = pathlib.Path("/app/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
def load_persona_job(path: pathlib.Path) -> tuple[dict, str]:
    """
    Reads persona definition JSON of the shape
    {
      "persona": { ... },
      "job_to_be_done": "string"
    }
    """
    data = json.load(open(path, "r", encoding="utf-8"))
    return data["persona"], data["job_to_be_done"]


# ─────────────────────────────────────────────────────────────
def main() -> None:
    # 1) locate persona-job file
    persona_files = list(INPUT_DIR.glob("*.json"))
    if not persona_files:
        print("✗ No persona JSON found in /app/input. Exiting.", file=sys.stderr)
        sys.exit(1)

    persona, job = load_persona_job(persona_files[0])
    query        = build_query(persona, job)

    # 2) section extraction for every PDF
    sections = []
    for idx, pdf_path in enumerate(sorted(INPUT_DIR.glob("*.pdf")), start=1):
        sections.extend(extract(pdf_path, f"doc{idx}"))

    if not sections:
        print("✗ No PDFs or no sections extracted – nothing to do.", file=sys.stderr)
        sys.exit(1)

    # 3) rank sections (dense + BM25 fusion)
    top_secs, _ = rank_sections(sections, persona, job, keep_top=15)

    # 4) paragraph-level refinement per top section
    sub_analysis = []
    for sec in top_secs:
        # find original section dict that still has full_text & paragraphs
        origin = next(
            s for s in sections
            if s["doc_name"] == sec["document"] and s["heading"] == sec["section_title"]
        )
        refined = refine_section(origin, query)
        if refined:
            sub_analysis.append(refined)

    # 5) assemble JSON
    out_json = {
        "metadata": {
            "input_documents"     : sorted({s["doc_name"] for s in sections}),
            "persona"             : persona,
            "job_to_be_done"      : job,
            "processing_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "extracted_sections"  : top_secs,
        "sub_section_analysis": sub_analysis,
    }

    # 6) write result
    result_path = OUTPUT_DIR / "result.json"
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump(out_json, fh, ensure_ascii=False, indent=2)

    print(f"✓ Wrote {result_path}  ({len(top_secs)} sections, "
          f"{sum(len(s['subsections']) for s in sub_analysis)} paragraphs)", file=sys.stderr)


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()