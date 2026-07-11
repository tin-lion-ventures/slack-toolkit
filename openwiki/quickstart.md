# slack-toolkit — Quickstart

**slack-toolkit** is a zero-dependency CLI for the Slack Web API. It bundles a 306-method API catalog, 33 Claude Code skills, raw API passthrough, and full profile-based configuration — all running on Python stdlib alone (no `requests`, no `slack_sdk`, no transitive dependencies).

Built for AI agents, automation scripts, and developers who need a scriptable Slack client with their own bot identity, full API coverage, and no MCP server overhead.

---

## Install

```bash
pip install slack-toolkit
# or with uv
uv tool install slack-toolkit
```

Requires Python 3.9+. No other dependencies.

## Configure

Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps), add OAuth scopes (minimum `chat:write`), install it, then:

```bash
slack-cli config set-profile default \
  --bot-token xoxb-your-bot-token \
  --workspace-name "My Workspace"
```

Or set an env var for quick use:

```bash
export SLACK_BOT_TOKEN=xoxb-your-bot-token
```

Config lives at `~/.slack-cli.json` (file mode 600). Multiple workspaces are supported via named profiles.

## Verify

```bash
slack-cli api auth.test
```

## Post a Message

```bash
slack-cli chat post C0YOURCHANNEL "Hello from slack-cli"
```

---

## Feature Overview

| Feature | What it gives you |
|---|---|
| **306-method catalog** | Search, inspect, and call any Slack Web API method offline. Auto-warns at 30 days stale. |
| **33 Claude Code skills** | Structured prompt files that teach Claude Code how to use slack-cli. Install with one command. |
| **Raw API passthrough** | `slack-cli api <method> --params '{...}'` — call any method even without a dedicated command. |
| **Zero dependencies** | Pure Python stdlib. No supply chain surface. |
| **Profile-based config** | Named profiles per workspace, env var overrides for CI, secure file permissions. |
| **Auto-pagination** | Cursor-based pagination handled automatically by `client.paginate()`. |
| **Rate-limit retry** | Exponential backoff with jitter, up to 5 retries on 429 responses. |
| **Per-method docs** | Fetch and cache full API docs from docs.slack.dev with a 30-day TTL. |

---

## Why Not Just Use the Slack MCP?

The Slack MCP server has three limitations this tool addresses:

1. **Identity** — MCP posts as whatever OAuth identity it's configured with. `slack-cli` always uses your bot token.
2. **Coverage** — MCP exposes ~15 tools. slack-cli ships all 306 methods plus raw passthrough.
3. **Distribution** — MCP requires a running process and per-client config. `slack-cli` is a single CLI binary.

---

## Documentation Sections

- [**Architecture Overview**](architecture/overview.md) — Zero-dependency design, module structure, client/config/catalog layers, and how the pieces fit together.
- [**Command Reference**](reference/commands.md) — All 17 command groups and ~70 subcommands with syntax and examples.
- [**Skills System**](guides/skills.md) — 33 Claude Code skills, two-layer architecture, install/doctor, custom skill creation.
- [**Method Catalog & Docs**](guides/method-catalog.md) — 306-method catalog, search/inspect, live updates, per-method doc caching.
- [**Testing & CI**](operations/testing.md) — Test structure, coverage, and the OpenWiki CI workflow.

---

## Key Source Files

| File | Purpose |
|---|---|
| `slack_cli/cli.py` | Argparse command tree — all 17 top-level commands and subcommands (~50K lines) |
| `slack_cli/client.py` | `SlackClient` — HTTP layer (urllib), rate limiting, pagination, file upload |
| `slack_cli/config.py` | Profile-based config with env var overrides |
| `slack_cli/api.py` | Raw API passthrough — the escape hatch for any Slack method |
| `slack_cli/methods.py` | Method catalog system — search, inspect, update (bundled or live) |
| `slack_cli/skills.py` | Skills management — discover, install, list, validate |
| `slack_cli/docs.py` | Per-method documentation fetcher with 30-day cache |
| `slack_cli/catalog_data/methods.json` | Bundled 306-method catalog (shipped in the wheel) |
| `slack_cli/skills_data/*.md` | 33 bundled skill files |
