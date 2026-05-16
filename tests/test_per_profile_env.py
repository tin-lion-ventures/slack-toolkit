"""Tests for per-profile env-var bot-token resolution.

Tin Lion fork — covers the no-disk-persistence credential pattern:
bot tokens resolved from SLACK_<PROFILE_UPPER>_BOT_TOKEN at invocation
time, with fallback to global SLACK_BOT_TOKEN then to profile file.
"""
import json
import os
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Redirect CONFIG_FILE to a temp path so tests don't touch ~/.slack-cli.json."""
    config_path = tmp_path / ".slack-cli.json"
    monkeypatch.setattr("slack_cli.config.CONFIG_FILE", config_path)
    return config_path


def _write_config(path: Path, profiles: dict, default: str = "default"):
    path.write_text(json.dumps({
        "default_profile": default,
        "profiles": profiles,
    }, indent=2))


def _clear_slack_env(monkeypatch):
    """Remove every SLACK_*_BOT_TOKEN / SLACK_*_USER_TOKEN from the test env."""
    for key in list(os.environ.keys()):
        if key.startswith("SLACK_") and (key.endswith("_BOT_TOKEN") or key.endswith("_USER_TOKEN")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_USER_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_PROFILE", raising=False)


def test_per_profile_env_var_takes_precedence_over_profile_file(tmp_config, monkeypatch):
    """SLACK_SHIP_BOT_TOKEN beats profile file's bot_token field."""
    _clear_slack_env(monkeypatch)
    _write_config(tmp_config, {
        "ship": {"name": "Test WS", "bot_token": "xoxb-from-file", "user_token": "", "default_channel": ""},
    })
    monkeypatch.setenv("SLACK_SHIP_BOT_TOKEN", "xoxb-from-env")

    from slack_cli.config import get_profile
    result = get_profile("ship")

    assert result["bot_token"] == "xoxb-from-env"
    assert result["profile_name"] == "ship"


def test_per_profile_env_var_takes_precedence_over_global_env_var(tmp_config, monkeypatch):
    """SLACK_SHIP_BOT_TOKEN beats SLACK_BOT_TOKEN."""
    _clear_slack_env(monkeypatch)
    _write_config(tmp_config, {
        "ship": {"name": "", "bot_token": "", "user_token": "", "default_channel": ""},
    })
    monkeypatch.setenv("SLACK_SHIP_BOT_TOKEN", "xoxb-per-profile")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-global")

    from slack_cli.config import get_profile
    result = get_profile("ship")

    assert result["bot_token"] == "xoxb-per-profile"


def test_falls_back_to_global_env_var_when_per_profile_unset(tmp_config, monkeypatch):
    """SLACK_BOT_TOKEN used when SLACK_SHIP_BOT_TOKEN is absent."""
    _clear_slack_env(monkeypatch)
    _write_config(tmp_config, {
        "ship": {"name": "", "bot_token": "", "user_token": "", "default_channel": ""},
    })
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-global-fallback")

    from slack_cli.config import get_profile
    result = get_profile("ship")

    assert result["bot_token"] == "xoxb-global-fallback"


def test_falls_back_to_profile_file_when_no_env_var(tmp_config, monkeypatch):
    """profile.bot_token used when no env var is set — backwards compat."""
    _clear_slack_env(monkeypatch)
    _write_config(tmp_config, {
        "ship": {"name": "", "bot_token": "xoxb-from-file-only", "user_token": "", "default_channel": ""},
    })

    from slack_cli.config import get_profile
    result = get_profile("ship")

    assert result["bot_token"] == "xoxb-from-file-only"


def test_require_profile_fails_with_naming_guidance_when_all_paths_unset(tmp_config, monkeypatch, capsys):
    """Failure message names the expected per-profile env var."""
    _clear_slack_env(monkeypatch)
    _write_config(tmp_config, {
        "curator": {"name": "", "bot_token": "", "user_token": "", "default_channel": ""},
    })

    from slack_cli.config import require_profile

    with pytest.raises(SystemExit) as exc_info:
        require_profile("curator")

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "SLACK_CURATOR_BOT_TOKEN" in captured.err
    assert "op read" in captured.err
    assert "op://Superesque - Agents" in captured.err


def test_user_token_per_profile_env_var(tmp_config, monkeypatch):
    """SLACK_<PROFILE>_USER_TOKEN follows the same pattern as bot token."""
    _clear_slack_env(monkeypatch)
    _write_config(tmp_config, {
        "ship": {"name": "", "bot_token": "xoxb-bot", "user_token": "", "default_channel": ""},
    })
    monkeypatch.setenv("SLACK_SHIP_USER_TOKEN", "xoxp-per-profile-user")

    from slack_cli.config import get_profile
    result = get_profile("ship")

    assert result["user_token"] == "xoxp-per-profile-user"


def test_profile_name_with_hyphen_normalises_to_underscore_in_env_var(tmp_config, monkeypatch):
    """Profile 'my-bot' -> SLACK_MY_BOT_BOT_TOKEN (hyphen replaced)."""
    _clear_slack_env(monkeypatch)
    _write_config(tmp_config, {
        "my-bot": {"name": "", "bot_token": "", "user_token": "", "default_channel": ""},
    })
    monkeypatch.setenv("SLACK_MY_BOT_BOT_TOKEN", "xoxb-hyphen-normalised")

    from slack_cli.config import get_profile
    result = get_profile("my-bot")

    assert result["bot_token"] == "xoxb-hyphen-normalised"
