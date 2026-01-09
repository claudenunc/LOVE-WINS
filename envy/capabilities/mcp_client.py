import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class MCPClient:
    """
    Implements 'The Hands' of the Digital Twin using the Model Context Protocol.
    Allows connection to local and remote MCP servers to acquire dynamic skills.
    """

    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.available_tools: Dict[str, List[Dict[str, Any]]] = {}

    async def connect_stdio(self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """Connects to a local MCP server via stdio."""
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
        # Note: In a real implementation, we need to manage the context manager lifecycle properly.
        # For this prototype, we're simplifying the connection storage.
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self.sessions[server_name] = session
                    
                    # Discover tools
                    tools = await session.list_tools()
                    self.available_tools[server_name] = tools
                    logger.info(f"Connected to MCP server '{server_name}' with {len(tools)} tools.")
                    
                    # Keep session alive? 
                    # This architecture is tricky with async context managers in a class.
                    # Usually, the session needs to run in a background task or be managed differently.
                    # For now, we acknowledge the connection.
                    pass
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_name}: {e}")

    async def list_all_tools(self) -> List[Dict[str, Any]]:
        """Returns a flat list of all tools from all connected servers."""
        all_tools = []
        for server, tools in self.available_tools.items():
            for tool in tools:
                tool['server'] = server
                all_tools.append(tool)
        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Executes a specific tool on a specific server."""
        if server_name not in self.sessions:
            raise ValueError(f"Server {server_name} not connected.")
        
        session = self.sessions[server_name]
        try:
            result = await session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
            raise

    # Dynamic Skill Loading (Registry Pattern)
    async def load_skill(self, skill_name: str):
        """
        Dynamically loads an MCP server based on a skill registry.
        (Placeholder for the 'Progressive Disclosure' mechanism)
        """
        # Logic to lookup skill_name in a SKILL.md or config, 
        # find the server command, and call connect_stdio
        pass
