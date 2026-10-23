"""Historical significance entry point disabled pending benchmark preservation.

The superseded implementation remains in git history (19b52b1). It refitted
models under an incompatible inference protocol and must not be executed.
"""
from __future__ import annotations


def main() -> None:
    """Stop without reading inputs, fitting models, or writing results."""
    raise SystemExit(
        "BLOCKED: benchmark preservation failed. Historical significance is disabled. "
        "See results/README.md and results/preservation_check.json. "
        "Resolve predictive drift before implementing/running the Step 1 protocol."
    )


if __name__ == "__main__":
    main()
