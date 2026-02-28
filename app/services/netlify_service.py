"""Netlify REST API service for prototype deployment.

Uses httpx for async HTTP requests. Each prototype gets its own Netlify site
linked to a GitHub repo for continuous deployment.
"""

from __future__ import annotations

import asyncio

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

NETLIFY_API = "https://api.netlify.com/api/v1"


class NetlifyService:
    """Manages Netlify sites for prototype deployments."""

    def __init__(self, auth_token: str, team_slug: str = "readytogo"):
        self.auth_token = auth_token
        self.team_slug = team_slug
        self._headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

    async def create_site(
        self,
        name: str,
        repo_url: str,
        build_cmd: str = "npm install && npm run build",
        publish_dir: str = "dist",
    ) -> dict:
        """Create a Netlify site linked to a GitHub repo."""
        async with httpx.AsyncClient(timeout=30) as client:
            # Parse GitHub owner/repo from URL
            # e.g., https://github.com/readytogo-ai/proto-acme-abc123
            parts = repo_url.rstrip("/").split("/")
            repo_path = f"{parts[-2]}/{parts[-1]}" if len(parts) >= 2 else repo_url

            resp = await client.post(
                f"{NETLIFY_API}/sites",
                headers=self._headers,
                json={
                    "name": name,
                    "account_slug": self.team_slug,
                    "repo": {
                        "provider": "github",
                        "repo": repo_path,
                        "branch": "main",
                        "cmd": build_cmd,
                        "dir": publish_dir,
                    },
                    "build_settings": {
                        "env": {"NODE_VERSION": "20"},
                    },
                },
            )
            resp.raise_for_status()
            site = resp.json()
            logger.info(f"Created Netlify site {name}: {site.get('ssl_url', site.get('url'))}")
            return site

    async def get_site(self, site_id: str) -> dict:
        """Get site details."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{NETLIFY_API}/sites/{site_id}",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def trigger_deploy(self, site_id: str) -> dict:
        """Trigger a new deploy for a site."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{NETLIFY_API}/sites/{site_id}/builds",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def wait_for_deploy(self, site_id: str, timeout: int = 300) -> dict:
        """Poll until the latest deploy is ready. Returns deploy data."""
        elapsed = 0
        interval = 10

        while elapsed < timeout:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{NETLIFY_API}/sites/{site_id}/deploys",
                    headers=self._headers,
                    params={"per_page": 1},
                )
                resp.raise_for_status()
                deploys = resp.json()

                if deploys:
                    latest = deploys[0]
                    state = latest.get("state", "")
                    if state == "ready":
                        logger.info(f"Deploy ready: {latest.get('ssl_url')}")
                        return latest
                    if state == "error":
                        logger.error(f"Deploy failed: {latest.get('error_message')}")
                        return latest

            await asyncio.sleep(interval)
            elapsed += interval

        logger.warning(f"Deploy timed out after {timeout}s for site {site_id}")
        return {"state": "timeout", "site_id": site_id}

    async def delete_site(self, site_id: str) -> bool:
        """Delete a Netlify site."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"{NETLIFY_API}/sites/{site_id}",
                headers=self._headers,
            )
            if resp.status_code == 204:
                logger.info(f"Deleted Netlify site {site_id}")
                return True
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            return False
