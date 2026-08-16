# Architecture Overview

## Design Philosophy

slack-toolkit is built on a single principle: **zero external dependencies**. The entire tool — HTTP client, JSON handling, SSL, CLI parsing, file upload — uses only the Python standard library. This eliminates supply chain risk, package conflicts, and installation friction.

The architecture follows a clean three-layer separation:

```
┌─────────────────────────────────────────────┐
│            CLI Layer (cli.py)                │
│  argparse command tree → handler functions   │
│  17 top-level commands, ~70 subcommands      │
├─────────────────────────────────────────────┤
│         Domain Modules (chat.py,             │
│  conversations.py, files.py, users.py, ...)  │
│  Business logic + output formatting          │
├─────────────────────────────────────────────┤
│         Core Infrastructure                   │
│  client.py   config.py   methods.py          │
│  api.py      skills.py   docs.py             │
└─────────────────────────────────────────────┘
```

---

## Core Infrastructure

### `client.py` — SlackClient

The HTTP layer. All Slack API calls go through `SlackClient`.

- **Token resolution**: supports `bot` (xoxb-), `user` (xoxp-), and `auto` (prefer bot, fall back to user) token types
- **Request formats**: JSON body (`call()`) and form-urlencoded (`call_form()`) for methods that require it
- **Rate limiting**: exponential backoff with jitter on 429 responses, respecting `Retry-After` header, up to 5 retries (`_MAX_RETRIES`)
- **Auto-pagination**: `paginate()` handles cursor-based pagination automatically — auto-detects the list key in the response, follows `response_metadata.next_cursor`, supports a total limit
- **File upload (V2)**: `upload_request()` posts multipart form data to a pre-signed Slack URL without bearer auth (the upload URL is pre-authenticated)

Key entry points:
- `client.call(method_name, params, token_type, body_format)` — POST to any Slack API method, verify `ok=true`
- `client.call_form(method_name, params, token_type)` — form-urlencoded variant
- `client.paginate(method_name, params, token_type, limit, response_key)` — auto-paginate list endpoints
- `client.upload_request(url, file_data, filename, token_type)` — upload to pre-signed URL (step 2 of files.uploadV2)

`SlackApiError` is the standard exception, carrying `error`, `status`, and `body` fields.

### `config.py` — Profile Management

Configuration is stored at `~/.slack-cli.json` with mode 600 (secure file permissions, atomic writes).

**Resolution priority** (highest first):
1. Environment variables: `SLACK_BOT_TOKEN`, `SLACK_USER_TOKEN`, `SLACK_PROFILE`
2. Named profile from config file
3. `default` profile from config file

Each profile contains: `name` (workspace name), `bot_token`, `user_token`, `default_channel`.

The `_build_client(args)` helper in `cli.py` resolves the profile and constructs a `SlackClient` — this is called by every command handler.

### `api.py` — Raw API Passthrough

The escape hatch. `call_method()` takes any Slack API method name and arbitrary params dict, calls `client.call()`, and prints the result. This gives AI agents full Slack API coverage (all 306 methods) even when no dedicated CLI command exists.

```bash
slack-cli api admin.conversations.bulkArchive \
  --params '{"channel_ids": ["C123", "C456"]}' \
  --token-type user
```

### `methods.py` — Method Catalog System

A bundled JSON catalog of all 306 Slack Web API methods, stored at `slack_cli/catalog_data/methods.json` and shipped in the wheel.

- **Local cache**: copied to `~/.slack-cli/methods/catalog.json` on first use
- **Staleness check**: warns if catalog is older than 30 days
- **Live update**: `methods update --live` scrapes docs.slack.dev to refresh the catalog
- **Search/inspect**: `search`, `get`, `list`, `namespaces`, `info` subcommands

Each catalog entry includes: method name, parameters, required scopes, rate tier, and token type.

### `skills.py` — Skills Management

Discovers, installs, lists, and validates the 33 bundled skill `.md` files from `slack_cli/skills_data/`.

