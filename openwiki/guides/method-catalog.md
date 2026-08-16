# Method Catalog & Docs

## The 306-Method Catalog

slack-toolkit bundles a complete catalog of all 306 Slack Web API methods as a local JSON file at `slack_cli/catalog_data/methods.json` (shipped in the Python wheel).

This catalog is the "library card" that gives AI agents dynamic capability to discover and call any Slack API method — even those without a dedicated CLI command.

### Catalog Entry Structure

Each entry in the catalog includes:

| Field | Description |
|---|---|
| Method name | Dotted name (e.g., `chat.postMessage`, `conversations.list`) |
| Parameters | Expected params with types |
| Required scopes | OAuth scopes needed to call the method |
| Rate tier | Slack's rate limit classification |
| Token type | `bot` (xoxb-) or `user` (xoxp-) token required |

### Using the Catalog

```bash
# Search by keyword
slack-cli methods search usergroups

# Get full details for a method
slack-cli methods get conversations.open

# List methods in a namespace
slack-cli methods list --namespace admin.conversations

# List all namespaces
slack-cli methods namespaces

# Catalog stats (method count, last updated)
slack-cli methods info
```

### Catalog Updates

The catalog is decoupled from the CLI release cycle — it can be updated independently:

```bash
slack-cli methods update          # Reset to bundled catalog (offline, reliable)
slack-cli methods update --live   # Fetch from docs.slack.dev
```

**Staleness detection**: the catalog auto-warns if it's older than 30 days. The local cache lives at `~/.slack-cli/methods/catalog.json` with metadata in `~/.slack-cli/methods/meta.json`.

**Live update mechanism** (`methods update --live`): scrapes `https://docs.slack.dev/reference/methods` using urllib, parses the page to extract method names and metadata, and writes the refreshed catalog locally.

Source: `slack_cli/methods.py`, `slack_cli/catalog_data/methods.json`

---

## Per-Method Documentation

The `docs` command fetches and caches full API method documentation directly from `docs.slack.dev`:

```bash
slack-cli docs conversations.open          # Fetch (or read from cache)
slack-cli docs chat.postMessage --fresh    # Bypass cache
```

### How It Works

1. **Fetch**: `urllib.request` GET to `https://docs.slack.dev/reference/methods/{method}`
2. **Parse**: Best-effort HTML→Markdown conversion using regex. Handles the Docusaurus site structure — extracts headings, tables, paragraphs, and code blocks; strips inline HTML tags.
3. **Cache**: Saves to `~/.slack-cli/docs/{method}.md` with a 30-day TTL
4. **Output**: Prints Markdown to stdout (or JSON with `--json`)

### Cache Management

- **Location**: `~/.slack-cli/docs/`
- **TTL**: 30 days (`_is_cache_fresh()` checks file modification time)
- **`--fresh`**: Bypasses cache and re-fetches
- **`_cache_path()`**: Converts method name to safe filename (e.g., `conversations.open` → `conversations.open.md`)

Source: `slack_cli/docs.py`

---

## The Dynamic Pattern

Together, the catalog and docs enable a powerful 3-step pattern for AI agents (codified in the `/slack-dynamic` skill):

1. **Search** the catalog to find the right method:
   ```bash
   slack-cli methods search "archive channel"
   ```
2. **Read** the method spec for parameters and scopes:
   ```bash
   slack-cli methods get conversations.archive
   ```
3. **Call** via the raw API passthrough:
   ```bash
   slack-cli api conversations.archive --params '{"channel": "C123456"}'
   ```

This pattern covers all 306 Slack API methods, including those without dedicated CLI commands.
