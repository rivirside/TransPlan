#!/usr/bin/env python3
"""Backfill `_meta.generated` on published artifacts that never carried one (#328).

Only 4 of 21 JSONs under docs-site/static/data/ recorded when they were
produced, so the model card cannot show a uniform "last refreshed" column and
a reader cannot tell whether a reported number reflects current data.

Re-running every generator purely to obtain a timestamp would be dishonest
about cost and precision — several are MCMC fits that take tens of minutes,
and re-running them would produce NEW numbers, not date the existing ones.
Instead this dates each file by the commit that last touched it, which is
exactly "when this artifact last changed", and labels it as such so nobody
mistakes a backfilled date for a recorded run time.

Idempotent: files that already carry `_meta.generated` are left alone.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
DATA_DIR = REPO / "docs-site" / "static" / "data"
BACKFILL_NOTE = ("git-commit-date — backfilled by "
                 "scripts/backfill-artifact-meta.py (#328); this generator "
                 "did not stamp its own output, so this is when the file last "
                 "changed, not a recorded run time")


def last_commit_date(path: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", str(path)],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return None
    if not out:
        return None
    # %cI is ISO-8601 with an offset; convert to the UTC "Z" form the other
    # artifacts already use so the model card can sort them as plain strings.
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(out).astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return out


def existing_timestamp(doc: dict) -> str | None:
    """Some artifacts stamp at top level rather than under _meta."""
    if not isinstance(doc, dict):
        return None
    meta = doc.get("_meta")
    if isinstance(meta, dict):
        for key in ("generated", "generated_at", "fetchedAt"):
            if meta.get(key):
                return meta[key]
    for key in ("generated_at", "generated", "fetchedAt"):
        if doc.get(key):
            return doc[key]
    return None


def main() -> int:
    if not DATA_DIR.is_dir():
        print(f"no such directory: {DATA_DIR}", file=sys.stderr)
        return 1

    stamped, already, skipped = [], [], []
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            print(f"SKIP {path.name}: {e}", file=sys.stderr)
            skipped.append(path.name)
            continue
        if not isinstance(doc, dict):
            skipped.append(path.name)
            continue

        found = existing_timestamp(doc)
        if found:
            # Lift a top-level stamp into _meta so consumers have one place
            # to look, but never overwrite a real recorded time.
            meta = doc.setdefault("_meta", {})
            if not meta.get("generated"):
                meta["generated"] = found
                path.write_text(json.dumps(doc, indent=1) + "\n")
                stamped.append(f"{path.name} (lifted from top level)")
            else:
                already.append(path.name)
            continue

        date = last_commit_date(path)
        if not date:
            print(f"SKIP {path.name}: no git history", file=sys.stderr)
            skipped.append(path.name)
            continue

        meta = doc.setdefault("_meta", {})
        meta["generated"] = date
        meta["generated_source"] = BACKFILL_NOTE
        path.write_text(json.dumps(doc, indent=1) + "\n")
        stamped.append(path.name)

    for name in stamped:
        print(f"stamped   {name}")
    print(f"\n{len(stamped)} stamped, {len(already)} already had one, "
          f"{len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
