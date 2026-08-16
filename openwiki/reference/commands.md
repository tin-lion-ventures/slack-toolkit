# Command Reference

All commands support `--json/-j` for raw JSON output and `--profile/-p` for workspace switching.

## Global Flags

```
--version             Print slack-cli version
--profile PROFILE     Use a named config profile
--json                Output raw JSON (most commands)
--help                Show help for any command or subcommand
```

---

## `config` — Manage Profiles

```bash
slack-cli config show                                    # Show current config
slack-cli config set-profile NAME --bot-token xoxb-...   # Create/update profile
  --user-token xoxp-... --workspace-name "..." --default-channel "..."
slack-cli config set-default NAME                        # Set default profile
slack-cli config remove-profile NAME                     # Remove a profile
```

Config lives at `~/.slack-cli.json` (mode 600). Env vars `SLACK_BOT_TOKEN`, `SLACK_USER_TOKEN`, `SLACK_PROFILE` override config file values.

---

## `chat` — Send & Manage Messages

```bash
slack-cli chat post CHANNEL TEXT [--blocks JSON] [--thread-ts TS] [--no-unfurl]
slack-cli chat update CHANNEL TS [--text TEXT] [--blocks JSON]
slack-cli chat delete CHANNEL TS
slack-cli chat schedule CHANNEL TEXT POST_AT [--blocks JSON] [--thread-ts TS]
slack-cli chat schedule-list [--channel]
slack-cli chat schedule-delete CHANNEL SCHEDULED_MESSAGE_ID
slack-cli chat permalink CHANNEL MESSAGE_TS
```

Wraps: `chat.postMessage`, `chat.update`, `chat.delete`, `chat.scheduleMessage`, `chat.scheduledMessages.list`, `chat.deleteScheduledMessage`, `chat.getPermalink`.

---

## `conversations` (alias: `conv`) — Channels & DMs

### Standard Operations

```bash
slack-cli conv list [--types public_channel,private_channel] [--include-archived] [--limit N]
slack-cli conv info CHANNEL
slack-cli conv history CHANNEL [--limit N] [--oldest TS] [--latest TS]
slack-cli conv replies CHANNEL TS [--limit N]
slack-cli conv members CHANNEL [--limit N]
slack-cli conv create NAME [--private]
slack-cli conv archive CHANNEL
slack-cli conv unarchive CHANNEL
slack-cli conv invite CHANNEL USERS
slack-cli conv kick CHANNEL USER
slack-cli conv topic CHANNEL TOPIC
slack-cli conv purpose CHANNEL PURPOSE
slack-cli conv join CHANNEL
slack-cli conv leave CHANNEL
slack-cli conv open --users USER_IDS
```

### Composite Operations

```bash
slack-cli conv invite-all CHANNEL [--dry-run]          # Batches in groups of 30 (Slack API limit)
slack-cli conv clone-members --from CHANNEL_A --to CHANNEL_B [--dry-run]
slack-cli conv export-members CHANNEL [--format table|csv|json|markdown]
slack-cli conv diff CHANNEL_A CHANNEL_B
slack-cli conv random CHANNEL
slack-cli conv inactive CHANNEL [--days N] [--dry-run]  # Scans last 1000 messages
```

Wraps: `conversations.list`, `.info`, `.history`, `.replies`, `.members`, `.create`, `.archive`, `.unarchive`, `.invite`, `.kick`, `.setTopic`, `.setPurpose`, `.join`, `.leave`, `.open`.

**Notes:**
- `export-members` makes one `users.info` call per member — can be slow for large channels.
- `inactive` scans history since cutoff, limited to 1000 messages initially.

---

## `users` — User Information & Presence

```bash
slack-cli users list [--limit N]
slack-cli users info USER
slack-cli users lookup EMAIL
slack-cli users profile USER
slack-cli users presence USER
slack-cli users set-presence auto|away
```

Wraps: `users.list`, `users.info`, `users.lookupByEmail`, `users.profile.get`, `users.setPresence`, `users.getPresence`.

---

## `search` — Message & File Search

```bash
slack-cli search messages QUERY [--sort timestamp|relevance] [--sort-dir asc|desc] [--count N]
slack-cli search files QUERY [--sort ...] [--sort-dir ...] [--count N]
slack-cli search all QUERY [--sort ...] [--sort-dir ...] [--count N]
```

**Requires user token** (`xoxp-`). All search methods use `token_type="user"`. Supports Slack search operators in the query string.

Wraps: `search.messages`, `search.files`, `search.all`.

---

## `files` — File Upload & Management

```bash
slack-cli files upload FILEPATH [--channels CHANNELS] [--title TITLE] [--comment COMMENT] [--thread-ts TS]
slack-cli files list [--channel CHANNEL] [--user USER] [--types TYPES] [--count N]
slack-cli files info FILE_ID
slack-cli files delete FILE_ID
```

Uses the **V2 two-step upload flow**:
1. `files.getUploadURLExternal` — get a pre-signed upload URL
2. POST file data to the pre-signed URL (no Slack auth header)
3. `files.completeUploadExternal` — register the file and share to channels

