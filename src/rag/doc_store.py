from doc_model import Document, DocumentChunk
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class DocumentStore:
    """
    An in-memory store for Documents and their Chunks.

    This is the foundation, later, we'll replace the internal dict
    with a vector database - but the interface stas the same.
    """
    documents: dict[str, Document] = field(default_factory=dict)
    chunks: dict[str, DocumentChunk] = field(default_factory =dict)

    def add(self, doc: Document)-> str:
        """
        Add a document to store.
        Args:
            doc (Document): The document to be added.
        Returns:
            str: doc_id of the added document.
        """

        if not doc.doc_id:
            doc.doc_id = f"DOC{len(self.documents)+1:04d}"
        self.documents[doc.doc_id] = doc
        return doc.doc_id

    def get(self, doc_id: str) -> Optional[Document]:
        """
        Retrieve a document
         Args:
            doc_id (str): The ID of the document.

        Returns:
            Optional[Document]: The document if found, otherwise None.
        """
        return self.documents.get(doc_id)

    def delete(self, doc_id: str) -> bool:
        """
        Delete a document by its ID.

        Args:
            doc_id (str): The ID of the document.

        Returns:
            bool: True if deleted, False if not found.
        """

        if doc_id not in self.documents:
            return False

        del self.documents[doc_id]

        self.chunks = [
            chunk for chunk in self.chunks
            if chunk.doc_id != doc_id
        ]

        return True
        

    def list_all (self) -> list[Document]:
        """
        Return all documents in the store.

        Returns:
            List[Document]: A list of all documents.
        """
        return list(self.documents.values())
    

    def add_chunk(self, chunk: DocumentChunk) ->str:    # return its chunk_id
        """Add a chunk to repository and back to chunk_id"""
        if not chunk.chunk_id:
            chunk.chunk_id = f"CHK{len(self.chunks) + 1:05d}"

        self.chunks[chunk.chunk_id] = chunk
        return chunk.chunk_id

    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:  # retrieve a chunks by chunk_id
        """Lấy ra một chunk cụ thể dựa vào chunk_id."""
        # Duyệt qua mảng chunks để tìm ID tương ứng
        for chunk in self.chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
        return None
    
    def get_chunk_by_doc (self, doc_id: str) -> list[DocumentChunk]: # get all chunks of the doc
        """Lấy toàn bộ các chunks thuộc về một Document cụ thể."""
        # Dùng list comprehension để lọc nhanh các chunk có doc_id trùng khớp
        # (Lưu ý: Dựa theo hàm delete bên trên, mình giả định biến liên kết trong class DocumentChunk của bạn tên là doc_id, nếu ở bài trước bạn dùng dpc_id thì nhớ đổi lại nhé).
        return [chunk for chunk in self.chunks if chunk.doc_id == doc_id]
        
    def Count(self) ->dict: # return count of Document and chunks
        """Trả về thống kê số lượng tài liệu và đoạn cắt hiện có."""
        return {
            "documents": len(self.documents),
            "chunks": len(self.chunks)
        }