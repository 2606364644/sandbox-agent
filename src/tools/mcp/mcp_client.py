"""
MCP客户端实现
"""
import asyncio
import json
import subprocess
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP协议客户端"""

    def __init__(self, server_command: List[str], server_name: str = None):
        """
        初始化MCP客户端

        Args:
            server_command: 启动MCP服务器的命令列表
            server_name: 服务器名称
        """
        self.server_command = server_command
        self.server_name = server_name or " ".join(server_command)
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.tools_cache: Optional[List[Dict[str, Any]]] = None

    async def start(self) -> bool:
        """
        启动MCP服务器

        Returns:
            bool: 启动是否成功
        """
        try:
            # 启动MCP服务器进程
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )

            # 发送初始化请求
            await self._send_request({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "langchain-agent",
                        "version": "1.0.0"
                    }
                }
            })

            logger.info(f"MCP服务器 {self.server_name} 启动成功")
            return True

        except Exception as e:
            logger.error(f"启动MCP服务器 {self.server_name} 失败: {str(e)}")
            return False

    async def stop(self) -> None:
        """停止MCP服务器"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info(f"MCP服务器 {self.server_name} 已停止")
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.error(f"停止MCP服务器 {self.server_name} 时出错: {str(e)}")
            finally:
                self.process = None

    async def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        发送JSON-RPC请求

        Args:
            request: 请求数据

        Returns:
            Optional[Dict[str, Any]]: 响应数据
        """
        if not self.process or not self.process.stdin:
            raise ConnectionError("MCP服务器进程未运行")

        try:
            # 发送请求
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()

            # 读取响应
            response_line = self.process.stdout.readline()
            if not response_line:
                raise ConnectionError("无法从MCP服务器读取响应")

            response = json.loads(response_line.strip())

            # 检查错误
            if "error" in response:
                raise Exception(f"MCP服务器错误: {response['error']}")

            return response

        except Exception as e:
            logger.error(f"发送MCP请求失败: {str(e)}")
            raise

    def _next_id(self) -> int:
        """生成下一个请求ID"""
        self.request_id += 1
        return self.request_id

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表

        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        if self.tools_cache is not None:
            return self.tools_cache

        try:
            response = await self._send_request({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list"
            })

            if response and "result" in response:
                self.tools_cache = response["result"].get("tools", [])
                return self.tools_cache

            return []

        except Exception as e:
            logger.error(f"获取MCP工具列表失败: {str(e)}")
            return []

    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用MCP工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            Dict[str, Any]: 工具执行结果
        """
        try:
            response = await self._send_request({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments or {}
                }
            })

            if response and "result" in response:
                return response["result"]

            raise Exception("无效的MCP工具响应")

        except Exception as e:
            logger.error(f"调用MCP工具 {name} 失败: {str(e)}")
            raise

    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """
        获取MCP资源

        Args:
            uri: 资源URI

        Returns:
            Dict[str, Any]: 资源数据
        """
        try:
            response = await self._send_request({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "resources/read",
                "params": {
                    "uri": uri
                }
            })

            if response and "result" in response:
                return response["result"]

            raise Exception("无效的MCP资源响应")

        except Exception as e:
            logger.error(f"获取MCP资源 {uri} 失败: {str(e)}")
            raise

    def is_alive(self) -> bool:
        """
        检查服务器是否存活

        Returns:
            bool: 是否存活
        """
        return self.process is not None and self.process.poll() is None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()


class MCPStdioClient:
    """基于标准输入输出的MCP客户端（用于子进程通信）"""

    def __init__(self):
        """初始化标准IO客户端"""
        self.request_id = 0
        self.tools_cache: Optional[List[Dict[str, Any]]] = None

    def _next_id(self) -> int:
        """生成下一个请求ID"""
        self.request_id += 1
        return self.request_id

    def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        发送JSON-RPC请求（同步）

        Args:
            request: 请求数据

        Returns:
            Optional[Dict[str, Any]]: 响应数据
        """
        try:
            # 发送请求到标准输出
            request_json = json.dumps(request)
            print(request_json, flush=True)

            # 从标准输入读取响应
            response_line = input().strip()
            response = json.loads(response_line)

            # 检查错误
            if "error" in response:
                raise Exception(f"MCP服务器错误: {response['error']}")

            return response

        except Exception as e:
            logger.error(f"发送MCP请求失败: {str(e)}")
            raise

    def initialize(self) -> bool:
        """
        初始化MCP连接

        Returns:
            bool: 初始化是否成功
        """
        try:
            response = self._send_request({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "langchain-agent",
                        "version": "1.0.0"
                    }
                }
            })

            return response is not None

        except Exception as e:
            logger.error(f"MCP初始化失败: {str(e)}")
            return False

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表

        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        if self.tools_cache is not None:
            return self.tools_cache

        try:
            response = self._send_request({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list"
            })

            if response and "result" in response:
                self.tools_cache = response["result"].get("tools", [])
                return self.tools_cache

            return []

        except Exception as e:
            logger.error(f"获取MCP工具列表失败: {str(e)}")
            return []

    def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用MCP工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            Dict[str, Any]: 工具执行结果
        """
        try:
            response = self._send_request({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments or {}
                }
            })

            if response and "result" in response:
                return response["result"]

            raise Exception("无效的MCP工具响应")

        except Exception as e:
            logger.error(f"调用MCP工具 {name} 失败: {str(e)}")
            raise