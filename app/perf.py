import time, pathlib, json, tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from .pdf_loader import load_document
from .layout import build_lines
from .features import compute_features
from .level_assign import assign_levels
from .scoring import score_candidate

def synth_pdf(path: str, pages=50):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    w,h=A4
    c=canvas.Canvas(path,pagesize=A4)
    for p in range(1,pages+1):
        if p==1:
            c.setFont("Helvetica-Bold",22); c.drawString(72,h-80,"Synthetic Benchmark Title")
        c.setFont("Helvetica-Bold",16); c.drawString(72,h-140,f"{p} Section Heading")
        c.setFont("Helvetica",12)
        y = h-170
        for i in range(20):
            c.drawString(72,y,f"Body line {i+1} on page {p}.")
            y -= 14
        c.showPage()
    c.save()

def main():
    tmp = pathlib.Path("/app/input/benchmark.pdf")
    if not tmp.exists():
        synth_pdf(str(tmp))
    t0 = time.time()
    doc = load_document(str(tmp))
    t1 = time.time()
    lines = build_lines(doc)
    t2 = time.time()
    feats = compute_features(lines, doc.page_count)
    t3 = time.time()
    cand = [f for f in feats if f["candidate_heading"]]
    t4 = time.time()
    enriched = []
    for f in cand:
        enriched.append({
            **f,
            "score": score_candidate(f)
        })
    assigned = []
    if enriched:
        assigned, title_c = assign_levels([
            {
                "page": e["page"],
                "text": e["text"],
                "avg_size": e["avg_size"],
                "rel_font_size": e["rel_font_size"],
                "is_bold": e["is_bold"],
                "starts_numbering": e["starts_numbering"],
                "gap_above": e["gap_above"],
                "score": e["score"]
            } for e in enriched
        ], doc.page_count)
    t5 = time.time()
    print(json.dumps({
        "timings_sec":{
            "parse": round(t1-t0,3),
            "line_build": round(t2-t1,3),
            "feature": round(t3-t2,3),
            "candidate_filter": round(t4-t3,3),
            "level_assign": round(t5-t4,3),
            "total": round(t5-t0,3)
        },
        "page_count": doc.page_count,
        "candidates": len(cand),
        "assigned": len(assigned)
    }, indent=2))

if __name__ == "__main__":
    main()
