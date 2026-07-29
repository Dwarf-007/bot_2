from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:

    path = Path(sys.argv[1])

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    discovered = set(
        data.get(
            "discovered_rooms",
            []
        )
    )

    ordered = data.get(
        "discovery_order",
        []
    )

    print(
        f"discovered_rooms={len(discovered)}"
    )

    print(
        f"discovery_order={len(ordered)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())