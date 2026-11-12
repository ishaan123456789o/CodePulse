"""Budget-bounded optional activity; a partial page sequence is never a total."""

from datetime import timedelta
from urllib.parse import quote

from app.github.client import GitHubClient, GitHubError
from app.models.entities import Repository, utcnow


async def enrich_activity(client: GitHubClient, repo: Repository) -> bool:
    if client.remaining < 2:
        return False
    now = utcnow()
    authors: set[str] = set()
    count, unknown_author = 0, False
    try:
        for page in range(1, 3):
            result = await client.get(
                f"/repos/{quote(repo.owner, safe='')}/{quote(repo.name, safe='')}/commits",
                params={
                    "since": (now - timedelta(days=7)).isoformat(),
                    "until": now.isoformat(),
                    "per_page": 100,
                    "page": page,
                },
            )
            if not isinstance(result.data, list):
                return False
            count += len(result.data)
            for commit in result.data:
                login = (commit.get("author") or {}).get("login")
                if login:
                    authors.add(login)
                else:
                    unknown_author = True
            if not result.has_next:
                repo.commits_7d = count
                repo.contributors = None if unknown_author else len(authors)
                repo.activity_fetched_at = now
                return True
    except GitHubError:
        # Metadata and past valid optional signals survive noncritical endpoint failure.
        return False
    return False
