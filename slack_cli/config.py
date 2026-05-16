"""Configuration management for slack-cli.

Reads from ~/.slack-cli.json or environment variables.
Supports multiple named profiles for different Slack workspaces.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

CONFIG_FILE = Path.home() / ".slack-cli.json"

DEFAULT_CONFIG = {
    "default_profile": "default",
    "profiles": {
        "default": {
            "name": "",
            "bot_token": "",
            "user_token": "",
            "default_channel": "",
        }
    },
}


def load_config() -> dict:
    """Load config file, creating default if missing."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    import copy
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Write config to disk atomically with secure permissions."""
    import tempfile
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=CONFIG_FILE.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=2)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, CONFIG_FILE)
    except Exception:
        os.unlink(tmp_path)
        raise


def get_profile(profile_name: Optional[str] = None) -> dict:
    """Resolve the active profile, with env-var overrides.

    Priority order for bot_token and user_token:
    1. Per-profile env var: SLACK_<PROFILE_UPPER>_BOT_TOKEN / _USER_TOKEN
       (takes precedence over both the global env var and the profile file —
       this is the on-demand-resolution path; tokens live in 1Password
       and are read into the env at invocation time, not persisted to disk)
    2. Global env var: SLACK_BOT_TOKEN / SLACK_USER_TOKEN
       (preserved for backwards compatibility with single-bot setups)
    3. Profile file: ~/.slack-cli.json profile.bot_token / profile.user_token
       (legacy persistent storage; still honoured but no longer required)

    The per-profile env var name is constructed from the resolved profile
    name with `[^A-Z0-9]` characters replaced by `_` and the string
    upper-cased. So profile "ship" -> SLACK_SHIP_BOT_TOKEN; profile
    "my-bot" -> SLACK_MY_BOT_BOT_TOKEN.
    """
    import re
    config = load_config()

    name = (
        profile_name
        or os.environ.get("SLACK_PROFILE")
        or config.get("default_profile", "default")
    )
    profiles = config.get("profiles", {})
    profile = profiles.get(name, {})

    # Normalise profile name to a valid env-var suffix.
    env_safe = re.sub(r"[^A-Za-z0-9]", "_", name).upper()
    per_profile_bot = os.environ.get(f"SLACK_{env_safe}_BOT_TOKEN")
    per_profile_user = os.environ.get(f"SLACK_{env_safe}_USER_TOKEN")

    bot_token = (
        per_profile_bot
        or os.environ.get("SLACK_BOT_TOKEN")
        or profile.get("bot_token", "")
    )
    user_token = (
        per_profile_user
        or os.environ.get("SLACK_USER_TOKEN")
        or profile.get("user_token", "")
    )
    default_channel = profile.get("default_channel", "")

    return {
        "bot_token": bot_token,
        "user_token": user_token,
        "default_channel": default_channel,
        "profile_name": name,
        "workspace_name": profile.get("name", ""),
    }


def require_profile(profile_name: Optional[str] = None) -> dict:
    """Get profile or exit with error if not configured.

    Error message names the expected per-profile env var so the operator
    knows which name to set (or which 1Password item to read).
    """
    import re
    p = get_profile(profile_name)
    if not p["bot_token"]:
        env_safe = re.sub(r"[^A-Za-z0-9]", "_", p["profile_name"]).upper()
        expected_env = f"SLACK_{env_safe}_BOT_TOKEN"
        print("Error: Slack bot token not configured.", file=sys.stderr)
        print(
            f"  Expected one of (in priority order):",
            file=sys.stderr,
        )
        print(
            f"    1. Per-profile env var: {expected_env}",
            file=sys.stderr,
        )
        print(
            f"       (Tin Lion pattern: read on demand from 1Password,",
            file=sys.stderr,
        )
        print(
            f"        e.g. $env:{expected_env} = "
            f"(op read \"op://Superesque - Agents/<item-name>/credential\"))",
            file=sys.stderr,
        )
        print(
            f"    2. Global env var: SLACK_BOT_TOKEN",
            file=sys.stderr,
        )
        print(
            f"    3. Profile file entry: "
            f"slack-cli config set-profile {p['profile_name']} --bot-token xoxb-...",
            file=sys.stderr,
        )
        sys.exit(1)
    return p
