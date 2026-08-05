"""Local MCP connector exposing Zendesk ticket and Help Center search/lookup to Claude.

Runs over stdio: Claude Desktop / Claude Code spawns this as a subprocess
on demand and shuts it down when the chat session ends — nothing needs to
be kept running in the background.
"""

import html
import os
import re

from mcp.server.fastmcp import FastMCP

import zendesk_client as zd

mcp = FastMCP("zendesk-tickets")


def _format_user(user: dict | None) -> dict:
    if not user:
        return {}
    return {"id": user.get("id"), "name": user.get("name"), "email": user.get("email")}


def _html_to_text(body: str | None) -> str:
    if not body:
        return ""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", body)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


@mcp.tool()
async def get_ticket(ticket_id: int) -> dict:
    """Fetch a single Zendesk ticket by its numeric ID, including its full
    comment/conversation thread, so it can be used as chat context.

    Args:
        ticket_id: The numeric Zendesk ticket ID (e.g. 12345).
    """
    ticket = await zd.fetch_ticket(ticket_id)
    comments = await zd.fetch_ticket_comments(ticket_id)

    requester = None
    if ticket.get("requester_id"):
        try:
            requester = await zd.fetch_requester(ticket["requester_id"])
        except zd.ZendeskAPIError:
            requester = None

    return {
        "id": ticket["id"],
        "url": f"https://{os.environ.get('ZENDESK_SUBDOMAIN')}.zendesk.com/agent/tickets/{ticket['id']}",
        "subject": ticket.get("subject"),
        "description": ticket.get("description"),
        "status": ticket.get("status"),
        "priority": ticket.get("priority"),
        "type": ticket.get("type"),
        "tags": ticket.get("tags", []),
        "created_at": ticket.get("created_at"),
        "updated_at": ticket.get("updated_at"),
        "requester": _format_user(requester),
        "comments": [
            {
                "author_id": c.get("author_id"),
                "created_at": c.get("created_at"),
                "public": c.get("public"),
                "body": c.get("plain_body") or c.get("body"),
            }
            for c in comments
        ],
    }


@mcp.tool()
async def search_tickets(query: str, max_results: int = 10) -> list:
    """Search Zendesk tickets using Zendesk's search syntax (e.g. subject
    keywords, status:open, requester:email@example.com). Returns brief
    summaries — use get_ticket(id) to pull full details for one result.

    Args:
        query: Zendesk search query text (combined with type:ticket automatically).
        max_results: Maximum number of results to return (default 10).
    """
    results = await zd.search_tickets(query, max_results)
    return [
        {
            "id": r["id"],
            "subject": r.get("subject"),
            "status": r.get("status"),
            "priority": r.get("priority"),
            "updated_at": r.get("updated_at"),
        }
        for r in results
    ]


@mcp.tool()
async def search_help_center(query: str, max_results: int = 10) -> list:
    """Search Zendesk Help Center articles by keyword. Returns brief
    summaries — use get_help_center_article(id) to pull the full body
    for one result.

    Args:
        query: Free-text search query.
        max_results: Maximum number of results to return (default 10).
    """
    results = await zd.search_help_center(query, max_results)
    return [
        {
            "id": r["id"],
            "title": r.get("title"),
            "url": r.get("html_url"),
            "snippet": _html_to_text(r.get("snippet")),
        }
        for r in results
    ]


@mcp.tool()
async def get_help_center_article(article_id: int) -> dict:
    """Fetch a single Zendesk Help Center article by its numeric ID, with
    its full body as plain text, so it can be used as chat context.

    Args:
        article_id: The numeric Help Center article ID.
    """
    article = await zd.fetch_help_center_article(article_id)
    return {
        "id": article["id"],
        "title": article.get("title"),
        "url": article.get("html_url"),
        "body": _html_to_text(article.get("body")),
        "locale": article.get("locale"),
        "created_at": article.get("created_at"),
        "updated_at": article.get("updated_at"),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
