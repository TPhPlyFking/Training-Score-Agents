import logging
import os
import re
import time
from typing import Any
from groq import Groq
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

logger = logging.getLogger(__name__)

class APIHandler:
    def __init__(self,model: str ="qwen/qwen3.8-27b",
                 timeout: float =30.0, max_retries: int=2):
        self.model = model
        self.max_retries = max(0,max_retries)
        api_key = os.getenv("GROQ_API_KEY")
        self.last_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

        if not api_key:
            raise ValueError("Không tìm thấy GROQ_API_KEY")
        
        self.client= Groq(
            api_key = api_key,
            timeout = timeout,
            max_retries = 0,
        )

    def generate(self, messages: list[dict[str,Any]],)->str:
        if not messages:
            raise ValueError("Danh sách Message đang trống")
        
        for attempt in range(self.max_retries +1):
            try:
                response = self.client.chat.completions.create(
                    model = self.model,
                    messages = messages,                    
                )
                content = response.choices[0].message.content

                if not content:
                    raise RuntimeError("Mô hình trả về nội dung rỗng")
                usage = response.usage
                self.last_usage = {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                }
                return content
            
            except Exception as error:
                logger.warning(
                    "Gọi Groq API thất bại (lần %s/%s): %s",
                    attempt +1,
                    self.max_retries+1,
                    error,
                )
                # lỗi 413 = prompt quá dài, gửi lại y nguyên cũng lỗi -> dừng luôn, không thử lại
                if getattr(error, "status_code", None) == 413:
                    raise RuntimeError("Prompt quá dài (lỗi 413), cần giảm số chunk hoặc độ dài chunk")
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Không thể gọi Groq API sau "
                        f"{self.max_retries +1} lần thử"
                    )
                # lỗi 429 = vượt giới hạn token/phút. Groq ghi rõ "try again in 47.28s"
                # -> chờ đúng số giây đó. Không có thì chờ 1, 2, 4... giây như cũ.
                wait = 2 ** attempt
                match = re.search(r"try again in\s*([\d.]+)(ms|s)", str(error))
                if match:
                    wait = float(match.group(1)) / (1000 if match.group(2) == "ms" else 1) + 1
                time.sleep(wait)
        raise RuntimeError("Không nhận diện được phản hồi từ Groq API")