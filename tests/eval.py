import json 
import os
import re
import sys
from dotenv import load_dotenv
import asyncio
import time
import csv
from datetime import datetime
from pathlib import Path

from src.utils.api_handler import APIHandler
from src.mcp.mcp_client import MCPClient
from src.agent.agent__loop import AgentLoop
from src.rag.hybrid_search import (hybrid_search,build_bm25_index,embed_text)
from src.rag.doc_store import DocumentStore
from src.rag.document_parser import load_all_documents   # đọc các tài liệu trong DOCUMENTS
load_dotenv()

path = Path(__file__).resolve().parents[1]

# chọn chế độ truy vấn khi chạy:  python -m tests.eval dense   (không ghi gì thì là hybrid)
MODE = sys.argv[1] if len(sys.argv) > 1 else "hybrid"


def judge_faithfulness(question: str, found_chunks, answer: str):
    """Nhờ LLM đếm xem bao nhiêu ý trong câu trả lời có căn cứ trong tài liệu tìm được.
    faithfulness = số ý có căn cứ / tổng số ý  (1.0 = bám tài liệu hoàn toàn, 0 = bịa hoàn toàn)"""
    judge_prompt = (path / "tests" / "prompts" / "judge_faithfulness.txt").read_text(encoding="utf-8")
    context = "\n\n".join(f"[doc_id: {chunk.doc_id}] {chunk.metadata['title']}\n{chunk.content}" for chunk in found_chunks)
    messages = [
        {"role": "system", "content": judge_prompt},
        {"role": "user", "content": f"CÂU HỎI:\n{question}\n\nTÀI LIỆU:\n{context}\n\nCÂU TRẢ LỜI:\n{answer}"},
    ]
    try:
        raw = APIHandler().generate(messages)
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))   # lấy phần JSON trong câu trả lời của LLM
        if data["total_claims"] == 0:
            return 1.0
        return data["supported_claims"] / data["total_claims"]
    except Exception as error:
        print(f"   (Chấm faithfulness bị lỗi: {error})")
        return None

async def ask_agent_real(question: str, chunks, bm25_index, embeddings) -> str:
    api_handler = APIHandler()
    server_path = path / "src" / "mcp" / "mcp_server.py"
    mcp_client = MCPClient(server_path)
    found_chunks = []   # giữ lại các chunk tìm được để chấm faithfulness
    
    async def search_rag(query: str):
        results = hybrid_search(
            query=query,
            chunks=chunks,
            bm25_index=bm25_index,
            embeddings=embeddings,
            top_k=5,
            mode=MODE,      # dense hoặc hybrid
        )
        found_chunks.extend(chunk for chunk, hybrid, bm25, vector in results)   # 
        return [
            {
                "doc_id": chunk.doc_id,
                "title": chunk.metadata.get(
                    "title", "Quy định đánh giá rèn luyện"
                ),
                "content": chunk.content,
            }
            for chunk, hybrid, bm25, vector in results
        ]

    try:
        await mcp_client.connect()

        agent = AgentLoop(
            api_handler=api_handler,
            mcp_client=mcp_client,
            rag_search=search_rag,
        )

        result = await agent.run(question)
        return result, found_chunks  

    finally:
        await mcp_client.close()

