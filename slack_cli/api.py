"""Raw Slack API method passthrough.

The escape hatch: call ANY Slack Web API method by name with arbitrary
params, even if slack-cli has no dedicated command for it. Combined
with the method catalog, this gives AI agents full Slack API coverage.
"""

import json
import sys


def _paginated_call(client, method_name, params, token_type):
    """Follow response_metadata.next_cursor until exhausted, merging pages.

    Returns a single response dict shaped like the first page, with the
    paginated list merged across all pages. The list key comes from the
    method catalog's response_key when known, else the first list value
    in the response.
    """
    from .methods import get_method

    p = dict(params or {})
    p.setdefault("limit", 200)

    merged = None
    list_key = None
    while True:
        resp = client.call(method_name, params=p, token_type=token_type)

        if merged is None:
            merged = resp
            catalog_entry = get_method(method_name)
            candidate = (catalog_entry or {}).get("response_key")
            if candidate and isinstance(resp.get(candidate), list):
                list_key = candidate
            else:
                list_key = next(
                    (
                        k
                        for k, v in resp.items()
                        if k not in ("ok", "response_metadata", "cache_ts")
                        and isinstance(v, list)
                    ),
                    None,
                )
        elif list_key:
            merged[list_key].extend(resp.get(list_key, []))

        cursor = resp.get("response_metadata", {}).get("next_cursor", "")
        if not cursor or not list_key:
            break
        p["cursor"] = cursor

    # The last page's cursor metadata is meaningless for the merged result
    merged.pop("response_metadata", None)
    return merged


def call_method(
    client,
    method_name,
    params=None,
    token_type="bot",
    as_json=False,
    paginate=False,
    body_format="form",
):
    """Call any Slack API method by name with raw params.

    Args:
        client: A slack_cli.client.SlackClient instance.
        method_name: Slack API method name (e.g. "chat.postMessage").
        params: Dict of params to pass to the method.
        token_type: "bot" or "user" -- which token to authenticate with.
        as_json: If True, print raw JSON to stdout.
        paginate: If True, follow cursor pagination and merge all pages.
        body_format: "form" (default, accepted by every method) or "json"
            (only honored by some write methods).

    Returns:
        The parsed response dict.
    """
    if paginate:
        result = _paginated_call(client, method_name, params, token_type)
    else:
        result = client.call(
            method_name,
            params=params,
            token_type=token_type,
            body_format=body_format,
        )

    if not result.get("ok"):
        error = result.get("error", "unknown_error")
        print(f"Error: {error}", file=sys.stderr)
        if result.get("response_metadata", {}).get("messages"):
            for msg in result["response_metadata"]["messages"]:
                print(f"  {msg}", file=sys.stderr)

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))

    return result
