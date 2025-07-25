from typing import List, Dict, Any

VALID_LEVELS = {"H1","H2","H3"}

def build_final_json(title: str, outline_items: List[Dict[str,Any]]):
    # Sanitize outline
    clean = []
    for o in outline_items:
        lvl = o.get("level")
        txt = o.get("text","").strip()
        page = o.get("page")
        if lvl in VALID_LEVELS and txt and isinstance(page,int):
            clean.append({"level": lvl, "text": txt, "page": page})
    return {"title": title, "outline": clean}
