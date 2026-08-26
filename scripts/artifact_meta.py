"""Shared `_meta` stamping for published validation artifacts (#328).

Every JSON under docs-site/static/data/ is served publicly and read by the
model card, but only 4 of 21 carried any timestamp — so a reader could not
tell whether a reported correlation came from this week's data or from
March, and a "last refreshed" column could not be built at all.

Generators should build their `_meta` through `stamped_meta` so the field is
present by construction rather than by remembering.

    from artifact_meta import stamped_meta
    result = {"organs": {}, "_meta": stamped_meta(
        script="scripts/run-coverage-audit.py",
        method="...",
    )}
"""
from datetime import datetime, timezone


def utc_now() -> str:
    """ISO-8601 UTC timestamp, second resolution, matching existing artifacts."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamped_meta(**fields) -> dict:
    """`_meta` dict carrying a `generated` timestamp plus whatever is passed.

    An explicit `generated` in *fields* wins, so a caller that already
    computes one (or is replaying a historical run) is not overwritten.
    """
    meta = {"generated": utc_now()}
    meta.update(fields)
    return meta
