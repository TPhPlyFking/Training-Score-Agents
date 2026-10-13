import sys
from pathlib import Path 
from typing import Any
from mcp import Client, StdioServerParameters

class MCPClient:
    def __init__(self, server_script: str |Path):
        self.server_script = Path(server_script).resolve()
        self.client = None
        self._context = None
        self.tools : list[Any] = []

    async def connect(self)->None:
        if not self.server_script.exists():
            raise FileNotFoundError(
                f"Không tìm thấy MCP Server: {self.server_script}"
            )
        server = StdioServerParameters(
            command = sys.executable,
            args=[str(self.server_script)],
            cwd = str(self.server_script.parent),
        )
        context = Client(server)
        try:
            client = await context.__aenter__()
            self._context = context
            self.client = client

            response = await client.list_tools()
            self.tools = response.tools

        except Exception:
            if self._context is not None:
                await self.close()
            else:
                await context.__aexit__(None, None, None)
            raise
    def get_tool_schemas(self) ->list[dict[str,Any]]:
        schemas = []
        for tool in self.tools:
            schemas.append({
                "name":tool.name,
                "description": tool.description or "",
                "input_schema": tool.input_schema,
            })
        return schemas

    async def call_tool (self, name:str, arguments: dict[str,Any])->str:
        if self.client is None:
            return "Error: MCP Client chưa được kết nối"

        available_tools = {tool.name for tool in self.tools}
        if name not in available_tools:
            return f"Error: Không tìm thấy tool {name}"
        if not isinstance (arguments, dict):
            return "Error: Arguments phải là dictionary"
        
        try: 
            result = await self.client.call_tool(name,arguments)
            if result.is_error:
                messages = [
                    getattr(item, "text", str(item))
                    for item in (result.content or [])
                ]
                return "Error: " + ("\n".join(messages) or "MCP tool thực thi thất bại")
            messages= [
                getattr(item,"text",str(item))
                for item in (result.content or [])
            ]
            return "\n".join(messages) or "Tool đã chạy nhưng không trả về nội dung"
        except Exception as error:
            return f"Error: Gọi tool '{name}' thất bại: {error}" 

    
    async def close(self) -> None:
        context = self._context
        self.client = None
        self._context = None
        self.tools = []

        if context is not None:
            await context.__aexit__(None, None, None)
