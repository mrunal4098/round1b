# app/main.py
import json, time, pathlib, sys
from .pdf_loader import load_document
from .layout import build_lines
from .features import compute_features
from .level_assign import assign_levels, dedupe_outline
from .scoring import score_candidate
from .config import Config
from .output_format import build_final_json

INPUT_DIR = pathlib.Path("/app/input")
OUTPUT_DIR = pathlib.Path("/app/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def process_pdf(pdf_path: pathlib.Path):
    doc_ctx = load_document(str(pdf_path))
    lines = build_lines(doc_ctx)
    feats = compute_features(lines, doc_ctx.page_count)

    candidates = []
    for f in feats:
        if f["candidate_heading"]:
            candidates.append({
                "page": f["page"],
                "text": f["text"],
                "avg_size": f["avg_size"],
                "rel_font_size": f["rel_font_size"],
                "is_bold": f["is_bold"],
                "starts_numbering": f["starts_numbering"],
                "gap_above": f["gap_above"],
                "y0": f.get("y0", 0.0),
                "score": score_candidate(f)
            })

    candidates.sort(key=lambda c: (c["page"], c.get("y0", 0.0)))

    outline_entries = []
    title_text = pdf_path.stem

    if candidates:
        assigned, title_c = assign_levels(candidates, doc_ctx.page_count)
        if title_c:
            title_text = title_c["text"]
        for c in assigned:
            if c["proposed_level"] == "TITLE":
                continue
            outline_entries.append({
                "level": c["proposed_level"],
                "text": c["text"],
                "page": c["page"]
            })

    outline_entries = dedupe_outline(outline_entries)
    outline_entries.sort(key=lambda x: (x["page"]))

    base_json = build_final_json(title_text, outline_entries)

    if Config.INCLUDE_DEBUG:
        base_json["_debug_candidates"] = [
            {"page": c["page"], "text": c["text"][:120], "score": c["score"]}
            for c in candidates
        ][:50]
        base_json["_debug_first_lines"] = [
            {"page": f["page"], "text": f["text"][:100], "rel": f["rel_font_size"]}
            for f in feats[:15]
        ]

    out_file = OUTPUT_DIR / (pdf_path.stem + ".json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(base_json, f, ensure_ascii=False, indent=2)

def main():
    t0 = time.time()
    arg_pdfs = [pathlib.Path(a) for a in sys.argv[1:] if a.lower().endswith(".pdf")]
    if arg_pdfs:
        pdfs = arg_pdfs
    else:
        pdfs = sorted([p for p in INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower()==".pdf"])
    if not pdfs:
        print("[INFO] No PDFs found.", file=sys.stderr)
    for p in pdfs:
        print(f"[INFO] Processing {p.name}", file=sys.stderr)
        process_pdf(p)
    print(f"[INFO] Final extraction done in {time.time()-t0:.2f}s (debug={Config.INCLUDE_DEBUG})", file=sys.stderr)

if __name__ == "__main__":
    main()