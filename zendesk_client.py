"""Thin async client for the Zendesk REST API (tickets + Help Center, read/search only)."""

import os

import httpx


class ZendeskConfigError(RuntimeError):
    pass


class ZendeskAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(f"Zendesk API error {status_code}: {message}")
        self.status_code = status_code


def _get_client() -> httpx.AsyncClient:
    subdomain = os.environ.get("ZENDESK_SUBDOMAIN")
    email = os.environ.get("ZENDESK_EMAIL")
    api_token = os.environ.get("ZENDESK_API_TOKEN")

    missing = [
        name
        for name, value in (
            ("ZENDESK_SUBDOMAIN", subdomain),
            ("ZENDESK_EMAIL", email),
            ("ZENDESK_API_TOKEN", api_token),
        )
        if not value
    ]
    if missing:
        raise ZendeskConfigError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return httpx.AsyncClient(
        base_url=f"https://{subdomain}.zendesk.com/api/v2",
        auth=(f"{email}/token", api_token),
        timeout=20.0,
    )


async def _request(method: str, path: str, **kwargs) -> dict:
    async with _get_client() as client:
        response = await client.request(method, path, **kwargs)
        if response.status_code == 404:
            raise ZendeskAPIError(404, "Not found")
        if response.status_code == 401:
            raise ZendeskAPIError(401, "Unauthorized — check ZENDESK_EMAIL/ZENDESK_API_TOKEN")
        if response.status_code >= 400:
            raise ZendeskAPIError(response.status_code, response.text)
        return response.json()


async def fetch_ticket(ticket_id: int) -> dict:
    data = await _request("GET", f"/tickets/{ticket_id}.json")
    return data["ticket"]


async def fetch_ticket_comments(ticket_id: int) -> list:
    data = await _request(
        "GET", f"/tickets/{ticket_id}/comments.json", params={"sort_order": "asc"}
    )
    return data["comments"]


async def fetch_requester(user_id: int) -> dict:
    data = await _request("GET", f"/users/{user_id}.json")
    return data["user"]


async def search_tickets(query: str, max_results: int = 10) -> list:
    full_query = f"type:ticket {query}"
    data = await _request(
        "GET",
        "/search.json",
        params={"query": full_query, "sort_by": "updated_at", "sort_order": "desc"},
    )
    return data["results"][:max_results]


async def search_help_center(query: str, max_results: int = 10) -> list:
    data = await _request(
        "GET",
        "/help_center/articles/search.json",
        params={"query": query, "per_page": max_results},
    )
    return data["results"][:max_results]


async def fetch_help_center_article(article_id: int) -> dict:
    data = await _request("GET", f"/help_center/articles/{article_id}.json")
    return data["article"]
