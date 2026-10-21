# Architecture

CLI / localhost UI → Agent → HTML evidence → provider adapter → revisioned plan → explicit approval → generated files → static review → attachments.

- `net.py`: DNS-pinned public HTTPS transport, bounded responses, redirect policy. Never forwards API credentials across redirects.
- `core.py`: HTML parser, SQLite project repository, JSON model adapter, plan schema, approval digest, bounded generate/review loop, path-safe artifact writer.
- `server.py`: loopback HTTP gateway, Host/Origin/CSRF checks, process-only credentials, PKCE OAuth, attachment-only artifact serving.
- `cli.py`: same core workflow without UI; explicit approval prompt.
- `web/`: no build step, no remote scripts, DOM text rendering instead of untrusted HTML interpolation.

## Trust boundaries

Reference page HTML and model output are untrusted. The model cannot call shell commands, run generated code, browse authenticated pages, or access secrets via tools. Approval is enforced by code rather than prompts. File writes are constrained to validated relative names under a generated project ID. Local users with direct access to the data directory are trusted and can alter it; this is not a multi-user hosting product.

## State

`planned → approved → building → complete`; revision returns to `planned`, invalidating approval. Recoverable generation errors return to `approved`. Approval hashes the exact canonical JSON plan. UI uses current revision to prevent stale approval. SQLite stores plans, evidence, audit events and review; tokens never enter it.

## Provider contract

Configured HTTPS Base URL + `/chat/completions`; Bearer token from API key or OAuth. Input: model, system/user messages. Output: `choices[0].message.content` containing JSON. No provider SDK required. OAuth must be a compatible PKCE public client; no browser session token extraction or subscription-login emulation.

## Quality limits

One initial implementation call, one review, at most one correction and final review. Static review success is required for delivery. No claim of visual/browser validation for generated artifacts. The single-file HTML must contain inline assets by prompt contract; future versions should validate external references with a real HTML/JS parser and add sandboxed browser evaluations. Do not treat model review as a security certification.

## Future work

Opt-in browser rendering with sandbox isolation, provider-specific OAuth adapters and refresh, streaming jobs/cancellation/restart recovery, stronger JSON schemas, artifact browser tests, OS credential vault, package signing and release automation.
