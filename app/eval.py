import json, sys, re, pathlib, math
from collections import defaultdict, Counter

STRICT = "strict"
LENIENT = "lenient"

_numbering_strip_re = re.compile(r'^\d+(?:\.\d+)*\s+')

def norm_text(s: str):
    return re.sub(r'\s+', ' ', s.strip()).lower()

def strip_number_prefix(s: str):
    return _numbering_strip_re.sub('', s, count=1)

def load_outline(path: pathlib.Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    outline = data.get("outline", [])
    return data.get("title",""), outline

def build_sets(outline, mode):
    items = set()
    for o in outline:
        lvl = o["level"]
        page = o["page"]
        txt = o["text"]
        if mode == LENIENT:
            txt = strip_number_prefix(txt)
        items.add((lvl, page, norm_text(txt)))
    return items

def compare(gt_outline, pred_outline):
    results = {}
    for mode in (STRICT, LENIENT):
        gt = build_sets(gt_outline, mode)
        pr = build_sets(pred_outline, mode)
        tp = len(gt & pr)
        fp = len(pr - gt)
        fn = len(gt - pr)
        prec = tp / (tp + fp) if (tp + fp) else 1.0
        rec = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = 0 if (prec+rec)==0 else 2*prec*rec/(prec+rec)
        results[mode] = dict(tp=tp, fp=fp, fn=fn,
                             precision=round(prec,4),
                             recall=round(rec,4),
                             f1=round(f1,4))
    return results

def level_breakdown(gt_outline, pred_outline):
    # strict only
    gt_by_level = defaultdict(set)
    pr_by_level = defaultdict(set)
    for o in gt_outline:
        gt_by_level[o["level"]].add((o["level"], o["page"], norm_text(o["text"])))
    for o in pred_outline:
        pr_by_level[o["level"]].add((o["level"], o["page"], norm_text(o["text"])))
    levels = sorted(set(gt_by_level) | set(pr_by_level))
    out = {}
    for L in levels:
        gt = gt_by_level[L]
        pr = pr_by_level[L]
        tp = len(gt & pr)
        fp = len(pr - gt)
        fn = len(gt - pr)
        prec = tp / (tp + fp) if (tp + fp) else 1.0
        rec = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = 0 if (prec+rec)==0 else 2*prec*rec/(prec+rec)
        out[L] = dict(tp=tp, fp=fp, fn=fn,
                      precision=round(prec,4),
                      recall=round(rec,4),
                      f1=round(f1,4))
    return out

def main():
    if len(sys.argv) < 3:
        print("Usage: python -m app.eval <ground_truth_dir> <pred_dir>")
        sys.exit(2)
    gt_dir = pathlib.Path(sys.argv[1])
    pr_dir = pathlib.Path(sys.argv[2])
    if not gt_dir.is_dir() or not pr_dir.is_dir():
        print("Ground truth or prediction dir not found")
        sys.exit(2)

    aggregate_counts = {STRICT: Counter(), LENIENT: Counter()}
    per_file = []

    for gt_file in sorted(gt_dir.glob("*.json")):
        stem = gt_file.stem
        pred_file = pr_dir / f"{stem}.json"
        if not pred_file.exists():
            print(f"[WARN] Missing prediction for {stem}")
            continue
        _, gt_outline = load_outline(gt_file)
        _, pr_outline = load_outline(pred_file)
        res = compare(gt_outline, pr_outline)
        lvl = level_breakdown(gt_outline, pr_outline)
        per_file.append((stem, res, lvl))
        for mode in (STRICT, LENIENT):
            c = aggregate_counts[mode]
            c["tp"] += res[mode]["tp"]
            c["fp"] += res[mode]["fp"]
            c["fn"] += res[mode]["fn"]

    # Print per-file
    for stem, res, lvl in per_file:
        print(f"\nFILE: {stem}")
        print(f"  STRICT : P={res[STRICT]['precision']} R={res[STRICT]['recall']} F1={res[STRICT]['f1']} (TP={res[STRICT]['tp']} FP={res[STRICT]['fp']} FN={res[STRICT]['fn']})")
        print(f"  LENIENT: P={res[LENIENT]['precision']} R={res[LENIENT]['recall']} F1={res[LENIENT]['f1']} (TP={res[LENIENT]['tp']} FP={res[LENIENT]['fp']} FN={res[LENIENT]['fn']})")
        print("  Level breakdown (strict):")
        for L, stats in lvl.items():
            print(f"    {L}: P={stats['precision']} R={stats['recall']} F1={stats['f1']} (TP={stats['tp']} FP={stats['fp']} FN={stats['fn']})")

    # Aggregate
    for mode in (STRICT, LENIENT):
        c = aggregate_counts[mode]
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        prec = tp / (tp + fp) if (tp + fp) else 1.0
        rec = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = 0 if (prec+rec)==0 else 2*prec*rec/(prec+rec)
        print(f"\nAGGREGATE {mode.upper()}: P={prec:.4f} R={rec:.4f} F1={f1:.4f} (TP={tp} FP={fp} FN={fn})")

if __name__ == "__main__":
    main()
