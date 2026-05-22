"""
Vibhu-Oska AI-OS — Model Context Protocol (MCP) Server
Exposes all Vibhu-Oska plugins as standard MCP tools over stdio.
Allows Cursor, VS Code, and Claude/Gemini Desktops to run local AI-OS plugins.
"""

from __future__ import annotations

import json
import sys
import traceback
import asyncio
from typing import Any

from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Backend.Plugins.ToolRegistry.Registry import ToolRegistry
from Backend.Plugins.DatabaseConnector.DatabaseConnector import DatabaseConnector
from Backend.Plugins.CacheManager.CacheManager import CacheManager
from Backend.Plugins.SearchEngine.SearchEngine import SearchEngine
from Backend.Plugins.FeedbackCollector.FeedbackCollector import FeedbackCollector
from Backend.Plugins.TestingFramework.TestingFramework import TestingFramework
from Backend.Plugins.CodeAnalyzer.CodeAnalyzer import CodeAnalyzer
from Backend.Plugins.ReplayLogger.ReplayLogger import ReplayLogger
from Backend.Plugins.Scheduler.Scheduler import Scheduler
from Backend.Plugins.ThermalMonitor.ThermalMonitor import ThermalMonitor
from Backend.Plugins.AuthenticationManager.AuthenticationManager import AuthenticationManager

# Redirect standard logging to stderr so it does not pollute stdout (reserved for JSON-RPC)
sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")


class MCPServer:
    """
    Model Context Protocol server for Vibhu-Oska.
    Listens on stdin and writes JSON-RPC responses to stdout.
    """

    def __init__(self) -> None:
        self.registry = ToolRegistry()
        self.initialized = False

    async def init_plugins(self) -> None:
        """Instantiate and register all plugins."""
        try:
            # Load config
            ConfigLoader.load()
            
            # Register plugins
            await self.registry.register_and_init(DatabaseConnector())
            await self.registry.register_and_init(CacheManager())
            await self.registry.register_and_init(SearchEngine())
            await self.registry.register_and_init(FeedbackCollector())
            await self.registry.register_and_init(TestingFramework())
            await self.registry.register_and_init(CodeAnalyzer())
            await self.registry.register_and_init(ReplayLogger())
            await self.registry.register_and_init(Scheduler())
            await self.registry.register_and_init(ThermalMonitor())
            await self.registry.register_and_init(AuthenticationManager())
            
            sys.stderr.write(f"[MCP] Loaded {self.registry.plugin_count} plugins as tools.\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"[MCP] Failed to initialize plugins: {str(e)}\n")
            sys.stderr.write(traceback.format_exc() + "\n")
            sys.stderr.flush()

    def list_tools(self) -> list[dict[str, Any]]:
        """Return lists of available tools based on registered plugins."""
        tools = []
        for plugin_info in self.registry.list_plugins():
            tool_name = plugin_info.name
            desc = plugin_info.description or f"Vibhu-Oska plugin for '{tool_name}' capabilities."
            
            # Define schema dynamically
            schema = {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The specific plugin action to execute."
                    },
                    "arguments": {
                        "type": "object",
                        "description": "Action-specific keyword arguments."
                    }
                },
                "required": ["action"]
            }
            
            tools.append({
                "name": tool_name,
                "description": desc,
                "inputSchema": schema
            })
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute the plugin corresponding to the tool name."""
        plugin = self.registry.get_safe(name)
        if not plugin:
            raise ValueError(f"Tool/plugin '{name}' not found in registry")
            
        action = arguments.get("action")
        if not action:
            raise ValueError("Argument 'action' is required")
            
        kwargs = arguments.get("arguments", {})
        if not isinstance(kwargs, dict):
            kwargs = {}
            
        # Run execution
        res = await plugin.execute(action, **kwargs)
        
        # Return content in MCP format
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(res, indent=2, default=str)
                }
            ]
        }

    async def run(self) -> None:
        """Start the stdio JSON-RPC processing loop."""
        await self.init_plugins()
        sys.stderr.write("[MCP] Server is running and listening on stdin...\n")
        sys.stderr.flush()

        while True:
            try:
                line = await asyncio.to_thread(sys.stdin.readline)
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse request
                req = json.loads(line)
                req_id = req.get("id")
                method = req.get("method")
                params = req.get("params", {})
                
                # Process based on method
                if method == "initialize":
                    self.initialized = True
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": "vibhu-oska-mcp",
                                "version": "0.1.0"
                            }
                        }
                    }
                elif not self.initialized:
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32002,
                            "message": "Server not initialized"
                        }
                    }
                elif method == "tools/list":
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "tools": self.list_tools()
                        }
                    }
                elif method == "tools/call":
                    tool_name = params.get("name")
                    args = params.get("arguments", {})
                    try:
                        result = await self.call_tool(tool_name, args)
                        res = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": result
                        }
                    except Exception as e:
                        res = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {
                                "code": -32603,
                                "message": f"Execution error: {str(e)}",
                                "data": traceback.format_exc()
                            }
                        }
                elif method == "notifications/initialized":
                    # No response needed for initialized notification
                    continue
                else:
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                
                # Write response line
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
                
            except json.JSONDecodeError:
                sys.stderr.write("[MCP] Error decoding JSON line\n")
                sys.stderr.flush()
            except Exception as e:
                sys.stderr.write(f"[MCP] Loop error: {str(e)}\n")
                sys.stderr.flush()


def main() -> None:
    asyncio.run(MCPServer().run())


if __name__ == "__main__":
    main()
