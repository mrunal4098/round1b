"""
Hybrid section-ranking:
    score = 0.5 · cosine(MiniLM)  +  0.5 · BM25
+10 % bonus for H1/H2 headings.
"""
from __future__ import annotations
from typing import List, Dict, Tuple
import time, numpy as np
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi           # lightweight BM25

# ──────────────────────────────────────────────────────────
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        t0 = time.time()
        _model = SentenceTransformer(_MODEL_NAME, device="cpu")
        print(f"[ranker] MiniLM loaded in {time.time()-t0:.1f}s")
    return _model

# make accessible for paragraph_summarize.py
get_model = _get_model

# ──────────────────────────────────────────────────────────
def build_query(persona: dict, job: str) -> str:
    role   = persona.get("role", "")
    expert = persona.get("expertise", "")
    focus  = ", ".join(persona.get("focus_areas", []))
    return f"Role: {role}. Expertise: {expert}. Focus: {focus}. Task: {job}"

def _embed(texts: List[str]) -> np.ndarray:
    mdl = _get_model()
    return mdl.encode(texts, convert_to_numpy=True,
                      normalize_embeddings=True, batch_size=64)

# ──────────────────────────────────────────────────────────
def rank_sections(
    sections : List[dict],
    persona  : dict,
    job      : str,
    keep_top : int = 15
) -> Tuple[List[dict], List[dict]]:

    query   = build_query(persona, job)
    q_vec   = _embed([query])[0]

    # Dense similarity
    payloads   = [f"{s['heading']}\n{s['full_text'][:400]}" for s in sections]
    dense_vecs = _embed(payloads)
    dense_sim  = dense_vecs @ q_vec       # cosine

    # BM25 similarity
    corpus_tok = [s["full_text"].lower().split() for s in sections]
    bm25       = BM25Okapi(corpus_tok)
    bm25_sim   = np.array(bm25.get_scores(query.lower().split()), dtype=np.float32)
    if bm25_sim.max() > 0:
        bm25_sim /= bm25_sim.max()

    # Late fusion
    final = 0.5 * dense_sim + 0.5 * bm25_sim

    # +10 % bonus for H1 / H2
    for i, s in enumerate(sections):
        if s["level"] in (1, 2):          # lower number == higher level
            final[i] *= 1.10

    order = np.argsort(-final)[: keep_top]

    top_sections = [{
        "document"       : sections[i]["doc_name"],
        "page_number"    : sections[i]["page_start"],
        "section_title"  : sections[i]["heading"],
        "importance_rank": r + 1
    } for r, i in enumerate(order)]

    return top_sections, []   # paragraph refinement happens elsewhere