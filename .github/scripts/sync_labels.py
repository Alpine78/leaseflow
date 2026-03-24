"""Sync GitHub labels from .github/labels.json."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from urllib.parse import quote


def gh_api(*args: str) -> str:
    result = subprocess.run(
        ["gh", "api", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def is_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    labels_path = Path(".github/labels.json")
    desired_labels = json.loads(labels_path.read_text(encoding="utf-8"))
    desired_names = {label["name"] for label in desired_labels}
    delete_stale_labels = is_enabled(os.environ.get("DELETE_STALE_LABELS"))

    existing_labels = json.loads(gh_api(f"repos/{repo}/labels?per_page=100"))
    existing_by_name = {label["name"]: label for label in existing_labels}

    for label in desired_labels:
        name = label["name"]
        color = label["color"]
        description = label["description"]

        current = existing_by_name.get(name)
        if current is None:
            gh_api(
                "-X",
                "POST",
                f"repos/{repo}/labels",
                "-f",
                f"name={name}",
                "-f",
                f"color={color}",
                "-f",
                f"description={description}",
            )
            print(f"created {name}")
            continue

        current_color = current.get("color", "").upper()
        current_description = current.get("description") or ""
        if current_color == color and current_description == description:
            print(f"unchanged {name}")
            continue

        gh_api(
            "-X",
            "PATCH",
            f"repos/{repo}/labels/{quote(name, safe='')}",
            "-f",
            f"new_name={name}",
            "-f",
            f"color={color}",
            "-f",
            f"description={description}",
        )
        print(f"updated {name}")

    if not delete_stale_labels:
        print("strict mode disabled; stale labels were not deleted")
        return

    stale_label_names = sorted(set(existing_by_name) - desired_names)
    for name in stale_label_names:
        gh_api(
            "-X",
            "DELETE",
            f"repos/{repo}/labels/{quote(name, safe='')}",
        )
        print(f"deleted {name}")


if __name__ == "__main__":
    main()
