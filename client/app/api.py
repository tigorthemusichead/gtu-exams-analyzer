import httpx

class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._token: str | None = None
        self._client = httpx.Client(base_url=base_url, timeout=10.0)

    def set_token(self, token: str) -> None:
        self._token = token

    def clear_token(self) -> None:
        self._token = None

    def _auth_headers(self) -> dict:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    def post(self, path: str, json: dict) -> httpx.Response:
        return self._client.post(path, json=json, headers=self._auth_headers())

    def get(self, path: str) -> httpx.Response:
        return self._client.get(path, headers=self._auth_headers())

    def close(self) -> None:
        self._client.close()

# Singleton — imported by other modules
from app.config import SERVER_URL
api_client = ApiClient(SERVER_URL)
