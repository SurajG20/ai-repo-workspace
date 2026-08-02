from __future__ import annotations

from typing import Optional

import httpx
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)


class GitHubOAuthService:
    def __init__(self) -> None:
        self.client_id = settings.github_client_id
        self.client_secret = settings.github_client_secret
        self.redirect_uri = settings.github_redirect_uri
        self.http = httpx.AsyncClient(timeout=30.0)

    def get_authorization_url(self, state: str) -> str:
        return (
            "https://github.com/login/oauth/authorize"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
            "&scope=repo,user:email"
        )

    async def exchange_code(self, code: str) -> dict | None:
        try:
            resp = await self.http.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                logger.error("github_oauth_error", error=data.get("error"))
                return None
            return data
        except Exception as e:
            logger.error("github_oauth_exchange_failed", exc_info=e)
            return None

    async def get_user_info(self, access_token: str) -> dict | None:
        try:
            resp = await self.http.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("github_user_info_failed", exc_info=e)
            return None

    async def list_repositories(self, access_token: str, page: int = 1) -> tuple[list[dict], dict]:
        resp = await self.http.get(
            "https://api.github.com/user/repos",
            params={"page": page, "per_page": 30, "sort": "updated"},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
        repos = resp.json()
        link_header = resp.headers.get("Link", "")
        return repos, _parse_link_header(link_header)

    async def get_repository(self, access_token: str, owner: str, repo: str) -> dict | None:
        try:
            resp = await self.http.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("github_get_repo_failed", owner=owner, repo=repo, exc_info=e)
            return None

    async def register_webhook(
        self, access_token: str, owner: str, repo: str, webhook_url: str
    ) -> Optional[int]:
        webhook_secret = settings.github_webhook_secret or settings.api_secret_key[:32]
        try:
            resp = await self.http.post(
                f"https://api.github.com/repos/{owner}/{repo}/hooks",
                json={
                    "name": "web",
                    "active": True,
                    "events": ["push", "pull_request"],
                    "config": {
                        "url": webhook_url,
                        "content_type": "json",
                        "secret": webhook_secret,
                    },
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("id")
        except Exception as e:
            logger.error("github_webhook_registration_failed", owner=owner, repo=repo, exc_info=e)
            return None

    async def close(self) -> None:
        await self.http.aclose()


def _parse_link_header(header: str) -> dict:
    links: dict[str, int] = {}
    for part in header.split(","):
        section = part.strip()
        url_part, rel_part = section.split(";") if ";" in section else (section, "")
        url = url_part.strip(" <>")
        rel = rel_part.strip().replace('rel="', "").replace('"', "")
        import re
        match = re.search(r"[?&]page=(\d+)", url)
        if match and rel:
            links[rel] = int(match.group(1))
    return links


def create_github_service() -> GitHubOAuthService:
    return GitHubOAuthService()
