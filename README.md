# Serial Shell MCP

一个基于 [labgrid](https://github.com/labgrid-project/labgrid) 和 [FastMCP](https://github.com/jlowin/fastmcp) 的串口 Shell MCP 服务，支持通过 AI 助手连接嵌入式设备串口并执行 Shell 命令。

## 使用方式

### Antigravity

在 `~/.gemini/antigravity/mcp_config.json` 中添加以下配置（直接从 GitHub 运行，无需本地克隆）：

```json
{
  "mcpServers": {
    "serial_mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/scavenger-caesar/serial_mcp.git",
        "serial-shell-mcp"
      ]
    }
  }
}
```

---

## 本地开发调试

### 环境准备

> 前置依赖：[uv](https://docs.astral.sh/uv/)（Python 包管理器）

```bash
# 克隆仓库
git clone https://github.com/scavenger-caesar/serial_mcp.git
cd serial_mcp

# 安装依赖并创建虚拟环境
uv sync
```

### 直接运行服务

```bash
# 在虚拟环境中运行 MCP 服务（stdio 模式）
uv run serial-shell-mcp
```

### 配置 Antigravity 使用本地版本

将 `~/.gemini/antigravity/mcp_config.json` 中的配置改为指向本地项目路径，以便调试时实时生效：

```json
{
  "mcpServers": {
    "serial_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/serial_mcp",
        "run",
        "serial-shell-mcp"
      ]
    }
  }
}
```

> 将 `/path/to/serial_mcp` 替换为实际的本地项目绝对路径，例如 `/home/xxx/code/serial_mcp`。

### 使用 MCP Inspector 调试

1. 启用venv虚拟环境
```bash
source .venv/bin/activate
```
2. 使用fastmcp dev inspector 启动服务
```bash
fastmcp dev inspector serial_shell_mcp/server.py
```

### 项目结构

```
serial_mcp/
├── pyproject.toml              # 项目配置与依赖声明
├── serial_shell_mcp/
│   └── server.py               # MCP 服务主入口，定义所有串口工具
└── README.md
```

### 可用工具一览

| 工具名               | 描述                               |
| -------------------- | ---------------------------------- |
| `connect_serial`     | 连接串口设备并建立 Shell 会话      |
| `run_command`        | 在已连接的串口上执行 Shell 命令    |
| `disconnect_serial`  | 断开指定串口连接                   |
| `list_connections`   | 列出当前所有已连接的串口           |