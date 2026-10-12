import re
import os
from doc_model import Document, DocumentChunk
from doc_store import DocumentStore

def parse_htrl_document (filepath: str, doc_id: str, title: str) -> list[DocumentChunk]:
    """Read file HTRL.md and cut by chunk"""
    with open(filepath, 'r', encoding='utf8') as f:
        content =  f.read()

    raw_chunks = re.split(r'\n(?=Điều \d+\.)', content)

    chunks = []
    for index, text in enumerate(raw_chunks):
        text  = text.strip()
        if not text: 
            continue

        chunk = DocumentChunk(
            content = text,
            chunk_id = f"{doc_id}__CHK{index:03d}",
            doc_id=doc_id,
            chunk_index=index,
            metadata={
                "title": title,
                "version": "2021-2022",
                "owner": "Trường ĐH SPKT TP.HCM"
            }
        )
        chunks.append(chunk)
    return chunks

if __name__ == "__main__":
    #1. link path to HTRL.md file
    file_path = "../../data/HTRL.md"

    #2. start storage (from my doc_store.py)
    store = DocumentStore()

    #3. create chunks
    my_chunks = parse_htrl_document(file_path, "DOC0007", "Quy định  đánh giá kết quả điểm rèn luyện")

    #4. save to store
    for c in my_chunks:
        store.add_chunk(c)

    print(f"Đã cắt và lưu thành công {len(store.chunks)} chunks.")
    print("Test thư chunk 0 (Điều 19):")
    print(my_chunks[19].content)
