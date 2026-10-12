from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Document:
    """A full document to be indexed."""
    content: str
    doc_id: str = ""
    title: str = ""
    source: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class DocumentChunk:
    """A chunk of a document after splitting."""
    content: str
    chunk_id: str = ""
    doc_id: str = ""
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None     

def chunk_document(doc: Document, chunk_size: int = 512, overlap: int = 64) -> list[DocumentChunk]:
    """
    Split a document into chunks of specified size.
    Args: 
        doc(Document): The document to be chunked.
        chunk_size(int): The size of each chunk.
        overlap(int): The number of overlapping characters between chunks.
    Returns:
        List[DocumentChunk]: A list of DocumentChunk instances.
    """
    chunks = []
    text = doc.content
    start = 0
    chunk_index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_content = text[start:end]

        chunk = DocumentChunk(
            content=chunk_content,
            chunk_id=f"{doc.doc_id}_CHK{chunk_index:03d}",
            doc_id=doc.doc_id,
            chunk_index=chunk_index,
            metadata=doc.metadata
        )
        chunks.append(chunk)

        start += (chunk_size - overlap)
        chunk_index += 1

    return chunks



