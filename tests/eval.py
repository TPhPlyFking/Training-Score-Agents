import json 
import os
from dotenv import load_dotenv
import asyncio
from src.utils.api_handler import APIHandler
from src.mcp.mcp_client import MCPClient
from src.agent.agent_loop import AgentLoop
from src.rag.hybrid_search import hybrid_search

load_dotenv()

async def ask_agent_real(question: str) -> str:
    api_handler = APIHandler()
    mcp_client = MCPClient("src/mcp/mcp_server.py")
    
    await mcp_client.start()
    
    agent = AgentLoop(
        api_handler=api_handler, 
        mcp_client=mcp_client,
        rag_search=hybrid_search 
    )
    
    result = await agent.run(question)
    
    await mcp_client.stop()
    
    return result.answer

def run_evaluation():
    test_file_path = "tests/testset.jsonl" if os.path.exists("tests/testset.jsonl") else "testset.jsonl"

    try:
        with open(test_file_path, "r", encoding="utf-8") as f:
            test_data = [json.loads(line) for line in f]
    except FileNotFoundError:
        print(f"Lỗi không tìm thấy files {test_file_path}. Hãy kiêm tra lại đường dẫn")
        return

    total_questions = len(test_data)
    total_unanswerable = 0
    correct_refusals = 0

    print(f"Bắt ĐẦU CHẤM ĐIỂM{total_questions} CÂU HỎI\n")

    for i, item in enumerate(test_data, 1):
        question = item["question"]
        expected = item["expected_answer"]
        is_answerable = item["is_answerable"]

        print(f"Câu {i}: {question}")
        
        # Dùng asyncio.run() để chạy hàm bất đồng bộ
        agent_answer = asyncio.run(ask_agent_real(question))
        
        if not is_answerable:
            total_unanswerable += 1
            # Các từ khóa chứng tỏ AI đã từ chối đúng
            refusal_keywords = ["không có thông tin", "chỉ giải đáp", "chỉ trả lời", "không hỗ trợ", "không thể"]
            
            if any(kw in agent_answer.lower() for kw in refusal_keywords):
                correct_refusals += 1
                print("✅ ĐÁNH GIÁ: Đạt (TỪ CHỐI ĐÚNG).")
            else:
                print("❌ ĐÁNH GIÁ: Không đạt (BỊ LỪA - Trả lời bừa).")
        else:
            print(f"   - Đáp án chuẩn: {expected}")
            print(f"   - AI trả lời: {agent_answer}")
        
        print("-" * 60)

    print("\n=== BÁO CÁO KẾT QUẢ (REPORT) ===")
    if total_unanswerable > 0:
        refusal_rate = (correct_refusals / total_unanswerable) * 100
        print(f"🎯 Tỷ lệ từ chối đúng (Correct Refusal Rate): {correct_refusals}/{total_unanswerable} ({refusal_rate:.1f}%)")

if __name__ == "__main__":
    run_evaluation()