# The Unofficial Guide — Project 1

---

## Domain

My system covers student reviews of CS professors at Stevens Institute of Technology. This knowledge is valuable because students need it to make informed course enrollment decisions, but official course evaluations are never made public. The only way this information spreads is through peer-to-peer sharing across platforms like Rate My Professors and Reddit threads that aren't collectively indexed anywhere. A student trying to choose between two professors for the same course has no official resource — they have to hunt across multiple platforms manually.

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Rate My Professors | Professor reviews | https://www.ratemyprofessors.com/professor/2326104 |
| 2 | Rate My Professors | Professor reviews | https://www.ratemyprofessors.com/professor/3141334 |
| 3 | Rate My Professors | Professor reviews | https://www.ratemyprofessors.com/professor/2721847 |
| 4 | Rate My Professors | Professor reviews | https://www.ratemyprofessors.com/professor/3065505 |
| 5 | Rate My Professors | Professor reviews | https://www.ratemyprofessors.com/professor/3013137 |
| 6 | Rate My Professors | Professor reviews | https://www.ratemyprofessors.com/professor/1239339 |
| 7 | r/stevens | "Why I chose to attend Stevens for CS" thread | documents/stevens_cs_recommendation_thread.txt |
| 8 | r/stevens | Engineering/CS students thread | documents/stevens_cs_thread.txt |
| 9 | r/stevens | "Would you recommend Stevens for CS?" thread | documents/stevens_cs_recommendation_thread.txt |
| 10 | r/stevens | MS CS admitted students thread | documents/stevens_mscs_thread.txt |

---

## Chunking Strategy

**Chunk size:** 400 characters

**Overlap:** 75 characters

**Why these choices fit your documents:** RMP reviews are short and self-contained — a single student's opinion is usually two to five sentences. The original spec called for 250-character chunks, but retrieval testing showed distance scores consistently above 0.7, meaning the embedding model didn't have enough semantic signal per chunk to match queries confidently. Increasing to 400 characters gave each chunk enough context to embed meaningfully while still staying within a single student's review. The 75-character overlap prevents a sentence that spans a chunk boundary from being split in a way that loses meaning — for example, "exams are brutal but fair" should never be split into two chunks where neither half retrieves well on a grading query. Each RMP review is chunked individually so overlap never bleeds across two different students' opinions. Reddit threads are chunked as plain text since they lack the structured review format.

**Final chunk count:** 287

---

## Embedding Model

**Model used:** all-MiniLM-L6-v2 via sentence-transformers

