from datetime import datetime, timedelta

CATEGORIES = {
    "machine-learning": "Artificial Intelligence / Machine Learning",
    "ai-agents": "AI Agents",
    "developer-tools": "Developer Tools",
    "database": "Databases",
    "distributed-systems": "Infrastructure / Distributed Systems",
    "security": "Security",
    "web": "Web Development",
    "data-engineering": "Data Engineering",
    "programming-language": "Programming Languages",
    "open-source": "General Open Source",
}


def discovery_queries(now: datetime, rotation: int, topics: list[str]) -> list[tuple[str, str]]:
    windows = [
        f"created:>={(now - timedelta(days=30)).date()} stars:10..2000",
        f"created:{(now - timedelta(days=365)).date()}..{(now - timedelta(days=30)).date()} stars:50..10000",
        f"created:<{(now - timedelta(days=365)).date()} stars:100..30000",
    ]
    recent = (now - timedelta(days=30)).date()
    return [
        (
            f"topic:{topic} {windows[(rotation + i) % 3]} pushed:>={recent} archived:false fork:false",
            CATEGORIES.get(topic, "General Open Source"),
        )
        for i in range(len(topics))
        for topic in [topics[(i + rotation) % len(topics)]]
    ]


def classify(topics: list[str], fallback: str = "General Open Source") -> str:
    return next((CATEGORIES[t] for t in topics if t in CATEGORIES), fallback)
