"""
ENVY Tool Manager v2.0
======================
Manages the exposure and execution of tools for the Agent.
Aggregates:
- MCP tools (from connected servers)
- Vision tools (screen analysis)
- Code execution tools
- File management tools
- Agent spawning tools
- Builder Suite tools (New!)
"""

from typing import List, Dict, Any, Optional
import json
import logging
import asyncio

from ..tools.builder_suite import BUILDER_TOOLS

logger = logging.getLogger(__name__)


class ToolManager:
    """
    Manages the unified tool interface for ENVY.
    
    Features:
    - Dynamic tool discovery from MCP connectors
    - Built-in tools (vision, code, files)
    - Agent spawning integration
    - Builder Suite (n8n, Research, Git)
    - Tool execution with error handling
    """
    
    def __init__(
        self,
        mcp_client=None,
        vision=None,
        code=None,
        file_handler=None,
        agent_spawner=None,
        connector_registry=None
    ):
        self.mcp = mcp_client
        self.vision = vision
        self.code = code
        self.file_handler = file_handler
        self.agent_spawner = agent_spawner
        self.connector_registry = connector_registry
        
        # Built-in tools registry
        self._builtin_tools = self._register_builtin_tools()
        self._register_builder_tools()
    
    def _register_builder_tools(self):
        """Register the Builder Suite tools"""
        for func in BUILDER_TOOLS:
            # Create a simple schema based on the function name
            # In a real app we'd parse signatures, but this is a stub for now.
            name = func.__name__
            self._builtin_tools[name] = {
                "definition": {
                    "name": name,
                    "description": func.__doc__.strip() if func.__doc__ else f"Tool {name}",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "arg1": {"type": "string", "description": "Generic argument"}
                        }
                    }
                },
                "handler": lambda args, f=func: f(**args) # Simple wrapper
            }

    def _register_builtin_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register all built-in tools with their definitions and handlers"""
        tools = {}
        
        # Vision Tool
        if self.vision:
            tools["see_screen"] = {
                "definition": {
                    "name": "see_screen",
                    "description": "Takes a screenshot and analyzes it. Use when user asks about what's on their screen.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "instruction": {
                                "type": "string",
                                "description": "What to look for or analyze in the screenshot."
                            }
                        },
                        "required": ["instruction"]
                    }
                },
                "handler": self._handle_vision
            }
        
        # Code Tool
        if self.code:
            tools["run_code"] = {
                "definition": {
                    "name": "run_code",
                    "description": "Executes Python or Bash code. Use for calculations, file operations, or system tasks. DANGEROUS: Use with caution.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "The code to execute."
                            },
                            "language": {
                                "type": "string",
                                "enum": ["python", "bash"],
                                "description": "The programming language."
                            }
                        },
                        "required": ["code"]
                    }
                },
                "handler": self._handle_code
            }
        
        # File Tools
        if self.file_handler:
            tools["read_file"] = {
                "definition": {
                    "name": "read_file",
                    "description": "Read content from an uploaded file.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "ID of the uploaded file to read."
                            }
                        },
                        "required": ["file_id"]
                    }
                },
                "handler": self._handle_read_file
            }
            
            tools["list_files"] = {
                "definition": {
                    "name": "list_files",
                    "description": "List all uploaded files in the current session.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["document", "image", "code"],
                                "description": "Filter by file type (optional)."
                            }
                        }
                    }
                },
                "handler": self._handle_list_files
            }
        
        # Agent Spawning Tools
        if self.agent_spawner:
            tools["spawn_agent"] = {
                "definition": {
                    "name": "spawn_agent",
                    "description": "Spawn a specialized sub-agent to handle a specific task.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["coder", "researcher", "analyst", "writer", "planner", "debugger", "reviewer"],
                                "description": "The type of agent to spawn."
                            },
                            "task": {
                                "type": "string",
                                "description": "The task for the agent to perform."
                            },
                            "context": {
                                "type": "object",
                                "description": "Additional context to pass to the agent."
                            }
                        },
                        "required": ["role", "task"]
                    }
                },
                "handler": self._handle_spawn_agent
            }
            
            tools["get_agent_status"] = {
                "definition": {
                    "name": "get_agent_status",
                    "description": "Get the status and result of a spawned agent.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent to check."
                            }
                        },
                        "required": ["agent_id"]
                    }
                },
                "handler": self._handle_agent_status
            }
            
            tools["wait_agent"] = {
                "definition": {
                    "name": "wait_agent",
                    "description": "Wait for an agent to complete and return its result.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent to wait for."
                            },
                            "timeout": {
                                "type": "number",
                                "description": "Maximum seconds to wait (default: 30)."
                            }
                        },
                        "required": ["agent_id"]
                    }
                },
                "handler": self._handle_wait_agent
            }
        
        # Artifact Generation Tool
        tools["generate_artifact"] = {
            "definition": {
                "name": "generate_artifact",
                "description": "Generate a visual artifact (React component, HTML, SVG, etc.) that will be rendered in the artifact panel.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["react", "html", "svg", "mermaid", "code"],
                            "description": "The type of artifact to generate."
                        },
                        "title": {
                            "type": "string",
                            "description": "Title for the artifact."
                        },
                        "content": {
                            "type": "string",
                            "description": "The artifact content (code/markup)."
                        }
                    },
                    "required": ["type", "title", "content"]
                }
            },
            "handler": self._handle_generate_artifact
        }
        
        return tools
    
    # ===================================
    # TOOL DEFINITIONS
    # ===================================
    
    async def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Returns all available tools in a format suitable for LLM system prompts.
        Aggregates built-in tools + MCP tools from connectors.
        """
        tools = []
        
        # Add built-in tools
        for tool_info in self._builtin_tools.values():
            tools.append(tool_info["definition"])
        
        # Add MCP tools from connector registry
        if self.connector_registry:
            mcp_tools = self.connector_registry.get_all_tools()
            for tool in mcp_tools:
                tools.append({
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["input_schema"]
                })
        
        return tools
    
    def get_tool_definitions_sync(self) -> List[Dict[str, Any]]:
        """Synchronous version for cases where async isn't available"""
        tools = []
        
        for tool_info in self._builtin_tools.values():
            tools.append(tool_info["definition"])
        
        if self.connector_registry:
            mcp_tools = self.connector_registry.get_all_tools()
            for tool in mcp_tools:
                tools.append({
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["input_schema"]
                })
        
        return tools
    
    # ===================================
    # TOOL EXECUTION
    # ===================================
    
    async def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Execute a tool by name.
        Routes to appropriate handler based on tool source.
        """
        logger.info(f"Executing tool: {tool_name} with args: {args}")
        
        try:
            # Check built-in tools first
            if tool_name in self._builtin_tools:
                handler = self._builtin_tools[tool_name]["handler"]
                # Handle both async and sync handlers
                if asyncio.iscoroutinefunction(handler):
                    return await handler(args)
                else:
                    return handler(args)
            
            # Check MCP tools
            if self.connector_registry and "__" in tool_name:
                # MCP tools are prefixed: connector__toolname
                return await self.connector_registry.call_tool(tool_name, args)
            
            # Try direct MCP call for unprefixed tools
            if self.mcp:
                all_tools = await self.mcp.list_all_tools() if hasattr(self.mcp, 'list_all_tools') else []
                for t in all_tools:
                    if t.get('name') == tool_name:
                        server_name = t.get('_server') or t.get('server')
                        if server_name:
                            return await self.mcp.call_tool(server_name, tool_name, args)
            
            return f"Error: Tool '{tool_name}' not found."
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"Error executing '{tool_name}': {str(e)}"
    
    # ===================================
    # BUILT-IN TOOL HANDLERS
    # ===================================
    
    async def _handle_vision(self, args: Dict[str, Any]) -> str:
        """Handle see_screen tool"""
        instruction = args.get("instruction", "Describe what you see")
        return self.vision.analyze(instruction)
    
    async def _handle_code(self, args: Dict[str, Any]) -> str:
        """Handle run_code tool"""
        lang = args.get("language", "python")
        code_str = args.get("code", "")
        prompt = f"```{{lang}}\n{{code_str}}\n```"
        return self.code.chat(prompt)
    
    async def _handle_read_file(self, args: Dict[str, Any]) -> str:
        """Handle read_file tool"""
        file_id = args.get("file_id")
        if not file_id:
            return "Error: file_id is required"
        
        file = self.file_handler.get_file(file_id)
        if not file:
            return f"Error: File {{file_id}} not found"
        
        if file.content:
            return f"Content of {{file.filename}}:\n\n{{file.content}}"
        return f"Error: Could not read content of {{file.filename}}"
    
    async def _handle_list_files(self, args: Dict[str, Any]) -> str:
        """Handle list_files tool"""
        from ..capabilities.file_handler import FileType
        
        file_type = None
        if args.get("type"):
            try:
                file_type = FileType(args["type"])
            except ValueError:
                pass
        
        files = self.file_handler.list_files(file_type)
        
        if not files:
            return "No files uploaded."
        
        lines = ["Uploaded files:"]
        for f in files:
            lines.append(f"- {{f['id']}}: {{f['filename']}} ({{f['type']}}, {{f['size_bytes']}} bytes)")
        
        return "\n".join(lines)
    
    async def _handle_spawn_agent(self, args: Dict[str, Any]) -> str:
        """Handle spawn_agent tool"""
        role = args.get("role", "coder")
        task = args.get("task", "")
        context = args.get("context", {})
        
        if not task:
            return "Error: task is required"
        
        try:
            agent_id = await self.agent_spawner.spawn(
                role=role,
                task=task,
                context=context
            )
            return f"Spawned agent {{agent_id}} ({{role}}). Use get_agent_status or wait_agent to check results."
        except Exception as e:
            return f"Error spawning agent: {str(e)}"
    
    async def _handle_agent_status(self, args: Dict[str, Any]) -> str:
        """Handle get_agent_status tool"""
        agent_id = args.get("agent_id")
        if not agent_id:
            return "Error: agent_id is required"
        
        status = self.agent_spawner.get_status(agent_id)
        if not status:
            return f"Agent {{agent_id}} not found"
        
        return json.dumps(status, indent=2, default=str)
    
    async def _handle_wait_agent(self, args: Dict[str, Any]) -> str:
        """Handle wait_agent tool"""
        agent_id = args.get("agent_id")
        timeout = args.get("timeout", 30.0)
        
        if not agent_id:
            return "Error: agent_id is required"
        
        result = await self.agent_spawner.wait_for(agent_id, timeout)
        
        if result:
            return f"Agent {{agent_id}} result:\n\n{{result}}"
        
        status = self.agent_spawner.get_status(agent_id)
        if status:
            return f"Agent {{agent_id}} did not complete in time. Current status: {{status['status']}}"
        return f"Agent {{agent_id}} not found"
    
    async def _handle_generate_artifact(self, args: Dict[str, Any]) -> str:
        """Handle generate_artifact tool - returns XML for frontend to render"""
        artifact_type = args.get("type", "code")
        title = args.get("title", "Artifact")
        content = args.get("content", "")
        
        # Map type to MIME-like format
        type_map = {
            "react": "application/vnd.ant.react",
            "html": "text/html",
            "svg": "image/svg+xml",
            "mermaid": "application/vnd.ant.mermaid",
            "code": "application/vnd.ant.code"
        }
        
        mime_type = type_map.get(artifact_type, "text/plain")
        artifact_id = f"artifact_{{hash(content) % 10000}}"
        
        # Return in the format the frontend expects
        return f"""<antArtifact identifier="{{artifact_id}}" type="{{mime_type}}" title="{{title}}">
{{content}}
</antArtifact>"""
    
    # ===================================
    # SYSTEM PROMPT GENERATION
    # ===================================
    
    def get_system_prompt_addition(self) -> str:
        """
        Returns a string to append to the system prompt explaining available tools.
        """
        tools = self.get_tool_definitions_sync()
        
        if not tools:
            return ""
        
        prompt = """
