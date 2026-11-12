# Architecture decisions

CodePulse is a Next.js client and a modular FastAPI service backed by PostgreSQL. Celery worker and Beat run the same Python package. Redis is the broker and shared rate-limit/locking store. PostgreSQL remains authoritative for metadata, immutable observations, score history, jobs and anonymous workspace watchlists.

Repository identity is GitHub's immutable numeric ID. Discovery uses rotating topic, age and star windows; tracking uses configurable priority cadences. Upserts and unique observation buckets make retries safe. Serial budgeted collection, Redis locks, shared cooldowns and finite retries prevent overlapping collectors and retry storms. Optional activity signals remain nullable.

Analytics is a pure Python package: no database, network, or wall-clock dependencies. A boundary observation must be at or before the target window boundary, within a bounded tolerance; endpoint freshness and interior gaps are checked. Rates use actual elapsed timestamps. An observation first establishes a baseline; an early heuristic is explicitly distinct from observed momentum. Score records retain inputs, contributions, missing features, confidence and model version.

API reads use async SQLAlchemy sessions. Query construction lives in the data-access layer; orchestration lives in services. Browser requests go through a same-origin Next.js proxy. API read and watchlist access is anonymous and intended for a trusted single-user deployment. A random local browser workspace identifies watchlists but is not authentication. No ingestion trigger is exposed over HTTP; operator commands and scheduled workers own ingestion.

The UI has no generated production metrics. Missing history, unconfigured ingestion and failures are visible states. Demo data, when explicitly enabled, lives in a separate database and is labeled throughout the API/UI.
