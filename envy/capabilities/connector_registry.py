"""
ENVY Connector Registry
=======================
Manages MCP connectors for external integrations:
- Filesystem (local file access)
- Web Search (Brave Search)
- Database (Supabase/PostgreSQL)
- GitHub (repository management)
- Custom connectors
"""

import os
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectorType(Enum):
    """Types of MCP connectors"""
    FILESYSTEM = "filesystem"
    WEB_SEARCH = "web_search"
    DATABASE = "database"
    GITHUB = "github"
    MEMORY = "memory"
    FETCH = "fetch"
    CUSTOM = "custom"


class ConnectorStatus(Enum):
    """Connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class TransportType(Enum):
    """MCP transport types"""
    STDIO = "stdio"  # Local subprocess
    SSE = "sse"      # Server-Sent Events (remote)
    HTTP = "http"    # HTTP/REST


@dataclass
class ConnectorConfig:
    """Configuration for an MCP connector"""
    id: str
    name: str
    type: ConnectorType
    description: str
    icon: str  # Emoji or icon name
    transport: TransportType
    command: Optional[str] = None  # For stdio transport
    args: Optional[List[str]] = None
    url: Optional[str] = None  # For SSE/HTTP transport
    env: Dict[str, str] = field(default_factory=dict)
    auth_required: bool = False
    auth_type: Optional[str] = None  # "api_key", "oauth", "bearer"
    enabled: bool = True
    auto_connect: bool = False


@dataclass
class ConnectorState:
    """Runtime state of a connector"""
    config: ConnectorConfig
    status: ConnectorStatus = ConnectorStatus.DISCONNECTED
    connected_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tools: List[Dict[str, Any]] = field(default_factory=list)
    resources: List[Dict[str, Any]] = field(default_factory=list)
    prompts: List[Dict[str, Any]] = field(default_factory=list)


# ============================================
# BUILTIN CONNECTOR CONFIGURATIONS
# ============================================

BUILTIN_CONNECTORS: Dict[str, ConnectorConfig] = {
    "filesystem": ConnectorConfig(
        id="filesystem",
        name="Filesystem",
        type=ConnectorType.FILESYSTEM,
        description="Read, write, and manage local files",
        icon="📁",
        transport=TransportType.STDIO,
        command="uvx",
        args=["mcp-server-filesystem", "./uploads"],
        enabled=True
    ),
    
    "brave_search": ConnectorConfig(
        id="brave_search",
        name="Brave Search",
        type=ConnectorType.WEB_SEARCH,
        description="Search the web using Brave Search API",
        icon="🔍",
        transport=TransportType.STDIO,
        command="uvx",
        args=["mcp-server-brave-search"],
        env={"BRAVE_API_KEY": ""},
        auth_required=True,
        auth_type="api_key"
    ),
    
    "memory": ConnectorConfig(
        id="memory",
        name="Memory",
        type=ConnectorType.MEMORY,
        description="Persistent knowledge graph memory",
        icon="🧠",
        transport=TransportType.STDIO,
        command="uvx",
        args=["mcp-server-memory"],
        enabled=True
    ),
    
    "fetch": ConnectorConfig(
        id="fetch",
        name="Web Fetch",
        type=ConnectorType.FETCH,
        description="Fetch and extract content from URLs",
        icon="🌐",
        transport=TransportType.STDIO,
        command="uvx",
        args=["mcp-server-fetch"],
        enabled=True
    ),
    
    "github": ConnectorConfig(
        id="github",
        name="GitHub",
        type=ConnectorType.GITHUB,
        description="Manage repositories, files, issues, and PRs",
        icon="🐙",
        transport=TransportType.STDIO,
        command="uvx",
        args=["mcp-server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
        auth_required=True,
        auth_type="api_key"
    ),
    
    "supabase": ConnectorConfig(
        id="supabase",
        name="Supabase Database",
        type=ConnectorType.DATABASE,
        description="Query and manage Supabase PostgreSQL database",
        icon="🗄️",
        transport=TransportType.SSE,
        url="",  # Will be derived from settings
        auth_required=True,
        auth_type="bearer"
    ),
    
    "sqlite": ConnectorConfig(
        id="sqlite",
        name="SQLite",
        type=ConnectorType.DATABASE,
        description="Local SQLite database operations",
        icon="📊",
        transport=TransportType.STDIO,
        command="uvx",
        args=["mcp-server-sqlite", "--db-path", "./data/envy.db"],
        enabled=True
    ),
}


class ConnectorRegistry:
    """
    Manages MCP connector lifecycle and tool aggregation.
    
    Features:
    - Register/unregister connectors
    - Connect/disconnect to connector servers
    - Aggregate tools from all connected servers
    - Credential management
    """
    
    def __init__(self, mcp_client=None):
        self.mcp_client = mcp_client
        self.configs: Dict[str, ConnectorConfig] = BUILTIN_CONNECTORS.copy()
        self.states: Dict[str, ConnectorState] = {}
        self._credentials: Dict[str, Dict[str, str]] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # Initialize states for all configs
        for config_id, config in self.configs.items():
            self.states[config_id] = ConnectorState(config=config)
    
    def register(self, config: ConnectorConfig) -> None:
        """Register a new connector configuration"""
        self.configs[config.id] = config
        self.states[config.id] = ConnectorState(config=config)
        logger.info(f"Registered connector: {config.name} ({config.id})")
    
    def unregister(self, connector_id: str) -> bool:
        """Unregister a connector"""
        if connector_id in self.configs:
            # Disconnect first if connected
            state = self.states.get(connector_id)
            if state and state.status == ConnectorStatus.CONNECTED:
                asyncio.create_task(self.disconnect(connector_id))
            
            del self.configs[connector_id]
            del self.states[connector_id]
            return True
        return False
    
    def set_credentials(self, connector_id: str, credentials: Dict[str, str]) -> None:
        """Set credentials for a connector"""
        self._credentials[connector_id] = credentials
        
        # Update config env
        if connector_id in self.configs:
            config = self.configs[connector_id]
            config.env = {**config.env, **credentials}
    
    def get_credentials(self, connector_id: str) -> Dict[str, str]:
        """Get credentials for a connector"""
        return self._credentials.get(connector_id, {})
    
    async def connect(self, connector_id: str, credentials: Dict[str, str] = None) -> ConnectorState:
        """
        Connect to an MCP server.
        
        Args:
            connector_id: ID of the connector to connect
            credentials: Optional credentials to use
            
        Returns:
            Updated connector state
        """
        if connector_id not in self.configs:
            raise ValueError(f"Unknown connector: {connector_id}")
        
        config = self.configs[connector_id]
        state = self.states[connector_id]
        
        # Update state
        state.status = ConnectorStatus.CONNECTING
        state.error_message = None
        
        # Merge credentials
        if credentials:
            self.set_credentials(connector_id, credentials)
        
        env = {**config.env, **self._credentials.get(connector_id, {})}
        
        try:
            if self.mcp_client:
                if config.transport == TransportType.STDIO:
                    await self.mcp_client.connect_stdio(
                        server_name=connector_id,
                        command=config.command,
                        args=config.args or [],
                        env=env
                    )
                elif config.transport == TransportType.SSE:
                    headers = {}
                    if config.auth_type == "bearer" and env.get("API_KEY"):
                        headers["Authorization"] = f"Bearer {env['API_KEY']}"
                    await self.mcp_client.connect_sse(
                        server_name=connector_id,
                        url=config.url,
                        headers=headers
                    )
                
                # Get capabilities
                state.tools = await self.mcp_client.list_tools_for_server(connector_id)
                state.resources = await self.mcp_client.list_resources_for_server(connector_id)
                state.prompts = await self.mcp_client.list_prompts_for_server(connector_id)
            
            state.status = ConnectorStatus.CONNECTED
            state.connected_at = datetime.now()
            logger.info(f"Connected to {config.name}: {len(state.tools)} tools available")
            
        except Exception as e:
            state.status = ConnectorStatus.ERROR
            state.error_message = str(e)
            logger.error(f"Failed to connect to {config.name}: {e}")
        
        # Emit event
        await self._emit("connector_status_changed", connector_id, state)
        
        return state
    
    async def disconnect(self, connector_id: str) -> ConnectorState:
        """Disconnect from an MCP server"""
        if connector_id not in self.states:
            raise ValueError(f"Unknown connector: {connector_id}")
        
        state = self.states[connector_id]
        
        try:
            if self.mcp_client:
                await self.mcp_client.disconnect(connector_id)
            
            state.status = ConnectorStatus.DISCONNECTED
            state.connected_at = None
            state.tools = []
            state.resources = []
            state.prompts = []
            logger.info(f"Disconnected from {state.config.name}")
            
        except Exception as e:
            state.error_message = str(e)
            logger.error(f"Error disconnecting from {state.config.name}: {e}")
        
        await self._emit("connector_status_changed", connector_id, state)
        return state
    
    async def reconnect(self, connector_id: str) -> ConnectorState:
        """Reconnect to a connector"""
        await self.disconnect(connector_id)
        return await self.connect(connector_id)
    
    def get_state(self, connector_id: str) -> Optional[ConnectorState]:
        """Get current state of a connector"""
        return self.states.get(connector_id)
    
    def list_connectors(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """
        List all connectors with their current status.
        
        Returns list of connector info dicts.
        """
        result = []
        for connector_id, state in self.states.items():
            config = state.config
            if not include_disabled and not config.enabled:
                continue
            
            result.append({
                "id": config.id,
                "name": config.name,
                "type": config.type.value,
                "description": config.description,
                "icon": config.icon,
                "transport": config.transport.value,
                "status": state.status.value,
                "connected_at": state.connected_at.isoformat() if state.connected_at else None,
                "error": state.error_message,
                "auth_required": config.auth_required,
                "auth_type": config.auth_type,
                "enabled": config.enabled,
                "tool_count": len(state.tools),
                "has_credentials": connector_id in self._credentials
            })
        
        return result
    
    def list_connected(self) -> List[str]:
        """List IDs of all connected connectors"""
        return [
            cid for cid, state in self.states.items()
            if state.status == ConnectorStatus.CONNECTED
        ]
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Aggregate tools from all connected connectors.
        
        Returns tools in format suitable for LLM tool definitions.
        """
        all_tools = []
        
        for connector_id, state in self.states.items():
            if state.status != ConnectorStatus.CONNECTED:
                continue
            
            for tool in state.tools:
                # Prefix tool name with connector ID to avoid collisions
                tool_def = {
                    "name": f"{connector_id}__{tool.get('name', 'unknown')}",
                    "description": tool.get('description', 'No description'),
                    "input_schema": tool.get('inputSchema', {}),
                    "_connector": connector_id,
                    "_original_name": tool.get('name')
                }
                all_tools.append(tool_def)
        
        return all_tools
    
    def get_tools_for_anthropic(self) -> List[Dict[str, Any]]:
        """
        Get tools formatted for Anthropic API.
        """
        tools = self.get_all_tools()
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"]
            }
            for t in tools
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool by name.
        
        Handles connector prefixing automatically.
        """
        # Parse connector and original tool name
        if "__" in tool_name:
            connector_id, original_name = tool_name.split("__", 1)
        else:
            # Try to find the tool in any connected connector
            connector_id = None
            original_name = tool_name
            for cid, state in self.states.items():
                if state.status == ConnectorStatus.CONNECTED:
                    for tool in state.tools:
                        if tool.get('name') == tool_name:
                            connector_id = cid
                            break
                if connector_id:
                    break
        
        if not connector_id:
            raise ValueError(f"Tool not found: {tool_name}")
        
        if self.mcp_client:
            return await self.mcp_client.call_tool(connector_id, original_name, arguments)
        
        raise RuntimeError("MCP client not configured")
    
    # Event handling
    def on(self, event: str, handler: Callable) -> None:
        """Register an event handler"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    async def _emit(self, event: str, *args) -> None:
        """Emit an event to all handlers"""
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args)
                else:
                    handler(*args)
            except Exception as e:
                logger.error(f"Error in event handler for {event}: {e}")
    
    async def auto_connect(self) -> None:
        """Connect to all connectors marked as auto_connect"""
        for connector_id, config in self.configs.items():
            if config.auto_connect and config.enabled:
                if not config.auth_required or connector_id in self._credentials:
                    await self.connect(connector_id)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of connectors"""
        total = len(self.states)
        connected = len([s for s in self.states.values() if s.status == ConnectorStatus.CONNECTED])
        errors = len([s for s in self.states.values() if s.status == ConnectorStatus.ERROR])
        
        return {
            "total_connectors": total,
            "connected": connected,
            "disconnected": total - connected - errors,
            "errors": errors,
            "total_tools": sum(len(s.tools) for s in self.states.values()),
            "status": "healthy" if errors == 0 else "degraded"
        }


# Global registry instance
_registry: Optional[ConnectorRegistry] = None


def get_connector_registry(mcp_client=None) -> ConnectorRegistry:
    """Get the global connector registry instance"""
    global _registry
    if _registry is None:
        _registry = ConnectorRegistry(mcp_client)
    elif mcp_client and _registry.mcp_client is None:
        _registry.mcp_client = mcp_client
    return _registry
