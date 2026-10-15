from dataclasses import dataclass
from typing import Any 

@dataclass
class ToolCall:
    name: str
    arguments: dict[str,Any]

@dataclass
class AgentResult:
    answer: str
    steps: int 
    success: bool