import os
import json

DB_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "complaints.jsonl")

def _ensure_db_exists():
    """Đảm bảo thư mục và tệp jsonl tồn tại."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            pass

def load() -> dict:
    """Đọc toàn bộ dữ liệu khiếu nại từ tệp JSONL vào RAM dưới dạng dict."""
    _ensure_db_exists()
    complaints = {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                complaints[item["complaint_id"]] = item
    return complaints

def save(complaint_id: str, data: dict) -> dict:
    """Ghi thêm hoặc cập nhật một khiếu nại vào tệp JSONL."""
    _ensure_db_exists()
    complaints = load()
    
    full_record = {"complaint_id": complaint_id, **data}
    complaints[complaint_id] = full_record
    with open(DB_FILE, "w", encoding="utf-8") as f:
        for item in complaints.values():
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    return full_record

def get(complaint_id: str) -> dict | None:
    """Lấy thông tin một khiếu nại theo ID từ file JSONL."""
    complaints = load()
    return complaints.get(complaint_id)