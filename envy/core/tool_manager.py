from typing import List, Dict, Any, Optional
import json
import logging

from ..capabilities.mcp_client import MCPClient
from ..capabilities.computer_control import VisionController, CodeController

logger = logging.getLogger(__name__)

class ToolManager:
    """
    Manages the exposure and execution of tools for the Agent.
    Aggregates MCP tools, Vision, and Code execution into a unified interface.
    """
    
    def __init__(
        self, 
        mcp_client: Optional[MCPClient] = None,
        vision: Optional[VisionController] = None,
        code: Optional[CodeController] = None
    ):
        self.mcp = mcp_client
        self.vision = vision
        self.code = code
        
    async def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Returns a JSON-schema list of all available tools for the LLM system prompt.
        """
        tools = []
        
        # 1. Vision Tool
        if self.vision:
            tools.append({
                "name": "see_screen",
                "description": "Takes a screenshot and analyzes it. Use this when the user asks about what is on their screen or asks you to look at something.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {
                            "type": "string",
                            "description": "What to look for or analyze in the screenshot."
                        }
                    },
                    "required": ["instruction"]
                }
            })
            
        # 2. Code Tool (Open Interpreter)
        if self.code:
            tools.append({
                "name": "run_code",
                "description": "Executes Python or Bash code on the user's machine. Use this for system operations, file management, or complex calculations. DANGEROUS: Only use if necessary.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The code to execute."
                        },
                        "language": {
                            "type": "string",
                            "enum": ["python", "bash"],
                            "description": "The language of the code."
                        }
                    },
                    "required": ["code"]
                }
            })
            
        # 3. MCP Tools (Dynamic)
        if self.mcp:
            # For now, we assume MCP tools are already discovered and stored in self.mcp.available_tools
            # This requires MCPClient to have run discovery.
            # We'll just list generic ones for the prototype.
            mcp_tools = await self.mcp.list_all_tools() 
            for tool in mcp_tools:
                tools.append({
                    "name": tool['name'],
                    "description": tool.get('description', 'No description'),
                    "parameters": tool.get('inputSchema', {})
                })
                
        return tools

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Executes a tool by name.
        """
        try:
            # 1. Vision
            if tool_name == "see_screen" and self.vision:
                return self.vision.analyze(args.get("instruction", ""))
            
            # 2. Code
            if tool_name == "run_code" and self.code:
                # Open Interpreter takes natural language or code blocks.
                # We'll adapt based on the simple chat interface.
                lang = args.get("language", "python")
                code_str = args.get("code", "")
                prompt = f"```{lang}\n{code_str}\n```"
                return self.code.chat(prompt)
            
            # 3. MCP
            if self.mcp:
                # We need to find which server has this tool
                all_tools = await self.mcp.list_all_tools()
                for t in all_tools:
                    if t['name'] == tool_name:
                        server_name = t['server']
                        return await self.mcp.call_tool(server_name, tool_name, args)
                        
            return f"Error: Tool '{tool_name}' not found."
            
        except Exception as e:
            return f"Error executing '{tool_name}': {str(e)}"

    def get_system_prompt_addition(self) -> str:
        """
        Returns a string to append to the system prompt explaining available tools.
        """
        # We can't use async here easily in a property, so we might need to pre-load or simplify.
        # For the prototype, we'll return a static instruction block.
        return """
## TOOL USE PROTOCOL
You have access to the following tools. To use one, you MUST output a JSON object in a distinct block:

```json
{
  "tool": "tool_name",
  "args": {
    "arg1": "value"
  }
}
```

Stop generating after the JSON block. The system will execute the tool and return the result to you.

AVAILABLE TOOLS:
1. see_screen(instruction): Analyze the user's screen.
2. run_code(code, language): Execute Python/Bash on the system.
"""
