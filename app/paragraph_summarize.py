# app/paragraph_summarize.py
from typing import List, Dict, Any
import re, networkx as nx
from sentence_transformers import util
from .ranker import _get_model as get_model

_SENT_SPLIT = re.compile(r'(?<=[.!?。！？])\s+')

def _textrank(sentences: List[str], top_n: int = 2) -> str:
    """Simple TextRank over sentence embeddings."""
    if len(sentences) <= top_n:
        return " ".join(sentences)
    mdl  = get_model()
    embs = mdl.encode(sentences, convert_to_tensor=True, normalize_embeddings=True)
    sim  = util.cos_sim(embs, embs).cpu().numpy()
    scores = nx.pagerank(nx.from_numpy_array(sim))
    ranked = sorted(((scores[i], s) for i, s in enumerate(sentences)), reverse=True)
    return " ".join(s for _, s in ranked[:top_n])

def refine_section(section: Dict[str, Any], query: str, k_paragraphs: int = 3) -> Dict[str, Any] | None:
    """
    section["paragraphs"] produced by extractor ⇒ [{page:int, text:str}, …]
    """
    paras_all = [p for p in section["paragraphs"] if len(p["text"]) > 30]
    if not paras_all:
        return None

    mdl   = get_model()
    q_emb = mdl.encode(query, convert_to_tensor=True, normalize_embeddings=True)
    p_emb = mdl.encode([p["text"] for p in paras_all],
                       convert_to_tensor=True, normalize_embeddings=True)
    sims = util.cos_sim(q_emb, p_emb)[0].cpu().tolist()
    top_idx = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:k_paragraphs]

    subsections = []
    for rk, i in enumerate(top_idx, 1):
        para = paras_all[i]
        refined = _textrank(_SENT_SPLIT.split(para["text"]))
        subsections.append({
            "rank"         : rk,
            "raw_paragraph": para["text"][:800],
            "refined_text" : refined,
            "page_number"  : para["page"]      # ← exact PDF page!
        })

    return {
        "document"     : section["doc_name"],
        "section_title": section["heading"],
        "subsections"  : subsections
    }