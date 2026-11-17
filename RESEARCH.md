# Research notes

This tool addresses a narrow and observable failure mode: relative local paths can be interpreted against a caller's working directory and consequently point somewhere unintended. It reports path existence/type for fields explicitly supplied as paths. It does not claim that all MCP clients use the same resolution contract or that these reports define a client's complete behavior.

## References

- [openclaw/mcporter issue #56](https://github.com/openclaw/mcporter/issues/56) reports a relative `dist/index.js` resolution failure from the caller cwd with `MODULE_NOT_FOUND`. This is an issue report, not evidence of a universal MCP rule.
- [openai/codex issue #35448](https://github.com/openai/codex/issues/35448) reports a third-party path resolution problem involving a relative `./...` command and `cwd=.`. It describes a specific reported integration behavior.
- [Python 3.11 pathlib documentation](https://docs.python.org/3.11/library/pathlib.html) documents path operations used here, including absolute paths, resolution and filesystem queries. The implementation is standard-library-only.

## Scope and limits

The checker requires the caller to identify path values and provide `base_directory` and `launch_cwd`. The canonical launch cwd must be beneath the canonical base, including when an absolute launch cwd is supplied. It cannot infer which command arguments are paths, expand variables, apply a client-specific configuration policy, start a server, or prove the target can be executed. `ok` means only that the requested file/directory type was observed at check time. Relative path entries escaping the canonical base through symlinks/junctions are rejected; absolute path entries remain absolute and can intentionally target outside the base. This depends on a trusted local filesystem and is not a race-free security boundary.

See [TESTING.md](TESTING.md) for exact output and exit-code examples. 中文版：[RESEARCH.zh-CN.md](RESEARCH.zh-CN.md)。
