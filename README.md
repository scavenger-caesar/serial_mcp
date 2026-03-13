# 使用方式
## Antigravity
`~/.gemini/antigravity/mcp_config.json`
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