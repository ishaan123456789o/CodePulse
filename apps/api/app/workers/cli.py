import argparse
import asyncio

from app.workers.tasks import run


def main():
    parser = argparse.ArgumentParser(
        description="CodePulse operator commands (no public ingestion endpoint)"
    )
    parser.add_argument(
        "command", choices=["discover", "track", "score", "recover", "forecast", "demo"]
    )
    args = parser.parse_args()
    if args.command == "demo":
        from app.services.demo import seed_demo

        asyncio.run(seed_demo())
    else:
        print(asyncio.run(asyncio.wait_for(run(args.command), timeout=3200)))


if __name__ == "__main__":
    main()
