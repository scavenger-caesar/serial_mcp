from contextlib import asynccontextmanager
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field

from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.contrib.mcp_mixin import MCPMixin, mcp_tool

from labgrid import Target
from labgrid.resource import RawSerialPort
from labgrid.driver import SerialDriver, ShellDriver


# ── 预制 shell prompt 类型 ──────────────────────────────────────────────────
class PromptType(str, Enum):
    linux_root = r'root@[\w.\-]+:[^ ]+ [#$] '    # 标准 Linux root
    linux_user = r'[\w]+@[\w.\-]+:[^ ]+ \$ '     # 标准 Linux 普通用户
    busybox = r'[\w/~\-]+ [#$] '                 # BusyBox / 嵌入式常见
    generic_root = r'# '                         # 极简 root prompt
    generic = r'[#$] '                           # 最通用（可能误匹配）

class SerialConnectResponse(BaseModel):
    port: str = Field(..., description="串口路径")
    baudrate: Optional[int] = Field(None, description="波特率")
    shell_type: Optional[PromptType] = Field(None, description="Shell 类型")
    connect_status: Literal["connected", "disconnected"] = Field(..., description="连接状态")
    message: str = Field(..., description="连接信息")   


class SerialCmdResponse(BaseModel):
    stdout: Optional[str] = Field(None, description="标准输出")
    stderr: Optional[str] = Field(None, description="标准错误")
    retcode: Optional[int] = Field(None, description="返回码") 
    cmd_status: Literal["success", "failed"] = Field(..., description="命令执行状态")
    message: str = Field(..., description="命令执行信息")    


# ── lifespan：管理串口连接的生命周期 ────────────────────────────────────────
@asynccontextmanager
async def lifespan(server: FastMCP):
    """Server 启动时初始化串口资源，关闭时自动清理。"""
    # 此处初始化一个空的连接池，具体连接由 connect_serial tool 动态创建
    connections: dict[str, ShellDriver] = {}
    try:
        yield {"connections": connections}
    finally:
        # 关闭所有活跃的串口连接
        for port, shell_drv in connections.items():
            try:
                shell_drv.target.deactivate(shell_drv)
            except Exception:
                pass
        connections.clear()

mcp = FastMCP("serial_cmd", lifespan=lifespan)


# ── MCPMixin：将 SerialSkill 类的方法注册为 MCP tools ────────────────────────
class SerialSkill(MCPMixin):
    """通过串口连接嵌入式设备并执行 Shell 命令的工具集"""

    @mcp_tool(
        name="connect_serial",
        description="Connect to the serial device and establish a shell session",
    )
    async def connect_serial(
        self,
        port: str,
        baudrate: int = 115200,
        shell_type: PromptType = PromptType.busybox,
        ctx: Context = None,
    ) -> SerialConnectResponse:
        """
        connect serial port

        Args:
            port (str): need to connect serial port
            baudrate (int, optional): baudrate. Defaults to 115200.
            shell_type (PromptType, optional): shell type. Defaults to PromptType.busybox.

        Returns:
            str: serial port connection information
        """ 
        await ctx.info(f"正在连接串口 {port}，波特率 {baudrate}，类型 {shell_type.name}")

        connections: dict = ctx.lifespan_context["connections"]
        if port in connections:
            return SerialConnectResponse(
                port=port,
                connect_status="connected",
                message="serial port already connected"
            )

        prompt = shell_type.value

        # 创建 labgrid Target 和 Driver
        target = Target(f"serial_{port.replace('/', '_')}")
        RawSerialPort(target, name=None, port=port, speed=baudrate)
        SerialDriver(target, name=None)
        shell_drv = ShellDriver(target, name=None, prompt=prompt)
        shell_drv.target = target  # 方便 lifespan 清理

        target.activate(shell_drv)
        connections[port] = shell_drv

        await ctx.info(f"串口 {port} 连接成功")
        return SerialConnectResponse(
            port=port,
            baudrate=baudrate,
            shell_type=shell_type,
            connect_status="connected",
            message="serial port connected successfully",
        )

    @mcp_tool(
        name="run_command",
        description="run command in the specified serial port",
        timeout=60.0,
    )
    async def run_command(
        self,
        port: str,
        command: str,
        ctx: Context = None,
    ) -> SerialCmdResponse:
        """
        run command in the specified serial port

        Args:
            port (str): serial port
            command (str): command to run

        Returns:
            SerialCmdResponse: command execution result
        """
        connections: dict = ctx.lifespan_context["connections"]
        shell_drv: ShellDriver = connections.get(port)
        if shell_drv is None:
            return SerialCmdResponse(
                cmd_status="failed",
                message=f"error: serial port {port} is not connected, please call connect_serial first"
            )

        await ctx.info(f"[{port}] 执行命令: {command}")
        await ctx.report_progress(0, 100, "发送命令中...")

        stdout, stderr, retcode = shell_drv.run(command)

        await ctx.report_progress(100, 100, "命令执行完毕")

        return SerialCmdResponse(
            stdout="\n".join(stdout),
            stderr="\n".join(stderr) if stderr else "",
            retcode=retcode,
            cmd_status="success",
            message="command executed successfully",
        )

    @mcp_tool(
        name="disconnect_serial",
        description="disconnect specified serial port",
    )
    async def disconnect_serial(
        self,
        port: str,
        ctx: Context = None,
    ) -> SerialConnectResponse:
        """disconnect specified serial port

        Args:
            port (str): need to disconnect serial port

        Returns:
            SerialConnectResponse: serial port connection information
        """
        connections: dict = ctx.lifespan_context["connections"]
        shell_drv: ShellDriver = connections.pop(port, None)
        if shell_drv is None:
            return SerialConnectResponse(
                port=port,
                connect_status="disconnected",
                message=f"Error: Serial port {port} is not connected or already disconnected"
            )

        try:
            shell_drv.target.deactivate(shell_drv)
        except Exception as e:
            await ctx.warning(f"断开 {port} 时出现警告: {e}")

        await ctx.info(f"串口 {port} 已断开")
        return SerialConnectResponse(
            port=port,
            connect_status="disconnected",
            message=f"Serial port {port} disconnected successfully",
        )

    @mcp_tool(
        name="list_connections",
        description="List all currently connected serial ports",
    )
    async def list_connections(self, ctx: Context = None) -> list[str]:
        """返回当前已激活的串口列表。"""
        connections: dict = ctx.lifespan_context["connections"]
        return list(connections.keys()) or ["当前没有任何已连接的串口"]


# ── 将 SerialSkill 的所有 mcp_tool 注册到 mcp server ──────────────────────
skill = SerialSkill()
skill.register_all(mcp)


def main():
    mcp.run()

if __name__ == "__main__":
    main()