**Production tradeoff reflection:** MiniLM is fast, free, and runs entirely locally with no API key or rate limits, which made it the right choice for a course project. Its weakness is that it was trained on general text, not student slang or course-specific terminology — it doesn't know that CS515 and CS515 at Stevens are taught by different professors, and it struggles when queries use vocabulary that doesn't appear verbatim in the documents. In a real deployment, `text-embedding-3-small` from OpenAI would likely score better on domain-specific queries at the cost of API fees and latency. Other tradeoffs worth weighing: context length (some models handle longer chunks better than MiniLM's 256-token limit), multilingual support (relevant if the student body writes reviews in languages other than English), and whether the model is hosted locally or via API (local is faster and private but harder to update).

---

## Grounded Generation

**System prompt grounding instruction:**
You are a helpful assistant that answers questions about CS professors
at Stevens Institute of Technology.
Answer ONLY using the information in the provided documents. Do not use
any outside knowledge. If the documents do not contain enough information
to answer the question, say exactly: "I don't have enough information on that."
Always cite which source(s) your answer comes from.

**How source attribution is surfaced in the response:** Retrieved chunk sources are passed to the LLM as numbered citations in the context block (e.g., `[1] (source: reza_peyrovian_rmp)`), and the model is instructed to cite them in its response. Source filenames are also collected programmatically from chunk metadata and displayed separately in the Gradio UI under "Retrieved from," independent of what the LLM chooses to mention.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What do students say about Prof. Peyrovian's grading style? | Fair, clear, lenient and transparent | Grading is unstructured and inconsistent; few projects; criticisms contradict each other | Relevant | Partially accurate — missed positive reviews about lenient/transparent grading |
| 2 | Which CS professor is most recommended for students who struggle with theory? | Alex LaGrassa | Erisa Terolli, inferred from general helpfulness | Partially relevant | Inaccurate — LaGrassa not retrieved; answer is an inference not directly supported by documents |
| 3 | What do students say about Prof. Polimeni's teaching? | Strong lectures, good feedback, accessible | Amazing professor, answers doubts patiently, great | Relevant | Accurate |
| 4 | Do students recommend Prof. Vesonder for upper-level CS courses? | Yes | "I don't have enough information on that." | Partially relevant | Inaccurate — system declined when answer was inferable from retrieved chunks |
| 5 | Which professors are known for being accessible outside of class? | Polimeni, Terolli, LaGrassa | LaGrassa confirmed; Vesonder mentioned with hedging | Partially relevant | Partially accurate — LaGrassa correct, Terolli and Polimeni missed |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** "Do students recommend Prof. Vesonder for upper-level CS courses?"

**What the system returned:** "I don't have enough information on that."

**Root cause:** The query uses the phrase "upper-level CS courses" but none of the Vesonder chunks use that terminology. Reviews mention specific course codes (CS545, SSW590, CS597) without labeling them as upper-level. The embedding model couldn't bridge the semantic gap between the query phrasing and the course codes in the documents, so the retrieved chunks scored as low-confidence matches. The grounding instruction then correctly caused the model to decline rather than infer. The failure is at the retrieval stage: the chunks contain enough information to answer the question, but the query vocabulary doesn't match how the information is expressed in the documents.

**What you would change:** Rephrase evaluation queries to match document vocabulary — "What do students say about Prof. Vesonder?" retrieves correctly. In a production system this would be addressed with query expansion (automatically generating alternative phrasings) or a reranker that scores chunks on semantic content rather than surface similarity alone.

---

## Spec Reflection

**One way the spec helped you during implementation:** The chunking strategy section in planning.md forced me to decide on chunk size and overlap before writing any code, which meant I had a concrete target to verify against. When I printed sample chunks during Milestone 3 and saw overlap bleeding across two different students' reviews, I knew exactly what the problem was and how to fix it — chunk each review individually rather than joining all reviews into one string — because the spec had made the reasoning behind overlap explicit.

**One way your implementation diverged from the spec, and why:** The spec called for a Reddit scraper using the `.json` trick, but Reddit returned 403 errors consistently even with a custom User-Agent header. Rather than spend debugging time on a network problem unrelated to the RAG pipeline, I collected the four Reddit threads manually as `.txt` files. This actually simplified the ingestion code and made the pipeline more reliable, since it removed a live network dependency that could fail at demo time.

---

## AI Usage

**Instance 1**

- *What I gave the AI:* Questions about core concepts before implementation — "how do I determine what chunk size to use," "what does top-k mean and what are the tradeoffs of setting it too high vs. too low," and "how do I scrape RateMyProfessors and Reddit."
- *What it produced:* Explanations of the tradeoffs, and a warning that RMP uses JavaScript rendering that blocks scrapers, suggesting manual collection as the practical alternative.
- *What I changed or overrode:* I used the conceptual explanations to write my own chunking strategy reasoning in planning.md rather than copying the AI's framing directly. For RMP I followed the advice to collect manually. For Reddit I tried the `.json` scraper as suggested but fell back to manual collection after hitting 403 errors.

**Instance 2**

- *What I gave the AI:* My pipeline.py with a broken `load_txt_files` function — it was calling `all_chunks.append` inside the function where `all_chunks` wasn't defined, and `return docs` was indented inside the for loop so it exited after the first file.
- *What it produced:* A corrected version that separated loading from chunking, kept `load_txt_files` focused on reading files and returning docs, and moved the per-review chunking logic into `chunk_docs`.
- *What I changed or overrode:* I kept the structure it suggested but adjusted chunk size from 250 to 400 characters after retrieval testing showed distances consistently above 0.7 with the smaller size.