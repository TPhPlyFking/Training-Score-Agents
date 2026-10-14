import json 
import os

def ask_agent_dummy(question: str) -> str:
    question_lower = question.lower()
    if any(word in question_lower for word in ["lịch", "thực đơn", "bãi gửi xe", "học phí"]):
        return "Tôi không cso thông tin. Tôi chỉ giải đáp về quy chế điểm rèn luyện."
    return "Dựa vào tài liệu, sinh viên sẽ được điểm cộng/trừ điểm theo quy định."

def run_evaluation():
    test_file_path = "tests/testset.json" if os.path.exists("tests/testset.json") else ("testset.jsonl")

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

        agent_answer = ask_agent_dummy(question)

        if not is_answerable:
            total_unanswerable += 1
            refusal_keywords = ["Không có thông tin", "chỉ giải đáp", "chỉ trả lời", "không hỗ trợ"]

            if any(kw in agent_answer.lower() for kw in refusal_keywords ):
                correct_refusals += 1
                print("✅ ĐÁNH GIÁ: Đạt (TỪ CHỐI ĐÚNG).")
            else:
                print("❌ ĐÁNH GIÁ: Không đạt (BỊ LỪA - Trả lời bừa).")
        
        else:
            print(f"   - Đáp án chuẩn: {expected}")
            print(f"   - AI trả lời: {agent_answer}")
            print("⏳ ĐÁNH GIÁ: Đang chờ tích hợp LLM-as-a-Judge để chấm điểm ngữ nghĩa.")
        
        print("-" * 60)

    print("\n=== BÁO CÁO KẾT QUẢ (REPORT) ===")
    if total_unanswerable > 0:
        refusal_rate = (correct_refusals / total_unanswerable) * 100
        print(f"🎯 Tỷ lệ từ chối đúng (Correct Refusal Rate): {correct_refusals}/{total_unanswerable} ({refusal_rate:.1f}%)")
    else:
        print("🎯 Không có câu hỏi bẫy nào trong đề thi.")
    print("🎯 Độ trung thực (Faithfulness): Sắp hoàn thiện.")

if __name__ == "__main__":
    run_evaluation()