import os
from sentence_transformers import SentenceTransformer, util

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # ~80 MB on disk

# keep global singleton
_model = None
def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME, device="cpu")
    return _model

def build_query(persona: dict, job: str) -> str:
    focus = ", ".join(persona.get("focus_areas", []))
    return f"Role: {persona['role']}. Expertise: {persona.get('expertise','')}. Focus: {focus}. Task: {job}"

def score_sections(query: str, sections: list[dict]) -> list[dict]:
    model = get_model()
    sec_texts = [s["heading"] + "\n" + s["text"][:400] for s in sections]
    with model:
        q_emb   = model.encode(query, convert_to_tensor=True, normalize_embeddings=True)
        s_embs  = model.encode(sec_texts, convert_to_tensor=True, normalize_embeddings=True)
    sims = util.cos_sim(q_emb, s_embs)[0].cpu().tolist()
    for s, sc in zip(sections, sims):
        s["sim"] = sc
    sections.sort(key=lambda x: x["sim"], reverse=True)
    for rank, s in enumerate(sections, 1):
        s["importance_rank"] = rank
    return sections