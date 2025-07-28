# Approach Explanation

This document outlines the end-to-end design of our Persona-Driven Document Intelligence pipeline, from PDF ingestion through to the final JSON output.

---

## 1. Outline Extraction

We begin by converting each PDF into a sequence of text “lines” with positional metadata (page number, font size, y-coordinate, boldness, etc.). A feature extractor tags candidate headings based on heuristics like relative font size, bold styling, and numbering patterns. We pass these candidates into a level-assignment module (`assign_levels`), which reconstructs the document’s hierarchy (e.g. H1, H2, H3). 

To prevent spurious splits, we merge:
- **Lowercase continuations** (e.g. “T” + “ogether” → “Together”) when the run is too close in vertical position.  
- **Full appendix subtitles** by recognizing `Appendix X:` followed by text on the same line.  

Finally, for each heading we collect all following lines up to the next heading of the same or higher level. Those lines are joined to form `full_text` for that section.

---

## 2. Persona–Job Query Construction

We accept a small JSON payload:
```json
{
  "persona": {
    "role": "...",
    "expertise": "...",
    "focus_areas": ["…", "…"]
  },
  "job_to_be_done": "..."
}

These fields are interpolated into a deterministic, no-LLM string:

Persona role: {role}. Expertise: {expertise}. Focus: {focus_areas}. Task: {job_to_be_done}

This “query” succinctly encodes what the user cares about and drives all subsequent retrieval steps.

⸻

3. Section-Level Ranking

We use the all-MiniLM-L6-v2 model (≈80 MB on disk) to embed both the query and each section’s representation (heading + first 400 chars of full_text). Embeddings are computed in batches on CPU with normalize_embeddings=True, so cosine similarity reduces to a dot product. Sections are sorted in descending order of similarity and assigned importance_rank 1…N. We keep the top 15 for deeper analysis.

⸻

4. Paragraph-Level TextRank Refinement

Within each top section, we split the full_text into paragraphs (blank-line separators). We embed each paragraph, score it against the same query embedding, and select the top 3. For longer paragraphs, we apply a lightweight TextRank:
	1.	Sentence splitting on punctuation.
	2.	Cosine similarity graph over sentence embeddings.
	3.	PageRank to pick the 2 most central sentences.

This yields concise “refined_text” snippets without any external APIs or LLMs.

⸻

5. Docker Constraints
	•	Base image: python:3.11-slim
	•	Dependencies installed via pip install --no-cache-dir -r requirements.txt (torch, sentence-transformers, networkx, numpy, scikit-learn, pypdf).
	•	Model pre-download: RUN python -c "SentenceTransformer('all-MiniLM-L6-v2')" to cache weights at build time.
	•	Offline-safe: no internet at runtime, CPU only.
	•	Image size stays under 1 GB by pinning minimal versions and cleaning caches.

⸻

6. Performance
	•	We disable gradients (torch.no_grad()) and use batch sizes of 64 for embedding.
	•	Embedding ~300 sections + ~900 paragraphs completes in under 60 s on a single CPU core.
	•	The memory footprint remains around 200–300 MB thanks to the compact MiniLM model and slim base image.

This architecture satisfies all Round 1B requirements: generic PDF support, strict-size models, CPU-only execution, and sub-minute processing time.