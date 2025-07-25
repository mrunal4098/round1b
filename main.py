import json, time, pathlib, datetime
from sentence_transformers import SentenceTransformer
from app.pdf_outline import extract_outline_and_sections  # you will create this
from app.ranking import rank_sections, build_subsection_analysis  # you will create this

INPUT_DIR = pathlib.Path("/app/input")
OUTPUT_DIR = pathlib.Path("/app/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PERSONA_FILE = INPUT_DIR / "persona.json"        # contains persona + job
OUTPUT_FILE  = OUTPUT_DIR / "challenge1b_output.json"

def load_persona():
    data = json.load(open(PERSONA_FILE, "r", encoding="utf-8"))
    return data["persona"], data["job_to_be_done"]

def main():
    t0 = time.time()
    persona, job = load_persona()

    pdfs = sorted([p for p in INPUT_DIR.iterdir() if p.suffix.lower()==".pdf"])
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")

    sections = []
    for p in pdfs:
        outline = extract_outline_and_sections(p)
        sections.extend(outline)  # each item: dict with doc, heading_text, level, page_start, page_end, full_text

    ranked = rank_sections(sections, persona, job, model)
    subsec = build_subsection_analysis(ranked, persona, job, model)

    out = {
        "metadata": {
            "input_documents": [p.name for p in pdfs],
            "persona": persona,
            "job_to_be_done": job,
            "processing_timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        },
        "extracted_sections": [
            {
                "document": r["document"],
                "page_number": r["page_start"],
                "section_title": r["heading_text"],
                "importance_rank": i+1
            } for i, r in enumerate(ranked)
        ],
        "sub_section_analysis": subsec
    }
    json.dump(out, open(OUTPUT_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Done in {time.time()-t0:.2f}s")

if __name__ == "__main__":
    main()