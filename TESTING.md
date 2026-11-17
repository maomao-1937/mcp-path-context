# Testing and exact examples

Run the standard-library suite from the repository root:

```sh
python -m unittest discover -s tests -v
```

The suite builds temporary local directories and files; it does not touch user paths or launch child processes.

## CLI example

The following PowerShell example uses the checked-in synthetic `fixtures/sample` directory, which contains `server.py` and `config`. From the project root, run:

```powershell
$base = (Resolve-Path .\fixtures\sample).Path
$input = @{ base_directory = $base; launch_cwd = "."; paths = @(
  @{ label = "server_script"; value = "server.py"; kind = "file" },
  @{ label = "config_dir"; value = "config"; kind = "directory" }
)} | ConvertTo-Json -Depth 4 -Compress
$input | python .\mcp_path_context.py
```

Exact stdout:

```json
{"results":[{"ordinal":1,"status":"ok"},{"ordinal":2,"status":"ok"}]}
```

Exit code: `0`.

If ordinal 1 is absent while ordinal 2 exists:

```json
{"results":[{"ordinal":1,"status":"missing"},{"ordinal":2,"status":"ok"}]}
```

Exit code: `1`.

An absolute `launch_cwd` outside the canonical base is rejected even if an individual absolute path entry is otherwise allowed to refer outside the base. For a regression check, pass `launch_cwd` as a sibling temporary directory's absolute path; exact stdout is:

```json
{"error":"path_escape"}
```

Exit code: `2`.

Malformed UTF-8/JSON, duplicate keys, unsupported path syntax, invalid shape, or filesystem errors produce one fixed-code JSON object and exit `2`. For example, input `{` produces exactly:

```json
{"error":"invalid_json"}
```

No label or path value appears in stdout errors or results. 中文版：[TESTING.zh-CN.md](TESTING.zh-CN.md)。
