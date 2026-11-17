# mcp-path-context

`mcp-path-context` is a small offline Python 3.11+ preflight CLI for checking explicitly labeled local paths against a supplied launch working directory. It helps answer “which local file or directory would this configuration refer to from this cwd?” It does not parse arbitrary command strings, infer path arguments, inspect MCP client behavior, or launch a process.

## Run

```powershell
$base = (Resolve-Path .\fixtures\sample).Path
$input = @{ base_directory = $base; launch_cwd = "."; paths = @(
  @{ label = "server_script"; value = "server.py"; kind = "file" },
  @{ label = "config_dir"; value = "config"; kind = "directory" }
)} | ConvertTo-Json -Depth 4 -Compress
$input | python .\mcp_path_context.py
```

Input is one strict UTF-8 JSON document on stdin, limited to 256 KiB. Its top-level keys must be exactly `base_directory`, `launch_cwd`, and `paths`. `base_directory` must be an absolute local directory. `launch_cwd` may be absolute or relative to that base, but its canonical resolved location must be beneath the canonical base directory; an outside absolute launch cwd is rejected with `path_escape`. `paths` contains 1–64 exact objects with `label`, `value`, and `kind`; labels use 1–64 ASCII letters, digits, `_`, `-`, or `.` and begin with a letter or digit. A path value is a nonempty string up to 4096 characters. `kind` is `file` or `directory`.

Relative values resolve from the effective launch cwd. Absolute path entries remain absolute and may target locations outside the base directory. Relative path entries are checked after symlink/junction resolution and rejected if they escape the canonical base directory. Symlink checking assumes a trusted, non-hostile local filesystem: another process can change links between resolution and status inspection, so this is not a race-free sandbox.

Network/UNC and device namespace paths, URI schemes, alternate data streams, and drive-relative paths are rejected before path inspection. The program makes no network requests and spawns no processes. It does not read environment variables.

## Output and exit codes

Successful checks produce deterministic compact JSON containing only 1-based ordinals and statuses; labels and path text are never echoed. For example, with the two fixture paths existing and having the requested types:

```json
{"results":[{"ordinal":1,"status":"ok"},{"ordinal":2,"status":"ok"}]}
```

Exit `0` means every path exists with its requested type. Exit `1` means at least one status is `missing` or `wrong_kind`. Exit `2` means input, path policy, or I/O error. Errors have fixed codes, for example `{"error":"invalid_json"}`; no exception messages or input values are emitted.

```json
{"results":[{"ordinal":1,"status":"missing"}]}
```

The preceding one-result response exits `1`. See [TESTING.md](TESTING.md) and [RESEARCH.md](RESEARCH.md) for examples and scope. 中文说明见 [README.zh-CN.md](README.zh-CN.md), [TESTING.zh-CN.md](TESTING.zh-CN.md), and [RESEARCH.zh-CN.md](RESEARCH.zh-CN.md)。
