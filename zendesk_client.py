"""Thin async client for the Zendesk REST API (tickets, Help Center, organizations; read/search only)."""

import asyncio
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



async def _find_organization(organization_name: str) -> dict:
    data = await _request(
        "GET", "/organizations/autocomplete.json", params={"name": organization_name}
    )
    candidates = data["organizations"]

    if not candidates:
        raise ZendeskAPIError(404, f"No organization found matching {organization_name!r}")

    exact = [o for o in candidates if o["name"].lower() == organization_name.lower()]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]

    options = "; ".join(f"{o['name']} (id {o['id']})" for o in candidates[:10])
    raise ValueError(
        f"Several organizations match {organization_name!r}: {options}. "
        "Ask the user which one they mean, or call again with the exact name."
    )


async def fetch_organization_info(
    organization_name: str, max_members: int = 50, max_tickets: int = 20
) -> dict:
    organization = await _find_organization(organization_name)
    org_id = organization["id"]

    users_data, tickets_data = await asyncio.gather(
        _request(
            "GET",
            f"/organizations/{org_id}/users.json",
            params={"per_page": min(max_members, 100)},
        ),
        _request(
            "GET",
            "/search.json",
            params={
                "query": f"type:ticket organization_id:{org_id}",
                "sort_by": "updated_at",
                "sort_order": "desc",
                "per_page": min(max_tickets, 100),
            },
        ),
    )

    return {
        "id": org_id,
        "name": organization["name"],
        "users": users_data["users"][:max_members],
        "users_total": users_data.get("count", len(users_data["users"])),
        "tickets": tickets_data["results"][:max_tickets],
        "tickets_total": tickets_data.get("count", len(tickets_data["results"])),
    }
