---
title: 用 LangChain 的 OpenAI 兼容客户端调用 OpenCode Go
date: 2026-11-20
category: developer-experience
module: baby_code_agent.model
problem_type: developer_experience
component: tooling
severity: medium
applies_when:
  - 正在为 OpenCode Go 订阅构建 OpenAI 兼容客户端
  - 向 Go 端点发送请求时返回缺少会话头的 HTTP 400
retire_when: OpenCode Go 不再要求会话请求头，或发布了官方 LangChain 集成；在该服务的 harness 文档与 models.dev 的 provider 条目中确认
tags: [opencode-go, langchain, openai-compatible, session-header, configuration]
---

# 用 LangChain 的 OpenAI 兼容客户端调用 OpenCode Go

[English](opencode-go-langchain-client.md) | 简体中文

## Context（背景）

本项目通过 `langchain-openai` 的 `ChatOpenAI` 调用 OpenCode Go 订阅。该服务商兼容
OpenAI 协议，但并不是可以直接替换的 OpenAI 端点：密钥变量名、base URL 以及一个
必需的会话请求头都属于服务商特有约定，仅从 OpenAI API 的形态看不出来。

## Guidance（做法）

- 从 `OPENCODE_GO_API_KEY` 读取密钥。models.dev 的 provider 条目同时声明
  `OPENCODE_API_KEY`；把它作为回退读取，两种命名都能工作。
- Go 订阅使用 `https://opencode.ai/inference/go/openai/v1`；按量付费（pay-as-you-go）
  使用另一个 base URL。
- 每个请求都带上稳定的会话标识：

```python
ChatOpenAI(
    model="deepseek-v4.1-flash",
    api_key=settings.api_key,
    base_url="https://opencode.ai/inference/go/openai/v1",
    default_headers={"x-opencode-session": session_id},
)
```

- 每个进程或每次对话生成一个 id，例如 `ses_<uuid hex>`；跨轮次复用同一个 id，
  以保证路由与提示词缓存的一致性。

## Why This Matters（为什么重要）

缺少 `x-opencode-session` 时，Go 网关会以 HTTP 400 拒绝请求，消息为
“Request is missing x-opencode-session and cannot be routed efficiently”。
认证本身是先通过的，因此如果不读响应体，失败看起来像模型或请求体的问题。
这个请求头还让服务商复用提示词缓存，直接影响延迟与成本。

## When to Apply（何时适用）

- 任何指向 OpenCode Go 的新客户端、新语言或新 SDK。
- 任何替换 `ChatOpenAI`、或直接构造 `openai` 客户端的重构。
- 密钥有效但 Go 请求返回 400 时的排查。

## Examples（示例）

修改前：普通 OpenAI 形态的客户端在请求时失败。

```text
openai.BadRequestError: Error code: 400 - Request is missing x-opencode-session ...
```

修改后：请求头随每个请求发送，真实冒烟返回正常结果。

```text
model=deepseek-v4.1-flash base_url=https://opencode.ai/inference/go/openai/v1 key=loaded
reply='pong'
```

## Related（相关）

- `src/baby_code_agent/model.py` — 客户端构造与会话 id
- `src/baby_code_agent/settings.py` — 环境变量与默认值
- `tests/test_model.py` — 断言会话请求头存在
- OpenCode Go 文档：`https://opencode.ai/v2/docs/console/go/`
- OpenCode harness base URL：`https://opencode.ai/v2/docs/console/harnesses/`
