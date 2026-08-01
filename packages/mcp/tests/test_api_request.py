from types import SimpleNamespace

import httpx
import pytest
from forkflux_mcp.main import _api_request, _get_authorization


def _patch_http_request(monkeypatch: pytest.MonkeyPatch, response: SimpleNamespace):
    captured: dict[str, object] = {}

    async def _fake_request(self, method, url, headers=None, params=None, json=None):
        captured["method"] = method
        captured["url"] = str(url)
        captured["headers"] = headers
        captured["params"] = params
        captured["json"] = json
        return response

    monkeypatch.setattr(httpx.AsyncClient, "request", _fake_request)
    return captured


async def test_get_authorization_prefers_request_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("forkflux_mcp.main.settings.forkflux_api_key", "fallback-key")

    def _fake_get_http_headers(*, include: set[str]) -> dict[str, str]:
        assert include == {"authorization"}
        return {"authorization": "Bearer request-key"}

    monkeypatch.setattr("forkflux_mcp.main.get_http_headers", _fake_get_http_headers)

    assert await _get_authorization() == "Bearer request-key"


async def test_get_authorization_falls_back_to_api_key_when_request_header_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("forkflux_mcp.main.settings.forkflux_api_key", "fallback-key")
    monkeypatch.setattr("forkflux_mcp.main.get_http_headers", lambda **_: {})

    assert await _get_authorization() == "fallback-key"


async def test_api_request_returns_success_payload_and_forwards_request_args(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("forkflux_mcp.main.settings.forkflux_api_url", "http://api.example.test")
    monkeypatch.setattr("forkflux_mcp.main.settings.forkflux_api_key", "test-key")

    response = SimpleNamespace(
        is_success=True,
        status_code=200,
        json=lambda: {"ok": True},
    )
    captured = _patch_http_request(monkeypatch, response)

    result = await _api_request("GET", "/agents/roles", params={"page": 1}, json_data={"x": "y"})

    assert result == {"success": True, "details": {"ok": True}}
    assert captured["method"] == "GET"
    assert captured["url"] == "http://api.example.test/mcp/agents/roles"
    assert captured["params"] == {"page": 1}
    assert captured["json"] == {"x": "y"}
    assert captured["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-key",
    }


async def test_api_request_forwards_request_authorization_header_without_duplicate_bearer_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("forkflux_mcp.main.settings.forkflux_api_url", "http://api.example.test")
    monkeypatch.setattr("forkflux_mcp.main.settings.forkflux_api_key", "fallback-key")
    monkeypatch.setattr(
        "forkflux_mcp.main.get_http_headers",
        lambda **_: {"authorization": "Bearer request-key"},
    )

    response = SimpleNamespace(
        is_success=True,
        status_code=200,
        json=lambda: {"ok": True},
    )
    captured = _patch_http_request(monkeypatch, response)

    result = await _api_request("GET", "/agents/me")

    assert result == {"success": True, "details": {"ok": True}}
    assert captured["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer request-key",
    }


async def test_api_request_returns_success_payload_with_none_details_for_204(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        is_success=True,
        status_code=204,
        json=lambda: (_ for _ in ()).throw(AssertionError("response.json() must not be called for 204")),
    )
    _patch_http_request(monkeypatch, response)

    result = await _api_request("POST", "/jobs/77/status", json_data={"status": "completed"})

    assert result == {"success": True, "details": None}


async def test_api_request_returns_success_payload_with_none_details_when_success_body_is_not_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_value_error() -> dict[str, object]:
        raise ValueError("not json")

    response = SimpleNamespace(
        is_success=True,
        status_code=200,
        json=_raise_value_error,
    )
    _patch_http_request(monkeypatch, response)

    result = await _api_request("GET", "/agents/roles")

    assert result == {"success": True, "details": None}


async def test_api_request_returns_validation_error_with_json_details_for_400(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        is_success=False,
        status_code=400,
        json=lambda: {"detail": [{"msg": "bad input"}]},
        text="",
    )
    _patch_http_request(monkeypatch, response)

    result = await _api_request("POST", "/jobs", json_data={"summary": "s"})

    assert result == {
        "success": False,
        "error": "Validation Error",
        "status_code": 400,
        "details": {"detail": [{"msg": "bad input"}]},
    }


async def test_api_request_returns_validation_error_with_text_details_when_body_is_not_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_value_error() -> dict[str, object]:
        raise ValueError("not json")

    response = SimpleNamespace(
        is_success=False,
        status_code=422,
        json=_raise_value_error,
        text="unprocessable entity",
    )
    _patch_http_request(monkeypatch, response)

    result = await _api_request("POST", "/jobs", json_data={"summary": "s"})

    assert result == {
        "success": False,
        "error": "Validation Error",
        "status_code": 422,
        "details": "unprocessable entity",
    }


async def test_api_request_returns_network_internal_error_for_401(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        is_success=False,
        status_code=401,
        text="",
    )
    _patch_http_request(monkeypatch, response)

    result = await _api_request("GET", "/agents/roles")

    assert result == {
        "success": False,
        "error": "Network or Internal Error",
        "details": "Wrong API key.",
    }


async def test_api_request_returns_http_error_for_non_validation_non_401(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        is_success=False,
        status_code=503,
        text="service unavailable",
    )
    _patch_http_request(monkeypatch, response)

    result = await _api_request("GET", "/agents/roles")

    assert result == {
        "success": False,
        "error": "HTTP Error",
        "status_code": 503,
        "details": "service unavailable",
    }


async def test_api_request_returns_network_internal_error_when_request_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_request(self, method, url, headers=None, params=None, json=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "request", _fake_request)

    result = await _api_request("GET", "/agents/roles")

    assert result == {
        "success": False,
        "error": "Network or Internal Error",
        "details": "connection refused",
    }