def run_evaluation():
    test_file_path = "tests/testset.jsonl" if os.path.exists("tests/testset.jsonl") else "testset.jsonl"

    try:
        with open(test_file_path, "r", encoding="utf-8") as f:
            test_data = [json.loads(line) for line in f]
    except FileNotFoundError:
        print(f"Lỗi không tìm thấy files {test_file_path}. Hãy kiêm tra lại đường dẫn")
        return
    store = DocumentStore()
    chunks = load_all_documents()  
    
    for chunk in chunks:
        chunk.embedding = embed_text(chunk.content)
        store.add_chunk(chunk)
    chunks = list(store.chunks.values())
    bm25_index = build_bm25_index(chunks)
    embeddings = [chunk.embedding for chunk in chunks]
    total_questions = len(test_data)
    total_unanswerable = 0
    correct_refusals = 0
    faithfulness_scores = []   #
    total_answerable = 0       
    false_refusals = 0        
    total_version = 0          # số câu có "expected_doc" (cần trả lời đúng phiên bản)
    correct_version = 0        # số câu agent ghi đúng doc_id của phiên bản cần dùng
    rows = []                 
    
    refusal_keywords = ["không có thông tin", "chỉ giải đáp", "chỉ trả lời", "không hỗ trợ",
                        "không đủ dữ liệu", "không đủ thông tin"]

    print(f"Bắt ĐẦU CHẤM ĐIỂM {total_questions} CÂU HỎI\n")

    for i, item in enumerate(test_data, 1):
        question = item["question"]
        expected = item["expected_answer"]
        is_answerable = item["is_answerable"]

        print(f"Câu {i}: {question}")
        
        # Dùng asyncio.run() để chạy hàm bất đồng bộ
        result, found_chunks = asyncio.run(ask_agent_real(question, chunks, bm25_index, embeddings))
        agent_answer = result.answer

        if not result.success:
            print(f"⚠️ ĐÁNH GIÁ: Lỗi khi chạy agent ({agent_answer}), không tính điểm câu này.")
            rows.append({"cau": i, "question": question, "is_answerable": is_answerable,
                         "status": "ERROR", "faithfulness": None, "answer": agent_answer})
            print("-" * 60)
            time.sleep(20)
            continue
        
        refused = any(kw in agent_answer.lower() for kw in refusal_keywords)
        faithfulness = None

        if not is_answerable:
            total_unanswerable += 1
            if refused:
                correct_refusals += 1
                status = "CORRECT_REFUSAL"
                print("✅ ĐÁNH GIÁ: Đạt (TỪ CHỐI ĐÚNG).")
            else:
                status = "HALLUCINATED"
                print("❌ ĐÁNH GIÁ: Không đạt (BỊ LỪA - Trả lời bừa).")
        else:
            total_answerable += 1
            print(f"   - Đáp án chuẩn: {expected}")
            print(f"   - AI trả lời: {agent_answer}")
            if refused:
                # câu trả lời được mà agent lại từ chối -> từ chối nhầm, không chấm faithfulness
                false_refusals += 1
                status = "FALSE_REFUSAL"
                print("❌ ĐÁNH GIÁ: Từ chối nhầm (quy chế có đáp án nhưng agent không trả lời).")
            else:
                status = "ANSWERED"
                # kiểm tra agent có dùng đúng phiên bản quy định 
                if item.get("expected_doc"):
                    total_version += 1
                    if item["expected_doc"] in agent_answer:
                        correct_version += 1
                    else:
                        status = "WRONG_VERSION"
                faithfulness = judge_faithfulness(question, found_chunks, agent_answer)
                print(f"   - Faithfulness: {faithfulness}")
                if faithfulness is not None:
                    faithfulness_scores.append(faithfulness)

        rows.append({"cau": i, "question": question, "is_answerable": is_answerable,
                     "status": status, "faithfulness": faithfulness, "answer": agent_answer})   # 
        
        print("-" * 60)
        time.sleep(20)  
    print("\n=== BÁO CÁO KẾT QUẢ (REPORT) ===")
    if total_unanswerable > 0:
        refusal_rate = (correct_refusals / total_unanswerable) * 100
        print(f"🎯 Tỷ lệ từ chối đúng (Correct Refusal Rate): {correct_refusals}/{total_unanswerable} ({refusal_rate:.1f}%)")

    if faithfulness_scores:
        average = sum(faithfulness_scores) / len(faithfulness_scores)
        print(f"🎯 Độ trung thực (Faithfulness) trung bình: {average:.2f} (trên {len(faithfulness_scores)} câu)")

    if total_answerable > 0:
        print(f"🎯 Tỷ lệ từ chối nhầm (False Refusal Rate): {false_refusals}/{total_answerable} "
              f"({false_refusals / total_answerable * 100:.1f}%)")
    if total_version > 0:
        print(f"🎯 Đúng phiên bản (Version Accuracy): {correct_version}/{total_version} "
              f"({correct_version / total_version * 100:.1f}%)")
    print(f"🎯 Chế độ truy vấn: {MODE}")

    csv_path = path / "logs" / f"eval_{MODE}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    csv_path.parent.mkdir(exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cau", "question", "is_answerable", "status", "faithfulness", "answer"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Đã lưu kết quả từng câu: {csv_path}")

if __name__ == "__main__":
    run_evaluation()
