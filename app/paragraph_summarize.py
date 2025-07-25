from typing import List, Dict, Any
import re, networkx as nx
from sentence_transformers import util
from .ranking import get_model

_para_split_re = re.compile(r'\n\s*\n')  # blank line separator
_sent_split_re = re.compile(r'(?<=[.!?。！？])\s+')

def _textrank(sentences: List[str], top_n=3) -> str:
    if len(sentences) <= top_n:
        return " ".join(sentences)
    model = get_model()
    embs  = model.encode(sentences, convert_to_tensor=True, normalize_embeddings=True)
    # cosine sim matrix
    sim_mat = util.cos_sim(embs, embs).cpu().numpy()
    graph = nx.from_numpy_array(sim_mat)
    scores = nx.pagerank(graph)
    ranked = sorted(((scores[i], s) for i, s in enumerate(sentences)), reverse=True)
    return " ".join(s for _, s in ranked[:top_n])

def refine_section(section: Dict[str,Any], query: str, k_paragraphs=3) -> Dict[str,Any]:
    paras = [p.strip() for p in _para_split_re.split(section["text"]) if len(p.strip()) > 30]
    if not paras:
        return None
    model = get_model()
    q_emb = model.encode(query, convert_to_tensor=True, normalize_embeddings=True)
    p_emb = model.encode(paras, convert_to_tensor=True, normalize_embeddings=True)
    sims  = util.cos_sim(q_emb, p_emb)[0].cpu().tolist()
    scored = sorted(zip(paras, sims, p_emb), key=lambda t: t[1], reverse=True)[:k_paragraphs]

    subsections = []
    for idx, (para, sim, emb) in enumerate(scored, 1):
        sentences = _sent_split_re.split(para)
        refined   = _textrank(sentences, top_n=2)
        subsections.append({
            "rank"        : idx,
            "raw_paragraph": para,
            "refined_text": refined,
            # simplistic page guess – first sentence in pdf text often carries original page
            "page_number" : section["page_start"]
        })
    return {
        "document"     : section["doc_name"],
        "section_title": section["heading"],
        "subsections"  : subsections
    }