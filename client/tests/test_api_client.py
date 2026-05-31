"""Unit tests for app.api.ApiClient."""

import pytest
import httpx
from unittest.mock import MagicMock, patch


def make_client():
    """Create ApiClient with a fake base URL (no real HTTP)."""
    # Avoid importing the singleton; test the class directly
    from app.api import ApiClient
    return ApiClient("http://test-server")


def test_set_token_stores_token():
    client = make_client()
    client.set_token("mytoken")
    assert client._token == "mytoken"


def test_clear_token_removes_token():
    client = make_client()
    client.set_token("mytoken")
    client.clear_token()
    assert client._token is None


def test_auth_headers_with_token():
    client = make_client()
    client.set_token("abc123")
    headers = client._auth_headers()
    assert headers == {"Authorization": "Bearer abc123"}


def test_auth_headers_without_token():
    client = make_client()
    headers = client._auth_headers()
    assert headers == {}


def test_post_sends_correct_request(mocker):
    client = make_client()
    client.set_token("tok")
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mocker.patch.object(client._client, "post", return_value=mock_response)

    res = client.post("/commits", {"commits": []})

    client._client.post.assert_called_once_with(
        "/commits",
        json={"commits": []},
        headers={"Authorization": "Bearer tok"},
    )
    assert res.status_code == 201


def test_post_without_token(mocker):
    client = make_client()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mocker.patch.object(client._client, "post", return_value=mock_response)

    client.post("/commits", {})

    client._client.post.assert_called_once_with("/commits", json={}, headers={})


def test_get_sends_correct_request(mocker):
    client = make_client()
    client.set_token("tok2")
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mocker.patch.object(client._client, "get", return_value=mock_response)

    res = client.get("/exams")

    client._client.get.assert_called_once_with(
        "/exams",
        headers={"Authorization": "Bearer tok2"},
    )
    assert res.status_code == 200


def test_close_calls_client_close(mocker):
    client = make_client()
    mocker.patch.object(client._client, "close")
    client.close()
    client._client.close.assert_called_once()
