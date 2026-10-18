# Khai báo sử dụng AI

Nhóm có dùng công cụ AI để hỗ trợ viết và sửa code. Mọi đoạn code do AI gợi ý đều được thành viên phụ trách
đọc lại, chạy thử và giải thích được. Bảng dưới liệt kê công cụ, phần áp dụng, yêu cầu chính và đoạn code do AI sinh.

## TV1 – Dữ liệu & Tra cứu

| Công cụ | Phần áp dụng | Yêu cầu chính (prompt) | Code do AI sinh / sửa |
|---|---|---|---|
| Claude (Anthropic) | Review toàn bộ phần RAG và eval | "Review code phần của mình, chỉ ra lỗi và giải thích kiến thức W3–W5" | Không sinh code, chỉ chỉ ra lỗi |
| Claude | `src/rag/doc_store.py` | "Sửa đúng chỗ sai, không tối ưu" | Sửa 3 hàm duyệt dict như list (`delete`, `get_chunk`, `get_chunk_by_doc`) |
| Claude | `src/rag/document_parser.py` | "Điều 19 quá dài, sửa cách chia chunk" | Tách bảng Phụ lục khỏi Điều 19; hàm `split_long_chunk` chia chunk dài hơn 500 ký tự; sửa đường dẫn file; hàm `load_all_documents` (danh sách tài liệu) |
| Claude | `src/rag/hybrid_search.py` | "Thêm chế độ dense, đề yêu cầu ≥ 2 chế độ" | Tham số `mode`; đổi `print` ra stderr |
| Claude | `tests/eval.py` | "Sửa lỗi lỗi API bị tính là từ chối đúng, thêm faithfulness" | Bỏ qua câu lỗi API; hàm `judge_faithfulness` (LLM-as-a-judge); đếm từ chối nhầm; ghi CSV; chọn chế độ truy vấn |
| Claude | `tests/testset.jsonl`, `tests/prompts/judge_faithfulness.txt` | "Kiểm tra đáp án testset, thêm câu tầng (b)" | Sửa đáp án câu 1; thêm 3 câu tính toán / thiếu dữ liệu; prompt chấm faithfulness |
| Claude | `data/HTRL_2024.md`, `src/rag/document_parser.py`, `tests/eval.py`, `tests/testset.jsonl`, `README.md` | "Thầy yêu cầu thêm phiên bản mới hơn của quy định, so sánh 2 bản và sửa code" | So sánh 2 bản để liệt kê chỗ khác nhau; thêm dòng `DOC0008` và ghi năm áp dụng vào tiêu đề; thêm chỉ số đúng phiên bản (`expected_doc`) trong eval; sửa đáp án 5 câu theo bản 2024 và thêm 6 câu về phiên bản |

## TV2 – MCP & Nghiệp vụ

| Công cụ | Phần áp dụng | Yêu cầu chính (prompt) | Code do AI sinh / sửa |
|---|---|---|---|
| Gemini | `src/mcp/mcp_server.py`, `src/utils/db.py` | "Hỏi về thứ tự thực hiện và form của code", "Tối ưu tools", "Nhờ AI định nghĩa các biến đầu vào" | Danh sách `TOOLS[]`, hàm `call_tool()`, hàm `_ensure_db_exists()` |
| Claude (qua TV1, lúc ghép hệ thống) | `src/mcp/mcp_server.py` | "Nối tool với RAG và db.py" | `search_regulations` gọi hybrid search thật; `create_complaint` / `get_complaint` dùng `db.py` thay cho dict trong RAM; thêm thư mục gốc vào `sys.path` |
| Claude (qua TV1, lúc thêm bản 2024) | `src/mcp/mcp_server.py` | "Tool tính điểm còn dùng mốc của bản 2021" | Đổi mốc xếp loại (92/82/68) và khung điểm tối đa từng nội dung theo bản 2024; kết quả `search_regulations` in kèm tiêu đề (có năm áp dụng) |

## TV3 – Agent & Điều phối

| Công cụ | Phần áp dụng | Yêu cầu chính (prompt) | Code do AI sinh / sửa |
|---|---|---|---|
| ChatGPT | `src/agent/agent__loop.py` | "Hỗ trợ xử lý lỗi khi LLM trả về JSON không hợp lệ" | Bắt `ValueError`, yêu cầu LLM trả lại JSON đúng định dạng; ghi log quá trình chạy vào `logs/run_<thời gian>.jsonl`. |
| ChatGPT | `src/agent/agent__loop.py` | "Hỗ trợ điều phối tool và xác minh kết quả tạo khiếu nại" | Sau khi gọi `create_complaint`, gọi `get_complaint` để xác minh kết quả tạo khiếu nại. |
| ChatGPT | `src/agent/agent__loop.py` | "Hỗ trợ ghi nhận quá trình sử dụng tool và token" | Ghi log câu hỏi, số bước, tool calls và token usage vào file JSONL. |
| ChatGPT | `src/utils/api_handler.py` | "Hỗ trợ xử lý lỗi 429 và 413 khi gọi Groq API" | Phân tích lỗi giới hạn API 429 và prompt quá dài 413; điều chỉnh cơ chế retry và thông báo lỗi. |
| Claude (qua TV1, lúc ghép hệ thống) | `src/agent/agent__loop.py`, `src/utils/api_handler.py`, `src/agent/prompts.txt` | "Sửa lỗi LLM không trả JSON làm dừng run", "Sửa retry khi gặp lỗi 429, 413 của Groq", "Viết lại prompt cho khớp với eval" | Sửa lại đoạn `except ValueError` để không dừng run; đặt tên file log theo thời gian chạy; đọc số giây chờ trong thông báo lỗi 429; viết lại `prompts.txt` (câu từ chối cố định, trường hợp thiếu dữ liệu, quy tắc dùng tool). |
| Claude (qua TV1, lúc thêm bản 2024) | `src/agent/prompts.txt` | "Agent phải chọn bản quy định mới nhất" | Thêm quy tắc: mặc định dùng phiên bản mới nhất, chỉ dùng bản cũ khi người dùng hỏi rõ; nói rõ đang dùng phiên bản nào |

## Phần nhóm tự viết

Thiết kế đề tài, cấu trúc repo, phần lớn code ban đầu của RAG, MCP server, agent loop, MCP client; chạy thử và đối chiếu kết quả; viết báo cáo.