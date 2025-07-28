# pdf-persona-1B

**Persona-Driven Document Intelligence**  
Extract and rank the most relevant sections and paragraphs from PDFs for a given persona & job-to-be-done.

---

## 📁 Inputs

1. **PDF documents**  
   Place one or more `.pdf` files in the `input/` directory.  
   ```text
   pdf-persona-1B/
   └── input/
       ├── file01.pdf
       ├── file02.pdf
       └── file03.pdf

	2.	Persona + Job JSON
A single file named persona_job.json in input/, with this shape:

{
  "persona": {
    "role": "Investment Analyst",
    "expertise": "Technology sector evaluation",
    "focus_areas": [
      "Revenue trends",
      "R&D investment",
      "Market positioning"
    ]
  },
  "job_to_be_done": "Analyze revenue trends, R&D investments, and market positioning strategies."
}



⸻

▶️ Building & Running
	1.	Build the Docker image
(pre-downloads the MiniLM model so it’ll run offline)

docker build -t round1b .


	2.	Run the container
Mount your input/ and output/ directories:

docker run --rm \
  -v "$PWD/input:/app/input" \
  -v "$PWD/output:/app/output" \
  --network none \
  round1b


	3.	Inspect the output

cat output/result.json | jq .



⸻

🔍 Expected Output Schema

Your output/result.json will look like:

{
  "metadata": {
    "input_documents": ["file01.pdf", "file02.pdf"],
    "persona": {
      "role": "...",
      "expertise": "...",
      "focus_areas": ["…", "…"]
    },
    "job_to_be_done": "...",
    "processing_timestamp": "2025-07-27T12:34:56Z"
  },
  "extracted_sections": [
    {
      "document": "file01.pdf",
      "page_number": 12,
      "section_title": "Revenue Trends",
      "importance_rank": 1
    },
    …
  ],
  "sub_section_analysis": [
    {
      "document": "file01.pdf",
      "section_title": "Revenue Trends",
      "subsections": [
        {
          "rank": 1,
          "raw_paragraph": "...",
          "refined_text": "...",
          "page_number": 12
        },
        …
      ]
    },
    …
  ]
}

	•	extracted_sections is a sorted list of your top 15 sections, each with its page number and rank.
	•	sub_section_analysis provides up to 3 top paragraphs per section, each with both the original text and a concise “refined_text.”