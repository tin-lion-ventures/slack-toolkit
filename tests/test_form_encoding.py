"""Regression tests for request body encoding and cursor pagination.

Background (2026-07-11): the client defaulted to application/json POST
bodies, but GET-style Web API methods (conversations.list, users.list, ...)
only read form-encoded params. Slack silently ignored the JSON body, so
`types`, `limit`, `exclude_archived`, and `cursor` were all dropped and every
call returned the default public-only first page with no error. A private
channel (#agent-native-os) was invisible to an agent as a result.

The fake Slack endpoints below reproduce that server behavior: they only
parse form-encoded bodies and ignore JSON ones, exactly like the real
conversations.list. Offline -- urllib.request.urlopen is mocked.
"""
import io
import json
import urllib.parse
from unittest import mock

from slack_cli.client import SlackClient

PUBLIC_CHANNEL = {"id": "C111GENERAL", "name": "general", "is_private": False}
PRIVATE_CHANNEL = {"id": "C0B085ZRKH9", "name": "agent-native-os", "is_private": True}


def _response(payload):
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


def _parse_request(req):
    """Parse params the way Slack does: form bodies only, JSON ignored."""
    ctype = req.get_header("Content-type", "")
    if ctype.startswith("application/x-www-form-urlencoded"):
        return dict(urllib.parse.parse_qsl(req.data.decode("utf-8")))
    return {}


def _fake_conversations_list(req, **kwargs):
    """Mimic conversations.list: default public-only unless form params say otherwise."""
    params = _parse_request(req)
    types = params.get("types", "public_channel")
    channels = []
    if "public_channel" in types:
        channels.append(PUBLIC_CHANNEL)
    if "private_channel" in types:
        channels.append(PRIVATE_CHANNEL)
    return _response(
        {"ok": True, "channels": channels, "response_metadata": {"next_cursor": ""}}
    )


def _client():
    return SlackClient(bot_token="test-token-not-real")


def test_call_sends_form_encoded_body_by_default():
    """client.call must form-encode params so GET-style methods see them."""
    captured = {}

    def fake_urlopen(req, **kwargs):
        captured["content_type"] = req.get_header("Content-type", "")
        captured["body"] = req.data.decode("utf-8")
        return _response({"ok": True})

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        _client().call(
            "conversations.list",
            params={"types": "private_channel", "exclude_archived": True, "limit": 200},
        )

    assert captured["content_type"].startswith("application/x-www-form-urlencoded")
    body = dict(urllib.parse.parse_qsl(captured["body"]))
    assert body["types"] == "private_channel"
    assert body["exclude_archived"] == "true"
    assert body["limit"] == "200"


def test_conversations_list_returns_private_channels():
    """Requesting types=private_channel must surface private channels.

    With the old JSON body, Slack dropped `types` and this returned only
    the default public page -- the exact bug that hid #agent-native-os.
    """
    with mock.patch("urllib.request.urlopen", side_effect=_fake_conversations_list):
        channels = _client().paginate(
            "conversations.list",
            params={"types": "public_channel,private_channel", "exclude_archived": True},
            response_key="channels",
        )

    ids = {c["id"] for c in channels}
    assert PRIVATE_CHANNEL["id"] in ids, "private channel missing: params were dropped"
    assert any(c.get("is_private") for c in channels)


def test_form_encoding_serializes_nested_values():
    """Dict/list params (blocks, attachments) are JSON-serialized form fields."""
    captured = {}

    def fake_urlopen(req, **kwargs):
        captured["body"] = req.data.decode("utf-8")
        return _response({"ok": True})

    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "hi"}}]
    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        _client().call(
            "chat.postMessage", params={"channel": "C111GENERAL", "blocks": blocks}
        )

    body = dict(urllib.parse.parse_qsl(captured["body"]))
    assert json.loads(body["blocks"]) == blocks


def test_api_passthrough_paginate_merges_pages():
    """api --paginate follows next_cursor (form-encoded) and merges pages."""
    from slack_cli.api import call_method

    seen_params = []

    def fake_urlopen(req, **kwargs):
        params = _parse_request(req)
        seen_params.append(params)
        if params.get("cursor") == "cursor-page-2":
            page = {
                "ok": True,
                "channels": [PRIVATE_CHANNEL],
                "response_metadata": {"next_cursor": ""},
            }
        else:
            page = {
                "ok": True,
                "channels": [PUBLIC_CHANNEL],
                "response_metadata": {"next_cursor": "cursor-page-2"},
            }
        return _response(page)

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = call_method(
            _client(),
            "conversations.list",
            params={"types": "public_channel,private_channel"},
            paginate=True,
        )

    assert len(seen_params) == 2
    assert seen_params[1].get("cursor") == "cursor-page-2"
    assert seen_params[1].get("types") == "public_channel,private_channel"
    ids = [c["id"] for c in result["channels"]]
    assert ids == [PUBLIC_CHANNEL["id"], PRIVATE_CHANNEL["id"]]
    assert "response_metadata" not in result


def test_api_passthrough_default_single_call_is_form_encoded():
    """The raw api passthrough must not send JSON bodies by default."""
    from slack_cli.api import call_method

    def fake_urlopen(req, **kwargs):
        return _fake_conversations_list(req)

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = call_method(
            _client(),
            "conversations.list",
            params={"types": "private_channel"},
        )

    assert [c["id"] for c in result["channels"]] == [PRIVATE_CHANNEL["id"]]
