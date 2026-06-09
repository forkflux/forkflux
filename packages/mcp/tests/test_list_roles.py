from types import SimpleNamespace

import httpx
import pytest


def _patch_http_request(monkeypatch: pytest.MonkeyPatch, response: SimpleNamespace):
    captured: dict[str, object] = {}

    def _fake_request(self, method, url, headers=None, params=None, json=None):
        captured["method"] = method
        captured["url"] = str(url)
        captured["headers"] = headers
        captured["params"] = params
        captured["json"] = json
        return response

    monkeypatch.setattr(httpx.Client, "request", _fake_request)
    return captured


async def test_list_roles_tool_returns_success_payload(client, monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        is_success=True,
        json=lambda: {"roles": ["qa", "security"]},
    )
    captured = _patch_http_request(monkeypatch, response)

    result = await client.call_tool("forkflux_list_roles")

    assert captured["method"] == "GET"
    assert str(captured["url"]).endswith("/agents/roles")
    assert result.structured_content == {"success": True, "details": {"roles": ["qa", "security"]}}


async def test_list_roles_tool_returns_validation_error_for_422(client, monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        is_success=False,
        status_code=422,
        json=lambda: {"detail": [{"loc": ["body"], "msg": "invalid"}]},
        text="",
    )
    _patch_http_request(monkeypatch, response)

    result = await client.call_tool("forkflux_list_roles")

    assert result.structured_content == {
        "success": False,
        "error": "Validation Error",
        "status_code": 422,
        "details": {"detail": [{"loc": ["body"], "msg": "invalid"}]},
    }


async def test_list_roles_tool_returns_network_internal_error_for_401(client, monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        is_success=False,
        status_code=401,
        text="",
    )
    _patch_http_request(monkeypatch, response)

    result = await client.call_tool("forkflux_list_roles")

    assert result.structured_content == {
        "success": False,
        "error": "Network or Internal Error",
        "details": "Wrong API key.",
    }


async def test_list_roles_tool_returns_http_error_for_non_validation_non_401(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = SimpleNamespace(
        is_success=False,
        status_code=500,
        text="server exploded",
    )
    _patch_http_request(monkeypatch, response)

    result = await client.call_tool("forkflux_list_roles")

    assert result.structured_content == {
        "success": False,
        "error": "HTTP Error",
        "status_code": 500,
        "details": "server exploded",
    }
