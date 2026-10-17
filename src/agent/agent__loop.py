import json
import asyncio
import logging
from pathlib import Path
from typing import Any, Callable
from datetime import datetime

from src.agent.tool_schemas import AgentResult
from src.mcp.mcp_client import MCPClient
from src.utils.api_handler import APIHandler

logger = logging.getLogger(__name__)
MAX_STEPS = 8
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
class AgentLoop:
    def __init__(self, api_handler: APIHandler, mcp_client:MCPClient, 
                 rag_search: Callable | None = None, max_steps: int = MAX_STEPS):
        self.api_handler = api_handler
        self.mcp_client = mcp_client
        self.rag_search = rag_search
        self.max_steps = max(1,max_steps)

        prompt_path = Path(__file__).with_name("prompts.txt")
        self.system_prompt = prompt_path.read_text(encoding = "utf-8")
    async def _search_rag(self, question: str) -> list[Any]:
        if self.rag_search is None:
            return []
        try:
            result = self.rag_search(question)
            if hasattr(result, "__await__"):
                result = await result
            return result or []
        except Exception:
            logger.exception("Rag search thất bại")
            return []
        
    @staticmethod
    def _parse_json(text: str) -> dict[str,Any]:
        start = text.find("{")
        if start == -1:
            raise ValueError ("Phản hồi LLM không chứa JSON")

        decoder = json.JSONDecoder()
        try:
            result, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            candidate = text[start:].strip()
            missing = candidate.count("{") - candidate.count("}")

            if missing <= 0:
                raise ValueError("JSON do LLM trả về không hợp lệ")

            candidate += "}" * missing
            result = json.loads(candidate)

        if not isinstance(result,dict):
            raise ValueError("JSON phải là một object")
        return result

    @staticmethod
    def _format_documents(documents: list[Any]) -> str:
        formatted = []
        for document in documents:
            if isinstance(document,dict):
                doc_id = document.get("doc_id", "unknown")
                content = document.get("content", document.get("text",""),)
                title = document.get("title","")
            else:
                doc_id = getattr(document, "doc_id", "unknown")
                content = getattr(document, "content", getattr(document,"text",""),)
                title = getattr(document, "title","")
            
            if content:
                formatted.append(
                    f"[doc_id: {doc_id}]\n"
                    f"Tiêu đề: {title}\n"
                    f"Nội dung: {content}"
                )
        return "\n\n".join(formatted)

    async def _ask_llm(self, messages:list[dict[str,Any]]) -> str:
        return await asyncio.to_thread(
            self.api_handler.generate,
            messages,
        )
    def _write_usage_log(self, steps:int, calls: int, prompt_tokens:int, completion_tokens: int,
                         max_prompt: int, tool_calls: list[dict[str,Any]], question: str = "") -> None:
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        log_dir.mkdir(parents=True,exist_ok=True)

        record = {
            "timestamp":datetime.now().astimezone().isoformat(),
            "question": question,   # ghi kèm câu hỏi để biết USAGE của câu nào
            "steps" : steps,
            "tool_calls": tool_calls,
            "USAGE":{
                "calls":calls,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "max_prompt": max_prompt,
            },
        }
        log_path= log_dir / f"run_{RUN_ID}.jsonl"   # trước đây mọi lần chạy ghi chung agent_runs.jsonl
        with log_path.open("a",encoding = "utf-8") as file:
            file.write(
                json.dumps(record,ensure_ascii=False,default = str) + "\n"
            )
    async def run (self,question: str) -> AgentResult:
        if not question or not question.strip():
            return AgentResult(
                answer = "Vui lòng nhập câu hỏi",
                steps = 0,
                success = False,
            )
        calls = 0
        prompt_tokens = 0
        completion_tokens =0
        max_prompt = 0
        tool_calls : list[dict[str,Any]] = []

        documents = await self._search_rag(question)
        document_context = self._format_documents(documents)

        tool_schemas = self.mcp_client.get_tool_schemas()

        system_message = (
            self.system_prompt
            + "\n\nTài liệu RAG:\n"
            + ( 
                document_context
                if document_context
                else "Chưa tìm thấy RAG phù hợp"
            )
            + "\n\nDanh sách tools MCP:\n"
            + json.dumps(
                tool_schemas,
                ensure_ascii = False,
                default = str,
            )
            + """
Hãy trả lời bằng đúng một JSON object, không thêm Markdown.

Nếu cần gọi tool:
{
  "action": "tool",
  "tool_name": "tên tool trong danh sách",
  "arguments": {}
}

Nếu đã đủ thông tin để trả lời:
{
  "action": "final",
  "answer": "câu trả lời cuối cùng"
}

Không tự bịa tên tool hoặc kết quả tool.
Chỉ sử dụng kết quả tool sau khi đã nhận được.
"""
        )
        messages : list[dict[str,Any]] = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": question},
        ]
        for step in range (1,self.max_steps +1):
            try:
                raw_response = await self._ask_llm(messages)
                usage = self.api_handler.last_usage
                calls +=1
                prompt_tokens += usage ["prompt_tokens"]
                completion_tokens += usage ["completion_tokens"]
                max_prompt = max(max_prompt, usage ["prompt_tokens"])
                decision = self._parse_json(raw_response)

            except ValueError as error:
                # LLM trả lời sai định dạng JSON: không dừng cả run nữa (đề mục 2.6 "parse action an toàn"),
                # mà báo lỗi cho LLM biết rồi cho thử lại ở bước sau. MAX_STEPS vẫn chặn lặp vô hạn.
                logger.warning("Phản hồi LLM sai định dạng JSON: %s", error)
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({
                    "role": "user",
                    "content": f"Error: {error}. Hãy trả lời lại bằng đúng một JSON object theo định dạng đã cho.",
                })
                continue

            except Exception as error:
                logger.exception("Không xử lí được phản hồi LLM")

                return AgentResult(
                    answer = f"Agent không xử lí được phản hồi : {error}",
                    steps = step,
                    success = False,
                )
            action = decision.get("action")

            if action == "final":
                answer = decision.get("answer")
                if not isinstance(answer,str) or not answer.strip():
                    return AgentResult(
                        answer = "LLM không cung cấp câu trả lời hợp lệ",
                        steps = step,
                        success = False,
                    )

                self._write_usage_log(
                    steps = step,
                    calls = calls,
                    prompt_tokens= prompt_tokens,
                    completion_tokens = completion_tokens,
                    max_prompt = max_prompt,
                    tool_calls = tool_calls,
                    question = question,
                )
                return AgentResult(
                    answer = answer,
                    steps = step,
                    success = True,
                )
            if action != "tool":
                messages.append({
                    "role": "user",
                    "content":(
                        'Error: action phải là "tool" hoặc "final"'
                        "Hãy trả về JSON đúng định dạng"
                    ),
                })
                continue
            tool_name = decision.get("tool_name")
            arguments = decision.get("arguments",{})
            if not isinstance(tool_name,str) or not isinstance(arguments,dict):
                messages.append({
                    "role": "user",
                    "content":(
                        "Error: tool_name phỉa là chuỗi và "
                        "arguments phải là JSON object"
                    )
                })
                continue

            tool_result = await self.mcp_client.call_tool(
                tool_name,
                arguments,
            )

            tool_calls.append({
                "step":step,
                "tool_name": tool_name,
                "arguments": arguments,
                "result": tool_result,
            })
            if tool_name == "create_complaint":
                try:
                    if isinstance(tool_result,str):
                        create_data = json.loads(tool_result)
                    elif isinstance(tool_result, dict):
                        create_data = tool_result
                    else:
                        create_data = {}

                    complaint_id = create_data.get("complaint_id")

                    if create_data.get("success") is True and complaint_id:
                        verification_result = await self.mcp_client.call_tool(
                            "get_complaint",
                            {"complaint_id": str(complaint_id)},
                        )

                        # Phân tích kết quả xác minh.
                        if isinstance(verification_result, str):
                            verification_data = json.loads(verification_result)
                        elif isinstance(verification_result, dict):
                            verification_data = verification_result
                        else:
                            verification_data = {}

                        verified = verification_data.get("found") is True

                        logger.info(
                            "Agent verify complaint_id=%s found=%s result=%s",
                            complaint_id,
                            verified,
                            verification_result,
                        )

                        tool_result = (
                            f"Kết quả tạo khiếu nại: {tool_result}\n"
                            f"Kết quả xác minh: {verification_result}\n"
                            f"Xác minh thành công: {verified}"
                        )
                    else:
                        tool_result = (
                            f"Kết quả tạo khiếu nại: {tool_result}\n"
                            "Không thể xác minh vì kết quả tạo không có "
                            "success=true và complaint_id hợp lệ."
                        )

                except (json.JSONDecodeError, TypeError, ValueError) as error:
                    logger.exception("Không phân tích được kết quả khiếu nại")
                    tool_result = (
                        f"Kết quả tạo/xác minh khiếu nại gặp lỗi: {error}\n"
                        f"Kết quả ban đầu: {tool_result}"
                    )


            logger.info(
                "Agent step=%s tool=%s arguments=%s result=%s",
                step,
                tool_name,
                arguments,
                tool_result,
            )

            messages.append({
                "role": "assistant",
                "content": json.dumps(
                    decision,
                    ensure_ascii = False,
                ),
            })
            messages.append({
                "role" : "user",
                "content" : (
                    f"Kết quả tool: '{tool_name}':\n{tool_result}\n\n"
                    "Hãy đánh giá kết quả. Nếu có lỗi, hãy sửa "
                    "tham số khi có đủ căn cứ. Nếu đã đủ thông tin, "
                    "hãy trả lời cuối cùng theo định dang JSON"
                ),
            })

        self._write_usage_log(
            steps = self.max_steps,
            calls = calls,
            prompt_tokens = prompt_tokens,
            completion_tokens = completion_tokens,
            max_prompt = max_prompt,
            tool_calls = tool_calls,
                    question = question,
        )
        return AgentResult(
            answer= (
                f"Agent đã đạt giới hạn: {self.max_steps} bước "
               "mà chưa hoàn thành yêu cầu"
            ),
            steps = self.max_steps,
            success=False
        )