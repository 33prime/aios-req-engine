"""GitHub REST API service for prototype repo management.

Uses httpx (already in deps) for async HTTP requests.
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubService:
    """Manages GitHub repos for prototype deployments."""

    def __init__(self, token: str, org: str = "readytogo-ai"):
        self.token = token
        self.org = org
        self._headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = True,
    ) -> dict:
        """Create a repo under the org. Returns repo data dict."""
        # Check if repo already exists
        existing = await self.get_repo(name)
        if existing:
            logger.info(f"Repo {self.org}/{name} already exists")
            return existing

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GITHUB_API}/orgs/{self.org}/repos",
                headers=self._headers,
                json={
                    "name": name,
                    "description": description or f"AIOS prototype: {name}",
                    "private": private,
                    "auto_init": False,
                },
            )
            resp.raise_for_status()
            repo = resp.json()
            logger.info(f"Created repo {self.org}/{name}: {repo.get('html_url')}")
            return repo

    async def get_repo(self, name: str) -> dict | None:
        """Get repo data, or None if not found."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{self.org}/{name}",
                headers=self._headers,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def delete_repo(self, name: str) -> bool:
        """Delete a repo. Returns True if deleted."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"{GITHUB_API}/repos/{self.org}/{name}",
                headers=self._headers,
            )
            if resp.status_code == 204:
                logger.info(f"Deleted repo {self.org}/{name}")
                return True
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            return False
