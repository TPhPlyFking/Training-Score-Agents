import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from src.utils.api_handler import APIHandler
from src.mcp.mcp_client import MCPClient
from src.agent.agent__loop import AgentLoop
from src.rag.document_parser import load_all_documents
from src.rag.hybrid_search import hybrid_search, build_bm25_index, embed_text

load_dotenv()
ROOT = Path(__file__).resolve().parent

# Câu hỏi mẫu: câu 1 thử tra cứu quy định (tầng a), câu 2 thử tạo khiếu nại + xác minh (tầng c)
SAMPLE_QUESTIONS = [
    "Sinh viên bị kỷ luật mức khiển trách thì điểm rèn luyện cao nhất đạt loại gì?",
    "Em là sinh viên mã số 22110001. Điểm hoạt động tình nguyện học kỳ 1 của em chưa được cộng, "
    "em muốn tạo đơn khiếu nại.",
]


async def main():
    questions = [sys.argv[1]] if len(sys.argv) > 1 else SAMPLE_QUESTIONS

    # 1. Chuẩn bị RAG: cắt chunk, dựng BM25, tạo embedding
    chunks = load_all_documents()
    bm25_index = build_bm25_index(chunks)
    embeddings = [embed_text(chunk.content) for chunk in chunks]

    def search_rag(query: str):
        results = hybrid_search(query, chunks, bm25_index, embeddings, top_k=5)
        return [{"doc_id": chunk.doc_id, "title": chunk.metadata["title"], "content": chunk.content}
                for chunk, hybrid, bm25, vector in results]

    # 2. Kết nối MCP server, tự lấy danh sách tool
    mcp_client = MCPClient(ROOT / "src" / "mcp" / "mcp_server.py")
    await mcp_client.connect()
    try:
        print("Tools tìm thấy từ MCP server:", [tool["name"] for tool in mcp_client.get_tool_schemas()])
        agent = AgentLoop(api_handler=APIHandler(), mcp_client=mcp_client, rag_search=search_rag)

        # 3. Hỏi agent từng câu
        for question in questions:
            print("\n" + "=" * 60)
            print("Câu hỏi:", question)
            result = await agent.run(question)
            print(f"Trả lời ({result.steps} bước):", result.answer)
    finally:
        await mcp_client.close()


if __name__ == "__main__":
    asyncio.run(main())
