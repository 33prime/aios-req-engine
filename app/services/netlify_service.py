"""Netlify REST API service for prototype deployment.

Uses httpx for async HTTP requests. Supports both repo-linked sites
and direct file-digest deploys (no GitHub required).
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

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

    async def deploy_from_dist(self, name: str, dist_path: str) -> tuple[str, str]:
        """Deploy local dist/ directory directly to Netlify via file digest API.

        Creates a headless site (no GitHub link), uploads files, returns (deploy_url, site_id).
        """
        dist = Path(dist_path)
        if not dist.is_dir():
            raise FileNotFoundError(f"dist directory not found: {dist_path}")

        # Collect all files and compute SHA1 digests
        file_digests: dict[str, str] = {}  # "/" prefixed path → sha1 hex
        file_paths: dict[str, Path] = {}  # "/" prefixed path → local Path
        for file_path in dist.rglob("*"):
            if file_path.is_file():
                rel = "/" + str(file_path.relative_to(dist))
                sha1 = hashlib.sha1(file_path.read_bytes()).hexdigest()  # noqa: S324
                file_digests[rel] = sha1
                file_paths[rel] = file_path

        if not file_digests:
            raise ValueError("No files found in dist directory")

        logger.info(f"Deploying {len(file_digests)} files from {dist_path}")

        async with httpx.AsyncClient(timeout=60) as client:
            # 1. Create headless site (no repo link)
            # If name is taken (422), retry with random suffix
            resp = await client.post(
                f"{NETLIFY_API}/sites",
                headers=self._headers,
                json={"name": name, "account_slug": self.team_slug},
            )
            if resp.status_code == 422:
                import secrets

                fallback = f"{name[:40]}-{secrets.token_hex(3)}"
                logger.warning(f"Site name '{name}' taken, retrying as '{fallback}'")
                resp = await client.post(
                    f"{NETLIFY_API}/sites",
                    headers=self._headers,
                    json={"name": fallback, "account_slug": self.team_slug},
                )
            resp.raise_for_status()
            site = resp.json()
            site_id = site["id"]
            logger.info(f"Created headless site {site.get('name', name)}: {site_id}")

            # 2. Create deploy with file digests
            resp = await client.post(
                f"{NETLIFY_API}/sites/{site_id}/deploys",
                headers=self._headers,
                json={"files": file_digests},
            )
            resp.raise_for_status()
            deploy = resp.json()
            deploy_id = deploy["id"]
            required = deploy.get("required", [])
            logger.info(
                f"Deploy {deploy_id} created, {len(required)} files need upload "
                f"(of {len(file_digests)} total)"
            )

            # 3. Upload required files
            upload_headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/octet-stream",
            }
            digest_to_paths = {v: k for k, v in file_digests.items()}
            for sha in required:
                rel_path = digest_to_paths.get(sha)
                if not rel_path:
                    continue
                local = file_paths[rel_path]
                resp = await client.put(
                    f"{NETLIFY_API}/deploys/{deploy_id}/files{rel_path}",
                    headers=upload_headers,
                    content=local.read_bytes(),
                )
                resp.raise_for_status()

            # 4. Wait for deploy to be ready
            for _ in range(30):
                resp = await client.get(
                    f"{NETLIFY_API}/deploys/{deploy_id}",
                    headers=self._headers,
                )
                resp.raise_for_status()
                deploy_data = resp.json()
                state = deploy_data.get("state", "")
                if state == "ready":
                    deploy_url = deploy_data.get("ssl_url") or deploy_data.get("url", "")
                    logger.info(f"Deploy ready: {deploy_url}")
                    return deploy_url, site_id
                if state == "error":
                    raise RuntimeError(
                        f"Deploy failed: {deploy_data.get('error_message', 'unknown error')}"
                    )
                await asyncio.sleep(5)

            raise TimeoutError(f"Deploy {deploy_id} did not become ready within 150s")

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
