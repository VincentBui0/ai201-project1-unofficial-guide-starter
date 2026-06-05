# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

My domain is student reviews of CS professors at Stevens Institute of Technology. This knowledge is valuable because students need it to make informed course enrollment decisions, but official course evaluations aren't made public. The only way it spreads is through peer-to-peer sharing across platforms that aren't collectively indexed anywhere.

---

## Documents

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Rate My Professors | Professor profile and reviews | https://www.ratemyprofessors.com/professor/2326104 |
| 2 | Rate My Professors | Professor profile and reviews | https://www.ratemyprofessors.com/professor/3141334 |
| 3 | Rate My Professors | Professor profile and reviews | https://www.ratemyprofessors.com/professor/2721847 |
| 4 | Rate My Professors | Professor profile and reviews | https://www.ratemyprofessors.com/professor/3065505 |
| 5 | Rate My Professors | Professor profile and reviews | https://www.ratemyprofessors.com/professor/3013137 |
| 6 | Rate My Professors | Professor profile and reviews | https://www.ratemyprofessors.com/professor/1239339 |
| 7 | r/stevens | "Why I chose to attend Stevens for CS" thread | https://www.reddit.com/r/stevens/comments/1b7zem9/why_i_chose_to_attend_stevens_for_cs/ |
| 8 | r/stevens | Engineering/CS students thread | https://www.reddit.com/r/stevens/comments/1qyg2kj/engineering_computer_science_students/ |
| 9 | r/stevens | "Would you recommend Stevens for CS?" thread | https://www.reddit.com/r/stevens/comments/unp3nx/would_you_recommend_going_to_stevens_for_a_cs/ |
| 10 | r/stevens | MS CS admitted students thread | https://www.reddit.com/r/stevens/comments/17wi370/hey_got_admitted_to_ms_cs_here_thoughts/ |

---

## Chunking Strategy

**Chunk size:** 200–300 characters

**Overlap:** ~50 characters

**Reasoning:** RMP reviews are brief and self-contained — a single student's viewpoint is usually two to five sentences. Chunks in this range capture one complete idea without bleeding into the next student's opinion. The overlap matters because a review might say "exams are brutal but fair" across a sentence boundary: without it, one chunk gets "exams are brutal" and the other gets "but fair," and neither retrieves well on a grading query. Chunks under 100 characters fragment individual opinions; chunks over 800 characters blend multiple students' views together and make attribution unreliable.

---

## Retrieval Approach

**Embedding model:** all-MiniLM-L6-v2 (via sentence-transformers)

**Top-k:** 5

**Production tradeoff reflection:** MiniLM is fast and free but was trained on general text, not student slang or course-specific terminology. A model like `text-embedding-3-small` (OpenAI) would likely score better on domain-specific queries but costs money and requires an API key. Other axes worth considering in a real deployment: context length (some models handle longer chunks better), multilingual support (relevant if the student body writes reviews in other languages), and latency (MiniLM is much faster at inference time than larger models, which matters if this is serving live queries).

---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What do students say about Prof. Peyrovian's grading style? | Fair, clear, lenient and transparent — not difficult |
| 2 | Which CS professor at Stevens is most recommended for students who struggle with theory? | Alex LaGrassa, due to positive reviews despite being a first-time teacher |
| 3 | What's the teaching quality like in CS515? | Strong lectures, good feedback, accessible outside class |
| 4 | Do students recommend Prof. Vesonder for upper-level CS courses? | Yes |
| 5 | Which professors are known for being accessible outside of class? | Rocco Polimeni, Erisa Terolli, Alex LaGrassa |

---

## Anticipated Challenges

1. Attribution collisions: multiple professors share similar descriptions like "tough but fair." If retrieval surfaces the wrong professor's reviews for a specific query, the answer will be confidently wrong. Keeping professor name metadata on every chunk and filtering by it at retrieval time should help.

2. Inconsistent review coverage: RMP reviews vary wildly in what they address. One student writes about exams, another about office hours, another about the textbook. A query about grading might retrieve chunks from the right professor that answer a completely different question, degrading response quality without the system flagging any obvious failure.

---

## Architecture

```
Raw Documents (HTML/text)
        ↓
  Ingestion & Cleaning
  (requests, BeautifulSoup)
        ↓
     Chunking
  (RecursiveCharacterTextSplitter)
        ↓
   Embedding + Vector Store
  (all-MiniLM-L6-v2 + ChromaDB)
        ↓
     Retrieval (top-k=5)
        ↓
  Response Generation
  (Groq / llama-3.3-70b)
```

---

## AI Tool Plan

**Milestone 3 — Ingestion and chunking:** RMP data is collected manually as `.txt` files (one per professor). I'll give Claude the Documents section and ask it to write a script that loads those local files from disk, plus a Reddit scraper using the `.json` trick for the four Reddit URLs. For chunking, I'll give Claude the Chunking Strategy section and ask it to implement `chunk_text()` using LangChain's `RecursiveCharacterTextSplitter` with chunk size 250 and overlap 50. I'll verify by printing chunk counts and spot-checking that no chunk cuts mid-sentence in a way that loses meaning.

## Milestone 3 Results
Total chunks: 390 (79 RMP, 311 Reddit)
Chunk size: 250, overlap: 50
Reddit collected manually as .txt files due to 403 errors on .json scraper

**Milestone 4 — Embedding and retrieval:** I'll give Claude the Architecture diagram and the Retrieval Approach section and ask it to write the script that embeds chunks using `all-MiniLM-L6-v2` and loads them into a local ChromaDB collection. I'll verify by running a test query against the collection and checking that the top-5 results are from the expected professor.

Distances under 0.55. Query 2 cannot find Polimeni by course number

**Milestone 5 — Generation and interface:** I'll give Claude the Retrieval Approach section and ask it to write the Groq API call with a system prompt that enforces grounding (i.e., the model should only answer from retrieved chunks, not general knowledge). I'll verify using the 5 evaluation questions and checking responses against expected answers.

After running query.py:
Query 1 is grounded — every claim traces back to a numbered source, the answer acknowledges conflicting reviews rather than averaging them away, and it only draws from Peyrovian chunks.
Query 2 is grounded — cites LaGrassa by source, and correctly hedges on the Reddit chunk ("does not specify a particular professor's name").
Query 3 is the most important one — the system declined cleanly instead of hallucinating a restaurant recommendation. That's your grounding instruction working.

App.py runs smoothly with minor issues.