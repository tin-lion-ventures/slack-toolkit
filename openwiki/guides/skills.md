# Skills System

## Overview

slack-toolkit ships **33 Claude Code skills** as structured Markdown prompt files. These teach Claude Code how to use slack-cli for common Slack operations — installable with a single command.

```bash
slack-cli skills install   # Install all 33 to ~/.claude/skills/
slack-cli skills list      # List all bundled skills
slack-cli skills doctor     # Validate skill integrity
```

Skills are installed to `~/.claude/skills/`. A marker comment (`<!-- installed by slack-cli -->`) identifies files managed by slack-cli so it won't overwrite user-created skills without `--force`.

---

## Two-Layer Architecture

### Layer 1: Operational Skills (28)

These are task-oriented skills — each maps to a specific CLI command group and tells Claude Code what to do for a given task:

| Skill | Command Group | Purpose |
|---|---|---|
| `slack-post` | chat | Post, update, delete, schedule messages |
| `slack-thread` | chat | Thread-based conversation patterns |
| `slack-dm` | conversations | Open and manage DMs |
| `slack-channel-create` | conversations | Create channels with best practices |
| `slack-channel-info` | conversations | Inspect channel details |
| `slack-bookmarks` | bookmarks | Channel bookmarks |
| `slack-search` | search | Message/file search (requires user token) |
| `slack-file-upload` | files | V2 file upload flow |
| `slack-reactions` | reactions | Emoji reactions |
| `slack-emoji` | — | Custom emoji (via passthrough) |
| `slack-status` | users | Presence and status |
| `slack-user-lookup` | users | Find users by ID/email |
| `slack-usergroup` | usergroups | User group management |
| `slack-canvas` | canvas | Canvas CRUD |
| `slack-lists` | — | Slack Lists (via passthrough) |
| `slack-calls` | — | Calls (via passthrough) |
| `slack-reminders` | reminders | Reminder CRUD |
| `slack-dnd` | dnd | Do Not Disturb |
| `slack-schedule` | chat | Scheduled messages |
| `slack-streaming` | — | Streaming patterns |
| `slack-admin` | — | Admin operations (via passthrough) |
| `slack-audit` | — | Audit and compliance (via passthrough) |
| `slack-bulk-ops` | conversations | Bulk operations (invite-all, clone, export, diff, inactive) |
| `slack-assistant` | — | Slack AI assistant (via passthrough) |
| `slack-archive-export` | conversations | Channel archival and member export |
| `slack-docs` | docs | Per-method documentation lookup |
| `slack-identity` | config/auth | Token and identity management |
| `slack-dynamic` | api | Meta-skill: catalog → spec → passthrough (see below) |

### Layer 2: Expert Skills (5)

These are knowledge-oriented skills that teach Claude Code how to do things *correctly* — Slack-specific formatting, best practices, and troubleshooting:

| Skill | Purpose |
|---|---|
| `slack-api-expert` | API method structure, pagination, token types, rate limits, error handling |
| `slack-block-kit` | Block Kit layout system — sections, actions, context, dividers, images, inputs |
| `slack-integration-patterns` | Common integration workflows: webhooks, events API, slash commands, interactive components |
| `slack-mrkdwn` | Slack's mrkdwn formatting syntax (bold, italic, code, links, lists, quotes) |
| `slack-troubleshooting` | Error diagnosis, token troubleshooting, scope issues, rate limit handling |

---

## The Dynamic Meta-Skill

`/slack-dynamic` is the most powerful skill — it teaches a 3-step pattern that covers all 306 Slack API methods, even those without a dedicated CLI command:

1. **Search** the method catalog: `slack-cli methods search "keyword"`
2. **Read** the method spec: `slack-cli methods get method.name`
3. **Call** via passthrough: `slack-cli api method.name --params '{...}'`

This pattern means an AI agent can dynamically discover and call any Slack API method without the CLI having a dedicated command for it.

---

## Skill File Format

Each skill is a Markdown file with YAML-ish frontmatter in `slack_cli/skills_data/`:

```markdown
---
name: slack-post
description: Post, update, delete, and schedule messages in Slack channels
command_name: /slack-post
tags: [chat, messaging, post]
---
<!-- installed by slack-cli -->
# Skill content...
```

The `skills.py` module:
- `_parse_skill_frontmatter()` — extracts name, description, command_name, tags
- `_extract_cli_commands()` — finds `slack-cli` invocations in skill text
- `install_skills()` — copies to `~/.claude/skills/` with marker-based overwrite detection
- `list_skills()` — shows all skills with metadata
- `doctor_skills()` — validates frontmatter and file integrity

---

## Custom Skills

You can create custom skill files following the same format. Place them in `~/.claude/skills/` — slack-cli will not overwrite them (no marker comment). The `--force` flag on `skills install` will overwrite non-marked files.

---

## Skill Description Optimization (v0.2.3)

In v0.2.3, all 33 skill descriptions were rewritten for better AI model selection:

- Descriptions kept under 230 characters (avoids 252-char truncation in model context)
- Trigger phrases front-loaded (the first words a model sees when choosing a skill)
- NOT-clauses added to disambiguate overlapping skills (e.g., "use slack-thread for replies, NOT slack-post")

Source: `slack_cli/skills.py`, `slack_cli/skills_data/*.md`
