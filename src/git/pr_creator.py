"""GitHub pull request creation via the REST API."""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from urllib.parse import urlparse


def _parse_owner_repo(remote_url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub remote URL."""
    path = urlparse(remote_url).path.lstrip("/")
    path = re.sub(r"\.git$", "", path)
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from URL: {remote_url}")
    return parts[0], parts[1]


def create_pull_request(
    remote_url: str,
    token: str,
    head_branch: str,
    base_branch: str,
    title: str,
    body: str,
) -> str:
    """Create a GitHub pull request and return its HTML URL.

    Args:
        remote_url: HTTPS URL of the GitHub repository (e.g. ``https://github.com/owner/repo.git``).
        token: Personal access token with ``repo`` scope.
        head_branch: The branch containing the changes.
        base_branch: The branch to merge into (e.g. ``main``).
        title: Pull request title.
        body: Pull request description (Markdown supported).

    Returns:
        The ``html_url`` of the created pull request.
    """
    owner, repo = _parse_owner_repo(remote_url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    payload = json.dumps(
        {"title": title, "head": head_branch, "base": base_branch, "body": body}
    ).encode()

    req = urllib.request.Request(api_url, data=payload, method="POST")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API error {exc.code}: {detail}") from exc

    return result["html_url"]
