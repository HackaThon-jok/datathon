"""Verified local version switching and rollback; no AWS operations."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from analytics.contracts import verify_run


def publish(output_root, run_dir, action="publish"):
    root = Path(output_root).resolve()
    folder = Path(run_dir).resolve()
    if folder.parent != root / "runs":
        raise ValueError("Run must belong to this output root")
    report = verify_run(folder)
    if report["run_id"] != folder.name:
        raise ValueError("Run ID does not match run directory")
    pointer = root / "published.json"
    previous = json.loads(pointer.read_text()) if pointer.exists() else None
    value = dict(run_id=report["run_id"], path=str(folder))
    event = dict(
        action=action,
        time_utc=datetime.now(timezone.utc).isoformat(),
        previous=previous,
        current=value,
    )
    # Single-writer local demo: immutable event evidence precedes atomic pointer replacement.
    history = root / "release-history"
    history.mkdir(exist_ok=True)
    import uuid

    (history / (uuid.uuid4().hex + ".json")).write_text(
        json.dumps(event, indent=2) + "\n"
    )
    temp = root / (".pointer-" + report["run_id"] + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(pointer)
    return event


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", default="artifacts/analytics")
    p.add_argument("--run-id", required=True)
    args = p.parse_args()
    if Path(args.run_id).name != args.run_id:
        raise ValueError("Use a run ID, not a path")
    event = publish(
        args.output, Path(args.output) / "runs" / args.run_id, action="rollback"
    )
    print(json.dumps(event, indent=2))


if __name__ == "__main__":
    main()
