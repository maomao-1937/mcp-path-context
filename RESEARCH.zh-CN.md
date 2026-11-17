# 研究说明

本工具针对一个范围有限且可观察的问题：相对本地路径可能按调用方的工作目录解释，因此指向非预期位置。它只检查调用方明确提供为路径的字段是否存在及类型是否匹配。它不声称所有 MCP 客户端遵循同一解析约定，也不声称这些检查能完整描述某个客户端的行为。

## 参考资料

- [openclaw/mcporter issue #56](https://github.com/openclaw/mcporter/issues/56) 报告相对路径 `dist/index.js` 从调用者 cwd 解析失败并出现 `MODULE_NOT_FOUND`。这是一个具体问题报告，不代表普遍适用的 MCP 规则。
- [openai/codex issue #35448](https://github.com/openai/codex/issues/35448) 报告第三方集成中，相对 `./...` 命令与 `cwd=.` 相关的路径解析问题。这反映的是特定集成的报告行为。
- [Python 3.11 pathlib 文档](https://docs.python.org/3.11/library/pathlib.html) 介绍本工具使用的路径操作，包括绝对路径、解析和文件系统查询。本实现只使用 Python 标准库。

## 范围与限制

调用方必须明确给出路径值、`base_directory` 和 `launch_cwd`。规范化后的启动目录必须位于规范化后的基准目录之下，即使输入的启动目录是绝对路径也是如此。工具无法推断哪些命令参数是路径、展开变量、应用特定客户端配置策略、启动服务器或证明目标可执行。`ok` 只表示检查时观察到指定类型的文件或目录存在。相对路径条目若通过符号链接/目录联接逃出规范化基准目录会被拒绝；绝对路径条目保持绝对，可明确指向基准目录外。检查依赖可信的本地文件系统，不构成无竞态的安全边界。

精确输出和退出码示例见 [TESTING.zh-CN.md](TESTING.zh-CN.md)，英文版见 [RESEARCH.md](RESEARCH.md) 和 [TESTING.md](TESTING.md)。
