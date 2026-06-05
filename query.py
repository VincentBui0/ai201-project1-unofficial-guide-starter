import os
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer
import chromadb

load_dotenv()

# Load model and collection once at import time
_model = SentenceTransformer("all-MiniLM-L6-v2")
_client = chromadb.PersistentClient(path="./chroma_db")
_collection = _client.get_collection("stevens_reviews")
_groq = Groq(api_key=os.environ["GROQ_API_KEY"])


def ask(question, k=5):
    # Retrieve
    query_embedding = _model.encode([question]).tolist()
    results = _collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        include=["documents", "metadatas", "distances"]
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    # Build context block
    context_parts = []
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        context_parts.append(f"[{i+1}] (source: {meta['source']})\n{doc}")
    context = "\n\n".join(context_parts)

    # Collect unique sources for attribution
    sources = list(dict.fromkeys(m["source"] for m in metas))

    # Generate
    system_prompt = """You are a helpful assistant that answers questions about CS professors at Stevens Institute of Technology.

Answer ONLY using the information in the provided documents. Do not use any outside knowledge.
If the documents do not contain enough information to answer the question, say exactly: "I don't have enough information on that."
Always cite which source(s) your answer comes from."""

    user_prompt = f"""Documents:
{context}

Question: {question}"""

    response = _groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )

    answer = response.choices[0].message.content

    return {
        "answer": answer,
        "sources": sources,
        "chunks": [{"text": d, "source": m["source"], "distance": dist}
                   for d, m, dist in zip(docs, metas, distances)]
    }


if __name__ == "__main__":
    # Quick end-to-end test
    test_questions = [
        "What do students say about Prof. Peyrovian's grading style?",
        "Which professors are known for being accessible outside of class?",
        "What is the best restaurant near Stevens?",  # should trigger "don't have enough info"
    ]

    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"Q: {q}")
        print('='*60)
        result = ask(q)
        print(result["answer"])
        print(f"\nSources: {', '.join(result['sources'])}")