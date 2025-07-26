# main.py (top-level)
import json, time, pathlib, sys, datetime
from app.extract_outline_and_sections import extract
from app.ranking import build_query, score_sections
from app.paragraph_summarize import refine_section

INPUT_DIR  = pathlib.Path("/app/input")
OUTPUT_DIR = pathlib.Path("/app/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    persona_job = json.load(open("persona_job.json","r",encoding="utf-8"))
    persona = persona_job["persona"]
    job     = persona_job["job"]

    query = build_query(persona, job)
    sections = []
    for i, pdf in enumerate(sorted(INPUT_DIR.glob("*.pdf")), 1):
        sections.extend(extract(pdf, f"doc{i}"))

    ranked_sections = score_sections(query, sections)
    # keep top-N, e.g. 15
    top_sections = ranked_sections[:15]

    subsec_analyses = []
    for s in top_sections:
        res = refine_section(s, query)
        if res:
            subsec_analyses.append(res)

    output = {
        "metadata": {
            "input_documents": [s["doc_name"] for s in sections],
            "persona" : persona,
            "job_to_be_done": job,
            "processing_timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        },
        "extracted_sections": [
            {
              "document": s["doc_name"],
              "page_number": s["page_start"],
              "section_title": s["heading"],
              "importance_rank": s["importance_rank"]
            } for s in top_sections
        ],
        "sub_section_analysis": subsec_analyses
    }
    with open(OUTPUT_DIR / "output.json","w",encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

if __name__=="__main__":
    main()