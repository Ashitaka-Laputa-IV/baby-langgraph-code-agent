# Baby LangGraph Code Agent

[English](README.md) | 简体中文

一个基于 LangGraph 构建、使用 Rich 终端界面、小巧易读的编程助手。
它会在你启动它的目录里读取、修改并运行代码。需要搜索时，让它执行 `rg`、
`findstr` 或其他 shell 搜索命令即可。

## 环境要求

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- 一个 OpenCode Go API Key

## 安装

```bash
uv sync
```

## 配置

助手只从进程环境变量读取配置，不会加载 `.env` 文件。

| 变量 | 是否必填 | 默认值 | 用途 |
| --- | --- | --- | --- |
| `OPENCODE_GO_API_KEY` | 是 | — | OpenCode Go 推理端点的 API Key（回退读取 `OPENCODE_API_KEY`） |
| `OPENCODEGO_MODEL` | 否 | `deepseek-v4.1-flash` | 发送给服务商的模型 ID（默认 DeepSeek V4.1 Flash） |
| `OPENCODEGO_BASE_URL` | 否 | `https://opencode.ai/inference/go/openai/v1` | OpenAI 兼容端点 |

如果这台机器不允许把代码发送到 OpenCode Go，请把 `OPENCODEGO_BASE_URL`
指向另一个 OpenAI 兼容端点。

## 运行

```bash
uv run baby-code-agent
```

输入一个请求，查看流式输出的回答，并在助手提出 shell 命令时选择批准或拒绝。

命令：

- `/help` — 显示命令列表
- `/reset` — 开启新的对话线程
- `/exit` — 退出会话（Ctrl+C 和 EOF 也会退出）
- `/quit` — `/exit` 的别名

## 数据处理

助手发送给模型的所有内容——你的提示词、它读取的文件内容、工具输出——都会
发往配置的端点，默认是 OpenCode Go。不要把它指向一个你不愿与该服务商共享
内容的代码仓库。

## Shell 命令审批

唯一的安全边界是审批提示。命令执行前，助手会展示完整命令，并把控制字符和
换行显示为可见文本，默认选择为 **否**。被批准的命令不会被沙箱隔离：它们会
以你的用户权限、在工作目录中运行。

文件写入不会弹出确认。写入范围限制在工作目录内，并且会拒绝 `.git/` 元数据
（例如 hooks）。

## 测试

```bash
uv run python -m pytest
```

测试套件完全离线运行，不需要 API Key。`uv run pytest` 通常也可以，除非本地的
启动器中间层拦截了 `pytest` 可执行文件。

## 项目结构

- `src/baby_code_agent/agent.py` — LangGraph 助手组装与系统提示词
- `src/baby_code_agent/tools.py` — 限定在工作目录内的文件系统与 shell 工具
- `src/baby_code_agent/cli.py` — Rich 终端会话与流式渲染
- `src/baby_code_agent/settings.py`、`model.py` — 环境配置与聊天模型
