# mcp-path-context

`mcp-path-context` 是一个离线的 Python 3.11+ 预检命令行工具，用于按调用方提供的启动工作目录检查明确标注的本地路径。它回答“从这个 cwd 看，这个配置明确指向的本地文件或目录是否存在？”它不会解析任意命令字符串、猜测参数是否为路径、推断 MCP 客户端行为，也不会启动进程。

## 运行

```powershell
$base = (Resolve-Path .\fixtures\sample).Path
$input = @{ base_directory = $base; launch_cwd = "."; paths = @(
  @{ label = "server_script"; value = "server.py"; kind = "file" },
  @{ label = "config_dir"; value = "config"; kind = "directory" }
)} | ConvertTo-Json -Depth 4 -Compress
$input | python .\mcp_path_context.py
```

标准输入必须是一个严格 UTF-8 JSON 文档，最大 256 KiB。顶层键必须恰好为 `base_directory`、`launch_cwd`、`paths`。`base_directory` 必须是绝对本地目录。`launch_cwd` 可以是绝对路径，也可以相对该目录，但其规范化解析位置必须位于规范化后的基准目录之下；位于目录外的绝对启动目录会以 `path_escape` 拒绝。`paths` 包含 1–64 个字段恰好为 `label`、`value`、`kind` 的对象；标签是 1–64 个 ASCII 字母、数字、下划线、短横线或句点，并以字母或数字开头。路径值是非空且最多 4096 字符的字符串；`kind` 为 `file` 或 `directory`。

相对路径值以有效启动工作目录为基准解析。绝对路径条目保持绝对，可明确指向基准目录外的位置。相对路径条目会在符号链接/目录联接解析后检查，若逃出规范化后的基准目录则拒绝。该检查假设本地文件系统可信：其他进程可能在解析和状态检查之间更改链接，因此它不是无竞态的沙箱。

网络/UNC 与设备命名空间路径、URI scheme、备用数据流以及盘符相对路径会在路径检查前拒绝。程序不联网、不启动进程，也不读取环境变量。

## 输出与退出码

输出为确定性的紧凑 JSON，只包含从 1 开始的序号和状态，不会回显标签或路径。若示例中的两个路径均存在且类型匹配：

```json
{"results":[{"ordinal":1,"status":"ok"},{"ordinal":2,"status":"ok"}]}
```

退出码 `0` 表示全部存在且类型匹配；`1` 表示至少一个状态为 `missing` 或 `wrong_kind`；`2` 表示输入、路径策略或 I/O 错误。错误使用固定代码，例如 `{"error":"invalid_json"}`；不会输出异常详情或输入值。

```json
{"results":[{"ordinal":1,"status":"missing"}]}
```

上述单项结果的退出码为 `1`。示例、测试和研究范围见 [TESTING.zh-CN.md](TESTING.zh-CN.md) 与 [RESEARCH.zh-CN.md](RESEARCH.zh-CN.md)。英文说明见 [README.md](README.md)、[TESTING.md](TESTING.md) 和 [RESEARCH.md](RESEARCH.md)。
