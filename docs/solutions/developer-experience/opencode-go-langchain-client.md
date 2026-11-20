---
title: Calling OpenCode Go from a LangChain OpenAI-compatible client
date: 2026-11-20
category: developer-experience
module: baby_code_agent.model
problem_type: developer_experience
component: tooling
severity: medium
applies_when:
  - Building an OpenAI-compatible client against an OpenCode Go subscription
  - A request to the Go endpoint returns HTTP 400 about a missing session header
retire_when: OpenCode Go stops requiring a session header, or publishes a first-party LangChain integration; check the Go harness docs and the models.dev provider entry
tags: [opencode-go, langchain, openai-compatible, session-header, configuration]
---

# Calling OpenCode Go from a LangChain OpenAI-compatible client

English | [简体中文](opencode-go-langchain-client.zh-CN.md)

## Context

The agent talks to an OpenCode Go subscription through `langchain-openai`'s
`ChatOpenAI`. The provider is OpenAI-compatible, but it is not a drop-in OpenAI
endpoint: the key variable, the base URL, and a required routing header are
provider-specific and not obvious from the OpenAI API shape.

## Guidance

- Read the key from `OPENCODE_GO_API_KEY`. The provider entry in models.dev also
  accepts `OPENCODE_API_KEY`; support it as a fallback so either naming works.
- Point the client at `https://opencode.ai/inference/go/openai/v1` for a Go
  subscription. The pay-as-you-go endpoint is a different base URL.
- Send a stable session identifier on every request:

```python
ChatOpenAI(
    model="deepseek-v4.1-flash",
    api_key=settings.api_key,
    base_url="https://opencode.ai/inference/go/openai/v1",
    default_headers={"x-opencode-session": session_id},
)
```

- Generate one id per process or conversation, for example `ses_<uuid hex>`.
  Reuse it across turns so routing and prompt caching stay consistent.

## Why This Matters

Without `x-opencode-session`, the Go gateway rejects the request with HTTP 400
and the message "Request is missing x-opencode-session and cannot be routed
efficiently". Authentication succeeds first, so the failure looks like a model
or payload problem until the response body is read. The header is also what lets
the provider reuse the prompt cache, which changes both latency and cost.

## When to Apply

- Any new client, language, or SDK pointed at OpenCode Go.
- Any refactor that replaces `ChatOpenAI` or constructs a raw `openai` client.
- Diagnostics when a Go request fails with 400 despite a valid key.

## Examples

Before: a plain OpenAI-shaped client fails at request time.

```text
openai.BadRequestError: Error code: 400 - Request is missing x-opencode-session ...
```

After: the header rides on every request, and a live smoke returns a normal reply.

```text
model=deepseek-v4.1-flash base_url=https://opencode.ai/inference/go/openai/v1 key=loaded
reply='pong'
```

## Related

- `src/baby_code_agent/model.py` — client construction and session id
- `src/baby_code_agent/settings.py` — environment variables and defaults
- `tests/test_model.py` — asserts the session header is present
- OpenCode Go docs: `https://opencode.ai/v2/docs/console/go/`
- OpenCode harness base URLs: `https://opencode.ai/v2/docs/console/harnesses/`
