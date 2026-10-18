# Trợ lý điểm rèn luyện và khiếu nại 

Agent trả lời câu hỏi về Quy định đánh giá kết quả rèn luyện của HCMUTE (có trích dẫn doc_id),
phân biệt 2 phiên bản quy định (bản 2021 và bản sửa đổi 2024, mặc định dùng bản mới nhất),
tính điểm rèn luyện, và tạo khiếu nại rồi tự kiểm tra lại khiếu nại đã được lưu.

Yêu cầu: **Python 3.11 trở lên**. Nhóm đã chạy thử trên Windows (Python 3.11) và Linux (Python 3.14).
Cần có mạng để cài thư viện, tải model embedding (lần đầu) và gọi Groq API.

## Cách chạy

### Windows, không cần cài `make` (dùng `make.cmd` có sẵn trong repo)

Mở **Command Prompt (cmd)** tại thư mục project và gõ đúng lệnh như Linux:

```bat
make setup && make demo
```

- `make setup`: tạo `.venv`, cài thư viện, tạo file `.env`. Mở `.env`, điền `GROQ_API_KEY` rồi chạy `make demo`.
- Hỏi câu tùy ý: `make demo "câu hỏi"`. Chấm điểm: `make eval`.
- Nếu dùng **PowerShell** thì thêm `.\` phía trước: `.\make setup`, rồi `.\make demo`.

### Windows, cách khác: `run.bat`

Mở PowerShell tại thư mục project:

```powershell
.\run.bat
```

1. Lần chạy đầu: tạo môi trường ảo `.venv`, cài thư viện trong `requirements.txt`, tạo file `.env` rồi **dừng lại**.
2. Mở file `.env`, điền `GROQ_API_KEY`, lưu lại.
3. Chạy lại `.\run.bat` → chạy demo (2 câu hỏi mẫu: tra cứu quy định và tạo khiếu nại).

Hỏi một câu tùy ý:

```powershell
.\run.bat "Sinh viên bị cảnh cáo thì xếp loại tối đa là gì?"
```

Chấm điểm testset:

```powershell
.\run.bat eval
```

> Không bấm đúp vào `run.bat`: cửa sổ sẽ tự đóng trước khi kịp đọc thông báo. Hãy chạy từ PowerShell.

### Linux / macOS / Windows có `make`

```bash
make setup && make demo
```

- `make setup`: tạo `.venv`, cài thư viện, tạo file `.env` từ `.env.example`.
- Trước khi chạy `make demo`, mở file `.env` và điền `GROQ_API_KEY`.
- Hỏi câu tùy ý: `.venv/bin/python demo.py "câu hỏi"` (Windows: `.venv\Scripts\python demo.py "câu hỏi"`).

### Lưu ý

- Lần chạy đầu tải model embedding `paraphrase-multilingual-MiniLM-L12-v2` (khoảng vài trăm MB), mất vài phút.
- Nếu gặp lỗi `HTTP Error 429` từ huggingface.co (model đã tải xong trước đó): đặt biến `HF_HUB_OFFLINE=1` rồi chạy lại
  (PowerShell: `$env:HF_HUB_OFFLINE=1`, Linux/macOS: `export HF_HUB_OFFLINE=1`).
- Nếu mạng chậm khi cài thư viện: `.venv\Scripts\python -m pip install -r requirements.txt --timeout 120 --retries 10`.

## Chấm điểm (make eval / run.bat eval)

```bash
make eval          # Linux/macOS
.\run.bat eval     # Windows
```

Chạy testset `tests/testset.jsonl` (21 câu, 7 câu phải từ chối) với 2 chế độ truy vấn `hybrid` và `dense`.
In ra: tỉ lệ từ chối đúng, tỉ lệ từ chối nhầm, faithfulness trung bình, tỉ lệ đúng phiên bản
(câu có trường `expected_doc`: câu trả lời phải ghi đúng doc_id của phiên bản cần dùng).
Kết quả từng câu lưu ở `logs/eval_<chế độ>_<thời gian>.csv`; USAGE (số lần gọi LLM, token) từng câu lưu ở `logs/run_<thời gian>.jsonl`.

Mỗi chế độ mất khoảng 8–10 phút vì nghỉ 20 giây giữa các câu (giới hạn token/phút của Groq).

Kiểm tra phần cắt chunk (in số chunk và độ dài chunk dài nhất, không cần API key):

```bash
python -m src.rag.document_parser
```

Xem nhanh dense và hybrid tìm ra đoạn nào (không gọi LLM, không cần API key):

```bash
python -m src.rag.hybrid_search
```

## Cấu trúc thư mục

| Thư mục / file | Nội dung |
|---|---|
| `run.bat`, `Makefile` | Lệnh cài đặt và chạy (Windows / Linux, macOS) |
| `demo.py` | Chạy demo: 2 câu mẫu hoặc 1 câu tùy ý |
| `data/` | Quy định bản 2021 `HTRL.md` (DOC0007) và bản sửa đổi 2024 `HTRL_2024.md` (DOC0008, bản giả lập GV cung cấp để kiểm tra phân biệt phiên bản); khiếu nại được lưu ở `data/complaints.jsonl` |
| `src/rag/` | Cắt chunk, lưu trữ, tìm kiếm dense và hybrid (BM25 + vector, lấy 5 đoạn) |
| `src/mcp/` | MCP server (5 tool) và MCP client |
| `src/agent/` | Vòng lặp agent, prompt (`prompts.txt`), schema tool |
| `src/utils/` | Gọi Groq API (retry, timeout), lưu khiếu nại (`db.py` → `data/complaints.jsonl`) |
| `tests/` | Testset, `eval.py`, prompt chấm faithfulness |
| `logs/` | Log các lần chạy |
| `docs/` | Báo cáo, khai báo dùng AI |

## Thành viên

| Thành viên | Phụ trách |
|---|---|
| TV1 – Trần Phát | Dữ liệu, chunking, hybrid search, testset, eval, README, run.bat, Makefile |
| TV2 – Quang Thành | MCP server, các tool, lưu trữ khiếu nại |
| TV3 – Trí Dũng | Agent loop, MCP client, gọi API, prompt, log USAGE |
