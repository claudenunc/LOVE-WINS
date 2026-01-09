"""
ENVY Enhanced MCP Client
========================
Full-featured MCP client supporting:
- stdio transport (local servers)
- SSE transport (remote servers)
- Tool discovery and aggregation
- Event streaming for frontend
- Connection lifecycle management
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager

# MCP SDK imports (graceful fallback if not available)
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool, Resource, Prompt
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None

logger = logging.getLogger(__name__)


@dataclass
class MCPServerInfo:
    """Information about a connected MCP server"""
    name: str
    transport: str  # "stdio" or "sse"
    connected_at: datetime
    capabilities: Dict[str, Any] = field(default_factory=dict)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    resources: List[Dict[str, Any]] = field(default_factory=list)
    prompts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MCPEvent:
    """Event for frontend streaming"""
    type: str  # "connection", "tool_call", "tool_result", "error", "notification"
    server: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "server": self.server,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }


class StdioConnection:
    """Manages a stdio MCP connection"""
    
    def __init__(self, server_name: str, command: str, args: List[str], env: Dict[str, str] = None):
        self.server_name = server_name
        self.command = command
        self.args = args
        self.env = env or {}
        self.session: Optional[ClientSession] = None
        self.process = None
        self._read_stream = None
        self._write_stream = None
        self._context_manager = None
    
    async def connect(self) -> Tuple[ClientSession, MCPServerInfo]:
        """Establish stdio connection"""
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP SDK not available")
        
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env={**self.env}
        )
        
        # Create the stdio client context
        self._context_manager = stdio_client(server_params)
        streams = await self._context_manager.__aenter__()
        self._read_stream, self._write_stream = streams
        
        # Create session
        self.session = ClientSession(self._read_stream, self._write_stream)
        await self.session.__aenter__()
        
        # Initialize
        init_result = await self.session.initialize()
        
        # Get capabilities
        tools = []
        resources = []
        prompts = []
        
        try:
            tools_result = await self.session.list_tools()
            tools = [self._tool_to_dict(t) for t in tools_result.tools]
        except Exception as e:
            logger.warning(f"Could not list tools for {self.server_name}: {e}")
        
        try:
            resources_result = await self.session.list_resources()
            resources = [self._resource_to_dict(r) for r in resources_result.resources]
        except Exception as e:
            logger.debug(f"Could not list resources for {self.server_name}: {e}")
        
        try:
            prompts_result = await self.session.list_prompts()
            prompts = [self._prompt_to_dict(p) for p in prompts_result.prompts]
        except Exception as e:
            logger.debug(f"Could not list prompts for {self.server_name}: {e}")
        
        server_info = MCPServerInfo(
            name=self.server_name,
            transport="stdio",
            connected_at=datetime.now(),
            capabilities=init_result.capabilities if hasattr(init_result, 'capabilities') else {},
            tools=tools,
            resources=resources,
            prompts=prompts
        )
        
        return self.session, server_info
    
    async def disconnect(self):
        """Close connection"""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
            if self._context_manager:
                await self._context_manager.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"Error disconnecting from {self.server_name}: {e}")
        finally:
            self.session = None
            self._context_manager = None
    
    @staticmethod
    def _tool_to_dict(tool) -> Dict[str, Any]:
        """Convert MCP Tool to dict"""
        return {
            "name": tool.name,
            "description": tool.description or "",
            "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
        }
    
    @staticmethod
    def _resource_to_dict(resource) -> Dict[str, Any]:
        """Convert MCP Resource to dict"""
        return {
            "uri": str(resource.uri),
            "name": resource.name or "",
            "description": resource.description or "",
            "mimeType": resource.mimeType if hasattr(resource, 'mimeType') else None
        }
    
    @staticmethod
    def _prompt_to_dict(prompt) -> Dict[str, Any]:
        """Convert MCP Prompt to dict"""
        return {
            "name": prompt.name,
            "description": prompt.description or "",
            "arguments": prompt.arguments if hasattr(prompt, 'arguments') else []
        }


class SSEConnection:
    """Manages an SSE MCP connection (for remote servers)"""
    
    def __init__(self, server_name: str, url: str, headers: Dict[str, str] = None):
        self.server_name = server_name
        self.url = url
        self.headers = headers or {}
        self.session = None
        self._client = None
    
    async def connect(self) -> Tuple[Any, MCPServerInfo]:
        """Establish SSE connection"""
        try:
            from mcp.client.sse import sse_client
        except ImportError:
            raise RuntimeError("MCP SSE client not available")
        
        # SSE connection
        self._client = sse_client(self.url, headers=self.headers)
        streams = await self._client.__aenter__()
        
        self.session = ClientSession(*streams)
        await self.session.__aenter__()
        
        init_result = await self.session.initialize()
        
        # Get capabilities
        tools = []
        try:
            tools_result = await self.session.list_tools()
            tools = [StdioConnection._tool_to_dict(t) for t in tools_result.tools]
        except:
            pass
        
        server_info = MCPServerInfo(
            name=self.server_name,
            transport="sse",
            connected_at=datetime.now(),
            capabilities=init_result.capabilities if hasattr(init_result, 'capabilities') else {},
            tools=tools,
            resources=[],
            prompts=[]
        )
        
        return self.session, server_info
    
    async def disconnect(self):
        """Close connection"""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
            if self._client:
                await self._client.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"Error disconnecting SSE {self.server_name}: {e}")


class EnhancedMCPClient:
    """
    Enhanced MCP Client with full feature support.
    
    Features:
    - Multiple concurrent server connections
    - Tool aggregation across servers
    - Event streaming for frontend updates
    - Automatic reconnection
    - Connection health monitoring
    """
    
    def __init__(self):
        self.connections: Dict[str, StdioConnection | SSEConnection] = {}
        self.server_info: Dict[str, MCPServerInfo] = {}
        self.sessions: Dict[str, ClientSession] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = True
    
    async def connect_stdio(
        self, 
        server_name: str, 
        command: str, 
        args: List[str] = None, 
        env: Dict[str, str] = None
    ) -> MCPServerInfo:
        """
        Connect to a local MCP server via stdio.
        
        Args:
            server_name: Unique identifier for this server
            command: Command to run (e.g., "uvx", "npx", "python")
            args: Command arguments
            env: Environment variables
            
        Returns:
            MCPServerInfo with server capabilities
        """
        if not MCP_AVAILABLE:
            # Return mock info for development
            logger.warning("MCP not available, returning mock server info")
            return self._create_mock_server_info(server_name, "stdio")
        
        # Create connection
        connection = StdioConnection(server_name, command, args or [], env)
        
        try:
            session, server_info = await connection.connect()
            
            # Store connection info
            self.connections[server_name] = connection
            self.sessions[server_name] = session
            self.server_info[server_name] = server_info
            
            # Emit event
            await self._emit_event(MCPEvent(
                type="connection",
                server=server_name,
                data={"status": "connected", "tools": len(server_info.tools)}
            ))
            
            logger.info(f"Connected to {server_name} via stdio: {len(server_info.tools)} tools")
            return server_info
            
        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {e}")
            await self._emit_event(MCPEvent(
                type="error",
                server=server_name,
                data={"error": str(e)}
            ))
            raise
    
    async def connect_sse(
        self, 
        server_name: str, 
        url: str, 
        headers: Dict[str, str] = None
    ) -> MCPServerInfo:
        """
        Connect to a remote MCP server via SSE.
        
        Args:
            server_name: Unique identifier for this server
            url: SSE endpoint URL
            headers: HTTP headers (for auth)
            
        Returns:
            MCPServerInfo with server capabilities
        """
        connection = SSEConnection(server_name, url, headers)
        
        try:
            session, server_info = await connection.connect()
            
            self.connections[server_name] = connection
            self.sessions[server_name] = session
            self.server_info[server_name] = server_info
            
            await self._emit_event(MCPEvent(
                type="connection",
                server=server_name,
                data={"status": "connected", "tools": len(server_info.tools)}
            ))
            
            logger.info(f"Connected to {server_name} via SSE: {len(server_info.tools)} tools")
            return server_info
            
        except Exception as e:
            logger.error(f"Failed to connect SSE to {server_name}: {e}")
            raise
    
    async def disconnect(self, server_name: str) -> None:
        """Disconnect from a server"""
        if server_name in self.connections:
            await self.connections[server_name].disconnect()
            del self.connections[server_name]
        
        if server_name in self.sessions:
            del self.sessions[server_name]
        
        if server_name in self.server_info:
            del self.server_info[server_name]
        
        await self._emit_event(MCPEvent(
            type="connection",
            server=server_name,
            data={"status": "disconnected"}
        ))
        
        logger.info(f"Disconnected from {server_name}")
    
    async def disconnect_all(self) -> None:
        """Disconnect from all servers"""
        for server_name in list(self.connections.keys()):
            await self.disconnect(server_name)
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """List all connected servers"""
        return [
            {
                "name": info.name,
                "transport": info.transport,
                "connected_at": info.connected_at.isoformat(),
                "tool_count": len(info.tools),
                "resource_count": len(info.resources),
                "prompt_count": len(info.prompts)
            }
            for info in self.server_info.values()
        ]
    
    def list_tools_for_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get tools for a specific server"""
        info = self.server_info.get(server_name)
        return info.tools if info else []
    
    async def list_tools_for_server_async(self, server_name: str) -> List[Dict[str, Any]]:
        """Async version for compatibility"""
        return self.list_tools_for_server(server_name)
    
    def list_resources_for_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get resources for a specific server"""
        info = self.server_info.get(server_name)
        return info.resources if info else []
    
    async def list_resources_for_server_async(self, server_name: str) -> List[Dict[str, Any]]:
        """Async version for compatibility"""
        return self.list_resources_for_server(server_name)
    
    def list_prompts_for_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get prompts for a specific server"""
        info = self.server_info.get(server_name)
        return info.prompts if info else []
    
    async def list_prompts_for_server_async(self, server_name: str) -> List[Dict[str, Any]]:
        """Async version for compatibility"""
        return self.list_prompts_for_server(server_name)
    
    def get_aggregated_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all connected servers"""
        all_tools = []
        for server_name, info in self.server_info.items():
            for tool in info.tools:
                all_tools.append({
                    **tool,
                    "_server": server_name
                })
        return all_tools
    
    async def call_tool(
        self, 
        server_name: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Execute a tool on a specific server.
        
        Args:
            server_name: Server to call
            tool_name: Tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        session = self.sessions.get(server_name)
        if not session:
            raise ValueError(f"Server {server_name} not connected")
        
        await self._emit_event(MCPEvent(
            type="tool_call",
            server=server_name,
            data={"tool": tool_name, "arguments": arguments}
        ))
        
        try:
            result = await session.call_tool(tool_name, arguments)
            
            # Process result
            result_data = self._process_tool_result(result)
            
            await self._emit_event(MCPEvent(
                type="tool_result",
                server=server_name,
                data={"tool": tool_name, "result": result_data, "success": True}
            ))
            
            return result_data
            
        except Exception as e:
            await self._emit_event(MCPEvent(
                type="tool_result",
                server=server_name,
                data={"tool": tool_name, "error": str(e), "success": False}
            ))
            raise
    
    def _process_tool_result(self, result) -> Any:
        """Process tool result into serializable format"""
        if hasattr(result, 'content'):
            # MCP CallToolResult
            content = result.content
            if isinstance(content, list):
                return [self._process_content_item(item) for item in content]
            return self._process_content_item(content)
        return result
    
    def _process_content_item(self, item) -> Any:
        """Process a single content item"""
        if hasattr(item, 'text'):
            return {"type": "text", "text": item.text}
        elif hasattr(item, 'data'):
            return {"type": "image", "data": item.data}
        return str(item)
    
    async def read_resource(self, server_name: str, uri: str) -> Any:
        """Read a resource from a server"""
        session = self.sessions.get(server_name)
        if not session:
            raise ValueError(f"Server {server_name} not connected")
        
        result = await session.read_resource(uri)
        return result
    
    async def get_prompt(
        self, 
        server_name: str, 
        prompt_name: str, 
        arguments: Dict[str, str] = None
    ) -> Any:
        """Get a prompt from a server"""
        session = self.sessions.get(server_name)
        if not session:
            raise ValueError(f"Server {server_name} not connected")
        
        result = await session.get_prompt(prompt_name, arguments or {})
        return result
    
    # Event streaming for frontend
    async def stream_events(self) -> AsyncGenerator[MCPEvent, None]:
        """
        Stream MCP events to frontend.
        
        Yields MCPEvent objects as they occur.
        """
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(), 
                    timeout=30.0
                )
                yield event
            except asyncio.TimeoutError:
                # Send keepalive
                yield MCPEvent(
                    type="keepalive",
                    server="system",
                    data={"connected_servers": list(self.server_info.keys())}
                )
    
    async def _emit_event(self, event: MCPEvent) -> None:
        """Emit an event to the queue"""
        await self._event_queue.put(event)
    
    def _create_mock_server_info(self, server_name: str, transport: str) -> MCPServerInfo:
        """Create mock server info for development without MCP"""
        return MCPServerInfo(
            name=server_name,
            transport=transport,
            connected_at=datetime.now(),
            capabilities={},
            tools=[
                {
                    "name": "mock_tool",
                    "description": "Mock tool for development",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            ],
            resources=[],
            prompts=[]
        )
    
    async def close(self) -> None:
        """Close the client and all connections"""
        self._running = False
        await self.disconnect_all()
    
    # Health check
    def get_health(self) -> Dict[str, Any]:
        """Get health status of all connections"""
        return {
            "connected_servers": len(self.server_info),
            "total_tools": sum(len(info.tools) for info in self.server_info.values()),
            "servers": {
                name: {
                    "transport": info.transport,
                    "tools": len(info.tools),
                    "uptime_seconds": (datetime.now() - info.connected_at).total_seconds()
                }
                for name, info in self.server_info.items()
            }
        }


# Global instance
_mcp_client: Optional[EnhancedMCPClient] = None


def get_mcp_client() -> EnhancedMCPClient:
    """Get the global MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = EnhancedMCPClient()
    return _mcp_client
