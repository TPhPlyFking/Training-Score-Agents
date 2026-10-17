import re
import os
from src.rag.doc_model import Document, DocumentChunk
from src.rag.doc_store import DocumentStore


MAX_CHARS = 500

def split_long_chunk(text: str) -> list[str]:
    """Chia chunk dài thành nhiều phần <= MAX_CHARS, cắt theo dòng.
    Phần nào cũng giữ dòng đầu tiên (tên Điều / tên mục) để vẫn biết nó thuộc Điều nào."""
    lines = [line for line in text.split("\n") if line.strip()]
    header = lines[0]
    parts = []
    current = header
    for line in lines[1:]:
        is_sub_item = line.startswith("|") and line.split("|")[1].count(".") >= 3
        if len(current) + len(line) > MAX_CHARS and current != header and not is_sub_item:
            parts.append(current)      
            current = header    
        current += "\n" + line
    parts.append(current)
    return parts

def parse_htrl_document (filepath: str, doc_id: str, title: str,
                         version: str = "2021-2022", owner: str = "Trường ĐH SPKT TP.HCM") -> list[DocumentChunk]:  
    """Read file HTRL.md and cut by chunk"""
    with open(filepath, 'r', encoding='utf8') as f:
        content =  f.read()

    body, _, appendix = content.partition("**Phụ lục 1")
    raw_chunks = re.split(r'\n(?=Điều \d+\.)', body)
    raw_chunks += re.split(r'\n(?=\| [IV]+\. )', appendix)[1:]

    small_chunks = []
    for text in raw_chunks:
        if text.strip():
            small_chunks += split_long_chunk(text.strip())
    raw_chunks = small_chunks

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
                "version": version,  
                "owner": owner
            }
        )
        chunks.append(chunk)
    return chunks


DOCUMENTS = [
    ("DOC0007", "HTRL.md", "Quy định đánh giá kết quả rèn luyện", "2021-2022", "Trường ĐH SPKT TP.HCM"),
]

def load_all_documents() -> list[DocumentChunk]:
    """Cắt chunk cho toàn bộ tài liệu trong DOCUMENTS."""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    chunks = []
    for doc_id, file_name, title, version, owner in DOCUMENTS:
        chunks += parse_htrl_document(os.path.join(data_dir, file_name), doc_id, title, version, owner)
    return chunks

if __name__ == "__main__":
    #1. link path to HTRL.md file
    file_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "HTRL.md")

    #2. start storage (from my doc_store.py)
    store = DocumentStore()

    #3. create chunks
    my_chunks = load_all_documents()   # cắt các tài liệu trong DOCUMENTS

    #4. save to store
    for c in my_chunks:
        store.add_chunk(c)

    print(f"Đã cắt và lưu thành công {len(store.chunks)} chunks.")
    print(f"Chunk dài nhất: {max(len(c.content) for c in my_chunks)} ký tự")
