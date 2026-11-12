"""Explicit synthetic data, isolated from live databases by Settings validation."""

from datetime import timedelta

from app.core.config import get_settings
from app.db.session import Session
from app.models.entities import utcnow
from app.repositories.ingestion import record_snapshot, upsert_repository
from app.services.scoring import score_all


async def seed_demo():
    if not get_settings().demo_mode:
        raise RuntimeError(
            "Refusing to seed: DEMO_MODE=true and a separate '*demo*' database are required"
        )
    now = utcnow().replace(minute=0, second=0, microsecond=0)
    specifications = [
        (
            "fixture-agent-kit",
            "Synthetic fixture: composable agent tools",
            "Python",
            "ai-agents",
            800,
            9,
        ),
        (
            "fixture-query-engine",
            "Synthetic fixture: an analytical query engine",
            "Rust",
            "database",
            1800,
            15,
        ),
        (
            "fixture-dev-console",
            "Synthetic fixture: a developer workspace",
            "TypeScript",
            "developer-tools",
            400,
            5,
        ),
        (
            "fixture-vector-lab",
            "Synthetic fixture: vector search experiments",
            "Python",
            "machine-learning",
            300,
            4,
        ),
        (
            "fixture-edge-runtime",
            "Synthetic fixture: distributed edge workloads",
            "Go",
            "distributed-systems",
            1200,
            8,
        ),
        (
            "fixture-security-scan",
            "Synthetic fixture: dependency inspection",
            "Rust",
            "security",
            90,
            2,
        ),
        (
            "fixture-ui-system",
            "Synthetic fixture: web interface primitives",
            "TypeScript",
            "web",
            250,
            3,
        ),
        (
            "fixture-data-flow",
            "Synthetic fixture: stream processing",
            "Python",
            "data-engineering",
            500,
            5,
        ),
        (
            "fixture-lang-tools",
            "Synthetic fixture: language tooling",
            "Rust",
            "programming-language",
            75,
            1,
        ),
        (
            "fixture-community-kit",
            "Synthetic fixture: open-source project tooling",
            "Go",
            "open-source",
            150,
            2,
        ),
        (
            "fixture-new-project",
            "Synthetic fixture: a new project with only a baseline",
            "Python",
            "developer-tools",
            55,
            0,
        ),
    ]
    async with Session() as session:
        for index, (name, description, language, topic, base, growth) in enumerate(specifications):
            data = {
                "id": 900000000000 + index,
                "owner": {"login": "codepulse-demo"},
                "name": name,
                "full_name": f"codepulse-demo/{name}",
                "description": description,
                "language": language,
                "topics": [topic, "synthetic-fixture"],
                "created_at": (now - timedelta(days=120)).isoformat(),
                "pushed_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "stargazers_count": base + growth * 140,
                "forks_count": base // 10,
                "open_issues_count": index + 1,
                "default_branch": "main",
                "license": {"spdx_id": "MIT"},
                "private": False,
            }
            repo, _ = await upsert_repository(session, data, now)
            for step in range(129 if growth else 1):
                observed = now - timedelta(hours=6 * (128 - step)) if growth else now
                repo.stars = base + growth * step + (max(0, step - 110) ** 2 // 3 if growth else 0)
                repo.forks = base // 10 + step // 4
                await record_snapshot(session, repo, observed, 6, "synthetic_demo_fixture")
        await session.commit()
    await score_all(Session)
    print("Seeded explicitly labeled synthetic demo fixtures in the isolated demo database")
