import asyncio
import json
import time
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types


FAKE_DATABASE = {"complaints": {}}


# 1. Khai báo danh sách tools
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


# 2. Handler liệt kê tools
async def list_tools(
    ctx: Any,
    params: types.PaginatedRequestParams | None,
) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOLS)


# 3. Handler thực thi tools
async def call_tool(
    ctx: Any,
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
    name = params.name
    arguments = params.arguments or {}

    try:
        if name == "search_regulations":
            query = arguments.get("query", "")
            result = (
                f"Tra cứu quy chế HCMUTE cho từ khóa '{query}': "
                "Thang điểm 100 chia 5 nội dung. "
                "Xếp loại tham khảo: Xuất sắc (>=90), "
                "Tốt (80-89), Khá (65-79), "
                "Trung bình (50-64), Yếu (35-49), Kém (<35)."
            )

        elif name == "calculate_training_score":
            c1 = arguments["content_i"]
            c2 = arguments["content_ii"]
            c3 = arguments["content_iii"]
            c4 = arguments["content_iv"]
            c5 = arguments["content_v"]

            score_i = max(
                0, min(c1.get("base", 0)
                       + c1.get("bonus", 0)
                       - c1.get("penalty", 0), 30)
            )
            score_ii = max(
                0, min(c2.get("base", 25)
                       - c2.get("penalty", 0), 25)
            )
            score_iii = max(
                0, min(c3.get("base", 0)
                       + c3.get("bonus", 0)
                       - c3.get("penalty", 0), 30)
            )
            score_iv = max(
                0, min(c4.get("base", 0)
                       + c4.get("bonus", 0)
                       - c4.get("penalty", 0), 38)
            )
            score_v = max(
                0, min(c5.get("base", 0)
                       + c5.get("bonus", 0), 15)
            )

            total = min(
                score_i + score_ii + score_iii + score_iv + score_v,
                100,
            )

            if total >= 90:
                classification = "Xuất sắc"
            elif total >= 80:
                classification = "Tốt"
            elif total >= 65:
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

            FAKE_DATABASE["complaints"][complaint_id] = {
                "student_id": student_id,
                "reason": reason,
                "status": "Pending",
            }

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
            complaint = FAKE_DATABASE["complaints"].get(complaint_id)

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


# 4. Đăng ký handlers theo API MCP hiện tại
app = Server(
    "training-score-mcp-server",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


# 5. Khởi động server qua stdio
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())