## TOOL USE PROTOCOL

You have access to the following tools. To use one, output a JSON object in a code block:

```json
{
  "tool": "tool_name",
  "args": {
    "arg1": "value"
  }
}
```

Stop generating after the JSON block. The system will execute the tool and return the result.

### AVAILABLE TOOLS:
"""
        
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "No description")
            schema = tool.get("input_schema", {})
            props = schema.get("properties", {})
            required = schema.get("required", [])
            
            args_str = ""
            for prop_name, prop_info in props.items():
                req_mark = "*" if prop_name in required else ""
                prop_type = prop_info.get("type", "any")
                args_str += f"  - {prop_name}{{req_mark}}: {prop_type}\n"
            
            prompt += f"\n**{{name}}**: {{desc}}\n"
            if args_str:
                prompt += f"Arguments:\n{{args_str}}"
        
        prompt += """
### ARTIFACT GENERATION

For visual outputs (React components, HTML, diagrams), use the generate_artifact tool OR wrap code in:

<antArtifact identifier="unique-id" type="application/vnd.ant.react" title="Title">
// Your React/HTML/SVG code here
</antArtifact>

This will render the content in the artifact panel.

### AGENT SPAWNING

For complex tasks, spawn specialized agents:
- **coder**: Write, debug, refactor code
- **researcher**: Search web, gather information
- **analyst**: Analyze data, produce insights
- **writer**: Create written content
- **planner**: Create plans and roadmaps

Use spawn_agent tool and wait_agent to get results.
"""
        
        return prompt
    
    # ===================================
    # UTILITY METHODS
    # ===================================
    
    def list_available_tools(self) -> List[str]:
        """Get list of all available tool names"""
        tools = list(self._builtin_tools.keys())
        
        if self.connector_registry:
            mcp_tools = self.connector_registry.get_all_tools()
            tools.extend([t["name"] for t in mcp_tools])
        
        return tools
    
    def get_tool_count(self) -> Dict[str, int]:
        """Get count of tools by source"""
        counts = {
            "builtin": len(self._builtin_tools),
            "mcp": 0
        }
        
        if self.connector_registry:
            counts["mcp"] = len(self.connector_registry.get_all_tools())
        
        counts["total"] = counts["builtin"] + counts["mcp"]
        return counts