Wraps: `files.getUploadURLExternal`, `files.completeUploadExternal`, `files.list`, `files.info`, `files.delete`.

---

## `reactions` (alias: `react`) — Emoji Reactions

```bash
slack-cli reactions add CHANNEL TIMESTAMP NAME
slack-cli reactions remove CHANNEL TIMESTAMP NAME
slack-cli reactions get CHANNEL TIMESTAMP
slack-cli reactions list [--user USER] [--count N]
```

Wraps: `reactions.add`, `.remove`, `.get`, `.list`.

---

## `pins` — Message Pinning

```bash
slack-cli pins add CHANNEL TIMESTAMP
slack-cli pins remove CHANNEL TIMESTAMP
slack-cli pins list CHANNEL
```

Wraps: `pins.add`, `.remove`, `.list`.

---

## `bookmarks` (alias: `bm`) — Channel Bookmarks

```bash
slack-cli bookmarks add CHANNEL TITLE LINK [--emoji EMOJI]
slack-cli bookmarks edit CHANNEL BOOKMARK_ID [--title ...] [--link ...] [--emoji ...]
slack-cli bookmarks list CHANNEL
slack-cli bookmarks remove CHANNEL BOOKMARK_ID
```

Wraps: `bookmarks.add`, `.edit`, `.list`, `.remove`.

---

## `usergroups` (alias: `ug`) — User Groups

```bash
slack-cli ug create NAME [--handle HANDLE] [--description DESC] [--channels CHANNELS]
slack-cli ug list [--include-disabled] [--include-users]
slack-cli ug update USERGROUP [--name ...] [--handle ...] [--description ...] [--channels ...]
slack-cli ug disable USERGROUP
slack-cli ug enable USERGROUP
slack-cli ug members-list USERGROUP [--include-disabled]
slack-cli ug members-update USERGROUP --users USER_IDS
```

Wraps: `usergroups.create`, `.list`, `.update`, `.disable`, `.enable`, `.users.list`, `.users.update`.

---

## `canvas` — Canvas Management

```bash
slack-cli canvas create [--title TITLE] [--content JSON] [--channel CHANNEL]
slack-cli canvas edit CANVAS_ID --changes JSON
slack-cli canvas delete CANVAS_ID
slack-cli canvas access-set CANVAS_ID read|write [--users IDS] [--channels IDS]
slack-cli canvas access-delete CANVAS_ID [--users IDS] [--channels IDS]
slack-cli canvas sections CANVAS_ID [--contains-text TEXT]
```

Wraps: `canvases.create`, `conversations.canvases.create`, `canvases.edit`, `canvases.delete`, `canvases.access.set`, `canvases.access.delete`, `canvases.sections.lookup`.

---

## `reminders` (alias: `rem`) — Reminders

```bash
slack-cli rem add TEXT TIME [--user USER]
slack-cli rem list
slack-cli rem info REMINDER
slack-cli rem complete REMINDER
slack-cli rem delete REMINDER
```

Supports natural language time (e.g., "in 30 minutes", "tomorrow at 9am").

Wraps: `reminders.add`, `.list`, `.info`, `.complete`, `.delete`.

---

## `dnd` — Do Not Disturb

```bash
slack-cli dnd info [--user USER]
slack-cli dnd set-snooze --minutes N
slack-cli dnd end-snooze
slack-cli dnd end-dnd
slack-cli dnd team-info [--users USER_IDS]
```

Wraps: `dnd.info`, `dnd.setSnooze`, `dnd.endSnooze`, `dnd.endDnd`, `dnd.teamInfo`.

---

## `api` — Raw API Passthrough

```bash
slack-cli api METHOD_NAME [--params JSON] [--token-type bot|user|auto]
```

Call any of the 306 Slack API methods by name with arbitrary params. The escape hatch for methods without dedicated commands.

Example:
```bash
slack-cli api admin.conversations.bulkArchive \
  --params '{"channel_ids": ["C123", "C456"]}' \
  --token-type user
```

Source: `slack_cli/api.py`

---

## `methods` — Method Catalog

```bash
slack-cli methods search QUERY [--limit N]
slack-cli methods get METHOD_NAME
slack-cli methods list [--namespace NAMESPACE]
slack-cli methods namespaces
slack-cli methods info
slack-cli methods update [--live]
```

- `update` (no flags) resets to bundled catalog (offline).
- `update --live` fetches from docs.slack.dev.
- Auto-warns if catalog is older than 30 days.

Source: `slack_cli/methods.py`, `slack_cli/catalog_data/methods.json`

---

## `docs` — Per-Method Documentation

```bash
slack-cli docs METHOD_NAME [--fresh]
```

Fetches and caches Slack API method docs from docs.slack.dev as Markdown. Cache lives at `~/.slack-cli/docs/` with a 30-day TTL. Use `--fresh` to bypass cache.

Source: `slack_cli/docs.py`

---

## `skills` — Claude Code Skills

```bash
slack-cli skills install [--force]
slack-cli skills list
slack-cli skills doctor
```

Installs 33 bundled skill files to `~/.claude/skills/`. See [Skills System](../guides/skills.md) for details.

Source: `slack_cli/skills.py`
