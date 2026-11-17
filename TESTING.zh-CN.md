# 测试与精确示例

在项目根目录运行标准库测试套件：

```sh
python -m unittest discover -s tests -v
```

测试使用临时本地目录和文件，不会触碰用户路径，也不会启动子进程。

## 命令行示例

以下 PowerShell 示例使用仓库内合成目录 `fixtures/sample`，其中包含 `server.py` 和 `config`。在项目根目录运行：

```powershell
$base = (Resolve-Path .\fixtures\sample).Path
$input = @{ base_directory = $base; launch_cwd = "."; paths = @(
  @{ label = "server_script"; value = "server.py"; kind = "file" },
  @{ label = "config_dir"; value = "config"; kind = "directory" }
)} | ConvertTo-Json -Depth 4 -Compress
$input | python .\mcp_path_context.py
```

精确 stdout：

```json
{"results":[{"ordinal":1,"status":"ok"},{"ordinal":2,"status":"ok"}]}
```

退出码：`0`。

若序号 1 不存在而序号 2 存在，精确 stdout 为：

```json
{"results":[{"ordinal":1,"status":"missing"},{"ordinal":2,"status":"ok"}]}
```

退出码：`1`。

即使某个绝对路径条目可以明确指向基准目录外，位于规范化基准目录外的绝对 `launch_cwd` 仍会被拒绝。回归测试使用另一个临时目录的绝对路径作为启动目录，精确 stdout 为：

```json
{"error":"path_escape"}
```

退出码：`2`。

格式错误的 UTF-8/JSON、重复键、不支持的路径语法、无效结构或文件系统错误会输出一个固定错误代码 JSON 并以 `2` 退出。例如输入 `{` 的精确 stdout：

```json
{"error":"invalid_json"}
```

stdout 错误和结果不会包含标签或路径值。英文版见 [TESTING.md](TESTING.md)。
