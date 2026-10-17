from rank_bm25 import BM25Okapi
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import sys
print("Đang tải AI Vector Embedding...", file=sys.stderr)
embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

from src.rag.doc_model import DocumentChunk
from src.rag.doc_store import DocumentStore
from src.rag.document_parser import parse_htrl_document

def normalise_scores(scores: list[float]) -> list[float]:
    if len(scores) == 0:
        return []
    min_s = min(scores)
    max_s = max(scores)
    if max_s == min_s:
        return [1.0] * len(scores)
    return [(s - min_s) / (max_s - min_s) for s in scores]

def build_bm25_index(chunks: list[DocumentChunk]) -> BM25Okapi:
    tokenized = [chunk.content.lower().split() for chunk in chunks]
    return BM25Okapi(tokenized)


def embed_text(text: str) -> list[float]:
    return embedding_model.encode(text).tolist()

def cosine_similarity_calc(vec_a, vec_b):
    """Tính toán Cosine Similarity giữa 2 vector."""
    vec_a = np.array(vec_a)
    vec_b = np.array(vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

def hybrid_search(
    query: str,
    chunks: list[DocumentChunk],
    bm25_index: BM25Okapi,
    embeddings: list[list[float]],
    top_k: int = 3,
    w_bm25: float = 0.3,
    w_vector: float = 0.7,
    mode: str = "hybrid"      
) -> list[tuple]:
    
    tokenized_query = query.lower().split()
    bm25_scores = bm25_index.get_scores(tokenized_query)
    bm25_normalized = normalise_scores(bm25_scores)
    
    query_embedding = embed_text(query) 
    vector_scores = []
    for embedding in embeddings:
        score = cosine_similarity_calc(query_embedding, embedding) 
        vector_scores.append(score)
    vector_normalized = normalise_scores(vector_scores)
    
    hybrid_score = []
    for i in range(len(chunks)):
        if mode == "dense":
            score = vector_scores[i]     
        else:
            score = (w_bm25 * bm25_normalized[i] + w_vector * vector_normalized[i])
        hybrid_score.append(score)
        
    rank = sorted(
        range(len(chunks)),
        key=lambda i: hybrid_score[i],
        reverse=True
    )
    
    results = []
    for i in rank[:top_k]:
        results.append((
            chunks[i],
            hybrid_score[i],
            bm25_scores[i],
            vector_scores[i]
        ))
    return results

if __name__ == "__main__":
    store = DocumentStore()
    path = Path(__file__).resolve().parents[2]
    file_path = path/"data"/"HTRL.md"
    my_chunks = parse_htrl_document(file_path, "DOC0007", "Quy định đánh giá rèn luyện")
    
    for c in my_chunks:
        c.embedding = embed_text(c.content) 
        store.add_chunk(c)

    chunks = list(store.chunks.values())
    bm25_index = build_bm25_index(chunks)
    embeddings = [chunk.embedding for chunk in chunks]

    test_queries = [
        "Học hộ thi hộ bị trừ mấy điểm?",
        "Em tham gia chiến dịch mùa hè xanh thì được cộng bao nhiêu điểm?",
        "Sinh viên đồng thời học hai chương trình đào tạo sẽ được đánh giá kết quả sao?"
    ]

    for query in test_queries:
        print(f"\n--- Câu hỏi: '{query}' ---")
        for mode in ["dense", "hybrid"]:          # chạy thử cả 2 chế độ để so sánh
            print(f"[Chế độ {mode}]")
            results = hybrid_search(query, chunks, bm25_index, embeddings, top_k=2, mode=mode)

            for chunk, hybrid, bm25_score, vector_score in results:
                print(f"⭐ Điểm: {hybrid:.3f} | BM25: {bm25_score:.3f} | Vector: {vector_score:.3f}")
                print(f"📄 Nguồn: {chunk.doc_id} - Nội dung: {chunk.content[:150]}...\n")