- **Install target**: `~/.claude/skills/` (Claude Code's skill directory)
- **Marker comment**: `<!-- installed by slack-cli -->` identifies files managed by slack-cli (won't overwrite user-created skills without `--force`)
- **Doctor**: validates skill frontmatter, file integrity, and catalog alignment

See [Skills System](../guides/skills.md) for the full skill catalog.

### `docs.py` — Per-Method Documentation

Fetches and caches full Slack API method documentation from `docs.slack.dev` as Markdown.

- **Cache location**: `~/.slack-cli/docs/<method>.md`
- **TTL**: 30 days
- **Parsing**: best-effort HTML→Markdown conversion using regex (handles Docusaurus site structure)
- **`--fresh` flag**: bypasses cache for a fresh fetch

---

## Domain Modules

Each domain module wraps related Slack API methods and handles output formatting (human-readable or `--json`):

| Module | Slack API Methods | Key Operations |
|---|---|---|
| `chat.py` | `chat.postMessage`, `chat.update`, `chat.delete`, `chat.scheduleMessage`, `chat.deleteScheduledMessage`, `chat.scheduledMessages.list`, `chat.getPermalink` | Post, update, delete, schedule messages |
| `conversations.py` | `conversations.list`, `.info`, `.history`, `.replies`, `.members`, `.create`, `.archive`, `.unarchive`, `.invite`, `.kick`, `.setTopic`, `.setPurpose`, `.join`, `.leave`, `.open` | Channel/DM CRUD plus composite ops: invite-all, clone-members, export-members, diff, random, inactive |
| `files.py` | `files.getUploadURLExternal`, `files.completeUploadExternal`, `files.list`, `files.info`, `files.delete` | V2 two-step file upload, list, info, delete |
| `users.py` | `users.list`, `users.info`, `users.lookupByEmail`, `users.profile.get`, `users.setPresence`, `users.getPresence` | User lookup, profiles, presence |
| `search.py` | `search.messages`, `search.files`, `search.all` | Search (requires user token) |
| `reactions.py` | `reactions.add`, `.remove`, `.get`, `.list` | Emoji reactions |
| `pins.py` | `pins.add`, `.remove`, `.list` | Message pinning |
| `bookmarks.py` | `bookmarks.add`, `.edit`, `.list`, `.remove` | Channel bookmarks |
| `usergroups.py` | `usergroups.create`, `.list`, `.update`, `.disable`, `.enable`, `.users.list`, `.users.update` | User group management |
| `canvas.py` | `canvases.create`, `conversations.canvases.create`, `canvases.edit`, `.delete`, `.access.set`, `.access.delete`, `.sections.lookup` | Canvas CRUD and access |
| `reminders.py` | `reminders.add`, `.list`, `.complete`, `.delete`, `.info` | Reminder CRUD |
| `dnd.py` | `dnd.info`, `dnd.setSnooze`, `dnd.endSnooze`, `dnd.endDnd`, `dnd.teamInfo` | Do Not Disturb |

---

## CLI Entry Point

`slack_cli/cli.py` is the argparse command tree (~50K bytes). It defines all 17 top-level commands and ~70 subcommands. The entry point is `main()`, registered in `pyproject.toml` as `slack-cli = "slack_cli.cli:main"`.

Each command handler follows the same pattern:
1. Call `_build_client(args)` to resolve the profile and construct a `SlackClient`
2. Delegate to the appropriate domain module function
3. The module function calls `client.call()` / `client.paginate()` and formats output

Global flags: `--version`, `--profile/-p`, `--json/-j`.

---

## Package Structure

```
slack_cli/
├── __init__.py              # __version__ = "0.2.3"
├── cli.py                   # Argparse command tree (entry point)
├── client.py                # SlackClient — HTTP, rate limiting, pagination
├── config.py                # Profile-based configuration
├── api.py                   # Raw API passthrough
├── methods.py               # Method catalog system
├── skills.py                # Skills management
├── docs.py                  # Per-method documentation fetcher
├── chat.py                  # Messages
├── conversations.py         # Channels & DMs
├── files.py                 # File upload/management
├── users.py                 # User info & presence
├── search.py                # Message/file search
├── reactions.py             # Emoji reactions
├── pins.py                  # Message pinning
├── bookmarks.py             # Channel bookmarks
├── usergroups.py            # User groups
├── canvas.py                # Canvas management
├── reminders.py             # Reminders
├── dnd.py                   # Do Not Disturb
├── catalog_data/
│   ├── __init__.py
│   └── methods.json          # 306-method bundled catalog
└── skills_data/
    └── *.md                  # 33 skill files
```

---

## Design Decisions (from Blueprint)

These decisions are documented in `blueprint/BLUEPRINT-DRAFT.md`:

1. **Zero dependencies** — eliminates supply chain risk and installation conflicts. Uses `urllib`, `json`, `ssl`, `argparse` only.
2. **Catalog decoupled from CLI** — the method catalog can be updated independently via `methods update --live` without upgrading the package.
3. **Profile isolation** — each workspace is a named profile, env vars override for CI/automation.
4. **Two-layer skills** — Layer 1 (28 operational skills: what to do) + Layer 2 (5 expert skills: how to do it right).
5. **Dynamic meta-skill** — `/slack-dynamic` teaches a 3-step pattern (search catalog → read spec → call via passthrough) covering all 306 methods.
