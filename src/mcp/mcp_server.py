import asyncio
import json
import time
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.utils.db import save, get

RAG_DATA = {}


def search_regulations_real(query: str) -> str:
    """Tra cứu quy chế thật bằng hybrid search (trước đây trả về 1 chuỗi cố định)."""
    from src.rag.document_parser import load_all_documents
    from src.rag.hybrid_search import hybrid_search, build_bm25_index, embed_text

    if not RAG_DATA:
        chunks = load_all_documents()   # các tài liệu trong DOCUMENTS
        RAG_DATA["chunks"] = chunks
        RAG_DATA["bm25"] = build_bm25_index(chunks)
        RAG_DATA["embeddings"] = [embed_text(c.content) for c in chunks]

    results = hybrid_search(query, RAG_DATA["chunks"], RAG_DATA["bm25"], RAG_DATA["embeddings"], top_k=5)
    lines = []
    for chunk, hybrid, bm25, vector in results:
        lines.append(f"[doc_id: {chunk.doc_id}] {chunk.metadata['title']}\n{chunk.content}")
    return "\n\n".join(lines)


TOOLS = [
    types.Tool(
        name="search_regulations",
        description="Tra cứu quy định về điểm rèn luyện và thủ tục khiếu nại.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"],
        },
    ),
    types.Tool(
        name="calculate_training_score",
        description="Tính điểm rèn luyện theo 5 nội dung.",
        input_schema={
            "type": "object",
            "properties": {
                "content_i": {"type": "object"},
                "content_ii": {"type": "object"},
                "content_iii": {"type": "object"},
                "content_iv": {"type": "object"},
                "content_v": {"type": "object"},
            },
            "required": [
                "content_i",
                "content_ii",
                "content_iii",
                "content_iv",
                "content_v",
            ],
        },
    ),
    types.Tool(
        name="compare_scores",
        description="So sánh điểm thực tế với điểm mục tiêu.",
        input_schema={
            "type": "object",
            "properties": {
                "actual_score": {"type": "integer"},
                "target_score": {"type": "integer"},
            },
            "required": ["actual_score", "target_score"],
        },
    ),
    types.Tool(
        name="create_complaint",
        description="Tạo đơn khiếu nại điểm rèn luyện.",
        input_schema={
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["student_id", "reason"],
        },
    ),
    types.Tool(
        name="get_complaint",
        description="Tra cứu đơn khiếu nại theo mã để xác minh.",
        input_schema={
            "type": "object",
            "properties": {
                "complaint_id": {"type": "string"}
            },
            "required": ["complaint_id"],
        },
    ),
]


async def list_tools(
    ctx: Any,
    params: types.PaginatedRequestParams | None,
) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOLS)


async def call_tool(
    ctx: Any,
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
    name = params.name
    arguments = params.arguments or {}

    try:
        if name == "search_regulations":
            query = arguments.get("query", "")
            result = search_regulations_real(query)   

        elif name == "calculate_training_score":
            c1 = arguments["content_i"]
            c2 = arguments["content_ii"]
            c3 = arguments["content_iii"]
            c4 = arguments["content_iv"]
            c5 = arguments["content_v"]

            score_i = max(
                0, min(c1.get("base", 0)
                       + c1.get("bonus", 0)
                       - c1.get("penalty", 0), 38)
            )
            score_ii = max(
                0, min(c2.get("base", 20)
                       - c2.get("penalty", 0), 20)
            )
            score_iii = max(
                0, min(c3.get("base", 0)
                       + c3.get("bonus", 0)
                       - c3.get("penalty", 0), 38)
            )
            score_iv = max(
                0, min(c4.get("base", 0)
                       + c4.get("bonus", 0)
                       - c4.get("penalty", 0), 30)
            )
            score_v = max(
                0, min(c5.get("base", 0)
                       + c5.get("bonus", 0), 15)
            )

            total = min(
                score_i + score_ii + score_iii + score_iv + score_v,
                100,
            )

            if total >= 92:
                classification = "Xuất sắc"
            elif total >= 82:
                classification = "Tốt"
            elif total >= 68:
                classification = "Khá"
            elif total >= 50:
                classification = "Trung bình"
            elif total >= 35:
                classification = "Yếu"
            else:
                classification = "Kém"

            result = json.dumps(
                {
                    "total_score": total,
                    "classification": classification,
                    "message": (
                        f"Tổng điểm: {total}/100 - "
                        f"Xếp loại: {classification}"
                    ),
                },
                ensure_ascii=False,
            )

        elif name == "compare_scores":
            actual = arguments["actual_score"]
            target = arguments["target_score"]
            diff = actual - target

            result = json.dumps(
                {
                    "actual_score": actual,
                    "target_score": target,
                    "difference": diff,
                    "status": (
                        "Đạt yêu cầu"
                        if diff >= 0
                        else f"Còn thiếu {abs(diff)} điểm"
                    ),
                },
                ensure_ascii=False,
            )

        elif name == "create_complaint":
            student_id = arguments["student_id"]
            reason = arguments["reason"]

            complaint_id = f"CMP-{int(time.time() * 1000)}"

            save(complaint_id, {
                "student_id": student_id,
                "reason": reason,
                "status": "Pending",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

            result = json.dumps(
                {
                    "success": True,
                    "complaint_id": complaint_id,
                    "message": "Đã tạo đơn khiếu nại thành công.",
                },
                ensure_ascii=False,
            )

        elif name == "get_complaint":
            complaint_id = arguments["complaint_id"]
            complaint = get(complaint_id)  

            if complaint:
                data = {
                    "complaint_id": complaint_id,
                    "found": True,
                    **complaint,
                }
            else:
                data = {
                    "complaint_id": complaint_id,
                    "found": False,
                    "message": "Không tìm thấy khiếu nại.",
                }

            result = json.dumps(data, ensure_ascii=False)

        else:
            raise ValueError(f"Tool không tồn tại: {name}")

        return types.CallToolResult(
            content=[types.TextContent(type="text", text=result)]
        )

    except Exception as error:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Error: {error}",
                )
            ],
            isError=True,
        )


app = Server(
    "training-score-mcp-server",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())