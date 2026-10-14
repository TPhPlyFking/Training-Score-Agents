import asyncio
import json
import time
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Import các hàm từ file db.py trong thư mục utils
from utils.db import save, get

app = Server("training-score-mcp-server")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_regulations",
            description="Tra cứu các quy định về điểm rèn luyện hoặc thủ tục khiếu nại theo quy chế HCMUTE.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Từ khóa hoặc nội dung cần tra cứu"}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="calculate_training_score",
            description="Tính toán điểm rèn luyện 5 nội dung theo đúng quy chế HCMUTE bằng code Python thực sự.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content_i": {"type": "object", "description": "Điểm phần I: Học tập"},
                    "content_ii": {"type": "object", "description": "Điểm phần II: Chấp hành nội quy"},
                    "content_iii": {"type": "object", "description": "Điểm phần III: Hoạt động xã hội"},
                    "content_iv": {"type": "object", "description": "Điểm phần IV: Phẩm chất công dân"},
                    "content_v": {"type": "object", "description": "Điểm phần V: Công tác Đoàn Hội"}
                },
                "required": ["content_i", "content_ii", "content_iii", "content_iv", "content_v"]
            }
        ),
        types.Tool(
            name="compare_scores",
            description="So sánh điểm rèn luyện tính toán được với mức điểm yêu cầu.",
            inputSchema={
                "type": "object",
                "properties": {
                    "actual_score": {"type": "integer", "description": "Điểm thực tế"},
                    "target_score": {"type": "integer", "description": "Điểm mục tiêu"}
                },
                "required": ["actual_score", "target_score"]
            }
        ),
        types.Tool(
            name="create_complaint",
            description="Tạo yêu cầu khiếu nại điểm rèn luyện mới (Side Effect - Ghi dữ liệu vào JSONL).",
            inputSchema={
                "type": "object",
                "properties": {
                    "student_id": {"type": "string", "description": "Mã sinh viên"},
                    "reason": {"type": "string", "description": "Lý do khiếu nại"}
                },
                "required": ["student_id", "reason"]
            }
        ),
        types.Tool(
            name="get_complaint",
            description="Đọc thông tin khiếu nại theo ID để xác minh trạng thái từ file JSONL (Bước Verify).",
            inputSchema={
                "type": "object",
                "properties": {
                    "complaint_id": {"type": "string", "description": "Mã khiếu nại"}
                },
                "required": ["complaint_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "search_regulations":
            query = arguments.get("query", "")
            result = f"Tra cứu quy chế HCMUTE cho từ khóa '{query}': Thang điểm 100 chia 5 nội dung. Phân loại: Xuất sắc (>=90), Tốt (80-89), Khá (65-79), Trung bình (50-64), Yếu (35-49), Kém (<35)."
            return [types.TextContent(type="text", text=result)]

        elif name == "calculate_training_score":
            c1 = arguments.get("content_i", {"base": 16, "bonus": 0, "penalty": 0})
            c2 = arguments.get("content_ii", {"base": 25, "penalty": 0})
            c3 = arguments.get("content_iii", {"base": 15, "bonus": 0, "penalty": 0})
            c4 = arguments.get("content_iv", {"base": 20, "bonus": 0, "penalty": 0})
            c5 = arguments.get("content_v", {"base": 6, "bonus": 0})

            score_i = max(0, min(c1.get("base", 0) + c1.get("bonus", 0) - c1.get("penalty", 0), 30))
            score_ii = max(0, min(c2.get("base", 25) - c2.get("penalty", 0), 25))
            score_iii = max(0, min(c3.get("base", 0) + c3.get("bonus", 0) - c3.get("penalty", 0), 30))
            score_iv = max(0, min(c4.get("base", 0) + c4.get("bonus", 0) - c4.get("penalty", 0), 38))
            score_v = max(0, min(c5.get("base", 0) + c5.get("bonus", 0), 15))

            total_score = min(score_i + score_ii + score_iii + score_iv + score_v, 100)

            if total_score >= 90:
                classification = "Xuất sắc"
            elif total_score >= 80:
                classification = "Tốt"
            elif total_score >= 65:
                classification = "Khá"
            elif total_score >= 50:
                classification = "Trung bình"
            elif total_score >= 35:
                classification = "Yếu"
            else:
                classification = "Kém"

            response_data = {
                "total_score": total_score,
                "classification": classification,
                "message": f"Tổng điểm: {total_score}/100 - Xếp loại: {classification}"
            }
            return [types.TextContent(type="text", text=json.dumps(response_data, ensure_ascii=False))]

        elif name == "compare_scores":
            actual = arguments.get("actual_score", 0)
            target = arguments.get("target_score", 0)
            diff = actual - target
            status = "Đạt yêu cầu" if diff >= 0 else f"Còn thiếu {abs(diff)} điểm"
            response_data = {"actual_score": actual, "target_score": target, "difference": diff, "status": status}
            return [types.TextContent(type="text", text=json.dumps(response_data, ensure_ascii=False))]

        elif name == "create_complaint":
            student_id = arguments.get("student_id")
            reason = arguments.get("reason")
            complaint_id = f"CMP-{int(time.time())}"
            complaint_data = {
                "student_id": student_id,
                "reason": reason,
                "status": "Pending",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            # Gọi hàm save từ db.py để ghi bền vững vào file JSONL
            save(complaint_id, complaint_data)
            
            response_data = {"success": True, "complaint_id": complaint_id, "message": "Đã tạo và lưu đơn khiếu nại thành công vào tệp JSONL."}
            return [types.TextContent(type="text", text=json.dumps(response_data, ensure_ascii=False))]

        elif name == "get_complaint":
            complaint_id = arguments.get("complaint_id")
            # Gọi hàm get từ db.py để đọc dữ liệu từ file JSONL
            complaint_info = get(complaint_id)
            
            if complaint_info:
                response_data = {"complaint_id": complaint_id, "found": True, **complaint_info}
            else:
                response_data = {"complaint_id": complaint_id, "found": False, "message": "Không tìm thấy khiếu nại trong cơ sở dữ liệu."}
            return [types.TextContent(type="text", text=json.dumps(response_data, ensure_ascii=False))]

        else:
            raise ValueError(f"Tool không tồn tại: {name}")

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())