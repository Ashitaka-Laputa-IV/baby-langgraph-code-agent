# Baby LangGraph Code Agent

English | [简体中文](README.zh-CN.md)

A small, readable coding agent built on LangGraph with a Rich terminal interface.
It reads, edits, and runs code in the directory where you start it. For search, ask
it to run `rg`, `findstr`, or another shell search command.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- An OpenCode Go API key

## Install

```bash
uv sync
```

## Configuration

The agent reads configuration from the process environment only. It never loads a
`.env` file.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `OPENCODE_API_KEY` | yes | — | API key for the OpenCode Go inference endpoint |
| `OPENCODEGO_MODEL` | no | `deepseek-v4.1-flash` | Model id sent to the provider (DeepSeek V4.1 Flash by default) |
| `OPENCODEGO_BASE_URL` | no | `https://opencode.ai/inference/go/openai/v1` | OpenAI-compatible endpoint |

Point `OPENCODEGO_BASE_URL` at another OpenAI-compatible endpoint when this machine
must not send code to OpenCode Go.

## Run

```bash
uv run baby-code-agent
```

Type a request, review the streamed answer, and approve or deny shell commands as
they are proposed.

Commands:

- `/help` — show the command list
- `/reset` — start a new conversation thread
- `/exit` — leave the session (Ctrl+C and EOF also exit)
- `/quit` — alias for `/exit`

## Data handling

Everything the agent sends to the model — your prompts, file contents it reads, and
tool output — goes to the configured endpoint, by default OpenCode Go. Do not point
it at a checkout whose contents you cannot share with that provider.

## Shell approval

The only safety boundary is the approval prompt. Before a command runs, the agent
shows the complete command, with control characters and newlines made visible, and
defaults to **no**. Approved commands are not sandboxed: they run with your user
permissions in the working directory.

File writes are not confirmed. They are limited to the working directory and refuse
`.git/` metadata such as hooks.

## Test

```bash
uv run python -m pytest
```

The test suite runs offline and does not require an API key. `uv run pytest` works
too unless a local launcher shim intercepts the `pytest` executable.

## Layout

- `src/baby_code_agent/agent.py` — LangGraph agent assembly and system prompt
- `src/baby_code_agent/tools.py` — rooted filesystem and shell tools
- `src/baby_code_agent/cli.py` — Rich terminal session and streaming renderer
- `src/baby_code_agent/settings.py`, `model.py` — environment config and chat model
