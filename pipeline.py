import os
import re
import html
import requests
from sentence_transformers import SentenceTransformer
import chromadb

# --- Config ---
DOCS_DIR = "documents"
REDDIT_URLS = [
    "https://www.reddit.com/r/stevens/comments/1b7zem9/why_i_chose_to_attend_stevens_for_cs/",
    "https://www.reddit.com/r/stevens/comments/1qyg2kj/engineering_computer_science_students/",
    "https://www.reddit.com/r/stevens/comments/unp3nx/would_you_recommend_going_to_stevens_for_a_cs/",
    "https://www.reddit.com/r/stevens/comments/17wi370/hey_got_admitted_to_ms_cs_here_thoughts/",
]
HEADERS = {"User-Agent": "stevens-rag-project/1.0 (vincent.bui657@gmail.com)"}


# --- Text splitter (no langchain needed) ---
def split_text(text, chunk_size=250, chunk_overlap=50, separators=["\n\n", "\n", ". ", " ", ""]):
    def _split(text, seps):
        if not text:
            return []
        sep = seps[0]
        remaining = seps[1:]

        parts = list(text) if sep == "" else text.split(sep)

        chunks = []
        current = ""
        for part in parts:
            piece = part + (sep if sep not in ("", " ") else " ")
            if len(current) + len(piece) <= chunk_size:
                current += piece
            else:
                if current.strip():
                    chunks.append(current.strip())
                if len(piece.strip()) > chunk_size and remaining:
                    chunks.extend(_split(piece.strip(), remaining))
                    current = ""
                else:
                    current = piece
        if current.strip():
            chunks.append(current.strip())
        return chunks

    raw_chunks = _split(text, separators)

    final = []
    for i, chunk in enumerate(raw_chunks):
        if i == 0:
            final.append(chunk)
        else:
            overlap_text = final[-1][-chunk_overlap:]
            final.append((overlap_text + " " + chunk).strip())
    return final


# --- Load and clean RMP .txt files ---
def parse_rmp_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    prof_name = filepath.replace("_rmp.txt", "").replace("_", " ").split("\\")[-1].split("/")[-1].title()

    blocks = re.split(r"\n{2,}", content)

    reviews = []
    in_review = False

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        if any(x in block for x in ["STUDENT RATINGS", "Overall Quality", "Rating Distribution"]):
            continue

        lines = block.splitlines()
        is_metadata = all(
            re.match(r"^\[\d+\]$", l.strip()) or
            re.match(r"^(Course|Date|Quality|For Credit|Attendance|Would Take Again|Grade|Textbook|Online Class|Tags)[:\|]", l.strip()) or
            l.strip() == ""
            for l in lines
        )

        if is_metadata:
            in_review = True
            continue

        if in_review and block:
            reviews.append(f"{prof_name}: {block}")

    return prof_name, reviews


def load_txt_files(folder):
    docs = []
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith(".txt"):
            continue
        filepath = os.path.join(folder, filename)
        source = filename.replace(".txt", "")

        if filename.startswith("stevens_"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read().strip()
            docs.append({"source": source, "prof_name": None, "text": text})
            print(f"Loaded {filename}: {len(text)} characters")
        else:
            prof_name, reviews = parse_rmp_file(filepath)
            combined = "\n\n".join(reviews)
            docs.append({"source": source, "prof_name": prof_name, "text": combined})
            print(f"Loaded {filename}: {len(reviews)} reviews, {len(combined)} characters")

    return docs


# --- Fetch Reddit comments via .json trick ---
def fetch_reddit_thread(url):
    json_url = url.rstrip("/") + ".json"
    response = requests.get(json_url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    comments = []

    def extract_comments(listing):
        if not listing or not isinstance(listing, dict):
            return
        if listing.get("kind") == "Listing":
            for child in listing["data"]["children"]:
                extract_comments(child)
        elif listing.get("kind") == "t1":
            body = listing["data"].get("body", "")
            if body and body not in ("[deleted]", "[removed]"):
                comments.append(html.unescape(body))
            replies = listing["data"].get("replies", "")
            if replies:
                extract_comments(replies)

    for top_level in data:
        extract_comments(top_level)

    return "\n\n".join(comments)


def load_reddit_docs(urls):
    docs = []
    for url in urls:
        slug = url.rstrip("/").split("/")[-1]
        print(f"Fetching Reddit thread: {slug}")
        text = fetch_reddit_thread(url)
        docs.append({"source": f"reddit_{slug}", "prof_name": None, "text": text})
        print(f"  Got {len(text)} characters")
    return docs


# --- Chunk ---
def chunk_docs(docs):
    chunks = []
    for doc in docs:
        reviews = doc["text"].split("\n\n")
        prof_name = doc["prof_name"]
        for review in reviews:
            splits = split_text(review, chunk_size=400, chunk_overlap=75)
            for s in splits:
                # Prepend professor name so the embedding captures it,
                # even when the chunk text alone doesn't mention it
                if prof_name and not s.startswith(prof_name):
                    chunk_text = f"Professor {prof_name}: {s}"
                else:
                    chunk_text = s
                chunks.append({
                    "source": doc["source"],
                    "prof_name": prof_name,
                    "chunk": chunk_text
                })
    return chunks


# --- Embed and store in ChromaDB ---
def build_vector_store(chunks):
    print("\nLoading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path="./chroma_db")

    try:
        client.delete_collection("stevens_reviews")
    except Exception:
        pass

    # Use cosine distance — better for semantic similarity than L2
    collection = client.create_collection(
        "stevens_reviews",
        metadata={"hnsw:space": "cosine"}
    )

    texts = [c["chunk"] for c in chunks]
    metadatas = [{"source": c["source"], "prof_name": c["prof_name"] or "unknown"} for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    print(f"Embedding {len(chunks)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    print(f"Stored {collection.count()} chunks in ChromaDB.")
    return collection, model


# --- Retrieval ---
def retrieve(query, collection, model, k=5):
    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        include=["documents", "metadatas", "distances"]
    )
    return results


# --- Main ---
if __name__ == "__main__":
    docs = []
    docs += load_txt_files(DOCS_DIR)
    # docs += load_reddit_docs(REDDIT_URLS)

    print(f"\nTotal documents loaded: {len(docs)}")

    chunks = chunk_docs(docs)
    print(f"Total chunks: {len(chunks)}")

    collection, model = build_vector_store(chunks)

    test_queries = [
        "What do students say about Prof. Peyrovian's grading style?",
        "What's the teaching quality like in CS515?",
        "Which professors are known for being accessible outside of class?",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {query}")
        print('='*60)
        results = retrieve(query, collection, model, k=5)
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            print(f"\n[{i+1}] source: {meta['source']} | distance: {dist:.3f}")
            print(doc)