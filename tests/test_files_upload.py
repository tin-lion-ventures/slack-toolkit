import json
import urllib.parse
import urllib.request

from slack_cli.client import SlackClient
from slack_cli.files import upload_file


class _FakeHTTPResponse:
    def __init__(self, body: bytes = b'{"ok": true}'):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


def _headers(request):
    return {key.lower(): value for key, value in request.header_items()}


def _parsed_form(request):
    return urllib.parse.parse_qs(request.data.decode("utf-8"))


def test_call_form_urlencodes_upload_url_external_request(monkeypatch):
    captured = []

    def fake_urlopen(request, context=None, timeout=None):
        captured.append(request)
        return _FakeHTTPResponse(
            b'{"ok": true, "upload_url": "https://files.slack.com/upload/v1/abc", "file_id": "F123"}'
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    client = SlackClient("bot-token-test")
    response = client.call_form(
        "files.getUploadURLExternal",
        params={"filename": "hello.txt", "length": 12},
    )

    assert response["file_id"] == "F123"
    request = captured[0]
    assert request.full_url == "https://slack.com/api/files.getUploadURLExternal"
    assert request.get_method() == "POST"
    assert _headers(request)["content-type"] == "application/x-www-form-urlencoded"
    assert _headers(request)["authorization"] == "Bearer bot-token-test"
    assert _parsed_form(request) == {"filename": ["hello.txt"], "length": ["12"]}


def test_call_form_serializes_complete_upload_files_array(monkeypatch):
    captured = []

    def fake_urlopen(request, context=None, timeout=None):
        captured.append(request)
        return _FakeHTTPResponse(b'{"ok": true, "files": [{"id": "F123", "title": "Report"}]}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    client = SlackClient("bot-token-test")
    client.call_form(
        "files.completeUploadExternal",
        params={
            "files": [{"id": "F123", "title": "Report"}],
            "channel_id": "C123",
            "initial_comment": "Here is the report",
            "thread_ts": "1712345678.000100",
        },
    )

    parsed = _parsed_form(captured[0])
    assert json.loads(parsed["files"][0]) == [{"id": "F123", "title": "Report"}]
    assert parsed["channel_id"] == ["C123"]
    assert parsed["initial_comment"] == ["Here is the report"]
    assert parsed["thread_ts"] == ["1712345678.000100"]


def test_upload_request_posts_multipart_file_without_slack_auth(monkeypatch):
    captured = []

    def fake_urlopen(request, context=None, timeout=None):
        captured.append(request)
        return _FakeHTTPResponse(b"OK - 5")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    client = SlackClient("bot-token-secret")
    client.upload_request(
        "https://files.slack.com/upload/v1/abc",
        b"hello",
        "report.txt",
    )

    request = captured[0]
    headers = _headers(request)
    assert request.full_url == "https://files.slack.com/upload/v1/abc"
    assert request.get_method() == "POST"
    assert headers["content-type"].startswith("multipart/form-data; boundary=")
    assert headers["content-length"] == str(len(request.data))
    assert "authorization" not in headers
    assert b'name="filename"; filename="report.txt"' in request.data
    assert b"Content-Type: application/octet-stream" in request.data
    assert b"\r\nhello\r\n" in request.data


class _RecordingSlackClient:
    def __init__(self):
        self.events = []

    def call_form(self, method_name, params=None, token_type="bot"):
        params = dict(params or {})
        self.events.append(("call_form", method_name, params))

        if method_name == "files.getUploadURLExternal":
            return {
                "ok": True,
                "upload_url": "https://files.slack.com/upload/v1/abc",
                "file_id": "F123",
            }
        if method_name == "files.completeUploadExternal":
            return {"ok": True, "files": params["files"]}
        raise AssertionError(f"Unexpected method: {method_name}")

    def upload_request(self, url, file_data, filename, token_type="bot"):
        self.events.append(("upload_request", url, file_data, filename))


def test_upload_file_v2_flow_preserves_filename_length_and_completion_fields(tmp_path):
    filepath = tmp_path / "report.txt"
    filepath.write_bytes(b"hello")
    client = _RecordingSlackClient()

    upload_file(
        client,
        str(filepath),
        channels="C123,C456",
        initial_comment="Here is the report",
        thread_ts="1712345678.000100",
    )

    assert client.events == [
        (
            "call_form",
            "files.getUploadURLExternal",
            {"filename": "report.txt", "length": 5},
        ),
        (
            "upload_request",
            "https://files.slack.com/upload/v1/abc",
            b"hello",
            "report.txt",
        ),
        (
            "call_form",
            "files.completeUploadExternal",
            {
                "files": [{"id": "F123", "title": "report.txt"}],
                "channel_id": "C123",
                "initial_comment": "Here is the report",
                "thread_ts": "1712345678.000100",
            },
        ),
    ]


def test_upload_file_v2_private_upload_omits_share_fields(tmp_path):
    filepath = tmp_path / "draft.csv"
    filepath.write_text("a,b\n1,2\n")
    client = _RecordingSlackClient()

    upload_file(client, str(filepath), title="Custom draft")

    complete_event = client.events[-1]
    assert complete_event == (
        "call_form",
        "files.completeUploadExternal",
        {"files": [{"id": "F123", "title": "Custom draft"}]},
    )
